"""Test capability (§54-62). Stdlib saja. Jalankan: py test_capability.py."""
import os
import sys
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "usb-drive"))
sys.path.insert(0, ROOT)
from agent import core
from tools import capabilities, environment, files

PASS = []


def check(name, cond):
    PASS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


env = environment.scan()
check("scan temukan aplikasi", len(env.get("applications", [])) >= 3)
check("scan tulis environment.json",
      os.path.exists(os.path.join(ROOT, "data", "environment.json")))
check("word terdeteksi", "Microsoft Word" in environment.summary())
d = capabilities.describe()
check("registry deskripsikan capability", "document_creation" in d and "spreadsheet" in d)

p = core.heuristic_plan("Buka aplikasi pengolah kata dan tulis Hello World")
check("intent dokumen -> docx", p and p[0]["tool"] == "create_docx")
p2 = core.heuristic_plan("Buat spreadsheet penjualan")
check("intent spreadsheet -> xlsx", p2 and p2[0]["tool"] == "create_xlsx")
check("hapus tak dibajak ketik",
      core.heuristic_plan("hapus file halo") == [])
check("buka laporan tak membuat file",
      all(s["tool"] != "create_xlsx"
          for s in core.heuristic_plan("buka laporan penjualan")))

files.create_xlsx("UjiCap.xlsx", "A;B\n1;2")
zp = os.path.join(ROOT, "data", "UjiCap.xlsx")
z = zipfile.ZipFile(zp)
check("xlsx valid", "xl/worksheets/sheet1.xml" in z.namelist())
z.close()
os.remove(zp)
check("list_dir jalan", "environment.json" in files.list_dir(""))
check("make+rename", files.make_dir("capdir") and files.rename_file("capdir", "capdir2"))
import shutil
shutil.rmtree(os.path.join(ROOT, "data", "capdir2"))

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
