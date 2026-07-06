"""Minimal smoke test: pipeline outputs exist and the site embeds real data.
Run: python tests/test_smoke.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def check(cond, msg):
    print(("  ok " if cond else "FAIL ")+msg)
    return cond

ok = True
payload = ROOT/"data"/"payload.json"
ok &= check(payload.exists(), "payload.json exists")
if payload.exists():
    d = json.load(open(payload, encoding="utf-8"))
    ok &= check(len(d.get("teams",{}))>=8, f"teams present ({len(d.get('teams',{}))})")
    ok &= check("modifiers" in d and "players" in d, "modifiers + players present")
    ok &= check(len(d.get("reliability",[]))>=3, "reliability curve present")
html = (ROOT/"site"/"index.html").read_text(encoding="utf-8")
ok &= check("const DATA = {" in html, "site has embedded DATA block")
ok &= check('"modifiers"' in html, "site DATA includes modifiers")
sys.exit(0 if ok else 1)
