"""Memory proyek ala koma MEMORY.md: konvensi yang menetap antar sesi.

File: usb-drive/data/memory.md (ditulis manual atau via catatan).
Hanya baris non-kosong ≤40 baris pertama yang disuntik ke konteks rencana
(hemat token, seperti koma hanya injeksikan indeks MEMORY.md).
Tanpa file = tanpa konteks tambahan, perilaku lama tak berubah.
"""
import os

MAX_LINES = 40


def _path():
    try:
        from _paths import writable as _wr
        return _wr("data", "memory.md")
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "data", "memory.md"))


def load_project_memory():
    try:
        with open(_path(), encoding="utf-8") as f:
            lines = [l.rstrip() for l in f
                     if l.strip() and not l.strip().startswith("#")][:MAX_LINES]
    except OSError:
        return ""
    if not lines:
        return ""
    return "Catatan proyek (memory.md):\n" + "\n".join("- " + l for l in lines)
