"""Central path resolution so scripts run from anywhere in the repo."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
RESULTS_CSV = DATA / "intl_results.csv"
SHOOTOUTS_CSV = DATA / "shootouts.csv"
WORLDCUP_JSON = DATA / "worldcup2026.json"
PAYLOAD_JSON = DATA / "payload.json"
PLAYERS_JSON = DATA / "players.json"
SIM_JSON = DATA / "sim_results.json"
INDEX_HTML = SITE / "index.html"
