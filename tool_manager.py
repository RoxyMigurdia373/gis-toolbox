"""独立 Streamlit 进程、原生窗口和退出回收。

仅服务使用 multiprocessing；后台线程只等待启动、收集状态和发出退出信号。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
from urllib.request import build_opener, ProxyHandler

from logger import LogStream, setup_logging
from port_allocator import PortAllocator
from process_job import ProcessJob
from resource_utils import find_ogr2ogr, temp_dir, user_data_dir

LOG = logging.getLogger(__name__)


def _run_streamlit(tool_dir, entry, port, log_dir, scratch, ready, stop):
    """spawn 可导入的顶层入口，打包后仍由同一个 exe 运行。"""
    os.chdir(tool_dir)
    sys.path.insert(0, tool_dir)
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    # 先缓存与父进程一致的用户目录，再重定向本工具的 TEMP；
    # APPDATA 不可写时也不能把 Streamlit 配置误放进本次 scratch。
    user_data_dir()
    os.environ["TMP"] = os.environ["TEMP"] = scratch
    tempfile.tempdir = scratch
    setup_logging(Path(tool_dir).name, log_dir)
    sys.stdout, sys.stderr = LogStream(), LogStream(logging.ERROR)
    try:
        import streamlit.file_util
        # Streamlit 1.40 没有独立用户目录配置，集中重定向其写入路径。
        streamlit_data = user_data_dir() / "streamlit"
        streamlit_data.mkdir(parents=True, exist_ok=True)
        streamlit.file_util.get_streamlit_file_path = lambda *parts: str(streamlit_data.joinpath(*parts))
        from streamlit.runtime import Runtime, RuntimeState

        def lifecycle():
            # 管道不持有跨进程的 Python 锁；即使服务被强杀，父进程也不会
            # 在 multiprocessing.Event.set() 上因遗留锁永久挂起。
            while not stop.poll(0.1):
                if Runtime.exists() and Runtime.instance().state in (
                        RuntimeState.NO_SESSIONS_CONNECTED, RuntimeState.ONE_OR_MORE_SESSIONS_CONNECTED):
                    ready.send_bytes(b'ready')
                    ready.close()
                    while not stop.poll(0.1):
                        pass
                    break
            if Runtime.exists():
                try:
                    Runtime.instance().stop()  # 官方线程安全的停止接口
                except RuntimeError:
                    LOG.exception("服务尚未完成初始化，将由父进程回收")

        threading.Thread(target=lifecycle, name="service-lifecycle", daemon=True).start()
        sys.argv = ["streamlit", "run", entry, f"--server.port={port}",
                    "--server.address=127.0.0.1", "--server.headless=true",
                    "--server.fileWatcherType=none", "--global.developmentMode=false",
                    "--browser.gatherUsageStats=false", "--server.enableCORS=true",
                    "--server.enableXsrfProtection=true"]
        import streamlit.web.cli as stcli
        stcli.main()
    except SystemExit:
        raise
    except BaseException:
        LOG.exception("Streamlit 启动或运行失败")
        raise


@dataclass
class RunningTool:
    process: object = None
    port: int | None = None
    window: object = None
    job: object = None
    stop: object = None
    ready: object = None
    scratch: Path | None = None
    status: str = "starting"
    cancel: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    closed: threading.Event = field(default_factory=threading.Event)
    stop_lock: threading.Lock = field(default_factory=threading.Lock)


class ToolManager:
    def __init__(self, manifests, config, webview_module=None):
        self.tools = manifests
        self.config = config
        self.running_tools: dict[str, RunningTool] = {}
        self.errors = {}
        self.notices = {}
        self.ports = PortAllocator(config.get("base_port", 8501), config.get("max_port", 8600))
        self._lock = threading.RLock()
        self._closing = False
        self._context = mp.get_context("spawn")
        self._webview = webview_module
        self._monitor_stop = threading.Event()
        self._monitor = threading.Thread(target=self._watch_processes, name="tool-monitor", daemon=True)
        self._monitor.start()

    @property
    def webview(self):
        if self._webview is None:
            import webview
            self._webview = webview
        return self._webview

    def states(self):
        with self._lock:
            return {tool_id: {"status": self.running_tools[tool_id].status if tool_id in self.running_tools
                             else ("error" if tool_id in self.errors else "closed"),
                             "error": self.errors.get(tool_id, ""), "notice": self.notices.get(tool_id, "")}
                    for tool_id in self.tools}

    def open_tool(self, tool_id):
        with self._lock:
            if self._closing:
                return {"ok": False, "error": "应用正在退出"}
            if tool_id not in self.tools:
                return {"ok": False, "error": "未找到该工具"}
            existing = self.running_tools.get(tool_id)
            if not existing:
                record = RunningTool()
                self.running_tools[tool_id] = record
                self.errors.pop(tool_id, None)
                self.notices.pop(tool_id, None)
        if existing:
            if existing.window and existing.status == "running":
                try:
                    existing.window.restore()
                    existing.window.show()
                except Exception:
                    LOG.exception("聚焦工具窗口失败：%s", tool_id)
            return {"ok": True, "status": existing.status}
        try:
            tool = self.tools[tool_id]
            if not tool.entry.is_file():
                raise FileNotFoundError(f"工具入口不存在：{tool.entry.name}")
            if tool.type == "streamlit":
                self.open_streamlit_tool(tool_id, record)
            else:
                self.open_static_tool(tool_id, record)
            return {"ok": True, "notice": self.notices.get(tool_id, "")}
        except Exception as exc:
            LOG.exception("打开工具失败：%s", tool_id)
            if not record.cancel.is_set():
                with self._lock:
                    self.errors[tool_id] = str(exc)
            self.close_tool(tool_id, expected=record)
            return {"ok": False, "error": str(exc)}
        finally:
            record.finished.set()

    def _create_window(self, tool_id, record, url):
        with self._lock:
            if self._closing or record.cancel.is_set():
                raise RuntimeError("工具启动已取消")
        # 不持有状态锁调用 GUI，避免同步窗口事件造成死锁。
        window = self.webview.create_window(self.tools[tool_id].name, url=url,
                                            width=self.config.get("tool_width", 1280),
                                            height=self.config.get("tool_height", 880),
                                            min_size=(800, 560), background_color="#FFFFFF")
        def on_closed():
            # pywebview 事件将返回值放入 set；不能返回 API 的 dict 响应。
            self.close_tool(tool_id, destroy_window=False, expected=record)

        window.events.closed += on_closed
        with self._lock:
            cancelled = self._closing or record.cancel.is_set()
            if not cancelled:
                record.window = window
                record.status = "running"
        if cancelled:
            window.destroy()
            raise RuntimeError("工具启动已取消")

    def open_static_tool(self, tool_id, record):
        # file URI 不触发 pywebview 内置 HTTP 服务，不占用端口。
        self._create_window(tool_id, record, self.tools[tool_id].entry.as_uri())

    def open_streamlit_tool(self, tool_id, record):
        tool = self.tools[tool_id]
        if tool.requires_ogr2ogr and not find_ogr2ogr():
            notice = "未检测到 ogr2ogr，将自动使用 Fiona + PyProj 转换，工具可正常使用。"
            with self._lock:
                self.notices[tool_id] = notice
            LOG.info("%s：%s", tool_id, notice)
        deadline = time.monotonic() + self.config.get("startup_timeout", 30)
        excluded = set()
        # 端口探测与子进程 bind 间存在 OS 级竞争，失败后换端口重试。
        for attempt in range(3):
            with self._lock:
                if record.cancel.is_set() or self._closing:
                    raise RuntimeError("工具启动已取消")
                record.port = self.ports.allocate(tool.port_preference, excluded)
                port = record.port
                record.scratch = Path(tempfile.mkdtemp(prefix=f"{tool_id}-", dir=temp_dir()))
                ready, ready_sender = self._context.Pipe(duplex=False)
                stop_receiver, record.stop = self._context.Pipe(duplex=False)
                record.ready = ready
                process = self._context.Process(target=_run_streamlit,
                    args=(str(tool.directory), str(tool.entry), port, str(user_data_dir() / "logs"),
                          str(record.scratch), ready_sender, stop_receiver), name=f"GIS-{tool_id}", daemon=True)
                record.process = process
                process.start()
                ready_sender.close()
                stop_receiver.close()
                try:
                    record.job = ProcessJob(process.pid)
                except OSError:
                    LOG.exception("Windows Job 绑定失败，仍使用进程退出与超时回收")
            opener = build_opener(ProxyHandler({}))  # localhost 不经过公司代理
            while time.monotonic() < deadline and not record.cancel.wait(0.1):
                if not process.is_alive():
                    break
                if ready.poll():
                    try:
                        with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=0.5) as response:
                            healthy = response.status == 200 and response.read(32).strip() == b"ok"
                        if healthy and process.is_alive():
                            LOG.info("工具就绪 %s pid=%s port=%s", tool_id, process.pid, port)
                            self._create_window(tool_id, record, f"http://127.0.0.1:{port}")
                            return
                    except OSError:
                        pass
            if record.cancel.is_set():
                raise RuntimeError("工具启动已取消")
            if not process.is_alive():
                with socket.socket() as probe:
                    probe.settimeout(0.2)
                    occupied = probe.connect_ex(("127.0.0.1", port)) == 0
                if occupied and attempt < 2:
                    with self._lock:
                        if record.cancel.is_set():
                            raise RuntimeError("工具启动已取消")
                        self._dispose_process(record)
                        self.ports.release(port)
                        self._remove_scratch(record)
                    excluded.add(port)
                    continue
                raise RuntimeError(f"服务启动失败（退出码 {process.exitcode}），请查看 {tool_id}.log。")
            raise RuntimeError(f"服务在 {self.config.get('startup_timeout', 30)} 秒内未就绪，请查看 {tool_id}.log 后重试。")
        raise RuntimeError("端口被其他程序反复占用，请稍后重试。")

    @staticmethod
    def _request_stop(record):
        with record.stop_lock:
            connection = record.stop
            record.stop = None
        if connection:
            try:
                connection.send_bytes(b'stop')
            except (OSError, ValueError):
                pass  # 进程已退出或另一关闭线程已发送
            finally:
                connection.close()

    @staticmethod
    def _dispose_process(record):
        process = record.process
        ToolManager._request_stop(record)
        if process and process.pid:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
        if record.job:
            record.job.close()  # 清理尚存的 ogr2ogr 等后代
            record.job = None
        if record.ready:
            record.ready.close()
            record.ready = None

    @staticmethod
    def _remove_scratch(record):
        if record.scratch:
            target = record.scratch.resolve()
            if target.parent == temp_dir().resolve():
                try:
                    shutil.rmtree(target)
                except FileNotFoundError:
                    pass
                except OSError:
                    LOG.exception("临时目录暂未清理：%s", target)

    def close_tool(self, tool_id, destroy_window=True, expected=None):
        with self._lock:
            record = self.running_tools.get(tool_id)
            if record is None or (expected is not None and record is not expected):
                return {"ok": True}
            already_closing = record.status == "closing"
            if not already_closing:
                record.status = "closing"
                record.cancel.set()
            window = record.window
        if already_closing:
            # destroy() 触发的 closed 回调不能等待自身；主界面退出则等待回收。
            if destroy_window:
                record.closed.wait(timeout=8)
            return {"ok": True}
        try:
            self._dispose_process(record)
            if window and destroy_window:
                try:
                    window.destroy()
                except Exception:
                    LOG.exception("关闭窗口失败：%s", tool_id)
            self._remove_scratch(record)
        finally:
            self.ports.release(record.port)
            with self._lock:
                if self.running_tools.get(tool_id) is record:
                    self.running_tools.pop(tool_id)
            record.closed.set()
            LOG.info("工具已关闭：%s", tool_id)
        return {"ok": True}

    def _watch_processes(self):
        while not self._monitor_stop.wait(1):
            with self._lock:
                dead = [(key, value) for key, value in self.running_tools.items()
                        if value.status == "running" and value.process and not value.process.is_alive()]
                for key, value in dead:
                    self.errors[key] = f"服务意外退出（{value.process.exitcode}），可重新打开；详情见 {key}.log。"
            for key, record in dead:
                LOG.error("工具进程意外退出：%s", key)
                self.close_tool(key, expected=record)

    def quit_all(self):
        with self._lock:
            self._closing = True
            items = list(self.running_tools.items())
            for _, record in items:
                record.cancel.set()
                self._request_stop(record)
        self._monitor_stop.set()
        for key, record in items:
            self.close_tool(key, expected=record)
