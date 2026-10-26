"""Environment scan: aplikasi apa yang tersedia di komputer ini.
Hasil: data/environment.json. Stdlib saja."""
import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
try:
    from _paths import writable as _wr
    OUT = _wr("data", "environment.json")
except ImportError:
    OUT = os.path.join(ROOT, "data", "environment.json")

CANDIDATES = {
    "winword": ("Microsoft Word", ["document_creation", "text_editing"]),
    "excel": ("Microsoft Excel", ["spreadsheet", "table_data"]),
    "powerpnt": ("Microsoft PowerPoint", ["presentation"]),
    "chrome": ("Google Chrome", ["browser"]),
    "msedge": ("Microsoft Edge", ["browser"]),
    "firefox": ("Firefox", ["browser"]),
    "code": ("VS Code", ["code_editor"]),
    "notepad": ("Notepad", ["text_editing"]),
    "calc": ("Kalkulator", ["calculator"]),
    "discord": ("Discord", ["messaging", "voice_chat"]),
    "spotify": ("Spotify", ["music"]),
    "whatsapp": ("WhatsApp", ["messaging"]),
}


def _which(prog):
    if shutil.which(prog):
        return True
    try:
        r = subprocess.run(["where", prog], capture_output=True,
                           text=True, timeout=10)
        return r.returncode == 0
    except OSError:
        return False


def _app_paths(prog):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s.exe" % prog) as k:
            return winreg.QueryValue(k, None) or True
    except OSError:
        return False


def scan():
    apps = []
    for prog, (label, caps) in CANDIDATES.items():
        found = _which(prog + ".exe") or _app_paths(prog)
        if found:
            apps.append({"name": label, "program": prog, "capabilities": caps})
    if os.path.exists(r"C:\Riot Games\VALORANT\live\VALORANT.exe"):
        apps.append({"name": "Valorant", "program": "valorant",
                     "capabilities": ["game"]})
    try:
        py = subprocess.run(["py", "--version"], capture_output=True,
                            text=True, timeout=10)
        python = (py.stdout or py.stderr or "").strip()
    except OSError:
        python = ""
    env = {"applications": apps, "python": python,
           "internet": True}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(env, ensure_ascii=False, indent=1))
    return env


def load():
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.loads(f.read() or "{}")
    except (OSError, ValueError):
        return {"applications": []}


def summary():
    env = load() or {"applications": []}
    names = [a["name"] for a in env.get("applications", [])]
    if not names:
        return "belum ada hasil scan. Aplikasi umum diasumsikan ada."
    return "Terinstall: " + ", ".join(names) + "."


if __name__ == "__main__":
    print(json.dumps(scan(), ensure_ascii=False, indent=1))
