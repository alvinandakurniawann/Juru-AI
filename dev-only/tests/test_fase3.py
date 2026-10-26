"""Test Fase 3. Stdlib saja. Jalankan: py test_fase3.py (dari folder ini)."""
import json
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


check("fetch example", "Example Domain" in web.fetch("https://example.com"))
try:
    web.fetch("ftp://x")
    check("fetch tolak non-http", False)
except ValueError:
    check("fetch tolak non-http", True)

hits = web.search("jakarta", 2)
check("search hasil + url", len(hits) >= 1 and hits[0]["url"].startswith("http"))
check("web_fetch LOW", permissions.classify("web_fetch", {}) == "LOW")
check("research MEDIUM", permissions.classify("research", {}) == "MEDIUM")
check("heuristic baca url",
      core.heuristic_plan("bacakan https://example.com ini")[0]["tool"] == "web_fetch")

env_p = os.path.join(ROOT, "config", ".env")
if os.path.exists(env_p):
    d = dict(l.strip().split("=", 1) for l in open(env_p, encoding="utf-8")
             if l.strip() and not l.startswith("#") and "=" in l)
    if d.get("DEEPSEEK_API_KEY"):
        from agent import llm
        r = web.research("Jakarta", d["DEEPSEEK_API_KEY"], llm.ask, n=1)
        check("research + sumber", "Sumber:" in r and "http" in r)
    else:
        print("SKIP research (tanpa key)")
else:
    print("SKIP research (tanpa .env)")

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
