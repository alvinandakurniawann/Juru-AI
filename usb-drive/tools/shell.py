"""Shell tool. Selalu HIGH: hanya jalan setelah konfirmasi user."""
import subprocess

TIMEOUT = 30
MAX_OUT = 2000


def run(cmd):
    if not (cmd or "").strip():
        raise ValueError("perintah kosong")
    r = subprocess.run(cmd, shell=True, capture_output=True,
                       text=True, timeout=TIMEOUT)
    out = (r.stdout or "") + (r.stderr or "")
    return "exit %d: %s" % (r.returncode, out[:MAX_OUT] or "(tanpa output)")
