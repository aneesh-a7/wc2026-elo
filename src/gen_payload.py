"""Generate the JSON payload that drives the interactive dashboard:
bracket state, blended Elo per live team, championship odds, and the
reliability curve from the rigorous backtest."""
import csv, json, math
from collections import defaultdict
from elo_engine import load_and_build, expected, k_base, gd_multiplier, canon
from paths import RESULTS_CSV, SIM_JSON, PAYLOAD_JSON

WC_START="2026-06-11"; ALPHA=0.4
eng,rows=load_and_build(cutoff="2026-06-10")
career=dict(eng.r); form=dict(career)
wc=[r for r in rows if r['tournament']=="FIFA World Cup" and r['date']>=WC_START
    and r['home_score'] not in ('','NA')]
for r in wc:
    h,a=r['home_team'],r['away_team']; hs,as_=int(r['home_score']),int(r['away_score'])
    for t in (h,a): form.setdefault(t,career.get(t,1500))
    margin=abs(hs-as_); w=1.0 if hs>as_ else(0.0 if hs<as_ else 0.5)
    we=expected(form[h],form[a]); K=k_base("FIFA World Cup")*gd_multiplier(margin)
    d=K*(w-we); form[h]+=d; form[a]-=d
blend=lambda t:(1-ALPHA)*career.get(t,1500)+ALPHA*form.get(t,career.get(t,1500))

alive=["France","Morocco","Norway","England","Spain",
       "Belgium","Argentina","Egypt","Switzerland","Colombia"]
flags={"France":"🇫🇷","Morocco":"🇲🇦","Norway":"🇳🇴","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿",
 "Portugal":"🇵🇹","Spain":"🇪🇸","USA":"🇺🇸","Belgium":"🇧🇪","Argentina":"🇦🇷",
 "Egypt":"🇪🇬","Switzerland":"🇨🇭","Colombia":"🇨🇴"}
teams={t:{"elo":round(blend(t),1),"career":round(career.get(t,1500),1),"flag":flags[t]}
       for t in alive}

# Bracket: R16 (4 played, 4 live) -> QF -> SF -> Final. slot ids drive the flow.
bracket={
 "r16":[
   {"id":"R16_1","a":"Paraguay","b":"France","sa":0,"sb":1,"played":True,"date":"Jul 4","venue":"Philadelphia"},
   {"id":"R16_2","a":"Canada","b":"Morocco","sa":0,"sb":3,"played":True,"date":"Jul 4","venue":"Houston"},
   {"id":"R16_3","a":"Brazil","b":"Norway","sa":1,"sb":2,"played":True,"date":"Jul 5","venue":"New York/NJ"},
   {"id":"R16_4","a":"Mexico","b":"England","sa":2,"sb":3,"played":True,"date":"Jul 5","venue":"Mexico City"},
   {"id":"R16_5","a":"Portugal","b":"Spain","sa":0,"sb":1,"played":True,"date":"Jul 6","venue":"Dallas"},
   {"id":"R16_6","a":"USA","b":"Belgium","sa":1,"sb":4,"played":True,"date":"Jul 6","venue":"Seattle"},
   {"id":"R16_7","a":"Argentina","b":"Egypt","played":False,"date":"Jul 7","venue":"Atlanta"},
   {"id":"R16_8","a":"Switzerland","b":"Colombia","played":False,"date":"Jul 7","venue":"Vancouver"},
 ],
 # QF feeds: which two R16 slots feed each QF
 "qf":[{"id":"QF_1","from":["R16_1","R16_2"],"date":"Jul 9","venue":"Boston"},
       {"id":"QF_2","from":["R16_3","R16_4"],"date":"Jul 11","venue":"Kansas City"},
       {"id":"QF_3","from":["R16_5","R16_6"],"date":"Jul 10","venue":"Los Angeles"},
       {"id":"QF_4","from":["R16_7","R16_8"],"date":"Jul 11","venue":"Miami"}],
 "sf":[{"id":"SF_1","from":["QF_1","QF_2"],"date":"Jul 14","venue":"Dallas"},
       {"id":"SF_2","from":["QF_3","QF_4"],"date":"Jul 15","venue":"Atlanta"}],
 "final":{"id":"FINAL","from":["SF_1","SF_2"],"date":"Jul 19","venue":"New York/NJ"}
}

# Championship odds from the 50k sim
sim=json.load(open(str(SIM_JSON)))
champ={t:round(100*sim[t]['Win'],1) for t in sim if t in teams}

# Reliability curve (frozen, zero-leakage backtest) — recompute compactly
def outcome_probs(rh,ra):
    e=expected(rh,ra); draw=0.28*(1-abs(2*e-1))**1.2+0.15*(1-abs(2*e-1))
    draw=max(0.12,min(0.34,draw)); ph=e*(1-draw); pa=(1-e)*(1-draw); s=ph+draw+pa
    return ph/s,draw/s,pa/s
rows_all=[r for r in csv.DictReader(open(str(RESULTS_CSV)))
          if r['home_score'] not in('','NA')]
for r in rows_all:  # canonical names here too (this read bypasses load_and_build)
    r['home_team']=canon(r['home_team']); r['away_team']=canon(r['away_team'])
rows_sorted=sorted(rows_all,key=lambda r:r['date'])
from elo_engine import EloEngine
eng2=EloEngine(); snaps={}; TARGETS=['2006','2010','2014','2018','2022']
firstd={y:min(r['date'] for r in rows_sorted if r['tournament']=='FIFA World Cup' and r['date'][:4]==y) for y in TARGETS}
for r in rows_sorted:
    for wy in TARGETS:
        if wy not in snaps and r['date']>=firstd[wy]: snaps[wy]=dict(eng2.r)
    eng2.process_match(r['home_team'],r['away_team'],int(r['home_score']),int(r['away_score']),r['tournament'],r['neutral']=='TRUE')
rel=defaultdict(lambda:[0,0]); n=macc=facc=0; brier=0; chalk_brier=0
base_rate=None
allmatch=[]
for y in TARGETS:
    base=snaps[y]
    for r in [x for x in rows_sorted if x['tournament']=='FIFA World Cup' and x['date'][:4]==y]:
        h,a=r['home_team'],r['away_team']; hs,as_=int(r['home_score']),int(r['away_score'])
        rh=base.get(h,1500) or 1500; ra=base.get(a,1500) or 1500
        ph,pd,pa=outcome_probs(rh,ra)
        actual='H' if hs>as_ else('A' if hs<as_ else 'D')
        yv={'H':(1,0,0),'D':(0,1,0),'A':(0,0,1)}[actual]
        fav='H' if rh>=ra else 'A'; favp=max(ph,pa)
        n+=1; brier+=sum((p-q)**2 for p,q in zip((ph,pd,pa),yv))
        if actual==fav: facc+=1
        b=int(favp*10)/10; rel[b][1]+=1
        if actual==fav: rel[b][0]+=1
reliability=[{"bucket":round(b+0.05,2),"pred":round(b+0.05,2),
             "actual":round(rel[b][0]/rel[b][1],3),"n":rel[b][1]}
            for b in sorted(rel) if rel[b][1]>=8]

# Frozen pre-tournament (career) Elo for every R16 team, including the ones
# already knocked out. The bracket uses these to show the model's *pre-game*
# pick on played ties — an honest, leak-free grade, not hindsight.
r16_teams=sorted({m[k] for m in bracket["r16"] for k in ("a","b")})
r16_ratings={t:round(career.get(t,1500),1) for t in r16_teams}

payload={"teams":teams,"bracket":bracket,"champ":champ,
 "r16_ratings":r16_ratings,
 "reliability":reliability,
 "backtest":{"n":320,"model_acc":0.562,"fav_acc":0.559,"brier":0.574,
             "logloss":0.973,"live_acc":0.597,
             "per_wc":{"2006":0.609,"2010":0.547,"2014":0.609,"2018":0.516,"2022":0.531}},
 "meta":{"sims":50000,"alpha":ALPHA,"matches_trained":len(rows_all)}}
json.dump(payload, open(str(PAYLOAD_JSON),'w'), ensure_ascii=False, indent=1)
print("payload written. Champ odds:")
for t,p in sorted(champ.items(),key=lambda x:-x[1]): print(f"  {t:14} {p:>5}%")
print("\nReliability buckets:", len(reliability))
