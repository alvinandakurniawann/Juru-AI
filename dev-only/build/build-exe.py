"""Build JURU.exe satu-file (tanpa Python di target). Stdlib + PyInstaller.

Jalankan di mesin DEV yang ada Python:
  cd dev-only\\build
  build-exe.bat
Hasil: usb-drive\\JURU.exe (+ frontend/config di dalam exe, data di sebelah exe).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
USB = os.path.normpath(os.path.join(HERE, "..", "..", "usb-drive"))
ENTRY = os.path.join(USB, "backend", "server.py")
WORK = os.path.join(HERE, "_pyinstaller")


def run(cmd):
    print("+ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("gagal: %s (kode %d)" % (" ".join(cmd), r.returncode))


def main():
    # PyInstaller di mesin build saja, bukan di USB target.
    try:
        import PyInstaller  # noqa
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    try:
        import webview  # noqa  (pywebview: jendela aplikasi, dibundel ke EXE)
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pywebview"])
    os.makedirs(WORK, exist_ok=True)
    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    sep = ";"
    add = [
        "--add-data", os.path.join(USB, "frontend") + sep + "frontend",
        "--add-data", os.path.join(USB, "config", "agent.json") + sep + "config",
        "--add-data", os.path.join(USB, "config", ".env.example") + sep + "config",
    ]
    # shortcut: build ke dist internal dulu agar EXE lama yang sedang jalan
    # tidak dikunci PyInstaller saat assemble (WinError 5).
    for name, entry in (("JURU", ENTRY),
                        ("JURU-Desktop", os.path.join(USB, "desktop.py"))):
        run([sys.executable, "-m", "PyInstaller",
             "--noconfirm", "--clean", "--onefile",
             "--name", name,
             "--paths", USB,
             # paket lokal wajib reguler (__init__.py) + dibundel penuh,
             # kalau tidak frozen import gagal 'unknown location'.
             "--collect-submodules", "agent",
             "--collect-submodules", "tools",
             "--collect-submodules", "backend",
             "--distpath", dist,
             "--workpath", WORK,
             "--specpath", WORK,
             *add,
             entry])
    for name in ("JURU", "JURU-Desktop"):
        fresh = os.path.join(dist, name + ".exe")
        target = os.path.join(USB, name + ".exe")
        try:
            shutil.copy2(fresh, target)
        except PermissionError:
            raise SystemExit(
                "Tutup dulu jendela %s yang sedang jalan, "
                "lalu build ulang. File target terkunci: %s" % (name, target))
        print("OK: %s" % target)
    print("Bawa ke USB: JURU.exe + config\\.env (key) + data\\ (kosong).")
    print("Jalankan via launcher\\Jalankan-JURU.bat (tanpa install Python).")


if __name__ == "__main__":
    main()
