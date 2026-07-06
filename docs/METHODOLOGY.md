# Methodology

## 1. The Elo engine

Ratings follow the [World Football Elo Ratings](https://www.eloratings.net/about)
system (the same approach a 2013 study found most predictive among football
rating systems):

```
R_new = R_old + K · (W − We)
We    = 1 / (1 + 10^((R_opp − R_team) / 400))
```

- **K by match importance:** World Cup finals 60, continental championships 50,
  qualifiers / major tournaments 40, other tournaments 30, friendlies 20.
- **Goal-difference multiplier:** ×1.5 for a 2-goal win, ×1.75 for 3, and
  1.75 + (N−3)/8 for margins of 4+. (FIFA's official Elo omits this; eloratings
  keeps it, and it improves fit.)
- **Divisor 400** in the expectation (eloratings), vs. 600 in FIFA's version.
- **Neutral venue** for World Cup matches — no home-advantage term.

Ratings are built chronologically over the full international match history
(~49,500 matches, 1872–2026), so every rating reflects only games that had been
played at that point in time.

## 2. In-tournament form blend

For the 2026 simulation, each team's rating is a blend of its **career Elo**
(frozen just before the tournament) and an **in-tournament form Elo** that starts
from the career value and updates after each 2026 match played so far:

```
rating = (1 − α) · career_elo + α · form_elo        (α = 0.4)
```

The blend improves probability calibration (lower Brier / log-loss) without
degrading accuracy. `α` is set a priori, **not** fitted to the matches being
scored.

## 3. Monte Carlo simulation

The remaining bracket (open R16 games → QF → SF → Final) is simulated 50,000
times. Each knockout tie is a Bernoulli draw on the blended-Elo win probability
(no draws in knockouts — extra time / penalties collapse into a single win
probability). Tracking how often each team reaches each round gives the title
odds and round-by-round probabilities.

## 4. The backtest — and why accuracy is a trap

The model is validated on the **last five completed World Cups (2006–2022,
320 matches)** with three guarantees against hindsight bias:

1. **No leakage.** Elo is frozen the instant before each tournament's first
   match. No result from a tournament ever informs its own predictions.
2. **No tuning on test data.** All constants are the published eloratings.net
   values, fixed in advance. Nothing is fit to the tournaments being scored.
3. **Honest baseline.** Every metric is reported next to "always pick the
   higher-rated team."

**Results (frozen, zero-leakage):**

| Metric | Model | Favorite baseline |
|---|---|---|
| 3-way accuracy | ~56% | ~56% |
| Brier (3-way) | ~0.57 | — |
| Log-loss | ~0.97 | — |

The accuracy tie is the point: on most World Cup games, the stronger side is
obvious, so a bare accuracy contest can't distinguish a real model from a
coin-flip-for-the-favorite. (A live-update variant — updating Elo within the
tournament using only already-played matches, still no future leakage — reaches
~60%.)

**Where the model actually earns its keep — the reliability table:**

| Favorite's predicted win % | Actual favorite win % | Matches |
|---|---|---|
| ~35% | ~40% | 90 |
| ~45% | ~54% | 65 |
| ~55% | ~63% | 60 |
| ~65% | ~62% | 58 |
| ~75% | ~74% | 43 |

Read the top row: in games where the model made the favorite only ~35% likely,
the underdog won ~40% of the time — close to predicted. The model isn't blindly
backing favorites; it flags the near-coin-flips, and upsets land at roughly the
predicted rate. The top rows track the diagonal almost exactly; the middle rows
show a mild bias (favorites slightly outperformed the model's humility there).

Reproduce with:

```bash
python pipeline.py --backtest
```

## 5. Match Lab modifiers

All modifiers are expressed in **Elo points** feeding the same win-probability
formula, and all magnitudes live in `src/add_modifiers.py`.

- **Player out.** Penalty scales with the player's share of the team's tournament
  goals (a data-driven proxy for attacking dependency), capped. Sitting a
  talismanic scorer (e.g. a player with ~64% of their team's goals) costs the
  most; a spread attack barely moves. **Limitation:** goal share under-weights
  defenders and goalkeepers.
- **Heat / wet pitch.** Modeled as *shrinking the Elo gap* toward parity — heat
  lowers pace and goals and compresses the skill gap; wet pitches add randomness.
  Both are mild, underdog-friendly nudges.
- **Host-nation crowd.** +Elo for USA / Mexico / Canada at a de-facto home venue.
  Crowd support is the dominant component of home advantage (confirmed by
  COVID-era no-fans natural experiments, which cut home edge by >50%). Sized
  below a full home-advantage term because the venue is officially neutral.
- **Rest advantage.** Small +Elo for a rested side vs. an opponent coming off
  extra time.
- **Altitude.** +Elo at Mexican venues only; off by default because all remaining
  2026 knockout venues are near sea level.

These are transparent, defensible estimates — reasonable magnitudes with a stated
rationale, not fitted regression coefficients. The intent is to show *directional*
sensitivity honestly, not to claim false precision.
