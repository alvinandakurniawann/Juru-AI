"""Application Discovery Layer (§1-6): temukan DULU, eksekusi KEMUDIAN.

Urutan jujur (tanpa klaim deteksi pin taskbar/shortcut yang tak bisa
diverifikasi stdlib): jendela terlihat -> proses berjalan -> terinstall
(App Paths/protokol/perintah khusus) -> Start search -> online.
"""
from tools import actions

# Tabel DATA peluncuran (bukan logika cabang): nama -> (metode, target, exe).
# metode: path (Popen langsung) | start (App Paths/protokol) | cmd (perintah khusus).
LAUNCH = {
    "notepad": ("path", "notepad.exe", "notepad.exe"),
    "calc": ("path", "calc.exe", "calc.exe"),
    "kalkulator": ("path", "calc.exe", "calc.exe"),
    "word": ("start", "winword", "WINWORD.EXE"),
    "excel": ("start", "excel", "EXCEL.EXE"),
    "powerpoint": ("start", "powerpnt", "POWERPNT.EXE"),
    "discord": ("start", "discord://", "Discord.exe"),
    "whatsapp": ("start", "whatsapp://", "WhatsApp.Root.exe"),
    "telegram": ("start", "tg://", "Telegram.exe"),
    "spotify": ("start", "spotify://", "Spotify.exe"),
    "valorant": ("cmd", [r"C:\Riot Games\Riot Client\RiotClientServices.exe",
                         "--launch-product=valorant", "--launch-patchline=live"],
                 "RiotClientServices.exe"),
}

NAMES = ", ".join(sorted(set(LAUNCH) - {"kalkulator"}))


def states(name):
    """Alur state untuk log natural. Generator langkah (state, pesan, aksi)."""
    key = (name or "").strip().lower()
    if key not in LAUNCH:
        yield ("FAILED", "Aplikasi '%s' belum didukung. Bisa dibuka: %s." % (name, NAMES.title()), None)
        return
    method, target, exe = LAUNCH[key]
    yield ("SEARCHING", "Memeriksa layar dan aplikasi berjalan untuk %s..." % key, None)
    if actions._has_window(exe):
        yield ("ACTIVE", "%s sudah terbuka di layar." % key.title(), ("focus", key))
        return
    if actions.is_running(exe):
        yield ("FOUND", "%s berjalan tapi tak terlihat. Memulihkan jendela..." % key.title(),
               ("relaunch", key))
        return
    yield ("FOUND", "%s terinstall. Membuka..." % key.title(), ("launch", key))


def describe_supported():
    return NAMES
