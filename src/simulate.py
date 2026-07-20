"""
Monte Carlo forward simulation of the remaining bracket.
Uses enhanced blended Elo (career + in-tournament form). Simulates the
remaining R16 + QF + SF + Final N times, tracking each team's probability
of reaching each round and winning the Cup. Knockouts -> no draws (extra
time / penalties modeled as a coin-flip nudged by Elo).

The 2026 tournament is over, so pipeline.py no longer calls this file: with
every 2026 result (including the final's) now in intl_results.csv, running
this again would fold the final's own outcome into its "prediction" of it.
Kept for the record and for future tournaments; data/sim_results.json stays
frozen at its last pre-final run (Spain 53.6% / Argentina 46.4%).
"""
import csv, math, random
from collections import defaultdict
from elo_engine import load_and_build, expected, k_base, gd_multiplier

random.seed(42)
WC_START="2026-06-11"
ALPHA=0.4  # form-blend weight (best calibration from A/B test)

def build_blended():
    eng,rows=load_and_build(cutoff="2026-06-10")
    career=dict(eng.r)
    form=dict(career)
    wc=[r for r in rows if r['tournament']=="FIFA World Cup" and r['date']>=WC_START
        and r['home_score'] not in ('','NA')]
    for r in wc:
        h,a=r['home_team'],r['away_team']; hs,as_=int(r['home_score']),int(r['away_score'])
        for t in (h,a): form.setdefault(t,career.get(t,1500))
        margin=abs(hs-as_); w=1.0 if hs>as_ else (0.0 if hs<as_ else 0.5)
        we=expected(form[h],form[a]); K=k_base("FIFA World Cup")*gd_multiplier(margin)
        d=K*(w-we); form[h]+=d; form[a]-=d
    blended={t:(1-ALPHA)*career.get(t,1500)+ALPHA*form.get(t,career.get(t,1500))
             for t in set(list(career)+list(form))}
    return blended

R = build_blended()
def p_win(a,b):  # knockout: win prob (no draw), neutral venue
    return expected(R.get(a,1500), R.get(b,1500))

# Remaining bracket structure (from live data).
# R16, quarter-finals, and semifinals all complete:
#   SF: Spain 2-0 France · Argentina 2-1 England (comeback, 85'/92')
# Final (Jul 19, MetLife Stadium): Spain v Argentina. Only the Final is left
# to simulate; everyone else's Elo still matters via the form blend below.
R16_REMAINING = []   # kept for the round-update checklist; nothing left to draw

def sim_match(a,b):
    return a if random.random()<p_win(a,b) else b

def simulate_once():
    # Semifinals decided; only the Final is simulated.
    champ=sim_match("Spain","Argentina")
    finalists={"Spain","Argentina"}
    semis=set(finalists)
    quarters=set(finalists)
    return quarters,semis,finalists,champ

N=50000
reach_qf=defaultdict(int); reach_sf=defaultdict(int)
reach_final=defaultdict(int); win=defaultdict(int)
for _ in range(N):
    q,s,f,c=simulate_once()
    for t in q: reach_qf[t]+=1
    for t in s: reach_sf[t]+=1
    for t in f: reach_final[t]+=1
    win[c]+=1

print(f"=== MONTE CARLO: {N:,} simulations, enhanced blended Elo (alpha={ALPHA}) ===\n")
teams=sorted(win, key=lambda t:-win[t])
print(f"  {'Team':16}{'QF%':>7}{'SF%':>7}{'Final%':>8}{'WIN%':>7}")
for t in teams[:14]:
    print(f"  {t:16}{100*reach_qf[t]/N:>6.1f}%{100*reach_sf[t]/N:>6.1f}%"
          f"{100*reach_final[t]/N:>7.1f}%{100*win[t]/N:>6.1f}%")

import json
out={t:{'QF':reach_qf[t]/N,'SF':reach_sf[t]/N,'Final':reach_final[t]/N,'Win':win[t]/N}
     for t in reach_qf}
from paths import SIM_JSON
json.dump(out, open(str(SIM_JSON),'w'), indent=2)
