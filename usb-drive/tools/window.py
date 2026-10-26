"""Kontrol jendela aplikasi Windows: selalu-di-depan + opacity.

Hanya bermakna di mode Desktop (JURU-Desktop.exe, jendela pywebview/WebView2
punya HWND). Mode browser tak bisa (tab tak punya handle) — pengaturan tetap
tersimpan dan diterapkan begitu Desktop jalan.
Implementasi ctypes user32 saja, tanpa pip install. Impor modul ini aman di
mana pun (windll diakses malas di dalam fungsi).
"""
import json
import os

TITLE = "JURU"
DEFAULTS = {"always_on_top": False, "opacity": 100}
MIN_OPACITY = 30


def _path():
    try:
        from _paths import writable as _wr
        return _wr("config", "ui.json")
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "config", "ui.json"))


def load():
    s = dict(DEFAULTS)
    try:
        with open(_path(), encoding="utf-8") as f:
            d = json.loads(f.read() or "{}")
        if isinstance(d.get("always_on_top"), bool):
            s["always_on_top"] = d["always_on_top"]
        o = d.get("opacity", 100)
        s["opacity"] = max(MIN_OPACITY, min(100, int(o)))
    except (OSError, ValueError, TypeError):
        pass
    return s


def save(patch):
    s = load()
    if isinstance(patch, dict):
        if isinstance(patch.get("always_on_top"), bool):
            s["always_on_top"] = patch["always_on_top"]
        if "opacity" in patch:
            try:
                s["opacity"] = max(MIN_OPACITY, min(100, int(patch["opacity"])))
            except (ValueError, TypeError):
                pass
    try:
        os.makedirs(os.path.dirname(_path()), exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            f.write(json.dumps(s))
    except OSError:
        pass
    return s


def _user32():
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    # Wajib: tanpa restype, handle 64-bit terpotong jadi 32-bit
    # (SetWindowPos diam-diam gagal pada handle palsu).
    u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.FindWindowW.restype = wintypes.HWND
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                               ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int,
                               ctypes.c_uint]
    u.SetWindowPos.restype = wintypes.BOOL
    u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetWindowTextW.restype = ctypes.c_int
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsWindowVisible.restype = wintypes.BOOL
    return u


def _hwnd():
    """Handle jendela JURU. None bila tak ada (misal mode browser)."""
    try:
        u = _user32()
    except (OSError, AttributeError):
        return None
    try:
        import ctypes
        h = u.FindWindowW(None, TITLE)
        if h:
            return h
        found = []
        buf = ctypes.create_unicode_buffer(256)

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(hwnd, _):
            try:
                if u.IsWindowVisible(hwnd) and u.GetWindowTextW(hwnd, buf, 256) > 0:
                    if buf.value == TITLE or buf.value.startswith(TITLE + " "):
                        found.append(hwnd)
                        return False
            except (OSError, ValueError):
                pass
            return True

        u.EnumWindows(cb, None)
        return found[0] if found else None
    except (OSError, ValueError):
        return None


def set_topmost(on):
    """Selalu-di-depan (Brave/browser lain tak menutupi). False = normal."""
    h = _hwnd()
    if not h:
        return False
    try:
        u = _user32()
        pos = -1 if on else -2  # HWND_TOPMOST / HWND_NOTOPMOST
        return bool(u.SetWindowPos(h, pos, 0, 0, 0, 0, 0x0001 | 0x0002))
    except (OSError, ValueError):
        return False


def set_opacity(pct):
    """Transparansi persen 30-100. 100 = solid penuh."""
    h = _hwnd()
    if not h:
        return False
    try:
        import ctypes
        u = _user32()
        GWL_EXSTYLE, WS_EX_LAYERED, LWA_ALPHA = -20, 0x80000, 0x2
        try:
            ex = u.GetWindowLongW(h, GWL_EXSTYLE)
            u.SetWindowLongW(h, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        except (OSError, ValueError):
            pass
        alpha = max(MIN_OPACITY, min(100, int(pct))) * 255 // 100
        return bool(u.SetLayeredWindowAttributes(h, 0, alpha, LWA_ALPHA))
    except (OSError, ValueError, TypeError):
        return False


def apply(settings=None):
    """Terapkan keduanya sekaligus. Return (top_ok, op_ok, settings)."""
    s = settings if isinstance(settings, dict) else load()
    return set_topmost(bool(s.get("always_on_top"))), \
        set_opacity(s.get("opacity", 100)), s


def diag():
    """Untuk baris log 'window: ...': handle + judul cocok 'juru'."""
    titles = []
    try:
        import ctypes
        u = _user32()
        buf = ctypes.create_unicode_buffer(256)

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(hwnd, _):
            try:
                if u.IsWindowVisible(hwnd) and u.GetWindowTextW(hwnd, buf, 256) > 0:
                    if "juru" in buf.value.lower():
                        titles.append(buf.value)
            except (OSError, ValueError):
                pass
            return True

        u.EnumWindows(cb, None)
    except (OSError, ValueError, AttributeError):
        pass
    return {"hwnd": _hwnd(), "titles": titles}
