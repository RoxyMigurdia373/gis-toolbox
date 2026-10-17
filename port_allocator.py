"""线程安全的应用内端口预留表；服务启动仍检查跨进程抢占。"""
import socket
import threading


class PortAllocator:
    def __init__(self, base_port=8501, max_port=8600):
        if not 1 <= base_port <= max_port <= 65535:
            raise ValueError("端口范围无效")
        self.base_port, self.max_port = base_port, max_port
        self._occupied = set()
        self._lock = threading.Lock()

    def allocate(self, preferred=None, excluded=()) -> int:
        candidates = list(range(self.base_port, self.max_port + 1))
        if preferred in candidates:
            candidates.remove(preferred)
            candidates.insert(0, preferred)
        with self._lock:
            for port in candidates:
                if port in self._occupied or port in excluded:
                    continue
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    try:
                        probe.bind(("127.0.0.1", port))
                    except OSError:
                        continue
                self._occupied.add(port)
                return port
        raise RuntimeError(f"{self.base_port}–{self.max_port} 端口已用完，请关闭部分工具或其他占用端口的程序。")

    def release(self, port):
        with self._lock:
            self._occupied.discard(port)
