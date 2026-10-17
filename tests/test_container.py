"""容器关键契约：端口冲突、manifest 隔离、真实服务生命周期。"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest
from urllib.request import build_opener, ProxyHandler

from manifest_loader import load_manifests
from port_allocator import PortAllocator
from resource_utils import resource_path, SingleInstanceLock
from tool_manager import ToolManager


class Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class FakeWindow:
    def __init__(self, title, url):
        self.title, self.url = title, url
        self.events = type('Events', (), {'closed': Event()})()
        self.destroyed = False

    def destroy(self):
        self.destroyed = True
        return_values = set()
        for handler in self.events.closed.handlers:
            return_values.add(handler())  # 与 pywebview Event 的返回值约束保持一致

    def restore(self):
        pass

    def show(self):
        pass


class FakeWebview:
    def __init__(self):
        self.windows = []

    def create_window(self, title, url, **kwargs):
        window = FakeWindow(title, url)
        self.windows.append(window)
        return window


class ContainerTests(unittest.TestCase):
    def test_allocator_skips_real_occupied_port_and_reserves_concurrently(self):
        with socket.socket() as busy:
            busy.bind(('127.0.0.1', 0))
            occupied = busy.getsockname()[1]
            allocator = PortAllocator(occupied, min(occupied + 20, 65535))
            with ThreadPoolExecutor(max_workers=4) as pool:
                selected = list(pool.map(lambda _: allocator.allocate(occupied), range(4)))
            self.assertEqual(len(set(selected)), 4)
            self.assertNotIn(occupied, selected)
            allocator.release(selected[0])
            self.assertEqual(allocator.allocate(selected[0]), selected[0])

    def test_allocator_exhaustion(self):
        with socket.socket() as busy:
            busy.bind(('127.0.0.1', 0))
            port = busy.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError, '端口已用完'):
                PortAllocator(port, port).allocate()

    def test_manifests_skip_bad_and_escaping_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key in ('good', 'bad', 'escape', 'array'):
                folder = root / 'tools' / key
                folder.mkdir(parents=True)
                (folder / 'app.py').write_text('pass', encoding='utf-8')
                (folder / 'icon.png').write_bytes(b'png')
                data = dict(id=key, name=key, description='desc', type='streamlit', entry='app.py',
                            icon='icon.png', port_preference=8501, working_dir=f'tools/{key}')
                if key == 'bad':
                    del data['name']
                if key == 'escape':
                    data['entry'] = '../../outside.py'
                if key == 'array':
                    data = []
                (folder / 'manifest.json').write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(list(load_manifests(root)), ['good'])

    def test_single_instance_lock_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            first = SingleInstanceLock(Path(folder) / '.lock')
            second = SingleInstanceLock(Path(folder) / '.lock')
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()

    def test_static_tool_is_local_without_process_or_port(self):
        manager = ToolManager(load_manifests(), {}, FakeWebview())
        try:
            result = manager.open_tool('coordinate_converter')
            self.assertTrue(result['ok'], result)
            record = manager.running_tools['coordinate_converter']
            self.assertTrue(record.window.url.startswith('file:///'))
            self.assertIsNone(record.process)
            self.assertIsNone(record.port)
            self.assertTrue(manager.open_tool('coordinate_converter')['ok'])
            self.assertEqual(len(manager.webview.windows), 1)
            manager.close_tool('coordinate_converter')
            self.assertTrue(record.window.destroyed)
        finally:
            manager.quit_all()

    def test_real_services_parallel_duplicate_close_and_crash(self):
        tools = load_manifests()
        tools = {key: value for key, value in tools.items() if value.type == 'streamlit'}
        self.assertEqual(set(tools), {'farmland_context', 'split_by_size', 'shp_to_kml'})
        view = FakeWebview()
        manager = ToolManager(tools, dict(startup_timeout=30), view)
        try:
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(manager.open_tool, tools))
            self.assertTrue(all(item['ok'] for item in results), results)
            records = dict(manager.running_tools)
            self.assertEqual(len({record.port for record in records.values()}), 3)
            self.assertTrue(all(record.process.is_alive() for record in records.values()))
            opener = build_opener(ProxyHandler({}))
            for record in records.values():
                with opener.open(f'http://127.0.0.1:{record.port}/_stcore/health', timeout=2) as response:
                    self.assertEqual(response.read(), b'ok')
            self.assertTrue(manager.open_tool('farmland_context')['ok'])
            self.assertEqual(len(view.windows), 3)
            records['farmland_context'].window.destroy()
            self.assertNotIn('farmland_context', manager.running_tools)
            self.assertFalse(records['farmland_context'].process.is_alive())
            self.assertTrue(records['split_by_size'].process.is_alive())
            records['split_by_size'].process.terminate()
            records['split_by_size'].process.join(timeout=3)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and 'split_by_size' in manager.running_tools:
                time.sleep(0.1)
            self.assertEqual(manager.states()['split_by_size']['status'], 'error')
            self.assertTrue(records['shp_to_kml'].process.is_alive())
        finally:
            manager.quit_all()
        self.assertFalse(manager.running_tools)
        for record in records.values():
            self.assertFalse(record.process.is_alive())
            self.assertFalse(record.scratch.exists())


if __name__ == '__main__':
    unittest.main()
