"""
Monte Carlo forward simulation of the remaining bracket.
Uses enhanced blended Elo (career + in-tournament form). Simulates the
remaining R16 + QF + SF + Final N times, tracking each team's probability
of reaching each round and winning the Cup. Knockouts -> no draws (extra
time / penalties modeled as a coin-flip nudged by Elo).
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

# Remaining bracket structure (from live data). R16 winners feed QF.
# Determined R16 (played): France, Morocco, Norway, England already through.
# Remaining R16 ties -> then QF pairings per FIFA 2026 bracket.
R16_REMAINING = [("Argentina","Egypt"),("Switzerland","Colombia")]
# R16_5/R16_6 already decided: Spain (1-0 Portugal) and Belgium (4-1 USA) through.
# QF pairings: (France v Morocco) and (Norway v England) already set.
# The other two QFs come from the 4 remaining R16 winners:
#   QF: winner(Portugal/Spain) v winner(USA/Belgium)
#   QF: winner(Argentina/Egypt) v winner(Switzerland/Colombia)
# SF: (France/Morocco winner) v (Norway/England winner)
#     (PS/USB winner) v (AE/SC winner)
# Final: SF1 v SF2

def sim_match(a,b):
    return a if random.random()<p_win(a,b) else b

def simulate_once():
    # remaining R16 (only two ties left; Spain & Belgium already through)
    ae=sim_match("Argentina","Egypt"); sc=sim_match("Switzerland","Colombia")
    # QFs
    qf1=sim_match("France","Morocco")
    qf2=sim_match("Norway","England")
    qf3=sim_match("Spain","Belgium")   # R16_5 winner v R16_6 winner, both decided
    qf4=sim_match(ae,sc)
    # SFs
    sf1=sim_match(qf1,qf2)
    sf2=sim_match(qf3,qf4)
    champ=sim_match(sf1,sf2)
    finalists={sf1,sf2}
    semis={qf1,qf2,qf3,qf4}
    quarters={"France","Morocco","Norway","England","Spain","Belgium",ae,sc}
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
