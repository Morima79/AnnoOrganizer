"""Remember normal window bounds and restore reachable windows on Windows monitors."""
import ctypes
from ctypes import wintypes
import os


def work_areas(root):
    if os.name == 'nt':
        areas = []
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                        ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                           ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        user = ctypes.windll.user32
        user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        def visit(monitor, *_):
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            if user.GetMonitorInfoW(monitor, ctypes.byref(info)):
                rect = info.work
                areas.append((rect.left, rect.top, rect.right, rect.bottom))
            return True
        callback = callback_type(visit)
        user.EnumDisplayMonitors(None, None, callback, 0)
        if areas:
            return areas
    return [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]


def visible_bounds(saved, areas, minimum):
    if not areas or not isinstance(saved, dict) or not all(type(saved.get(key)) is int for key in ('x', 'y', 'width', 'height')):
        return None
    x, y, width, height = (saved[key] for key in ('x', 'y', 'width', 'height'))
    if width <= 0 or height <= 0:
        return None
    def distance(area):
        left, top, right, bottom = area
        return max(left - x, 0, x - (right - 1)) ** 2 + max(top - y, 0, y - (bottom - 1)) ** 2
    left, top, right, bottom = min(areas, key=distance)
    width = max(minimum[0], min(width, right - left - 16))
    height = max(minimum[1], min(height, bottom - top - 40))
    x = max(left, min(x, right - width - 16))
    y = max(top, min(y, bottom - height - 40))
    return dict(x=x, y=y, width=width, height=height,
                state='zoomed' if saved.get('state') == 'zoomed' else 'normal')


def place(window, x, y):
    if os.name == 'nt':
        user = ctypes.windll.user32
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT]
        handle = user.GetAncestor(window.winfo_id(), 2)
        if not user.SetWindowPos(handle, None, x, y, 0, 0, 0x0015):
            raise ctypes.WinError()
    else:
        window.geometry(f'{x:+d}{y:+d}')


class WindowState:
    def __init__(self, root, store):
        self.root, self.store = root, store
        self.windows = {}
        if not isinstance(store.preferences.get('windows', {}), dict):
            store.preferences['windows'] = {}

    def watch(self, window, key, *, owner=None):
        self.windows[key] = window
        saved = self.store.preferences.get('windows', {}).get(key)
        bounds = visible_bounds(saved, work_areas(self.root), window.minsize())
        window.update_idletasks()
        if bounds is not None:
            window.geometry(f"{bounds['width']}x{bounds['height']}")
            window.update_idletasks()
            place(window, bounds['x'], bounds['y'])
            if bounds['state'] == 'zoomed':
                window.state('zoomed')
        elif owner is not None:
            x = owner.winfo_x() + (owner.winfo_width() - window.winfo_reqwidth()) // 2
            y = owner.winfo_y() + (owner.winfo_height() - window.winfo_reqheight()) // 2
            bounds = visible_bounds(dict(x=x, y=y, width=window.winfo_reqwidth(),
                                         height=window.winfo_reqheight()), work_areas(self.root), window.minsize())
            place(window, bounds['x'], bounds['y'])
        window.bind('<Configure>', lambda event: self.remember(key) if event.widget is window else None, add='+')
        self.remember(key)

    def remember(self, key):
        window = self.windows.get(key)
        if window is None or not window.winfo_exists() or not window.winfo_ismapped():
            return
        states = self.store.preferences.setdefault('windows', {})
        if window.state() == 'normal':
            states[key] = dict(x=window.winfo_x(), y=window.winfo_y(), width=window.winfo_width(),
                               height=window.winfo_height(), state='normal')
        elif window.state() == 'zoomed' and key in states:
            states[key]['state'] = 'zoomed'

    def remember_all(self):
        for key in self.windows:
            self.remember(key)

    def close_child(self, key):
        self.remember_all()
        self.store.save_preferences()
        self.windows[key].destroy()
