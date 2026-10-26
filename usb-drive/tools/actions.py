"""Tool kontrol komputer Windows. Stdlib + fitur bawaan OS saja, tanpa pip install."""
import ctypes
import os
import subprocess
import time
from datetime import datetime

ALLOW_APPS = {"notepad": "notepad.exe", "calc": "calc.exe", "kalkulator": "calc.exe",
              "word": "WINWORD.EXE", "excel": "EXCEL.EXE", "powerpoint": "POWERPNT.EXE",
              "discord": "Discord.exe", "whatsapp": "WhatsApp.Root.exe",
              "telegram": "Telegram.exe", "spotify": "Spotify.exe",
              "valorant": "RiotClientServices.exe"}


def _data_dir():
    try:
        from _paths import writable as _wr
        d = _wr("data")
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        d = os.path.normpath(os.path.join(here, "..", "data"))
    os.makedirs(d, exist_ok=True)
    return d


def screenshot():
    """Screenshot SELURUH virtual desktop (semua monitor). Return path."""
    out = os.path.join(_data_dir(),
                       "shot-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".png")
    ps = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
          "$v = [Windows.Forms.SystemInformation]::VirtualScreen;"
          "$b = New-Object Drawing.Bitmap($v.Width, $v.Height);"
          "$g = [Drawing.Graphics]::FromImage($b);"
          "$g.CopyFromScreen($v.X, $v.Y, 0, 0, $b.Size);$g.Dispose();"
          "$b.Save('%s');$b.Dispose()" % out.replace("'", "''"))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("screenshot gagal: " + (r.stderr or "unknown")[:200])
    return out


def open_app(app, emit=None):
    """Buka aplikasi via discovery (tanpa asumsi). emit(msg) untuk log natural."""
    from tools import discovery as _d
    key = (app or "").strip().lower()
    if key in ("chrome", "browser", "edge", "firefox"):
        raise ValueError("untuk browser pakai perintah 'buka browser', bukan nama aplikasi")

    def say(m):
        if emit:
            try:
                emit(m)
            except Exception:
                pass

    for state, msg, act in _d.states(key):
        say(msg)
        if state == "FAILED":
            raise ValueError(msg)
        if act is None:
            continue
        kind, target = act
        if kind == "focus":
            if not focus(target):
                raise RuntimeError("jendela '%s' tak ditemukan" % target)
            return "terbuka (sudah aktif)"
        _launch(target)
    exe = ALLOW_APPS[key]
    if not is_running(exe):
        raise RuntimeError("gagal membuka " + key)
    return "terbuka"


def _launch(key):
    """Luncurkan sesuai tabel discovery. Tunggu jendela, pulihkan bila zombie."""
    from tools import discovery as _d
    method, target, exe = _d.LAUNCH[key]
    if method == "path":
        p = subprocess.Popen([target])
        time.sleep(1.0)
        if p.poll() is not None and p.returncode != 0:
            raise RuntimeError("gagal membuka " + key)
        return
    if method == "cmd":
        if not is_running(exe):
            subprocess.Popen(target)
            time.sleep(4.0)
    else:
        if not is_running(exe):
            os.startfile(target)
            time.sleep(2.5)
        for _ in range(8):
            if _has_window(exe):
                return
            if not is_running(exe):
                os.startfile(target)
            time.sleep(1.0)
        if not _has_window(exe):
            subprocess.run(["taskkill", "/F", "/IM", exe],
                           capture_output=True, timeout=20)
            time.sleep(2.0)
            os.startfile(target)
            for _ in range(10):
                if _has_window(exe):
                    return
                time.sleep(1.0)
    if not is_running(exe):
        raise RuntimeError("gagal membuka " + key)


_LAST_HWND = None


def _bring(hwnd):
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    me = k.GetCurrentThreadId()
    fg = u.GetForegroundWindow()
    pid = ctypes.c_ulong()
    ft = u.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    attached = False
    if ft != me:
        attached = bool(u.AttachThreadInput(me, ft, True))
    u.ShowWindow(hwnd, 9)
    ok = bool(u.SetForegroundWindow(hwnd))
    if attached:
        u.AttachThreadInput(me, ft, False)
    time.sleep(0.3)
    return ok


def refocus_last():
    """Kembalikan fokus ke jendela terakhir. Best-effort, return bool."""
    try:
        return bool(_LAST_HWND) and _bring(_LAST_HWND)
    except (OSError, ValueError):
        return False


def type_text(text):
    if text is None:
        raise ValueError("teks kosong")
    refocus_last()
    safe = str(text).replace("{", "{{}").replace("}", "{}}")
    ps = ('$w = New-Object -ComObject WScript.Shell;'
          'Start-Sleep -m 800;'
          '$w.SendKeys("%s")' % safe.replace('"', '""'))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("mengetik gagal")
    return "terketik %d karakter" % len(str(text))


def click(x, y):
    try:
        xi, yi = int(x), int(y)
    except (TypeError, ValueError):
        raise ValueError("koordinat klik harus angka")
    u = ctypes.windll.user32
    vx, vy = u.GetSystemMetrics(76), u.GetSystemMetrics(77)
    vw, vh = u.GetSystemMetrics(78), u.GetSystemMetrics(79)
    if not (vx <= xi < vx + vw and vy <= yi < vy + vh):
        raise ValueError("koordinat di luar semua layar (%d,%d %dx%d)"
                         % (vx, vy, vw, vh))
    u.SetCursorPos(xi, yi)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    return "klik di (%d, %d)" % (xi, yi)

def open_url(url):
    u = (url or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValueError("URL harus http/https")
    os.startfile(u)
    return "terbuka di browser"


def hotkey(keys):
    """Tekan kombinasi tombol. Format SendKeys: ^n = Ctrl+N, %{F4} = Alt+F4."""
    k = (keys or "").strip()
    if not k or len(k) > 24:
        raise ValueError("kombinasi tombol kosong atau terlalu panjang")
    refocus_last()
    ps = ('$w = New-Object -ComObject WScript.Shell;'
          'Start-Sleep -m 800;'
          '$w.SendKeys("%s")' % k.replace('"', '""'))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError("hotkey gagal")
    return "tertekan %s" % k


BROWSERS = {"chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe"}


def _browser_path(exe):
    import shutil
    import winreg
    p = shutil.which(exe)
    if p:
        return p
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s" % exe) as k:
            return winreg.QueryValue(k, None) or ""
    except OSError:
        return ""


def open_browser(url="https://www.bing.com/", browser="", guest=False):
    """Buka URL di browser tertentu. browser: chrome|edge|firefox (kosong = default).
    guest=True: mode tamu (chrome/edge). Fallback ke default bila browser
    yang diminta tak terinstall (anti-stuck ala koma: jangan gagal keras)."""
    u = (url or "").strip() or "https://www.bing.com/"
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValueError("URL harus http/https")
    b = (browser or "").strip().lower()
    if b and b not in BROWSERS:
        raise ValueError("browser harus chrome|edge|firefox")
    if not b:
        os.startfile(u)
        return "terbuka di browser default"
    exe = BROWSERS[b]
    path = _browser_path(exe)
    if not path:
        # Fallback jujur: pakai default, beri tahu rencana berikutnya tetap jalan.
        try:
            os.startfile(u)
        except OSError:
            raise ValueError("browser %s tak terinstall" % b)
        return "terbuka di browser default (minta %s tak ada)" % b
    args = [path]
    if guest and b in ("chrome", "edge"):
        args.append("--guest")
    args.append(u)
    subprocess.Popen(args)
    time.sleep(1.5)
    return "terbuka di %s%s" % (b, " (guest)" if guest and b in ("chrome", "edge") else "")


def start_search(query):
    """Buka pencarian Start/taskbar lalu ketik query. Untuk cari app/file lokal."""
    q = (query or "").strip()
    if not q:
        raise ValueError("kata pencarian kosong")
    u = ctypes.windll.user32
    u.keybd_event(0x5B, 0, 0, 0)
    u.keybd_event(0x5B, 0, 2, 0)
    time.sleep(1.0)
    ps = ('$w = New-Object -ComObject WScript.Shell;'
          '$w.SendKeys("%s");Start-Sleep -m 900' % q.replace("{", "{{}").replace("}", "{}}").replace('"', '""'))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError("pencarian start gagal")
    return "mencari %s" % q


def wait(seconds=2):
    """Jeda N detik (maks 10) agar aplikasi selesai loading. LOW."""
    try:
        n = min(10, max(1, int(seconds)))
    except (TypeError, ValueError):
        raise ValueError("detik harus angka 1-10")
    time.sleep(n)
    return "tunggu %d detik" % n


def open_file(path):
    """Buka file dengan aplikasi default (misal .docx dengan Word)."""
    from tools import files as _f
    abs_p, _ = _f.resolve(path)
    if not os.path.exists(abs_p):
        raise FileNotFoundError("tidak ada: %s" % path)
    os.startfile(abs_p)
    time.sleep(1.5)
    return "terbuka"


def is_running(exe):
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + exe, "/FO", "CSV"],
                       capture_output=True, text=True, timeout=15)
    return exe.lower() in (r.stdout or "").lower()


def focus(title):
    """Aktifkan jendela via judul, fallback via nama process. Coba ~8 detik."""
    ps = ('$w = New-Object -ComObject WScript.Shell;'
          'if ($w.AppActivate("%s")) { Start-Sleep -m 500; exit 0 } else { exit 1 }'
          % title.replace('"', '""'))
    exe = ALLOW_APPS.get((title or "").strip().lower(), "")
    for _ in range(8):
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return True
        if exe and _focus_exe(exe):
            return True
        time.sleep(1.0)
    return False


def _exe_pids(exe):
    import csv
    import io
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + exe,
                            "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=15)
        pids = set()
        for row in csv.reader(io.StringIO(r.stdout or "")):
            if len(row) >= 2 and row[0].lower() == exe.lower():
                try:
                    pids.add(int(row[1]))
                except ValueError:
                    pass
        return pids
    except OSError:
        return set()


def _has_window(exe):
    """True jika ada jendela berjudul terlihat milik exe."""
    pids = _exe_pids(exe)
    if not pids:
        return False
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        try:
            if u.IsWindowVisible(hwnd) and u.GetWindowTextLengthW(hwnd) > 0:
                pid = ctypes.c_ulong()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids:
                    found.append(hwnd)
                    return False
        except (OSError, ValueError):
            pass
        return True

    try:
        u.EnumWindows(cb, None)
    except (OSError, ValueError):
        return False
    return bool(found)


def _focus_exe(exe):
    """SetForegroundWindow ke jendela berjudul pertama milik PID exe."""
    pids = _exe_pids(exe)
    if not pids:
        return False
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        try:
            if u.IsWindowVisible(hwnd) and u.GetWindowTextLengthW(hwnd) > 0:
                pid = ctypes.c_ulong()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids:
                    found.append(hwnd)
                    return False
        except (OSError, ValueError):
            pass
        return True

    try:
        u.EnumWindows(cb, None)
    except (OSError, ValueError):
        return False
    if not found:
        return False
    global _LAST_HWND
    _LAST_HWND = found[0]
    return _bring(found[0])
