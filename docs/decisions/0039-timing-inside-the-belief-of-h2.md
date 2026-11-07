# 0039. Timing inside H2's belief: two mechanism-based states, a shrunk and sign-constrained coefficient, kept only if it beats the untimed twin

Status: **Rejected by experiment 016** (timed H2 was worse than untimed; the code was deleted, commit 394314e holds it)   Date: 2026-11-07   Where: `agents/momentum.py` (`TimedMomentum`)   Evidence: [exp 016](../experiments/016-timing-inside-h2.md)

## Context
Plan decision 0034: each admitted agent is run timed against its untimed twin on the same dev data and timing is kept only if it helps. H2 was admitted in experiment 015b. Timing cannot create an edge; it can only help where an edge varies with an observable state. The skill of a per-period trend signal is very noisy (two coins: the per-period slope has a standard deviation of about 0.7 against a card IC of 0.05), so an unconstrained state regression would mostly fit noise.

## Decision
IC(state) = IC0 + c . s, clipped to [0, 2 IC0], belief = IC(state) x sigma_H x z, the rest of the agent (card, kill rule, universe) unchanged.
- **States (two, from BTC returns in the history window, standardised on past states only):** bull = t-statistic of BTC's return over the window (momentum is concentrated in bull markets; Han, Kang, Ryu), predicted coefficient >= 0; panic = log of BTC's 30-day volatility over its window volatility (momentum crashes follow high-volatility rebounds; Daniel and Moskowitz), predicted coefficient <= 0. Both predictions are from the mechanisms and are written here before any timed run.
- **Estimation:** walk-forward, information before the decision. y_t = slope of volatility-standardised realised returns on z in each past period; c = ridge of y on the standardised states with the Bayesian prior c ~ N(0, tau^2), tau = IC0/2, so lam = var(y)/tau^2 pseudo-periods (about 800 on 1d: the state coefficient is shrunk by about three quarters at 280 periods). A coefficient of the wrong predicted sign is set to zero. Nothing is tuned: no value here was chosen by looking at P&L.
- **Burn-in:** the untimed card belief until 30 periods are observed.
- Not included: a conditional-variance forecast scaling the agent's stake (the priced system volatility limit already acts on variance).

## Consequences
At most one more trial (the timed variant). Timing is a bounded multiplier of the card IC, between 0 and 2 times, so the worst case is switching H2 off or doubling its belief, which the volatility limit then rescales.

## Rollback
Delete `TimedMomentum`; the untimed agent is unchanged.
