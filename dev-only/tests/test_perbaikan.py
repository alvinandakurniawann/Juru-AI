"""Test perbaikan ala koma. Stdlib saja. Jalankan dari folder ini: py test_perbaikan.py"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "usb-drive"))
sys.path.insert(0, ROOT)
from agent import core
from tools import permissions, web

PASS = []


def check(name, cond):
    PASS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# 1) Casing dijaga (bug lama: lower semua)
check("ketik jaga casing",
      core._after_keyword("Tolong ketik Halo Dunia Ya") == "Halo Dunia Ya")

# 2) Kasus Raditya Dika -> 1 tool youtube_oldest, bukan [] / open_app chrome
plan = core.heuristic_plan(
    "buka chrome, lalu buka channel raditya dika dan tonton video paling lamanya")
check("heuristic youtube_oldest",
      len(plan) == 1 and plan[0]["tool"] == "youtube_oldest"
      and "raditya" in plan[0]["args"]["query"].lower())

# 3) Validasi tolak halusinasi + repair open_app chrome
valid, dropped = core._validate_plan([
    {"tool": "open_app", "args": {"app": "chrome"}},
    {"tool": "klik_ngawur", "args": {}},
    {"tool": "click", "args": {"x": "a", "y": "b"}},
    {"tool": "open_browser", "args": {"url": "https://www.bing.com/"}},
])
check("validate repair+buang",
      dropped == 2 and len(valid) == 2
      and valid[0]["tool"] == "open_browser")

# 4) type_text berisi kata hapus bukan HIGH
check("type_text hapus bukan HIGH",
      permissions.classify("type_text", {"text": "hapus ini"}) != "HIGH")
check("delete_file tetap HIGH",
      permissions.classify("delete_file", {"path": "a.txt"}) == "HIGH")

# 5) Pembersih query channel
check("clean channel",
      "raditya" in web._clean_channel_query(
          "buka channel raditya dika dan tonton video paling lamanya"))

# 6) Batas agen ada (anti infinite-loop)
check("MAX_AGENT_STEPS bounded",
      4 <= core.MAX_AGENT_STEPS <= 10 and core.MAX_REPLAN <= 1)

# 7) youtube_oldest jujur: provenance dibuka, bukan tebak ID dari HTML
check("verify terima provenance dibuka",
      core._verify("youtube_oldest", {"query": "raditya dika"},
                   "kanal: https://www.youtube.com/@radityadika (sumber: x).\n"
                   "Halaman terlama dibuka:\nhttps://x\nKlik video pertama.") is True)

# 8) artifact chatbot: screenshot jadi kartu gambar, file jadi kartu unduhan
check("artifact screenshot",
      (core._artifact_for("screenshot", {}, "tersimpan: shot-20240101-120000.png") or {}).get("kind") == "image")
check("artifact non-file None",
      core._artifact_for("web_search", {"query": "x"}, "ok") is None)

# 9) manifest satu sumber: RUNNERS vs manifest vs validasi sinkron
from tools import manifest as _mf
from agent import llm as _llm
check("manifest sinkron runners",
      set(core.RUNNERS) == set(_mf.names()) == set(core.TOOL_SCHEMAS))
check("manifest tercantum di prompt LLM",
      all(n in _llm.TOOLS for n in ("youtube_oldest", "web_fetch", "delete_file",
                                    "create_pdf", "create_pptx")))
check("peran model default aman",
      bool(_llm.MODEL_MAIN) and bool(_llm.MODEL_SAFE))

# 10) kontrol jendela: default aman tanpa efek samping
from tools import window as _win
_u = _win.load()
check("ui default",
      _u.get("always_on_top") is False and _u.get("opacity") == 100)
check("ui clamp opacity",
      _win.save({"opacity": 5})["opacity"] == 30 and
      _win.save({"opacity": 999})["opacity"] == 100)
check("ui apply tanpa jendela tetap bool",
      isinstance(_win.set_topmost(False), bool))

# 11) tabel acak: 5x5 random jadi grid 5x5 angka, bukan default 2 baris
_r = core._tabel_rows("buka excel buatkan tabel 5x5 dengan isi random")
check("tabel random 5x5",
      len(_r.splitlines()) == 5 and len(_r.splitlines()[0].split(";")) == 5)
_n = core._tabel_rows("buatkan tabel 3x2 di excel")
check("tabel dimensi tanpa data",
      len(_n.splitlines()) == 3 and _n.splitlines()[0].split(";") == ["A", "B"])
check("bukan tabel kosong",
      core._tabel_rows("halo apa kabar") == "")
check("heuristic excel bawa rows",
      core.heuristic_plan("buka excel buatkan tabel 5x5 dengan isi random")[0]["args"]["rows"].count("\n") == 4)

# 12) pdf/pptx terdaftar di semua registry
check("pdf pptx sinkron",
      all(t in core.RUNNERS and t in core.TOOL_SCHEMAS
          for t in ("create_pdf", "create_pptx")) and
      "create_pptx" in _mf.names())

# 13) WinError 5 diterjemahkan jadi saran aksi, bukan pesan mentah
check("saran akses ditolak",
      "flashdisk" in core._suggest_next("create_xlsx", "[WinError 5] Access is denied"))

# 14) folder gagal disiapkan sebut path penuh
from tools import files as _f
try:
    _f._ensure_dir("X:\\pasti\\tak\\ada\u0000buruk")
    check("ensure_dir angkat galat", False)
except OSError as e:
    check("ensure_dir sebut path", "X:\\pasti\\tak\\ada" in str(e))

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
