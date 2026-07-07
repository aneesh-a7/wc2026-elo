# Methodology

This is the long version: how the ratings get built, how I simulate the bracket,
and how I tried to keep myself honest when checking whether any of it works.

## 1. The Elo engine

The ratings use the [World Football Elo Ratings](https://www.eloratings.net/about)
system — the one a 2013 study found most predictive among the football rating
systems it compared. The core is the standard Elo update:

```
R_new = R_old + K · (W − We)
We    = 1 / (1 + 10^((R_opp − R_team) / 400))
```

A few choices worth spelling out:

- **K scales with how much the match matters.** World Cup finals get 60,
  continental championships 50, qualifiers and other major tournaments 40, lesser
  tournaments 30, friendlies 20. A friendly shouldn't move a rating the way a
  knockout game does.
- **Goal-difference multiplier.** A two-goal win counts ×1.5, three goals ×1.75,
  and bigger margins 1.75 + (N−3)/8. FIFA's official Elo drops this; eloratings
  keeps it and it fits better, so I kept it too.
- **Divisor of 400** in the expectation, which is the eloratings choice; FIFA
  uses 600.
- **Neutral venue for World Cup games** — no home-advantage term at all.

Everything is computed in chronological order across the full international record
(~49,500 matches, 1872–2026). That ordering matters: a team's rating on any given
day only reflects games that had already been played by then. No peeking ahead.

## 2. Blending in current form

Career Elo is stable, which is usually a virtue and occasionally a problem — a
team can show up to a tournament clearly better or worse than its long-run number.
So for the 2026 sim I blend two ratings: the **career Elo**, frozen just before
the tournament, and a **form Elo** that starts from that same value and updates
after each 2026 game played so far.

```
rating = (1 − α) · career_elo + α · form_elo        (α = 0.4)
```

The blend improves calibration (lower Brier and log-loss) without hurting
accuracy. And α is chosen up front — it is **not** fit to the games I'm about to
grade myself on. That distinction matters more than it sounds; the next section is
all about it.

## 3. Simulating the bracket

I take the games that are left — the open Round-of-16 ties, then QF → SF → Final —
and play the whole thing out 50,000 times. Each knockout tie is a single coin
flip weighted by the blended-Elo win probability. There are no draws here: extra
time and penalties always produce a winner, and they fold into that one
probability. Count how often each team survives to each round and you get the
title odds and the round-by-round numbers.

## 4. The backtest, and why "accuracy" is a trap

I tested the model on the **last five completed World Cups (2006–2022, 320
matches)**, under three rules meant to stop me from cheating:

1. **No leakage.** Elo is frozen the instant before each tournament's opening
   match. Nothing that happens in a World Cup is ever allowed to inform
   predictions about that same World Cup.
2. **No tuning on the test set.** Every constant is a published eloratings.net
   value, fixed ahead of time. I didn't fit anything to the tournaments I was
   scoring.
3. **An honest baseline.** Every number sits next to "just pick the higher-rated
   team," so you can see what the model adds over doing nothing clever.

**Frozen, zero-leakage results:**

| Metric | Model | Favorite baseline |
|---|---|---|
| 3-way accuracy | ~56% | ~56% |
| Brier (3-way) | ~0.57 | — |
| Log-loss | ~0.97 | — |

The accuracy tie *is* the finding, not an embarrassment. On most World Cup games
the stronger side is obvious, so an accuracy contest mostly rewards knowing that
the giant beats the minnow — which a coin that always picks the favorite "knows"
just as well. (For the curious: a live-update variant, which lets Elo move within
a tournament using only games already played, still with no future leakage, gets
to about 60%.)

The place the model actually has to prove itself is calibration:

| Favorite's predicted win % | Actual favorite win % | Matches |
|---|---|---|
| ~35% | ~40% | 90 |
| ~45% | ~54% | 65 |
| ~55% | ~63% | 60 |
| ~65% | ~62% | 58 |
| ~75% | ~74% | 43 |

Read the top row like this: in the games where the model gave the favorite only
about a 35% chance, the underdog went on to win about 40% of the time — right
about where it was supposed to. The model isn't rubber-stamping favorites; it
points at the near coin-flips, and the upsets show up at roughly the rate it
predicted. The top rows sit almost exactly on the diagonal. The middle rows drift
a little — favorites there did slightly better than the model's caution expected —
which I'd rather show you than quietly smooth over.

Reproduce it yourself:

```bash
python pipeline.py --backtest
```

## 5. The Match Lab knobs

Every modifier is expressed in Elo points feeding the same win-probability
formula, and every magnitude lives in one file, `src/add_modifiers.py`, so nothing
is buried in the front end.

- **Sitting a player.** The penalty scales with that player's share of the team's
  tournament goals — a rough proxy for how much the attack leans on them — and
  it's capped. Bench someone carrying ~64% of their team's goals and it stings;
  bench one piece of a spread-out attack and it barely registers. The obvious
  limitation: goal share flatters attackers and badly under-rates defenders and
  keepers.
- **Heat and a wet pitch.** Both work by shrinking the Elo gap toward parity
  rather than favoring a particular side. Heat drags down pace and scoring; a wet
  pitch adds noise. Either way it's a mild nudge in the underdog's favor.
- **Host crowd.** A bump for the USA, Mexico, or Canada playing in front of what
  is effectively a home crowd. Crowd support turns out to be most of what home
  advantage even is — the empty-stadium COVID seasons cut the home edge by more
  than half — but I size this below a full home-advantage term because the venue
  is officially neutral.
- **Rest.** A small edge for a team that's had more recovery than an opponent
  coming off extra time.
- **Altitude.** A bump at Mexican venues only, and off by default, because the
  remaining 2026 knockout venues are all near sea level.

None of these are fitted coefficients. They're transparent, defensible estimates —
sensible sizes with a reason attached. The point of the Match Lab is to show
honestly which way a factor pushes a match, not to pretend I can price it to the
decimal.
