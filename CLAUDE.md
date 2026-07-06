# CLAUDE.md — project guide for Claude Code

World Cup 2026 knockout predictor: an Elo model + Monte Carlo simulation with a
self-contained interactive front end. This file explains how the pieces fit so
you can make changes without breaking the pipeline.

## The one command that matters

```bash
python pipeline.py            # fetch live data -> rebuild model -> rebuild site
python pipeline.py --no-fetch # rebuild from cached data in data/ (offline)
python pipeline.py --backtest # also run the rigorous multi-World-Cup backtest
```

`pipeline.py` runs the steps in dependency order. Never run the individual
scripts out of order — later steps read files earlier steps write.

## Data flow (what writes what)

```
fetch_data.py     ->  data/intl_results.csv, data/shootouts.csv, data/worldcup2026.json
build_players.py  ->  data/players.json         (per-team goal share, from worldcup2026.json)
simulate.py       ->  data/sim_results.json     (50k Monte Carlo championship odds)
gen_payload.py    ->  data/payload.json         (teams, bracket, odds, reliability curve)
add_modifiers.py  ->  data/payload.json (+players, +modifiers)   <- edits payload in place
build_site.py     ->  site/index.html           (embeds payload.json into the HTML)
```

`site/index.html` is **self-contained** — the model data is embedded as a
`const DATA = {...}` block, so the page opens with no server and no fetch.
`build_site.py` replaces that block each run; don't hand-edit the embedded JSON.

## Key files

- `src/elo_engine.py` — Elo core. eloratings.net methodology: K by match
  importance, goal-difference multiplier, divisor 400, neutral venue for WC.
  `load_and_build()` computes ratings chronologically from the results CSV.
- `src/rigorous_backtest.py` — leak-free backtest across 2006–2022. Freezes Elo
  before each tournament, reports model vs favorite-baseline accuracy + Brier +
  log-loss + a reliability table. This is the credibility centerpiece.
- `src/simulate.py` — Monte Carlo of the remaining bracket. `ALPHA` blends career
  Elo with in-tournament form. `R16_REMAINING` + the QF/SF/Final wiring encode
  the bracket; update these as games are played.
- `src/gen_payload.py` — assembles everything the front end needs.
- `src/add_modifiers.py` — Match Lab config. Player-out penalties are derived
  from goal share; environmental/situational modifiers are in Elo points with
  cited rationale. All magnitudes live here — edit here, not in the HTML.
- `src/paths.py` — every script imports paths from here. Don't hardcode paths.
- `site/index.html` — the tool (bracket pick-em, title odds, Match Lab, calibration).

## Common tasks

- **Refresh after new results are played:** `python pipeline.py` (the fetch step
  pulls updated fixtures). If the bracket advanced a round, also update the
  bracket wiring in `simulate.py` and the R16 block in `gen_payload.py`, and the
  `ALIVE` list in `build_players.py`.
- **Change a modifier's magnitude or add a factor:** edit `src/add_modifiers.py`,
  then `python pipeline.py --no-fetch`.
- **Tune the model:** edit `src/elo_engine.py` (K values, multiplier, divisor) or
  `ALPHA` in `simulate.py`, then rerun with `--backtest` to check it didn't hurt
  calibration.

## Guardrails / intent

The project's whole value is intellectual honesty. When changing the model:
- Keep the backtest leak-free (freeze before each tournament; never tune params
  on the tournaments being scored).
- Don't lead with accuracy — the favorite-baseline nearly matches it. Calibration
  (the reliability table) is the real metric.
- Modifier magnitudes must stay defensible and documented in `add_modifiers.py`.
- Player value is proxied by goal share, which under-weights defenders/keepers.
  That's a known, stated limitation — don't quietly paper over it.

## Automation

`.github/workflows/refresh.yml` runs `python pipeline.py` daily and auto-commits
refreshed `data/` + `site/`. If you change the pipeline's outputs or file paths,
keep that workflow's `git add data/ site/` line in sync. The workflow needs no
secrets. To pause it, disable it in the repo's Actions tab.

## Data sources

- martj42/international_results (results.csv, shootouts.csv) — full international
  match history, 1872–present, live-updated.
- openfootball/worldcup.json — 2026 fixtures, scores, and goalscorers.
Not affiliated with FIFA. Portfolio project.
