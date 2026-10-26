"""Path root yang benar untuk mode script maupun EXE beku (PyInstaller).

EXE satu-file: data tulis (data/, config/.env) harus di sebelah JURU.exe,
bukan di _MEIPASS read-only. Frontend/config read-only boleh dari _MEIPASS.
"""
import os
import sys


def frozen():
    return bool(getattr(sys, "frozen", False))


def exe_dir():
    if frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(here)


def bundle_dir():
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    return exe_dir()


def resource(*parts):
    """File read-only: cari di bundle dulu, lalu di sebelah exe."""
    b = os.path.join(bundle_dir(), *parts)
    if os.path.exists(b):
        return b
    return os.path.join(exe_dir(), *parts)


def writable(*parts):
    """File tulis: selalu di sebelah exe (portable,anti-jejak sistem)."""
    return os.path.join(exe_dir(), *parts)
