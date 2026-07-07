"""Extract each alive team's top scorers and goal share from the live 2026 data.
Writes data/players.json. The 'alive' list is derived from the bracket in
gen_payload; edit ALIVE here if the tournament advances and teams change."""
import json
from collections import defaultdict
from paths import WORLDCUP_JSON, PLAYERS_JSON

ALIVE = ["France","Morocco","Norway","England","Spain",
         "Belgium","Argentina","Switzerland","Colombia"]

def build():
    d = json.load(open(WORLDCUP_JSON))
    team_players = defaultdict(lambda: defaultdict(int))
    team_goals = defaultdict(int)
    for m in d["matches"]:
        if "score" not in m: continue
        for side, team in (("goals1", m["team1"]), ("goals2", m["team2"])):
            for g in m.get(side, []):
                team_players[team][g["name"]] += 1
                team_goals[team] += 1
    out = {}
    for t in ALIVE:
        ranked = sorted(team_players[t].items(), key=lambda x: -x[1])[:5]
        tg = team_goals[t] or 1
        out[t] = [{"name": n, "goals": g, "share": round(g/tg, 3)} for n, g in ranked]
    json.dump(out, open(PLAYERS_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"players.json written for {len(out)} teams")

if __name__ == "__main__":
    build()
