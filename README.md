# World Cup 2026 — Elo Knockout Predictor

I built this to settle an argument I keep having: once you strip out the flags
and the vibes, who is actually likely to win the 2026 World Cup? So it's an Elo
rating model and a Monte Carlo simulation of the knockout bracket, wrapped in a
single interactive page you can poke at.

**The tournament's over — Spain beat Argentina 1–0 in extra time on July 19th.**
So the site is now a graded retrospective: all 16 knockout games locked to their
real results, each one carrying the model's honest *pre-tournament* call, plus a
scorecard on how those calls would have paid out at fair odds. Throw two teams
into a "Match Lab" and change the weather or bench a star, and (the part I care
about most) check the calibration that tells you whether the numbers were ever
worth trusting in the first place.

The ratings come from about 49,500 real international matches going back to 1872,
using the [World Football Elo Ratings](https://www.eloratings.net/about) method.
I validated the whole thing against the last five World Cups with a backtest
that's careful not to cheat, which turns out to be the interesting part.

Not affiliated with FIFA. This is a portfolio project.

## Quick start

```bash
python pipeline.py        # fetch live data, rebuild the model, rebuild the site
open site/index.html      # or just double-click it
```

The pipeline is pure standard-library Python, so there's nothing to
`pip install`. (There's one optional dependency, `playwright`, and only if you
want to run the headless render test.)

## What you can do with it

**Read the graded bracket.** All 16 knockout games, locked to their real scores,
each one carrying the model's *pre-tournament* call and a ✓ or ✗ for whether it
got it right. One frozen rating, applied the same way from the Round of 16 to
the Final — no cherry-picking, no hindsight.

**See what trusting it would've been worth.** The model went 13 for 16. Price
those calls at fair odds (no bookmaker's cut) and a flat $5 on every pick would
have turned $80 into $94 — not a betting system, just an honest look at what the
calibration bought you this time around.

**Break things in the Match Lab.** Drop any two teams from the 2026 knockout
field into a hypothetical and start turning knobs: sit a player (weighted by how
much of their team's scoring they actually account for), crank up the heat, soak
the pitch, hand one side a host crowd or an extra day of rest. The Elo and the
win probability move as you go.

**See the calibration.** A reliability curve pulled straight from the backtest,
showing that when the model calls something close to a coin flip, it lands like one.

## The one honest paragraph about accuracy

Here's the thing most prediction projects won't say out loud. Across the last
five World Cups (2006–2022, 320 matches), this model gets about 56% of results
right three ways — which is basically a tie with the dumbest baseline there is,
"always pick the higher-rated team," also around 56%. That's not a failure; it's
the whole point. On most World Cup games everyone already knows who's better, so
raw accuracy can't tell a real model apart from a shrug. What actually matters is
calibration: when the model gives a favorite a 35% chance, does the underdog
really win about 65% of the time? It does. The full write-up, including how I kept
the backtest from cheating, is in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

2026 itself turned out to be a decent stress test of that idea. The model called
13 of the 16 knockout games correctly, missing on two real upsets (Norway over
Brazil, Switzerland over Colombia on penalties) and one third-place shootout
(England over France). Three misses out of sixteen isn't a broken model — over
one tournament, it's close to exactly what a well-calibrated one should produce.

## Keeping it live (well, it isn't anymore)

There's a GitHub Actions workflow (`.github/workflows/refresh.yml`) that used to
re-run the pipeline every morning at 09:00 New York time and commit the fresh
`data/` and `site/` if anything changed — that's how the bracket stayed current
through the tournament without me touching it. Now that the final's been played,
the daily schedule is off (nothing left to refresh), but the workflow's still
there as `workflow_dispatch` if I ever need to rerun it by hand, and as a
starting point for the next tournament.

`pipeline.py` also stopped calling `simulate.py` for the same reason results are
now frozen: the results feed includes the final's own score, so re-running the
Monte Carlo today would leak that result into its own "prediction" of it.
`data/sim_results.json` stays frozen at its last pre-final run — exactly the
53.6% / 46.4% the site showed for Spain and Argentina before kickoff.

## How the repo is laid out

```
pipeline.py            # one command to rebuild everything
src/
  fetch_data.py        # pull live source data
  elo_engine.py        # Elo core (eloratings.net methodology)
  build_players.py     # per-team goal share -> data/players.json
  simulate.py          # 50k Monte Carlo -> data/sim_results.json (frozen post-final, see above)
  gen_payload.py       # assemble the front-end payload, incl. the 16-game scorecard
  add_modifiers.py     # Match Lab modifier config (documented magnitudes)
  build_site.py        # embed payload into site/index.html
  rigorous_backtest.py # leak-free multi-World-Cup validation
  paths.py             # central path resolution
data/                  # raw + derived data (regenerated by the pipeline)
site/index.html        # the self-contained interactive tool
docs/METHODOLOGY.md    # model + backtest write-up
```

## Where the data comes from

- [martj42/international_results](https://github.com/martj42/international_results)
  — international match history and shootouts, kept up to date.
- [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
  — 2026 fixtures, scores, and goalscorers.

## What it doesn't do well

I'd rather say this here than have you find it on your own:

- Player value is proxied by share of tournament goals. That's fair to strikers
  and wingers and pretty unfair to defenders and keepers, who barely register.
- Draw probabilities come from an empirical draw-width, not a real scoreline model.
- The Match Lab's environmental knobs are honest estimates in Elo points,
  documented in `src/add_modifiers.py`. They're reasonable magnitudes, not
  regression-fitted coefficients — the goal is to show which way a match moves,
  not to fake precision.

## License

MIT.
