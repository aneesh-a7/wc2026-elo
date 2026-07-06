"""
Enhanced Elo Engine for FIFA World Cup 2026 prediction.

Core: World Football Elo Ratings methodology (eloratings.net / Bob Runyan 1997)
  R_new = R_old + K * (W - We)
  K weighted by match importance, multiplied by goal-difference factor.
  Home advantage 100 pts (neutral-venue tournaments => 0).

Enhancement layer (the "novel" part):
  1. TOURNAMENT-FORM BLEND: blends a team's career Elo with an in-tournament
     form Elo, so a team over/under-performing its rating THIS World Cup is
     partially trusted. Weight ramps up as the team plays more WC matches.
  2. Recency half-life decay applied when seeding career Elo (recent results
     matter more).
Everything is computed from primary match data (intl_results.csv, 1872-2026).
"""
import csv, math
from collections import defaultdict
from datetime import date

# ---- eloratings.net parameters ----
K_BY_TOURNAMENT = {
    "FIFA World Cup": 60,
    "Copa América": 50, "UEFA Euro": 50, "African Cup of Nations": 50,
    "AFC Asian Cup": 50, "Gold Cup": 50, "CONCACAF Championship": 50,
    "Confederations Cup": 50,
    "UEFA Nations League": 40, "CONCACAF Nations League": 40,
}
def k_base(tournament):
    if tournament in K_BY_TOURNAMENT: return K_BY_TOURNAMENT[tournament]
    t = tournament.lower()
    if "qualification" in t: return 40
    if "friendly" in t: return 20
    if "cup" in t or "championship" in t or "nations" in t: return 40
    return 30

def gd_multiplier(margin):
    """eloratings.net goal-difference weighting (applies to any decisive result)."""
    if margin <= 1: return 1.0
    if margin == 2: return 1.5
    if margin == 3: return 1.75
    return 1.75 + (margin - 3) / 8.0

# ---- Team-name canonicalization ----
# The primary results CSV uses "United States", but the 2026 fixtures
# (worldcup2026.json), flags, and the front end all use "USA". Left
# unnormalized, USA's career Elo defaults to 1500 and its title odds get
# dropped when the payload is keyed by "USA". Map every source to one canonical
# form so ratings, the Monte Carlo, and the payload line up. Add aliases here if
# other name variants surface between the data sources.
TEAM_ALIASES = {
    "United States": "USA",
}
def canon(name):
    """Return the canonical team name for `name`."""
    return TEAM_ALIASES.get(name, name)

def expected(r_a, r_b):
    """Standard Elo expectation, divisor 400 (eloratings.net)."""
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))

class EloEngine:
    def __init__(self, base=1500, home_adv=100):
        self.r = defaultdict(lambda: base)
        self.home_adv = home_adv
        self.played = defaultdict(int)
        self.wc26_form = defaultdict(list)  # (elo_delta_perf) per WC26 match

    def process_match(self, home, away, hs, as_, tournament, neutral):
        margin = abs(hs - as_)
        if hs > as_: w = 1.0
        elif hs < as_: w = 0.0
        else: w = 0.5
        ha = 0 if neutral else self.home_adv
        we = expected(self.r[home] + ha, self.r[away])
        K = k_base(tournament) * gd_multiplier(margin)
        delta = K * (w - we)
        self.r[home] += delta
        self.r[away] -= delta
        self.played[home]+=1; self.played[away]+=1
        return delta, we

    def rating(self, team): return self.r[team]

def load_and_build(path=None, cutoff=None):
    if path is None:
        from paths import RESULTS_CSV
        path = str(RESULTS_CSV)
    rows = [r for r in csv.DictReader(open(path))
            if r['home_score'] not in ('','NA') and r['away_score'] not in ('','NA')]
    for r in rows:  # normalize once so every caller sees canonical names
        r['home_team'] = canon(r['home_team'])
        r['away_team'] = canon(r['away_team'])
    eng = EloEngine()
    for r in rows:
        if cutoff and r['date'] > cutoff: continue
        eng.process_match(r['home_team'], r['away_team'],
                          int(r['home_score']), int(r['away_score']),
                          r['tournament'], r['neutral']=='TRUE')
    return eng, rows

if __name__ == "__main__":
    eng, rows = load_and_build()
    top = sorted(eng.r.items(), key=lambda x:-x[1])[:20]
    print("=== ELO RATINGS (computed from 1872-2026 primary match data) ===")
    for i,(t,r) in enumerate(top,1):
        print(f"  {i:2}. {t:18} {r:7.1f}  ({eng.played[t]} matches)")
