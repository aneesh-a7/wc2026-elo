#!/usr/bin/env python3
"""One command to rebuild everything from live data:

    python pipeline.py            # full rebuild (fetch -> model -> site)
    python pipeline.py --no-fetch # skip download, rebuild from cached data
    python pipeline.py --backtest # also print the rigorous multi-WC backtest

Run order matters: fetch -> players -> simulate -> payload -> modifiers -> site.
"""
import sys, subprocess
from pathlib import Path

# Keep our own console output UTF-8-safe on Windows (the status lines below use
# non-ASCII); child steps get UTF-8 via the -X utf8 flag added in run().
for _stream in (sys.stdout, sys.stderr):
    try: _stream.reconfigure(encoding="utf-8")
    except Exception: pass

SRC = Path(__file__).resolve().parent / "src"
def run(mod, label):
    print(f"\n=== {label} ===")
    # -X utf8: force UTF-8 for all file I/O. The data files carry accented
    # player names and flag emojis; without this the steps crash on Windows
    # (cp1252 default). No-op on Linux/CI where UTF-8 is already the default.
    r = subprocess.run([sys.executable, "-X", "utf8", str(SRC / mod)], cwd=str(SRC))
    if r.returncode != 0:
        raise SystemExit(f"step failed: {mod}")

def main():
    args = set(sys.argv[1:])
    if "--no-fetch" not in args:
        run("fetch_data.py", "1/6 fetch live data")
    run("build_players.py", "2/6 extract player goal-share")
    run("simulate.py",      "3/6 monte-carlo simulation (50k)")
    run("gen_payload.py",   "4/6 build model payload")
    run("add_modifiers.py", "5/6 add match-lab modifiers")
    run("build_site.py",    "6/6 embed payload into site")
    if "--backtest" in args:
        run("rigorous_backtest.py", "extra: rigorous multi-WC backtest")
    print("\n✓ done — open site/index.html")

if __name__ == "__main__":
    main()
