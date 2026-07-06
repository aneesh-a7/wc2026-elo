"""Pull the live source data. Run this first (and any time you want fresh results)."""
import urllib.request, sys
from paths import DATA, RESULTS_CSV, SHOOTOUTS_CSV, WORLDCUP_JSON

SOURCES = {
    RESULTS_CSV:   "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
    SHOOTOUTS_CSV: "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv",
    WORLDCUP_JSON: "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json",
}

def fetch():
    DATA.mkdir(exist_ok=True)
    for dest, url in SOURCES.items():
        print(f"↓ {dest.name} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wc2026-elo/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                dest.write_bytes(r.read())
            print(f"{dest.stat().st_size:,} bytes")
        except Exception as e:
            print(f"FAILED ({e})"); sys.exit(1)
    print("done.")

if __name__ == "__main__":
    fetch()
