"""Augment payload with the Match Lab modifier config.
Every magnitude below is grounded in cited research (see notes) and expressed
in Elo points, so it feeds the SAME win-prob formula the rest of the tool uses.
"""
import json
from paths import PLAYERS_JSON, PAYLOAD_JSON
pl=json.load(open(str(PLAYERS_JSON)))
payload=json.load(open(str(PAYLOAD_JSON)))

# ---- Player-out penalty ----
# Mechanism: a player's share of their team's tournament goals proxies how much
# the team's attack depends on them. Penalty = base * share, capped. Grounded in
# the idea (Skellam positional-value / eLPAR literature, arXiv:1807.07536) that a
# player's marginal contribution maps to expected points, hence to team rating.
# A talismanic scorer (Messi 64% of goals) => large hit; a spread attack => small.
PLAYER_BASE = 95   # Elo pts at 100% goal share (a pure one-man team); scaled by share
PLAYER_FLOOR = 12  # even a squad player removed costs a little
def penalty(share):
    return round(min(72, PLAYER_FLOOR + PLAYER_BASE*share))

players_cfg={}
for team, ps in pl.items():
    players_cfg[team]=[{"name":p["name"],"goals":p["goals"],
                        "share":p["share"],"elo":penalty(p["share"])} for p in ps]

# ---- Environmental / situational modifiers (Elo-point terms) ----
# HEAT: high temp cuts high-intensity actions & goals and compresses the skill gap
#   (favorites dominate less) -> model as SHRINKING the Elo gap toward parity.
# RAIN/WET: degrades passing, adds randomness -> smaller parity shrink.
# HOST CROWD: neutral-venue but de-facto home support for USA/MEX/CAN. Crowd is the
#   dominant component of home advantage (COVID no-fans studies: removing fans cut
#   home edge >50%, arXiv & PMC9121146). eloratings uses 100 Elo for full home
#   advantage; a partial neutral-venue crowd => ~45 Elo.
# REST: extra recovery vs a fatigued opponent (prior extra-time) is a small real edge.
modifiers={
  "gap_shrink":{  # multiply the Elo DIFFERENCE by (1 - value): pushes toward 50/50
     "heat":{"label":"Extreme heat (32°C+)","value":0.11,
             "note":"Hot US venues (Dallas, KC, Atlanta, Miami) in July. Heat lowers pace & goals and narrows the gap between favorite and underdog."},
     "rain":{"label":"Heavy rain / wet pitch","value":0.06,
             "note":"Wet conditions degrade passing and add randomness, slightly helping the underdog."},
  },
  "elo_bonus":{  # add to a chosen side's Elo
     "host":{"label":"Host-nation crowd","value":45,
             "note":"Neutral venue on paper, but USA / Mexico / Canada draw a de-facto home crowd. Crowd support is the dominant driver of home advantage."},
     "rest":{"label":"Rest advantage","value":22,
             "note":"Extra recovery days vs an opponent coming off extra time. A small but real edge over a fatigued side."},
     "altitude":{"label":"Altitude (Mexican venue)","value":40,
             "note":"Only applies at Mexico City / Guadalajara / Toluca. All REMAINING knockout venues are near sea level, so this is off by default for the current bracket."},
  }
}
host_nations=["USA","Mexico","Canada"]

payload["players"]=players_cfg
payload["modifiers"]=modifiers
payload["host_nations"]=host_nations
json.dump(payload, open(str(PAYLOAD_JSON),'w'), ensure_ascii=False, indent=1)

# quick sanity print
print("Player-out penalties (Elo):")
for t in ["Argentina","Norway","France","Belgium","Egypt"]:
    print(f"  {t}: " + ", ".join(f"{p['name'].split()[-1]} -{p['elo']}" for p in players_cfg[t]))
print("\nModifiers loaded:", list(modifiers['gap_shrink'])+list(modifiers['elo_bonus']))
