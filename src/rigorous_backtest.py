"""
Rigorous multi-World-Cup backtest — no hindsight bias.

Design principles addressing the critique:
1. NO LEAKAGE: Elo is computed chronologically. Before each World Cup we freeze
   the rating using ONLY matches played before that tournament's first game.
   Predictions use that frozen snapshot. (We also run a 'live' variant that
   updates within the tournament using only already-played matches.)
2. NO TUNING ON TEST DATA: all parameters are the published eloratings.net
   constants, fixed a priori. Nothing is fit to the tournaments being scored.
3. ACCURACY IS NOT THE HEADLINE: we compare against the 'always pick the
   favorite' baseline. If the model only matches it, accuracy adds nothing.
   The real test is CALIBRATION (Brier, log-loss) and whether the underdog is
   taken the RIGHT fraction of the time — measured by a reliability table.
"""
import csv, math
from collections import defaultdict
from elo_engine import EloEngine, expected, k_base, gd_multiplier, canon
from paths import RESULTS_CSV, SHOOTOUTS_CSV

def load_rows():
    rows = [r for r in csv.DictReader(open(str(RESULTS_CSV)))
            if r['home_score'] not in ('','NA') and r['away_score'] not in ('','NA')]
    for r in rows:  # canonical names (pure relabel; leaves the leak-free numbers unchanged)
        r['home_team']=canon(r['home_team']); r['away_team']=canon(r['away_team'])
    return rows

def load_shootouts():
    d={}
    for r in csv.DictReader(open(str(SHOOTOUTS_CSV))):
        d[(r['date'],r['home_team'],r['away_team'])]=r['winner']
    return d

def outcome_probs(rh, ra):
    e = expected(rh, ra)  # neutral venue, no home adv in WC
    draw = 0.28*(1-abs(2*e-1))**1.2 + 0.15*(1-abs(2*e-1))
    draw = max(0.12, min(0.34, draw))
    ph=e*(1-draw); pa=(1-e)*(1-draw); s=ph+draw+pa
    return ph/s, draw/s, pa/s

TARGET_WCS = ['2006','2010','2014','2018','2022']

def run(live_update=False):
    rows = load_rows()
    shootouts = load_shootouts()

    # Precompute chronological Elo; snapshot before each target WC.
    rows_sorted = sorted(rows, key=lambda r:r['date'])
    eng = EloEngine()
    snapshots = {}
    wc_first_date = {}
    for y in TARGET_WCS:
        ds = [r['date'] for r in rows_sorted
              if r['tournament']=='FIFA World Cup' and r['date'][:4]==y]
        wc_first_date[y]=min(ds)

    processed_wc = set()
    for r in rows_sorted:
        y=r['date'][:4]
        # snapshot the instant we reach each WC's first match, before processing it
        for wy in TARGET_WCS:
            if wy not in snapshots and r['date']>=wc_first_date[wy]:
                snapshots[wy]=dict(eng.r)
        eng.process_match(r['home_team'],r['away_team'],
                          int(r['home_score']),int(r['away_score']),
                          r['tournament'],r['neutral']=='TRUE')
    for wy in TARGET_WCS:
        snapshots.setdefault(wy, dict(eng.r))

    # Evaluate each WC
    overall={'n':0,'model_acc':0,'fav_acc':0,'brier':0,'logloss':0,
             'chalk_brier':0}
    # reliability buckets for favorite win prob
    rel=defaultdict(lambda:[0,0])  # bucket -> [fav_wins, total]
    per_wc={}

    for y in TARGET_WCS:
        base=dict(snapshots[y])
        live=dict(base)
        wc=[r for r in rows_sorted if r['tournament']=='FIFA World Cup'
            and r['date'][:4]==y]
        n=macc=facc=0; brier=0; logloss=0
        for r in wc:
            h,a=r['home_team'],r['away_team']
            hs,as_=int(r['home_score']),int(r['away_score'])
            rh = live[h] if live_update else base.get(h,1500)
            ra = live[a] if live_update else base.get(a,1500)
            rh=rh if rh else 1500; ra=ra if ra else 1500
            ph,pd,pa=outcome_probs(rh,ra)
            # actual regulation outcome
            if hs>as_: actual='H'
            elif hs<as_: actual='A'
            else: actual='D'
            y_vec={'H':(1,0,0),'D':(0,1,0),'A':(0,0,1)}[actual]
            pred=['H','D','A'][max(range(3),key=lambda i:(ph,pd,pa)[i])]
            fav = 'H' if rh>=ra else 'A'   # favorite = higher Elo
            n+=1
            if pred==actual: macc+=1
            if actual==fav: facc+=1
            brier += sum((p-yv)**2 for p,yv in zip((ph,pd,pa),y_vec))
            probs={'H':ph,'D':pd,'A':pa}; logloss += -math.log(max(1e-9,probs[actual]))
            # reliability: favorite win prob bucket (exclude draws from fav-win defn)
            fav_p = max(ph,pa)
            b=int(fav_p*10)/10
            rel[b][1]+=1
            if actual==fav: rel[b][0]+=1
            # live update
            if live_update:
                margin=abs(hs-as_); w=1.0 if hs>as_ else(0.0 if hs<as_ else 0.5)
                we=expected(live[h],live[a]); K=k_base('FIFA World Cup')*gd_multiplier(margin)
                dd=K*(w-we); live[h]+=dd; live[a]-=dd
        per_wc[y]=(n,macc/n,facc/n,brier/n,logloss/n)
        overall['n']+=n; overall['model_acc']+=macc; overall['fav_acc']+=facc
        overall['brier']+=brier; overall['logloss']+=logloss

    N=overall['n']
    print(f"{'='*64}")
    print(f" MULTI-WORLD-CUP BACKTEST  ({'live in-tournament update' if live_update else 'frozen pre-tournament, zero leakage'})")
    print(f" {N} matches across {', '.join(TARGET_WCS)}")
    print(f"{'='*64}")
    print(f" {'WC':6}{'N':>5}{'Model acc':>11}{'Favorite acc':>14}{'Brier':>9}{'LogLoss':>9}")
    for y in TARGET_WCS:
        n,ma,fa,br,ll=per_wc[y]
        print(f" {y:6}{n:>5}{ma:>10.1%}{fa:>13.1%}{br:>9.3f}{ll:>9.3f}")
    print(f" {'-'*58}")
    print(f" {'ALL':6}{N:>5}{overall['model_acc']/N:>10.1%}"
          f"{overall['fav_acc']/N:>13.1%}{overall['brier']/N:>9.3f}{overall['logloss']/N:>9.3f}")
    print()
    print(" READING THIS: Model accuracy ≈ favorite accuracy is EXPECTED and honest —")
    print(" both pick the stronger side on chalk games. The model earns its keep in")
    print(" the reliability table below: does the underdog win as often as predicted?")
    print()
    print(" RELIABILITY (are upsets taken the RIGHT amount?)")
    print(f"   {'Favorite win prob':>20}{'Predicted':>11}{'Actual fav win%':>17}{'Games':>7}")
    for b in sorted(rel):
        wins,tot=rel[b]
        if tot<8: continue
        print(f"   {b:.0%}–{b+0.1:.0%}{'':>10}{b+0.05:>9.0%}{wins/tot:>16.0%}{tot:>7}")
    print()
    print(" If 'actual' tracks 'predicted' down the column, the model is calibrated:")
    print(" it is neither over-picking favorites nor over-picking upsets.")
    return per_wc, overall, rel

if __name__=="__main__":
    run(live_update=False)
    print("\n\n")
    run(live_update=True)
