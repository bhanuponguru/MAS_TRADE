# Building a Multi-Agent Portfolio System for Crypto Perpetuals: A Research Record

*Resilient Decentralised Portfolio Consensus, from the first prototype to the final evaluation*

AI3403 Multi-Agent Systems, project report. The work ran from 18 October to 9 November 2026 on one repository, with two contributors. Evidence is from the development period (April 2020 to November 2025); the final twelve months of data were sealed and have not been examined. Nothing was traded live. Experiments are numbered 001 to 023 and decisions 0001 to 0045 in the repository. Commit hashes are given so that every step can be checked in the git history.

## Abstract

This report tells, in order, what we did and why. We started with a consensus-based multi-agent portfolio system on US stocks (trust-weighted W-MSR consensus, capital that flows between agents, a robust defence against one compromised agent). We moved it to Binance crypto perpetual futures, built a second engine judged on absolute return, and added a temporal-logic safety layer. Ten experiments showed a consistent pattern: only one trading idea (funding carry) earned money after costs, no way of combining agents beat a simple average, and the "multi-agent" layer was a distributed solver of a problem a central optimiser solves identically. We therefore rebuilt the system from scratch around three ideas: agents that are documented trading hypotheses, a market in which agents stake capital on their own beliefs, and a joint convex optimisation solved by ADMM in which limits and trading costs are prices. We validated this on simulated markets, then on real data with one agent (carry), then with more agents (momentum, reversal). A bug in the risk limit changed several conclusions and forced a full re-run. We then removed the central node of the optimisation, studied network topology, link failures and a lying agent, added a signal-temporal-logic safety monitor with supervisors, and finished with a single comparison and a multiple-testing correction.

The main results: the decentralised system reproduces the centralised one to within 0.002 Sharpe under every network and failure condition tested; the capital market protects against a bad agent (about +0.9 Sharpe over a fixed mix) but adds no return over a fixed mix of good agents; carry is a real edge; and the combined system's Sharpe of about 1.4 to 1.5 does not survive correction for the 45 strategy variants tried (deflated Sharpe about 0.1 against 0.95). Many pre-registered gates failed, and we report them.

## How to read this report

The report follows the order of the work. Each phase has the same five parts, so you always know where you are:

1. **Why.** What the previous phase left unanswered.
2. **What we built.** The idea, with the mathematics it needs, introduced only when it is first used.
3. **Experiment.** The question, the rule fixed in advance, and the result.
4. **What we learned.**
5. **What it led to.** The next phase.

| Phase | Dates | Question | Outcome |
|---|---|---|---|
| 1 | 18 Oct | Can trust-weighted consensus beat its own agents on US stocks? | No; it reduces risk and resists one attacker, but adds nothing over a plain average |
| 2 | 1 to 5 Nov | Does it work on crypto perpetuals, and which ideas earn money after costs? | No edge vs Bitcoin; only carry earns money; no combiner beats a simple average |
| 3 | 5 Nov | Can a temporal-logic shield keep the system safe? | Yes, at little cost on stocks; limits need a mandate argument |
| 4 | 6 Nov | What do ten experiments tell us to do? | Rebuild around hypotheses, a capital market and ADMM prices |
| 5 | 6 Nov | Does the new machinery behave when the truth is known? | Mostly; two failures shaped the design |
| 6 | 7 Nov | Does the new engine reproduce carry on real data? | Yes, after fixing the belief calibration |
| 7 | 7 Nov | Do more agents help? Does timing help? | Momentum added, timing rejected, reversal rejected |
| 8 | 8 Nov | Do the conclusions survive a corrected risk limit? | Numbers changed; one admission decision flipped |
| 9 | 8 Nov | Can the optimiser run without a central node? | Yes, same portfolio |
| 10 | 8 Nov | What do network shape and link failures do? | Shape sets communication cost, not the outcome |
| 11 | 8 Nov | What about a dropped or lying agent, and W-MSR? | Absorbed or isolated on robust graphs; W-MSR trimming rejected |
| 12 | 8 to 9 Nov | Does a formal safety monitor with supervisors work? | Partly |
| 13 | 9 Nov | One comparison table, and the multiple-testing correction | Mechanisms match the reference; the return claim fails the correction |

Sections 14 to 16 draw the conclusions. Appendix A lists every experiment, Appendix B every decision, Appendix C the glossary and Appendix D how to reproduce any step from git.

## 0. Common tools

These are used throughout. Later sections refer back to them.

**Net return and Sharpe ratio.** All returns are net of fees, price impact and funding payments. The annualised Sharpe ratio is $\mathrm{SR}=\sqrt{P}\,\bar r/s_r$, where $P$ is the number of bars per year and $\bar r$, $s_r$ are the mean and standard deviation of per-bar net returns. About 1 is decent and above 2 is exceptional.

**Uncertainty.** Return series are autocorrelated and fat-tailed, so we use a *moving-block bootstrap*: resample blocks of 7 days with replacement, recompute the statistic, repeat 500 times, and report the 5th and 95th percentiles (a 90% interval). To compare two strategies we resample the *same* blocks for both and look at the difference of their Sharpe ratios (a *paired* difference).

**Alpha.** To separate skill from market exposure we regress a strategy's return on Bitcoin's: $r_t=\alpha+\beta\,r^{\mathrm{BTC}}_t+\epsilon_t$, and report $\alpha$ annualised with a block-bootstrap interval.

**Skill of a signal.** The *rank information coefficient* (IC) is the Spearman correlation between a score and the next return across coins. A small positive IC (0.02 to 0.05) is typical of a real signal.

**Research discipline.** Four rules were adopted in the first week and kept: (1) no lookahead, with a test that fails if any quantity at time $t$ uses data from $t$ or later; (2) the last 12 months of data are *sealed*: reported only once, at the end; (3) every variant tried is written to an append-only *trial log*, so that a multiple-testing correction (the deflated Sharpe, Section 13) can count them; (4) from Phase 4 on, the pass or fail rules of each experiment are written and committed *before* the runs. Where a rule was added or changed after seeing results, the text says so.

## 1. Phase 1: a trust-weighted consensus system on US stocks (18 October, commit `b48056d`)

### 1.1 Why

The course covers consensus, resilient consensus (W-MSR), ADMM, distributed learning and temporal logic. The first goal was to build one system that uses them, with a clear test: does a group of simple forecasting agents, coordinating by consensus, do better or more safely than the agents alone?

### 1.2 What we built

*Universe and agents.* Twenty US large caps (2015 to 2025, daily prices from a public source), and six simple forecasting agents: momentum, mean reversion, a shrinkage mean, a first-order autoregression, an exponentially weighted trend, and a low-volatility tilt. Each agent $i$ forecasts expected returns $\mu_i\in\mathbb{R}^N$ from the past year of data only and proposes a long-short portfolio with gross exposure one:
$$w_i=\frac{\mu_i}{\sum_a\lvert\mu_{ia}\rvert}.$$
A seventh, *adversarial* agent was part of the model from the start: it puts all its capital on one random stock on a random side and ignores what others say.

*Trust.* An agent's trust is the forecast probability that it makes money over the next holding period of $H$ days. From the exponentially weighted mean $m_i$ and standard deviation $\mathrm{sd}_i$ of its *stand-alone* daily returns (tracked from before trading starts),
$$s_i=\Phi\!\Big(\frac{m_i\sqrt{H}}{\mathrm{sd}_i}\Big).$$

*Consensus.* Agents agree on portfolios over a communication graph with adjacency $a_{ij}$. The consensus matrix listens more to trusted neighbours:
$$W_{ij}=\frac{a_{ij}\,s_j}{\sum_l a_{il}\,s_l}\qquad(\text{rows sum to one}).$$
Each rebalance runs $K=10$ rounds of **W-MSR**: in every coordinate (stock) an agent discards the $F$ neighbour values above its own that are largest and the $F$ below its own that are smallest, then averages the rest with weights from $W$. With $F=1$ one malicious neighbour is tolerated; $F=0$ is plain consensus. *Pinning* (leader-follower) keeps part of each agent's own view: $x\leftarrow(1-b)\,\mathrm{WMSR}(x)+b\,w_i$ with $b=0.3$.

*Capital.* Each agent controls its own dollars $c_i$. At each rebalance capital moves through the transpose of $W$:
$$c\leftarrow(1-\eta)\,c+\eta\,W^{\top}c,\qquad \eta=0.5 .$$
Since $W$ has rows summing to one, total capital $\sum_i c_i$ is conserved (this is asserted in the code), and capital drifts towards trusted agents. A floor of 2% of total capital keeps every agent alive.

*Execution.* The system position is $h=\sum_i c_i x_i$. Opposite trades by different agents cancel inside $h$, and the cost of 5 basis points per dollar is charged on the change of $h$ only.

*Alternative mode.* Consensus by ADMM instead of W-MSR: agent $i$ minimises its own view plus a shared risk term, $f_i(x)=-w_i^{\top}x+\tfrac{\gamma}{2}x^{\top}\Sigma x$, and agrees on a trust-weighted average. This is a mean-variance portfolio, a different problem from W-MSR consensus.

### 1.3 Experiments 001 to 004 (US stocks, 2017 to 2025, 5 bp costs)

**001: does the system beat its own agents?**

| Strategy | CAGR | Vol | Sharpe | Max drawdown |
|---|---|---|---|---|
| Equal-weight long-only | 19.1% | 17.8% | 1.07 | −31.8% |
| Best single agent (shrinkage mean) | 17.3% | 18.5% | 0.96 | −30.7% |
| **Naive average of the agents** | 10.7% | 12.1% | **0.90** | −18.1% |
| **Consensus system (W-MSR)** | 13.1% | 17.1% | **0.81** | −25.9% |
| Worst agent (mean reversion) | −1.2% | 15.7% | 0.00 | −42.6% |

The consensus system did *not* beat the naive average of its own agents (0.81 against 0.90) and traded more (turnover 5.0 against 4.0 times capital a year). Capital moved slowly: after nine years the worst agent still held 12% of capital.

**002: W-MSR against ADMM.** ADMM consensus gave Sharpe 0.33 with a third of the volatility, because it solves a different (mean-variance) problem. With ten iterations it was already close to its one-node optimum (0.27): the first sign that the "distributed" solver found what a central one finds.

**003: one compromised agent.**

| | Sharpe | Max drawdown |
|---|---|---|
| Clean system | 0.81 | −25.9% |
| One attacker, plain consensus ($F=0$) | 0.46 | −35.5% |
| One attacker, W-MSR ($F=1$) | 0.74 | −27.5% |

W-MSR recovered most of the loss. The protection came from trimming the *portfolios*, not from capital flow: the attacker ended with 9.8% of capital in every attacked run.

**004: a second level of capital (built on 1 November, see Phase 2).** A hierarchy gave each (strategy, stock) pair its own sub-agent with its own capital. It lowered volatility and turnover at the same Sharpe (0.80), but was less resilient under attack (0.66 against 0.74).

### 1.4 What we learned

1. The consensus and capital machinery did not add return over a plain average of agents; its value was risk reduction and resilience.
2. The one clear multi-agent result was W-MSR protecting against one attacker, and it worked by trimming, not by capital.
3. Against long-only holdings in a bull market the comparison mostly measured market exposure.

### 1.5 What it led to

Two questions: does this behave differently on a market with no easy long bias (crypto, 24 hours a day), and are the agents good enough? Both led to Phase 2.

## 2. Phase 2: crypto perpetuals, a second engine, and a decentralised combiner (1 to 5 November, commits `47fa8ee`, `92ccc47`)

### 2.1 Why

Stocks have a strong upward drift, so beating them is mostly about beta. Crypto perpetual futures trade around the clock, have a funding mechanism that makes them different from spot, and have a rich public data set. We also wanted a test that does not depend on a market benchmark.

### 2.2 What we built

*Data pipeline.* Binance USD-M perpetuals from the exchange's public data dump: klines, funding events, delisted symbols included. The universe is *point-in-time and survivorship-free*: a coin enters when its rank by the 90-day median daily dollar volume, computed strictly before the day, is within the top 50; it stays while within the top 75; the ranking is refreshed every 30 days. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded. Bars are stamped with their *open* time, so the return of bar $t$ is earned over bar $t$.

*Engine generalisation.* A coin is tradable only if it is in the universe and has a full history window; funding is charged to longs and paid to shorts; every schedule is expressed in bars, with three operating points: daily bars (rebalance every 14 days), four-hourly (every 5 days) and hourly (every 48 hours).

*The same consensus system on crypto* (called v1), plus the hierarchy of Section 1.3 and optional risk- and cost-aware capital speeds.

*A second engine, v2, judged in absolute terms.* The question changed from "does it beat Bitcoin" to "does it make money net of everything". v2 had three stages. *Books:* each agent's signal is rank-Gaussian transformed, projected to be dollar-neutral and Bitcoin-beta-neutral, and scaled to a volatility target (20% a year, gross cap 3). *Combiners:* equal weight, inverse volatility, an online-learning combiner (Fixed-Share Hedge), risk budgeting, and IC-calibrated view fusion. *Costs:* a taker fee plus square-root market impact, and a liquidity floor so that no coin with under one million dollars of daily volume is traded (a zero-volume coin once produced a 300% impact cost):
$$\text{cost}(d)=\lvert d\rvert\Big(\text{fee}+k\,\sigma_{\text{daily}}\sqrt{\lvert d\rvert\,\mathrm{AUM}/\mathrm{ADV}}\Big).$$
Four cross-sectional agents (momentum, residual reversal, funding carry, size) and one Bitcoin timing agent were used. v2 introduced the research discipline of Section 0 (sealed holdout, trial log, deflated Sharpe).

*A decentralised ADMM combiner (5 November).* Edge-form consensus ADMM over a ring in which each agent's local objective contained its view, a shared risk term and the *true* trading cost of the net trade.

### 2.3 Experiments 005 to 007

**005: the v1 consensus system on crypto, against Bitcoin (development period).**

| Bar | Bitcoin Sharpe | v1 system Sharpe | v1 volatility |
|---|---|---|---|
| Daily | 0.80 | −0.03 | 57% |
| 4-hourly | 1.04 | 0.25 | 74% |
| Hourly | 1.05 | 0.61 | 80% |

The v1 system had no edge over Bitcoin on any bar size, and held about 60 volatile coins at gross exposure one, running at 57% to 80% volatility. A first run failed because a missing day in the exchange's daily dump for *every* symbol emptied the universe; a day missing for all symbols is now treated as a dump hole and skipped.

**006: which agents earn money after costs (v2, development period, net Sharpe daily / 4-hourly / hourly).**

| Agent or combiner | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Funding carry | 1.03 | 0.99 | 0.88 |
| Bitcoin timing | 0.57 | 0.46 | 0.80 |
| Cross-sectional momentum | −0.42 | −0.23 | −0.15 |
| Residual reversal | −0.68 | −1.11 | −1.24 |
| Size and liquidity | −0.14 | −0.22 | −0.32 |
| Equal-weight combiner | 0.22 | −0.09 | −0.09 |
| Inverse-volatility combiner | 0.27 | −0.04 | 0.18 |

The rank IC of residual reversal was positive (0.025, 0.039, 0.049 on the three bar sizes) while its net Sharpe was negative: a signal can be real and still not tradable after costs. The rank IC of size was *significantly negative* ($t\approx-2.1$ to $-2.3$ on every bar size), and momentum's was about zero. No combiner beat the inverse-volatility average, and every combiner was worse than carry alone, because the other agents carried no net edge. After counting every variant tried, the deflated Sharpe was not significant for any row.

**007: does putting the true trading cost in the consensus objective lower cost drag?** No. Tests confirmed the decentralised result equals the one-node optimum and that neutrality and no-lookahead hold.

### 2.4 What we learned

1. Only carry (and, weakly, Bitcoin timing) earned money after costs; most of the other ideas did not.
2. Mixing agents cannot create information the agents do not have: with four agents of which three had no edge, every combiner lost to the single good one.
3. A real signal (reversal) can lose to trading costs. Costs must sit inside the optimisation, not after it.

### 2.5 What it led to

Safety: the system ran at 57% to 80% volatility with drawdowns up to 88%. The proposal also called for temporal-logic safety. Phase 3 addressed it.

## 3. Phase 3: a temporal-logic safety layer on the consensus system (5 November, commit `cf16351`, by the second contributor)

### 3.1 Why

A portfolio system needs formal safety requirements, monitored and, if needed, enforced. Signal temporal logic (STL) offers both a language for the requirements and a number, the *robustness*, for how close the system is to violating them.

### 3.2 What we built

*Quantitative STL.* For a real-valued signal $y$ and a limit $c$, the predicate $y\ge c$ has robustness $\rho(t)=y(t)-c$: positive means satisfied by that margin, negative means violated by that much. The operators are $\rho(\mathbf{G}_{[a,b]}\varphi,t)=\min_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (always) and $\rho(\mathbf{F}_{[a,b]}\varphi,t)=\max_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (eventually). Four specifications were monitored: a drawdown limit, a volatility limit, recovery from a volatility breach within a number of days, and a concentration limit. Robustness was normalised by each limit so that $-1$ means "twice over the limit".

*A shield.* A supervisor that, at each rebalance, scaled the portfolio towards cash when a specification was about to be violated, using only information from before the rebalance. The monitor always runs; the shield is opt-in.

*Limits from a mandate.* Each limit is justified by a risk-mandate argument, not by a backtest, because choosing limits by looking at performance is overfitting (decision 0026): for stocks a 15% drawdown over 252 days, 20% volatility, 10-day recovery, 20% per stock.

*A centralised reference.* The optimum of the ADMM consensus problem, solved by one node, as the benchmark for the distributed version.

### 3.3 Experiments 008 to 010

**008: shield on US stocks.** The shield cut violations roughly in half or better at almost no Sharpe cost. With daily checks (decision 0028) it cut the drawdown violations to a tenth: maximum drawdown $-18.6\%$ against $-25.9\%$ at the same Sharpe of 0.81.

**009: checks between rebalances.** A crash that starts mid-period (the 2020 COVID fall) was missed by a shield that acts only at rebalances. Daily checks reduced the worst volatility breach by two thirds (robustness $-1.51$ to $-0.50$) at a cost of 0.02 Sharpe and 15% more turnover. Adopted.

**010: how to split the cut across agents.** Cutting the agents that contribute most to risk, instead of cutting all agents alike, made the system *worse* with an attacker present: the attacker's single-stock bet looked low-risk, so honest agents were cut instead and the attacker's share grew (drawdown violations 0.3% to 10.5% on the test period). Risk contribution measures how much variance would fall if you cut an agent, not who is misbehaving. Uniform cuts were kept.

**On crypto (experiment 005).** The shield brought volatility to 20% to 26% and halved the maximum drawdown, but the drawdown specification was still violated on about 60% of bars. The cause was inconsistent limits (a 40% volatility limit with a 15% drawdown limit), visible from the limits alone; a fix was proposed but not applied.

### 3.4 What we learned

1. A shield is a risk control and not a return enhancer; it costs a little Sharpe and buys a lot of safety.
2. Limits must come from a mandate and must be consistent with each other.
3. Scaling a finished, cost-optimised portfolio re-trades the whole book: the shield sat *after* the optimisation instead of inside it.

### 3.5 What it led to

By 5 November the repository held two engines, v1 (consensus system, hierarchy, shield) and v2 (neutral books, combiners, decentralised ADMM). Decision 0022 proposed to build the proposal's system on v1 and freeze v2. The next day the evidence made us change course.

## 4. Phase 4: what ten experiments said, and the decision to rebuild (6 November, decision 0032, commit `7467db3`)

### 4.1 The evidence

Experiments 001 to 010 pointed the same way:
1. **Only one idea earned money after costs** (carry). Reversal had a real signal that costs ate; momentum and size had no edge in our liquid universe.
2. **No combiner beat a simple average**, because the agents carried too little information. Diversification multiplies information; it does not create it.
3. **The multi-agent layer added nothing over a central optimiser:** the consensus system did not beat its agents' average (001), ADMM consensus matched its one-node optimum (002), the decentralised combiner converged to the central solution by construction (007), and the true cost in the objective did not help (007).
4. **The safety layer worked but sat after the optimiser** (Phase 3), so it re-traded the book.

### 4.2 Options considered (decision 0032)

1. Keep both engines and add a third. This accumulates code nobody will run.
2. Freeze v2 and build on v1 (decision 0022).
3. **Replace both** with one implementation built around three ideas (chosen).

### 4.3 The new design, in one paragraph

*Agents are hypotheses.* Each agent is one established quantitative idea (carry, momentum, reversal, and so on) with a written *card*: the claim, the mechanism, the allowed coins, the predicted sign and size of its edge, and the rule that switches it off. *A capital market (Level 1).* Each agent stakes capital on its own belief, and its wealth follows its own results, so capital moves towards agents whose beliefs pay. *Joint optimisation by prices (Level 2).* All agents' stakes in all coins are turned into one portfolio by one convex problem solved by ADMM, in which trading cost on the *net* trade, margin, a gross cap, a market-beta band and a volatility limit are *prices*. *Safety inside the optimiser:* the volatility limit and beta band become priced constraints in the optimiser instead of a post-hoc rescale. *W-MSR dropped from the core:* a trimmed mean or a belief-size check gives the same protection more simply, and the earlier W-MSR result remains as history. *Evaluation:* absolute net Sharpe against zero, a sealed holdout, a trial log, and rules written before the runs.

### 4.4 What was kept and what was deleted

Superseded code was deleted, not preserved (decision 0032). History lives in three places: the experiment and decision records (001 to 031 are kept as written), the git tag `legacy-v1-v2` (commit `cf16351`), and small reference tables copied into the repository. Kept and moved: the data pipeline, the cost model, the covariance and beta estimation, the diagnostics (IC, deflated Sharpe, trial log), the performance statistics, the cost step of the ADMM, and the STL operators. The stock demo, W-MSR consensus, trust-weighted capital flow, the hierarchy, the adversary experiment and the v1 shield exist only at the tag.

### 4.5 What it led to

Phase 5: build the foundations and test each mechanism where the truth is known.

## 5. Phase 5: foundations, tested where the truth is known (6 November, commits `214ef28`, `5635d1e`, `4196905`, `e5fe402`)

### 5.1 Why

Before trusting anything on noisy market data, each new mechanism has to be tested on simulated markets in which the answer is known. The new agents also needed data the old store did not have.

### 5.2 Data store and audit (experiment 011)

The old store held only closing prices and quote volume. The new agents need tail risk (high and low prices), the funding mechanism (the premium over the index), crowding (open interest, long-short ratios, taker flow) and a spot price for basis. The data pipeline was extended to every kline column, the premium index, spot klines and hourly open-interest metrics, and audited against the exchange's public bucket.

| Dataset | History | Note |
|---|---|---|
| Klines (open, high, low, close, volume, trades, taker-buy volume) | 2020-01 onward | |
| Premium index klines | 2020-01 onward | |
| Funding events | 2020-01 onward | event time kept; not always 8 hours apart |
| Spot klines | Bitcoin from 2017-08 | |
| Open interest, long-short, taker ratios | Bitcoin 2020-09; most others 2021-12 | daily files, about 1,800 requests per symbol; opt-in; gaps (NaN) must be handled |
| Liquidation data | absent | any liquidation-based agent is out of scope |

*The funding rule was checked.* Binance's funding for an eight-hour interval is
$$F=P+\operatorname{clamp}\big(I-P,\,\pm c\big),\qquad I=0.01\%\text{ per 8 hours},\ c=0.05\%,$$
where $P$ is the time-weighted average of the premium index over the interval. On Bitcoin (2024-06, 89 events) the time-weighted version had a correlation of 0.995 with actual funding and a mean absolute error of $9\times10^{-7}$ (about 1% of the typical level); an equal-weighted average was worse (0.936). Funding intervals are shortened at the cap (1.5% of events for one coin in the probe), so funding is always summed per bar from event times.

### 5.3 What we built

**5.3.1 Agents and beliefs.** Notation: agents $i=1,\dots,M$, coins $a=1,\dots,N$, $x_i\in\mathbb{R}^N$ the position of agent $i$ in dollars of initial equity, $X=\sum_i x_i$ the net position, $h$ the net position held now. Agent $i$'s *belief* $\mu_i\in\mathbb{R}^N$ is its expected net return on a unit position over one holding period. If a standardised score $z_{ia}$ of the hypothesis (unit variance across coins) has rank correlation $\mathrm{IC}_i$ with the next return, the conditional mean return is $\mathrm{IC}_i\,\sigma_{H,a}\,z_{ia}$, where $\sigma_{H,a}$ is the volatility of the coin over one holding period (Grinold's fundamental law):
$$\mu_{ia}=\mathrm{IC}_i\;\sigma_{H,a}\;z_{ia}.$$
How $\mathrm{IC}_i$ is set was first planned as an estimate shrunk towards no skill; Phase 6 shows why this was changed.

**5.3.2 Level 1: the capital market.** For one asset with expected return $\mu$ and variance $\sigma^2$, the log-growth of wealth when a fraction $f$ is invested is approximately $g(f)=f\mu-\tfrac12 f^2\sigma^2$. It is largest at $f^\star=\mu/\sigma^2$ (the Kelly fraction) and is zero at $2f^\star$, so over-confident agents are punished by the mathematics. We use half the Kelly size. Minimising $-\mu x+\tfrac{\gamma}{2}\sigma^2x^2$ gives $x=\mu/(\gamma\sigma^2)$, so a bet of $fW\mu/\sigma^2$ corresponds to risk aversion $\gamma=1/(fW)$, with $f=0.5$ and $W$ the agent's wealth. The system trades the sum of the agents' positions; each agent has an *account* that earns the profit and loss of its own positions minus its allocated share of cost and funding, so the accounts sum exactly to the real result. Wealth compounds with the account return $r_i(t)$:
$$W_i(t+1)=\max\!\Big(W_i(t)\big(1+r_i(t)\big),\ \omega\sum_jW_j(t)\Big),\qquad\omega=0.02.$$
A floor $\omega$ keeps a failed agent alive. A loss larger than an agent's wealth is borne by the others (limited liability). Beliefs are never averaged between agents; they act through the wealth that backs them. This follows the literature on prediction markets with Kelly bettors, in which wealth shifts follow Bayes' rule.

**5.3.3 Level 2: the joint problem.** With $\Sigma=\operatorname{diag}(d)+F\,\beta\beta^\top$ the covariance of coin returns over one holding period (idiosyncratic variances $d$, one market factor with variance $F$ and betas $\beta$), the system solves at each rebalance
$$\min_{x_1,\dots,x_M}\ \sum_{i}\Big[-\mu_i^\top x_i+\tfrac{\gamma_i}{2}\,x_i^\top\Sigma\,x_i\Big]+C\big(X-h\big)+\tfrac{\lambda}{2}\,X^\top\Sigma X\tag{P}$$
$$\text{subject to}\quad x_i\in\mathcal{X}_i\ \ (i=1,\dots,M),\qquad X=\textstyle\sum_ix_i\in\mathcal{G}.$$
The trading cost is $C(d)=\sum_a\big(c_f\lvert d_a\rvert+\kappa_a\lvert d_a\rvert^{3/2}\big)$ with $\kappa_a=k\sigma_a/\sqrt{\mathrm{ADV}_a}$, a fee of $c_f=5$ basis points and a square-root price impact with coefficient $k=1$ (an assumption), and it acts on the **net** trade $X-h$: two agents trading opposite ways in the same coin cancel and pay only for the difference. The agent sets $\mathcal{X}_i$ collect what belongs to one agent: allowed coins ($x_{ia}=0$ outside the agent's card), capacity ($\lvert x_{ia}\rvert\le$ 5% of the coin's daily volume), margin ($\lVert x_i\rVert_1\le3W_i$) and, for market-neutral agents, dollar and beta neutrality ($\mathbf 1^\top x_i=0$, $\beta^\top x_i=0$). The system set $\mathcal{G}$ collects what belongs to the whole system: a gross cap ($\lVert X\rVert_1\le3E$, $E$ total equity) and a market-beta band ($\lvert\beta^\top X\rvert\le0.25E$). A pair (agent, coin) is a *cell*. The last term in (P) is a **price $\lambda$ on system variance**: after each solve the annual ex-ante volatility $\sqrt{P\,X^\top\Sigma X/H}$ of the net position (with $H$ bars per holding period) is compared with the 20% target, and if it is above, $\lambda$ is raised and (P) is solved again (up to five times). Problem (P) is convex, so it has multipliers; they are the *prices* of exposure, scarce capital, scarce gross exposure and trading. Agents react to prices and never see each other's beliefs.

**5.3.4 Solving (P): sharing ADMM.** Write $f_i(x_i)=-\mu_i^\top x_i+\tfrac{\gamma_i}{2}x_i^\top\Sigma x_i+\iota_{\mathcal{X}_i}(x_i)$ and $g(X)=C(X-h)+\tfrac\lambda2X^\top\Sigma X+\iota_{\mathcal{G}}(X)$, where $\iota$ is the indicator of a set. Then (P) is the sharing problem $\min\sum_if_i(x_i)+g(\sum_ix_i)$. With $\bar x=\frac1M\sum_ix_i$, penalty $\rho>0$ and scaled price $u$, the ADMM iteration (Boyd et al., 2011, Section 7.3) is
$$x_i^{k+1}=\arg\min_{x_i}f_i(x_i)+\tfrac\rho2\big\lVert x_i-x_i^k+\bar x^k-z^k+u^k\big\rVert^2\quad(\text{each agent})$$
$$z^{k+1}=\arg\min_zg(Mz)+\tfrac{M\rho}2\big\lVert z-\bar x^{k+1}-u^k\big\rVert^2\quad(\text{system step})$$
$$u^{k+1}=u^k+\bar x^{k+1}-z^{k+1}\quad(\text{price update})$$
It converges because (P) is convex. A one-node solver (SLSQP) is kept as a reference to check it.

**5.3.5 Model averaging inside an agent.** An agent may combine several forecasting models. Weights come from a regression of realised returns on the models' forecasts (stacking), shrunk towards equal weights, with a sanity guard that excludes a member if more than 5% of its coins violate a bound. Several estimators therefore live *inside* one agent and are averaged, instead of agreeing by consensus between agents.

**5.3.6 STL placements.** Three specifications were wired in: a *belief-sanity* spec at the input (a belief that is not a finite number within a bound is zeroed); an *agent calibration* spec (if the slope of realised returns on the agent's past beliefs falls below 0.5, its Kelly fraction is scaled down by the margin); and the system limits (volatility, beta band, gross cap) as priced constraints inside the optimiser, replacing the old shield.

**5.3.7 Timing inside a belief.** The skill of a hypothesis may depend on an observable state $s_t$: $\mathrm{IC}(s_t)=\mathrm{IC}_0+c\,s_t$ with $c$ estimated walk-forward and shrunk towards zero. Each agent can be run timed and untimed.

### 5.4 Experiment 012: the criteria were written first (commit `5635d1e`), the results second

| Mechanism | Criterion | Result |
|---|---|---|
| Joint optimiser | matches the one-node solver on every coupling (35 random problems) | pass; typical error $10^{-7}$; hardest case about 1,100 iterations |
| Prices | non-negative, zero when slack, equal to the marginal value of the limit within 5% | pass |
| Netting | opposite views on a coin are charged on the net trade, cheaper than the sum | pass |
| Capital follows its price | a tighter margin moves capital to the best-edge coin | pass |
| Market selects skill | a skilled agent's share exceeds 0.5 at the computed horizon in at least 90% of seeds | pass at 160 periods |
| Market drops decayed skill | share falls after skill vanishes | pass |
| Accounting | account profits, cells and wealth sum to the real values | pass to $10^{-9}$ |
| Over-confidence punished | an over-confident agent ends with less wealth | **fail** with the 2% floor (6 of 20 seeds); pass without a floor (18 of 20) |
| Model averaging | error-weighted beats equal weights when member errors differ 4 times, not worse when equal | pass (+4.3% and $-0.4\%$) |
| Guard against a corrupt member | fused belief changes by less than 10% | restated after a failed run: the guard equals the honest average exactly |
| STL recovery, deadline, belief sanity | match brute force; corrupt beliefs zeroed | pass |
| Timing on planted regime skill | timed beats untimed; costs little when no dependence | pass (+0.0020 per period; $-5.9\%$) |

**Changes to criteria, disclosed.** One criterion (capital follows its price) was restated before any result was read, because the first wording became ill-posed. Two were restated after a failed run (over-confidence with a floor; the corrupt-member guard), each with the diagnosis recorded. A later finding (Phase 7) superseded one claim: the calibration spec removed ruin entirely only in its point-estimate form.

### 5.5 What we learned

1. **The floor blunts selection.** It re-seeds a ruined agent, so it acts as a rebalancing rule; an over-confident agent kept a persistent share.
2. **An unlimited over-confident agent can ruin the system:** 2 to 5 of 20 seeds were wiped out at an effective Kelly fraction of 2, and selection is too slow to stop it. The defences are the priced margin and gross limits and the calibration spec.
3. Consequences for the defaults: margin and gross limits always on, Kelly fraction at most 0.5, the floor justified only as a liveness device.

### 5.6 What it led to

Phase 6: put the engine on real data with the one agent that was known to work, carry.

## 6. Phase 6: the engine on real data, with one agent (7 November, commits `bd1cb89`, `41c82d2`, `66840ff`, `ce251a5`, `8360532`)

### 6.1 Why

A regression test for the whole stack: if the new engine (beliefs, the joint ADMM with cost on the net trade, accounts) cannot reproduce the carry result of the old v2 engine (Sharpe about 1.0 on every bar size), nothing built on it can be trusted.

### 6.2 What we built

*The carry agent.* Funding is a transfer from the crowded side, so the expected return of a perpetual is its carry plus its expected price change. The agent ranks coins by the negative of their 14-day mean funding and turns the rank into a Gaussian score $z_a=\Phi^{-1}\big((\operatorname{rank}_a-0.5)/N\big)$: long coins with low funding, short coins with high funding, dollar- and beta-neutral. *The engine loop:* at each rebalance the agents form beliefs from information before $t$, the joint problem (P) turns them into positions, the net trade is costed, and accounts earn their profit and loss bar by bar. Settings were fixed and not tuned: Kelly fraction 0.5, margin 3 times wealth, gross cap 3 times equity, capacity 5% of volume, a 20% volatility limit, fee 5 basis points, one million dollars of assets.

### 6.3 Experiment 013: what happened

| Run | Daily | 4-hourly | Hourly | Note |
|---|---|---|---|---|
| **First run** | 0.48 | | | volatility 37%, drawdown $-63\%$ |
| First fix | 1.24 | 1.12 | 1.05 | flaw found in review |
| **Final design** | **1.27** | **1.12** | **1.00** | the regression target (old carry: 1.03 / 0.99 / 0.88) |

*Why the first run failed.* Two departures from the design. (1) The belief used an estimate of the IC that was shrunk towards zero and could change sign. Carry's per-period IC has a hit rate of only 53%, so the belief flipped sign about half the time: the failure of the old IC-weighted fusion, reproduced. (2) The 20% volatility limit was not yet enforced: half-Kelly on about 60 coins implies roughly 50% volatility.

*The first fix had a hidden flaw.* It shrank towards the card's prior with 50 pseudo-observations while an exponentially weighted IC carries at most about 18 effective observations, so evidence could never move the belief (300 periods of IC $-0.04$ still gave a positive belief). The improvement had come from clipping the sign, and the volatility re-solve hid the missing scale.

*The final design (decision 0038).* **The size of the belief is fixed by the agent's card, not estimated:**
$$\mu_{ia}=s_i\;\mathrm{IC}_i\;\sigma_{H,a}\;z_{ia},\qquad s_i\in\{+1,-1\},\ \ \mathrm{IC}_i\ \text{fixed by the card (carry: 0.02)}.$$
Evidence acts only through a kill rule. Let $\overline{\mathrm{IC}}_n$ and $s_n$ be the mean and standard deviation of the agent's realised per-period skill over $n$ periods, $t_n=\overline{\mathrm{IC}}_n/(s_n/\sqrt n)$. If $n\ge20$ and $s_it_n<-2$, the belief is set to zero; the agent never bets the opposite. Relative stakes between agents are then decided by wealth, not by noisy estimates.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Net Sharpe (90% interval, daily) | 1.27 [0.59, 2.01] | 1.12 | 1.00 |
| Volatility | 15.1% | 14.9% | 16.7% |
| Annual cost | 2.0% | 2.1% | 2.0% |
| Rank IC (t-statistic) | 0.035 (2.2) | 0.031 (3.5) | 0.019 (3.4) |

Profit splits into funding collected (+8.8%, +10.6%, +12.4% a year), selection of the right coins (+11.8%, +8.6%, +6.1%) and a market component of about zero (the agent is beta-neutral).

**Disclosure.** The first run, the first fix and the final design were three looks at the development data; for the deflated Sharpe they count as three variants of one design choice. Going from 0.48 to about 1.2 says the calibration matters; the match with the old book is a regression check and not evidence of an improvement.

### 6.4 Experiment 014: improving carry by forecasting funding

*Why.* Carry's profit may come partly from predicting the size of the funding that will be paid. A better forecast could be a better belief ("rung 1" of a ladder of improvements).

*The model (fixed in advance).* Premium follows an AR(1) in hours around its trailing 30-day mean, $P(h)=\mu+\varphi^{h}(p_t-\mu)$ with $\varphi$ pooled over coins on the history window. The funding rate per hour is $g(h)=[P(h)+\operatorname{clamp}(I-P(h),\pm c)]/8$, and the forecast funding over the holding period is the sum of $g$ over its hours.

*The rule (before any run).* On the development period, compare the forecast funding sum with the realised sum for every coin at every rebalance. The new forecast passes only if, on at least two of three bar sizes, its cross-sectional mean squared error beats the baseline's (the trailing 14-day mean times the horizon) with a 90% bootstrap lower bound above zero.

| Bar | $R^2$ of the baseline | $R^2$ of the funding forecast | Gate |
|---|---|---|---|
| Daily | −0.068 | −0.905 | **fail** (forecast significantly worse) |
| 4-hourly | +0.069 | −0.293 | **fail** (significantly worse) |
| Hourly | +0.084 | +0.159 | not significant |

**Result: rejected before any profit run, and its code was deleted** (it remains at commit `8360532`). The baseline itself explains almost none of the funding differences ($R^2$ between $-0.07$ and $0.08$), so *carry earns money from the ranking of coins, not from forecasting the size of funding.* The two further rungs (a crowding term from open interest, a tail cap from high-low ranges) were not run; the open-interest download was still incomplete.

### 6.5 What we learned

1. The engine reproduces the old carry result on all three bar sizes with exact accounting and costs of about 2% a year.
2. **Calibration matters more than the combiner:** with the same signal, a belief that can change sign cost about 60% of the Sharpe.
3. A mechanical test on forecast accuracy can reject an idea before any profit is computed, which limits the number of trials.

### 6.6 What it led to

One agent makes the capital market trivial. The next step was a second agent whose book is not neutral: Bitcoin and Ethereum momentum.

## 7. Phase 7: more agents. Momentum, its timing, and reversal (7 November, commits `75bd681` to `fc78b8a`)

### 7.1 Why

The capital market, per-agent neutrality and the shared limits only matter with several agents of different kinds. The roster in decision 0034 chose one agent per established hypothesis; the literature supports carry and time-series momentum in coins we can trade.

### 7.2 What we built

*Engine changes before any momentum result.* (1) Per-agent neutrality: carry is dollar- and beta-neutral, momentum owns net exposure. (2) A system limit on net beta, a priced constraint. (3) **The 20% volatility limit became a price** (Section 5.3.3), not a uniform rescale: in a solver test at equal total volatility the priced limit left the neutral agent 97% of its unconstrained book, where a uniform shrink left it 45%. (4) The calibration and belief-sanity specs were wired into the engine; both misfired on real data and were fixed before any logged run: a card-sized belief (about 0.002) against 15% returns gives a slope standard error above 1, so the calibration spec now acts on the *upper confidence bound* of the slope (slope plus 1.645 standard errors), and the sanity spec tests the volatility-standardised belief, because raw beliefs flagged legitimate high-volatility coins.

*Solver speed.* The volatility price and the beta band together made the net-position step 100 times slower (three nested root searches). We added a fast path for shared loadings, over-relaxation (factor 1.7), a penalty of five times the combined curvature, and a *relative* stopping rule (an absolute one had stopped real problems after about ten iterations because positions are about 0.01). A warm start across volatility prices made convergence eight times *slower* and was removed. Result: daily carry 5.5 minutes to 49 seconds; four-hourly momentum 90 minutes (unfinished) to 11 minutes. The net position is accurate to about $10^{-6}$, the split of the net between agents only to about 9%, so per-agent accounts carry that noise and the system result does not.

*The momentum card.* Claim: a coin's trailing 30-day return, in units of its own volatility, predicts the sign of its next return. Universe: Bitcoin and Ethereum only (the literature's per-asset version). Score $z_a=\operatorname{clip}\big(\sum_{\tau\in30\mathrm d}r_{a\tau}/(\operatorname{sd}(r_a)\sqrt L),-2,2\big)$. Not neutral. $\mathrm{IC}=0.05$, an *assumption* chosen by a mechanical check without profit: at the first value tried (0.10) the agent's ex-ante Sharpe at its own belief was 1.17 on daily bars, more than a time-series momentum strategy on two coins can be expected to deliver; 0.05 gave about 0.6. Kill rule on the pooled slope of returns on the score.

*Admission rule (before any run).* The annualised alpha of the agent against Bitcoin (and against Bitcoin plus carry) must have a 90% lower bound above zero on at least two of three bar sizes. Market acceptance: the market of carry and momentum must beat carry alone by the paired rule of experiment 014.

### 7.3 Experiment 015: momentum, in three steps

**015a, first run (unrestricted).** Momentum alone: Sharpe $-0.45$, $0.13$, $0.38$ with volatility 39%, 33%, 27%. Carry plus momentum through the market: 0.86, 0.91, 0.91 against carry alone 1.26, 1.15, 1.00. Admission failed on both rules; acceptance failed.

**Review of the footprint.** The agent's positions did not match its card. Besides Bitcoin and Ethereum (mean absolute positions 0.24 and 0.11 of equity) it held about 0.28 in *other coins*: the optimiser neutralised the beta band and variance with a basket of alt-coins, so the book was a Bitcoin and Ethereum trend bet plus a short alt basket, which a one-factor risk model does not price correctly. The engine did not enforce each agent's coin set. This was recorded as an amendment *before* the corrected runs, with the card magnitude unchanged.

**015b, corrected (universe enforced).**

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Momentum alone, net Sharpe | 1.06 | 0.95 | 0.90 |
| Volatility | 11.7% | 11.5% | 12.1% |
| Alpha vs Bitcoin, lower bound above 0? | yes | yes | no ($-0.5\%$) |
| Carry + momentum | 1.59 | 1.62 | 1.57 |
| Carry alone | 1.26 | 1.15 | 1.00 |
| Paired gain over carry alone | +0.34 | +0.47 | +0.57 |

Both admission rules passed (two of three bar sizes) and acceptance passed. The market's final wealth shares for momentum were 35%, 41% and 54%.

**A control that was not in the plan.** Is the gain due to the market, or simply to mixing two return streams? We compared the market with a fixed-weight blend of the two stand-alone runs (weights fixed before looking). Market minus blend: $-0.01$, $+0.14$, $+0.21$, all intervals containing zero. **The gain over carry alone was diversification.**

*Caveats written into the experiment.* The corrected run is a forking path (the fix came after seeing the failure; both runs count as trials). Two coins over one mostly rising period, with most of the profit in 2020 and 2021. The hourly bound was just below zero. The card magnitude is not horizon-neutral.

### 7.4 Experiment 016: timing momentum

*Design (decision 0039).* $\mathrm{IC}(s_t)=\mathrm{IC}_0+c\cdot s_t$ with two mechanism-based states from Bitcoin returns: a *bull* state (the $t$-statistic of the trailing return, momentum being concentrated in bull markets; predicted $c\ge0$) and a *panic* state (the log ratio of 30-day volatility to window volatility, momentum crashing after high-volatility rebounds; predicted $c\le0$). The coefficient is a ridge regression of each past period's skill on the standardised states with a prior $c\sim N(0,\tau^2)$, $\tau=\mathrm{IC}_0/2$, which shrinks it by about three quarters at 280 periods; a coefficient of the wrong predicted sign is set to zero; $\mathrm{IC}$ is clipped to $[0,2\,\mathrm{IC}_0]$. No value was chosen by looking at profit. *Rule (before any run):* timing is kept only if the timed Sharpe beats the untimed twin with a lower bound above zero on at least two of three bar sizes and none upper below zero.

*Result.* Timed momentum 1.03, 0.90, 0.86 against untimed 1.06, 0.95, 0.90: slightly *worse* (significantly on daily and four-hourly); the pair with carry unchanged (+0.00 to +0.01). **Rejected; the code was deleted.** The test has little power (few bull and panic episodes in five years), so the finding is "this estimator found nothing", not "nothing exists".

### 7.5 Experiment 017: reversal

*Card.* Residual reversal: the trailing 7-day return in excess of Bitcoin beta, $e_{a\tau}=r_{a\tau}-\hat\beta_ar_{\mathrm{BTC},\tau}$, negated, rank-Gaussian, neutral, $\mathrm{IC}=0.02$ (below the legacy measured 0.025 to 0.049, which came from the same data and so is not independent evidence). Mechanism: price pressure from demand for immediacy is temporary. *Admission (all three, on two of three bar sizes):* stand-alone Sharpe lower bound above zero; rank IC with $t>2$; alpha above zero against Bitcoin, carry and momentum. The market of three must beat the market of two. Reported with equal weight: the market of three against a fixed inverse-volatility blend of the three, and a rank-IC breakdown by liquidity tercile.

*Result at the time (before the volatility-limit fix, Section 8).* Reversal alone: Sharpe $-0.57$, $-1.08$, $-0.83$ with rank IC 0.025, 0.041, 0.046 ($t$ = 1.5, 4.3, 7.3): the signal is real but turnover of 31 to 58 times equity costs 10% to 17% a year. Gate (a) failed on every bar size; reversal was not admitted. The market of three was worse than the market of two (1.42, 1.39 against 1.59, 1.62) but much better than the fixed blend of the three (+0.33 daily, +0.75 on four-hourly with a lower bound above zero). The IC was highest in the middle liquidity tercile, not the least liquid, so the mechanism "stronger in less liquid coins" was not supported. The hourly three-agent run was cut short by a machine restart; it was completed in Phase 8.

### 7.6 What we learned

1. A hypothesis must be checked against what the agent *actually held*, not only against its return: the optimiser can satisfy a limit with positions the card forbids.
2. With good agents the market was no better than a fixed mix; with a bad agent in the roster it was clearly better, because it moves capital away.
3. Two further ideas (timing, reversal) were rejected; each rejection followed rules written before the runs.

### 7.7 What it led to

While extending the engine for the next experiments, a reviewer found a bug in how the volatility limit was measured. It changed several of the conclusions above.

## 8. Phase 8: a bug in the risk limit, and everything re-run (8 November, commits `cba8bff`, `56172cf`, `64154f0`)

### 8.1 Why

The system was supposed to run at 20% volatility in every year. On carry plus momentum (daily) realised volatility had fallen from 20% in 2021 to 8% in 2025.

### 8.2 The bug

The engine compared the ex-ante volatility of the net position, measured in units of the *initial* equity, with the 20% limit. Stakes grow with wealth, while the gross cap and the beta band already scaled with *current* equity. The effective limit was therefore $20\%/(\text{equity multiple})$: as the system made money it was held to less and less risk, and an agent that lost money got a limit far above 20% of what it had left. The fix measures volatility as a share of current equity (a regression test was added). Nothing else changed: same agents, cards, gates, settings, data and period. Experiments 013, 015b and 017 were re-run, once each, on all three bar sizes (experiment 018). Experiments 014 and 016 could not be re-run because their code had been deleted.

### 8.3 Results: before and after (net Sharpe, daily / 4-hourly / hourly)

| Run | Before the fix | After the fix | Daily 90% interval after |
|---|---|---|---|
| Carry | 1.26 / 1.15 / 1.00 | **1.14 / 1.12 / 0.94** | [0.36, 1.90] |
| Momentum | 1.06 / 0.95 / 0.90 | **0.96 / 0.80 / 0.76** | [0.24, 1.61] |
| Reversal | −0.57 / −1.08 / −0.83 | **−0.66 / −1.17 / −0.99** | [−1.29, −0.03] |
| Carry + momentum | 1.59 / 1.62 / 1.57 | **1.39 / 1.48 / 1.48** | [0.61, 2.09] |
| Carry + momentum + reversal | 1.42 / 1.39 / not run | **1.26 / 1.34 / 1.33** | [0.52, 1.97] |

Every multi-agent run now sits at 18% to 21% realised volatility in every year. Sharpe ratios fell by 0.03 to 0.2 (more risk costs more and holds the weaker part of each signal); returns rose (carry plus momentum CAGR 29% to 31% instead of 18% to 22%).

### 8.4 The pre-registered verdicts, re-applied

- **Carry baseline (013):** still passes.
- **Momentum admission (015b): now fails.** Alpha against Bitcoin has intervals $[+0.2\%,+17.7\%]$ (daily), $[-0.9\%,+18.5\%]$ (4-hourly), $[-2.7\%,+19.7\%]$ (hourly), so only daily clears zero. The point estimate barely moved (about +9% a year); the interval widened because the book now runs at 13% to 15% instead of 11% to 12% volatility.
- **Market acceptance of carry plus momentum: still passes** (+0.26, +0.36, +0.55).
- **The market against a fixed blend: still not distinguishable** (−0.07, +0.14, +0.29).
- **Reversal: not admitted**; the market of three is worse than the market of two ($-0.14$, $-0.14$, $-0.15$).
- **The market of three against a fixed blend of three: +0.35 [−0.17, 0.84], +0.86 [0.31, 1.35], +0.88 [0.34, 1.39].** The market cut reversal to the 2% floor (final wealth share 1.9%, 1.8%, 2.0%) while the fixed blend kept paying for its losses; the market's trading cost was 2.4% to 2.9% a year against 2.5% to 3.5%.

### 8.5 A rule conflict and its resolution (decision 0041)

Momentum now fails its own admission rule while the market that contains it still beats carry alone. We did not choose the rule that passes. Options: reject momentum and delete it; admit it on the market result (a forking path); or **keep it as a provisional agent**. We chose the last: momentum stays in the roster for the coordination experiments that follow, is recorded as *not admitted*, and no result may claim a proven stand-alone edge. Its status is re-judged in the final run with the rule unchanged.

### 8.6 What we learned

1. The bug mattered: it moved every number and flipped one decision.
2. **The worry that the risk model underestimates the risk of non-neutral books (015a, 017) was mostly this bug.** Reversal ran at 45% volatility because it was losing money and a fixed-size limit became large relative to its shrinking equity; corrected, it runs at 24% to 29%, still above 20%, so a smaller gap remains for books that are not tightly neutral.
3. **The clearest real-data evidence for the capital market is protection against a bad agent, not return.**

### 8.7 What it led to

The system's economics were now stable enough to ask the questions the course proposal is about: can the optimiser run without a central node, and what happens when the network or an agent fails?
## 9. Phase 9: removing the central node (8 November, decision 0042, commit `be15f90`, experiment 019)

### 9.1 Why

The course proposal is about *decentralised* coordination. The optimiser of Section 5.3.4 still has a hub: one node that averages all positions, solves the system step and sends back one price per coin. A hub is a single point of failure, and with a hub no question about network topology can be asked.

### 9.2 Options considered

1. **Keep the hub** and call it decentralised. Not what the proposal says.
2. **Dual consensus ADMM** (agents hold local copies of the price and agree on it over edges). Exact, but each agent's step becomes a proximal step on a sum of two convex conjugates with no closed form here, and positions must be recovered from the dual.
3. **Sharing ADMM with dynamic average consensus** (chosen). Each agent keeps local copies of what the hub held, and mixes with neighbours.

### 9.3 What we built

Three quantities are global in the hub: the average position $\bar x$, the system step $z$ and the price $u$. Agent $i$ now holds its own copies: an estimate $s_i$ of the group average, a system-step solution $z_i$ and a price $u_i$. The system data (cost parameters, limits) are public. Let the graph be undirected with edge set $\mathcal{E}$ and let $W$ be its **Metropolis** mixing matrix,
$$W_{ij}=\frac1{1+\max(\deg i,\deg j)}\ \ \text{for }\{i,j\}\in\mathcal{E},\qquad W_{ii}=1-\sum_{j\ne i}W_{ij},$$
which is symmetric with rows summing to one, hence doubly stochastic. One iteration:

> **Algorithm 1 (decentralised ADMM, one iteration).**
> 1. Each agent $i$ solves its local step against its own price $u_i$, giving $x_i^{\text{new}}$.
> 2. Tracking: $\;s\leftarrow W^{r}\big(s+x^{\text{new}}-x^{\text{old}}\big)$, mixing the stacked estimates over $r$ gossip rounds.
> 3. Each agent solves the system step from its own estimate $s_i$, giving $z_i$.
> 4. Price: $\;u\leftarrow W^{r}\big(u+s-z\big)$.

Initialise $s_i=x_i^0$.

> **Proposition 1 (sum invariant).** For every iteration $k$, $\sum_is_i^k=\sum_ix_i^k$.
>
> *Proof.* Let $\mathbf1$ be the all-ones vector. Since $W$ is doubly stochastic, $\mathbf1^\top W^r=\mathbf1^\top$. Then $\mathbf1^\top s^{k+1}=\mathbf1^\top(s^k+x^{k+1}-x^k)=\mathbf1^\top s^k+\mathbf1^\top x^{k+1}-\mathbf1^\top x^k$. With $s^0=x^0$ the claim follows by induction. $\square$

**Corollary.** At a fixed point $x^{k+1}=x^k$, so mixing drives every $s_i$ to the common value $\bar s=\frac1M\sum_is_i=\bar x$ (Proposition 1), and the prices agree for the same reason. That fixed point satisfies the optimality conditions of Section 5.3.4, so it is the optimum of (P). On the complete graph with exact mixing the algorithm *is* the hub algorithm.

*Convergence and cost.* With no new input, mixing shrinks the disagreement by the factor $\lvert\lambda_2(W)\rvert^{r}$ per iteration, where $\lambda_2$ is the second-largest eigenvalue modulus of $W$ (the *mixing rate*; smaller is faster). Messages per rebalance equal (iterations)$\,\times r\times2\lvert\mathcal{E}\rvert$.

*Two things stay central in our experiments, and we say so.* The step sizes use the mean risk aversion, a number the agents could agree on once before trading; the stopping test is evaluated by the simulator, where a deployment would run a max-consensus over the graph's diameter.

*Design details found during prototyping.* Over-relaxation (1.7) oscillated on an eight-agent ring and is off in graph mode. The stopping test must also require agreement between the agents' estimates and prices: a run once stopped as converged while agents still disagreed by about 10%. Two bugs found and fixed, recorded because they are easy to reintroduce: mixing *before* adding the agent's own change ($s\leftarrow Ws+\Delta x$) leaves every estimate off by its own last move; and without mixing the prices the agents settle on different prices.

### 9.4 Prototype findings (random problems, 3 and 8 agents)

On the complete graph the result equals the hub to $10^{-15}$; on a three-agent ring and line to $10^{-8}$. With eight agents and all limits binding, one gossip round per iteration needed about 2,700 iterations on a ring ($\lvert\lambda_2\rvert=0.81$) and over 3,000 on a line (0.95); three rounds brought the ring to 400 and ten rounds the line to about 600. So slower mixing costs communication, and the topology question becomes measurable.

### 9.5 Experiment 019: does it reproduce the hub on real data?

*Rule (before the runs).* On daily bars with three agents, the graph runs must match the hub's Sharpe within 0.01 and final equity within 1%, on the complete graph and on the line.

| Run | Net Sharpe | Final equity | Rebalances at the iteration cap (of about 137) |
|---|---|---|---|
| Centralised hub | 1.258 | 3.564 | 21 |
| Graph, complete | 1.257 | 3.560 | 22 |
| Graph, line, 1 gossip round | 1.256 | 3.554 | 43 |
| Graph, line, 3 gossip rounds | 1.257 | 3.559 | 24 |

**Pass.** Largest differences 0.002 in Sharpe and 0.3% in equity; every agent's account identical to three decimals.

### 9.6 What we learned

1. The neighbour-only optimiser gives the same portfolio as the hub. The small differences come from solves that stop at the iteration cap, not from the topology.
2. Communication matters even with three agents: the line with one round reaches the cap twice as often as the complete graph.
3. The hub itself reaches the cap at 21 of 137 rebalances, a pre-existing weakness (slow convergence of the split between agents).

### 9.7 What it led to

With only three agents most topologies coincide, so the topology experiment needed more agents.

## 10. Phase 10: network shape and communication budget (8 November, experiment 020, commits `855345b`, `1c24710`, `a1a41fd`)

### 10.1 Why

Proposal question: *how does the communication topology affect convergence and coordination?*

### 10.2 Rules (committed before any run)

*Part A, simulated problems* (all limits binding, tolerance $10^{-8}$, cap 4,000 iterations): agents $M\in\{4,8,16\}$; topologies complete, ring, line, star, random; gossip rounds $r\in\{1,3,10\}$.
- **A1 (gate):** at $r=3$ the Spearman correlation between $\lvert\lambda_2(W)\rvert$ and iterations to converge is at least 0.7 at each $M$.
- **A2 (sanity gate):** the complete graph takes the same iterations as the hub.
- A3, A4 (reported): the gossip rounds that minimise messages; error after a fixed iteration budget.

*Part B, real data* (daily, eight agents that are parameter variants of the three ideas, used only to study coordination: carry with 7, 14 and 30-day windows; momentum with 15, 30 and 60-day lookbacks; reversal with 3 and 7-day lookbacks). **B1 (gate):** every uncapped graph run within 0.02 Sharpe and 2% final equity of the hub. *Recommendation rule:* the default topology is the one with the fewest messages that passes B1 with no more capped rebalances than the hub plus 10% of rebalances.

**Amendment 1 (before any result).** The first Part A run was stopped after 46 minutes with no output: each agent solves the system step itself, and at 16 agents one iteration took 0.4 s. The grid was reduced to the full grid at $M\in\{4,8\}$ and, at $M=16$, only $r=3$ with 3 seeds (the setting of gate A1).

### 10.3 Results, part A (simulated problems)

Median iterations to converge at three gossip rounds, with $\lvert\lambda_2(W)\rvert$ in brackets:

| Agents | Complete | Ring | Random | Star | Line |
|---|---|---|---|---|---|
| 4 | 151 (0) | 165 (0.33) | 228 (0.75) | 264 (0.75) | 389 (0.80) |
| 8 | 386 (0) | 499 (0.80) | 883 (0.68) | 1,183 (0.88) | not converged (0.95) |
| 16 | 1,000 (0) | 3,709 (0.95), 2 of 3 converged | 1,000 (0.79) | not converged (0.94) | not converged (0.99) |

- **A1: fail.** Correlations 0.60 at 4 agents, 0.90 at 8, 0.78 at 16. At four agents the difficulty of the individual problem dominates: one problem needed about 830 iterations on every topology, including the complete graph. Inside each problem the ordering is as predicted (mean correlation 0.79, 0.96, 0.82), but that is not the pre-registered statistic. We report the failure.
- **A2: pass.**
- The star has higher algebraic connectivity than the ring (1.0 against 0.59 at 8 agents) but is slower (1,183 against 499 iterations). $\lvert\lambda_2(W)\rvert$ predicts better, because with Metropolis weights the centre of a star is a bottleneck.
- One gossip round minimises messages on the complete graph and (at 4 agents) the ring; three rounds elsewhere; ten rounds waste messages.
- After a fixed iteration budget the error is almost the same on every topology early on (about 0.40 at 25 iterations and 0.16 at 100 with eight agents); topology decides how long the last, precise part takes.

### 10.4 Results, part B (real data, eight agents)

| Run | Net Sharpe | Final equity vs hub | Rebalances at cap | Mean iterations | Messages per rebalance |
|---|---|---|---|---|---|
| Hub | 1.240 | 3.578 | 27 | 1,427 | (hub) |
| Complete, 1 round | 1.239 | −0.02% | 29 | 1,459 | 81,716 |
| Ring, 1 round | 1.238 | −0.16% | 114 | 2,885 | 46,160 |
| Ring, 3 rounds | 1.239 | −0.08% | 43 | 1,870 | 89,755 |
| Line, 3 rounds | 1.238 | −0.22% | 122 | 2,949 | 123,854 |
| Star, 3 rounds | 1.240 | −0.01% | 96 | 2,743 | 115,194 |
| Hub, 200-iteration cap | 1.217 | −2.8% | 135 | 200 | (hub) |
| Ring, 3 rounds, 200-iteration cap | 1.212 | −3.5% | 135 | 200 | 9,600 |

**B1: pass** (differences at most 0.002 and 0.23%). By the recommendation rule only the complete graph with one round qualifies (29 capped rebalances against a limit of 40.5), so it is the default for the resilience experiments. A caveat recorded in advance: link failures on a complete graph are a weak test, so the resilience experiments also use a sparse graph.

### 10.5 What we learned

1. **Network shape governs the communication, not the outcome.** Every uncapped topology gives the same system as the hub.
2. The link between mixing rate and iterations holds when graphs differ enough (8 and 16 agents), not universally.
3. Removing the hub costs computation that grows with the number of agents (each agent solves the system step).
4. A short budget costs money, little on any topology: 200 iterations lose about 3% of final equity.

### 10.6 What it led to

Phase 11: break it on purpose.

## 11. Phase 11: link failures, dropped agents, a lying agent, and W-MSR (8 November, decision 0043, experiment 021, commits `4194d43`, `6c87870`)

### 11.1 Why

Proposal question: *does the decentralised consensus stay correct when links fail, agents drop out or an agent misbehaves, and does W-MSR protect it?* This is where the first phase's W-MSR returns.

### 11.2 What we built (prototype on development problems, before the rules)

*Link failures.* In every gossip round each edge is down independently with probability $q$; the Metropolis weights are recomputed on the edges that are up. The recomputed matrix is again symmetric with unit row sums, hence doubly stochastic, so Proposition 1 still holds and the optimum is still reached. Failures cost iterations, not correctness.

*Agent dropout.* The agent's positions are closed and the others solve (P) without it, on the graph without its node.

*W-MSR trimming as the mixing rule: it does not work.* In W-MSR each agent drops up to $F$ larger and $F$ smaller neighbour values and averages the rest. The resulting weight matrix depends on the data and is not doubly stochastic in general, so $\mathbf1^\top s$ is no longer preserved, Proposition 1 fails, and the agents agree on a value that is not the average of the positions. In the prototype the net-position error was 40% to 120% with no attacker at all, and with a liar it did not help either. For $F=1$, W-MSR also needs the graph to be $(2,2)$-robust; a ring is connected but not $(2,2)$-robust, while a ring in which each agent is linked to its two nearest neighbours on each side ("ring2") is sparse but robust.

*W-MSR as a detector (chosen).* At iteration $k$ agent $i$ compares the value $v_j$ (the estimate and the price) of each neighbour $j$ with its own. For coordinate $c$ let $e_{ijc}=1$ if $v_{jc}$ is the largest value above $v_{ic}$ or the smallest below it, that is, the value W-MSR would discard first. Let $\pi_{ij}=\frac1n\sum_ce_{ijc}$. Agent $i$ flags $j$ when $\pi_{ij}\ge0.9$ for both the estimates and the prices for 50 consecutive iterations. An agent flagged by more than half of its neighbours is *isolated*, and the others restart without it. Plain averaging is used otherwise, so with no attacker the solver is exactly Algorithm 1. The parameters (0.9, 50, majority) were set on development problems before the evaluation. *Limit stated in advance:* a liar that sends random noise and hides inside the honest range may not be caught.

### 11.3 Rules (committed before any run; fresh problems and real data)

*Part A, simulated problems* (eight agents, every limit binding; the liar holds nothing, so the right answer is the optimum without it): **A1 (gate)** each link down with probability 0.1 or 0.3: every run on the complete graph, ring2 and the ring converges with error at most $10^{-4}$. **A2 (gate)** on the complete graph and ring2, with the detector on, a constant liar of size 0.001 to 1.0 is isolated, only the liar, with error at most $10^{-4}$; with no liar nobody is isolated. **A3** (reported, predicted to fail) the same on the plain ring. A4, A5 reported: undefended and noise liars; trimmed mixing with no attacker, rejected and deleted if the error exceeds $10^{-2}$ in most runs.

*Part B, real data* (daily, eight agents): **B1** with 30% of links down the result matches the hub (0.02 Sharpe, 2% equity). **B2** the largest agent offline from May to August 2022 (the Luna crash) gives the same as the hub with that agent offline, and the highest ex-ante volatility inside the window is no higher than outside. **B3** a lying agent is isolated at every rebalance, nobody else ever, and the run matches the hub without that agent.

**Amendment 1 (after the other runs finished).** The undefended liar on real data was stopped after 3 hours 40 minutes without output: with the lie every solve runs to the iteration cap and the volatility search repeats it up to five more times. It feeds only a reported item, which is shown on simulated problems instead.

### 11.4 Results, part A

| Gate | Result |
|---|---|
| **A1** link failures | **pass**; error at most $5.4\times10^{-6}$; converged even at 0.5; the ring needs 60% more iterations at $q=0.3$ |
| **A2** constant liar, detector on | **pass**; 18 of 18 runs: only the liar isolated; error at most $4.4\times10^{-6}$ |
| **A3** plain ring (predicted to fail) | **fail**, as predicted: in all 9 liar runs an honest agent was isolated too and the graph fell apart |
| A4 undefended constant liar | error 5.5 to 5.9 typical positions, no convergence |
| A4 noise liar, detector on | isolated in only 1 of 6 runs; otherwise no convergence, error 12.5 to 14.8 typical positions |
| A5 trimmed mixing, no attacker | no run converged; error 0.50 to 4.8 typical positions; **rejected and deleted** |

Median iterations with failing links (A1): complete graph 187, 215, 262, 288 at $q=0,0.1,0.3,0.5$; ring2 193, 214, 235, 265; ring 439, 513, 700, 1,075.

### 11.5 Results, part B (real data, daily, eight agents)

| Run | Net Sharpe | Final equity | Against the reference |
|---|---|---|---|
| Hub | 1.240 | 3.578 | |
| Complete, 30% of links down each round | 1.239 | 3.577 | within 0.001 of the hub (B1 pass) |
| Ring, 3 rounds, 30% of links down | 1.239 | 3.575 | iterations 1,870 to 2,155; capped rebalances 43 to 56 |
| Largest agent (38% of final wealth) offline May to August 2022; hub, complete, ring | 1.225, 1.225, 1.225 | 3.476, 3.476, 3.474 | graph equals the hub with that agent offline (B2 pass); highest ex-ante volatility in the window 17.5%, outside 20.9% |
| A momentum variant lies (adds 0.01 to everything), detector on | 1.182 | 3.391 | equals the hub without that agent, 1.182 (B3 pass); isolated at the first rebalance, nobody else ever |

Dropping the largest agent for four months costs 0.015 Sharpe and 2.8% of final equity; leaving out the lying agent costs 0.058 Sharpe and 5.2%. The cost comes from what is missing (its capital sits idle), not from coordination.

### 11.6 What we learned

1. **Link failures and dropped agents are absorbed at the price of communication.** The sum invariant makes it work.
2. **The lecture's W-MSR cannot be placed inside this optimiser:** trimming breaks the invariant, so it breaks the optimiser even with no attacker. This is a negative result about combining *resilient* consensus with *optimisation*.
3. **Used as a detector, the W-MSR test works when the graph is robust:** a consistent liar was caught from 4% of a typical position, with no false alarm, on simulated and real data, with exactly the right result. On the plain ring honest agents were isolated too: *robustness of the graph, not only connectivity, decides whether the system can defend itself.*
4. **A stealthy liar gets through.** Random noise was caught once in six; otherwise the result is far off and the solver does not converge. Non-convergence is visible, which points to a supervisor that refuses to trade on a solve that did not converge.

### 11.7 What it led to

Phase 12: the supervisor, and the formal safety specifications of Phase 3 rebuilt inside the new structure.

## 12. Phase 12: STL safety monitor and supervisors (8 to 9 November, decisions 0044 and 0045, experiment 022, commits `25ea584`, `09c98f7`)

### 12.1 Why

Proposal question: *does an STL safety monitor with a supervisor keep the system inside its safety specifications in stress periods, and at what cost?* Two gaps remained: there was no record over time of whether the system's specifications hold (so nobody could see the safety margin in a crash), and nothing reacted to a drawdown (the priced limits act on ex-ante risk, not on losses). Experiment 021 also showed that a noise liar produces a wrong portfolio from a solve that does not converge.

### 12.2 Options considered

1. A post-hoc shield scaling the finished portfolio to cash (Phase 3). Rejected: it re-trades the whole book.
2. More priced constraints inside the optimiser, such as a drawdown constraint. A drawdown is a property of a path, not of the next portfolio, so it has no clean form as a constraint.
3. **A monitor plus supervisors acting through what the optimiser already has** (chosen).

### 12.3 What we built

*Specifications and limits* (taken from the risk mandate of decision 0026, argued before any run, never chosen by a backtest). Let $\hat\sigma_t$ be the ex-ante volatility at a rebalance, $\sigma^\ast_t$ the volatility target in force, $\mathrm{DD}_t=E_t/\max_{s\in[t-365\mathrm d,t]}E_s-1$ the drawdown, and $\sigma^{\mathrm{real}}_t$ the realised 30-day volatility.

| Spec | Statement | Limit and its mandate |
|---|---|---|
| $\varphi_{\mathrm{vol}}$ | $\mathbf G\,(\hat\sigma_t\le1.05\,\sigma^\ast_t)$ | 5% tolerance; the priced limit's own search accepts 2% |
| $\varphi_{\mathrm{dd}}$ | $\mathbf G\,(\mathrm{DD}_t\ge-0.15)$ | 15% over 365 days: about half what an equity market lost in its worst stretch within a year |
| $\varphi_{\mathrm{rvol}}$ | $\mathbf G\big(\sigma^{\mathrm{real}}_t>0.4\Rightarrow\mathbf F_{[0,14\mathrm d]}\,\sigma^{\mathrm{real}}_t\le0.4\big)$ | 40% and 14 days: twice the 20% target |
| $\varphi_{\mathrm{solve}}$ | $\mathbf G\,(\text{relative residual}\le10^{-3})$ | a portfolio off by 0.1% of its size is immaterial against one rebalance's fee; clean hub solves reach $10^{-6}$ |

The **monitor** records the robustness of each specification for every bar and summarises it over three stress windows: May to July 2021, the May 2022 Luna collapse, and the November 2022 to January 2023 FTX collapse. Two **supervisors**, off by default:

*Derisk.* Let $m_t=(\mathrm{DD}_t+0.15)/0.15\in[0,1]$ be the share of the drawdown budget left. The volatility target is multiplied by
$$\kappa(m_t)=\begin{cases}1&m_t\ge0.5,\\0.2+1.6\,m_t&0\le m_t<0.5,\end{cases}$$
so de-risking starts with half the budget left and never goes below 20% of the target. It acts through the volatility price of Section 5.3.3, so (P) is re-solved with the tighter target, costs included; it is not a post-hoc rescale.

*Hold.* If the solve is unsafe (it did not converge and its relative residual exceeds $10^{-3}$) the system trades nothing and keeps its positions: the fail-safe against a corrupted solve.

*Dashboard (decision 0045).* An interactive page runs the real decentralised optimiser live on simulated problems (graph, gossip rounds, link failures, a liar with or without the detector) and shows the saved runs and tables (topology, performance, the safety record, resilience, the final comparison). It only reads saved runs and never uses sealed data.

### 12.4 Rules (committed before any run)

*Part A* (carry plus momentum, centralised, all three bar sizes, safety off and derisk; hold on daily): **A1 (gate)** the solver-health spec holds at every rebalance and the volatility spec at at least 95% of rebalances. **A2 (gate)** derisk has fewer bars violating the drawdown spec than off, and a shallower worst 365-day drawdown. **A3** reported: per window and mode, return, worst drawdown, volatility, robustness, and the cost in Sharpe and CAGR (never a criterion).

*Part B* (daily, three agents, complete graph): reversal sends random noise from May to July 2022. **B1 (gate)** with hold, every unsafe solve is held, all held rebalances are inside the window, and none outside is unsafe; without a supervisor at least one rebalance in the window trades on an unsafe solve.

**Amendment 1.** (i) A recording bug, fixed: on a held rebalance the engine logged the ex-ante volatility of the *rejected* solve (about 54%) as the system's instead of that of the positions it kept; the trades were right, only the record was wrong; a test now fails on the old code. (ii) The undefended noise-liar run was stopped after 9 hours 38 minutes: the iterates diverge (the largest value an agent steps on grows from 0.4 to 44 in 700 iterations), each solve takes about 45 minutes, and the search repeats it up to six times at each of six attacked rebalances.

### 12.5 Results, part A (carry plus momentum, centralised)

| Mode | Metric | Daily | 4-hourly | Hourly |
|---|---|---|---|---|
| Off | Sharpe | 1.394 | 1.478 | 1.483 |
| | CAGR | 31.2% | 29.8% | 29.2% |
| | worst 365-day drawdown | −23.7% | −24.4% | −25.9% |
| | rebalances with ex-ante volatility within $1.05\times$ target | 97.8% | 97.6% | 94.3% |
| Derisk | Sharpe | 1.277 | 1.275 | 1.462 |
| | CAGR | 23.9% | 21.0% | 24.3% |
| | worst 365-day drawdown | −19.7% | −18.8% | −16.7% |

- **A1: fail on hourly bars only.** Solver health always holds. The volatility spec holds at 97.8% and 97.6% of rebalances on daily and four-hourly bars but at 94.3% on hourly, with breaches of up to 10% over the limit: the price search (at most five re-solves, a 2% band) lags a covariance that moves faster between hourly rebalances. A limit of the search, not a bug.
- **A2: fail on daily, pass on four-hourly and hourly.** The worst drawdown is shallower on every bar size, and the violating bars fall on four-hourly (2,159 against 2,223) and hourly (5,135 against 7,695), but they *rise* on daily (229 against 211): smaller positions after a loss recover more slowly, so the account stays below the line longer even though it never falls as far.
- **A3.** The cost of derisk is Sharpe $-0.12$, $-0.20$, $-0.02$ and CAGR $-7.3$, $-8.8$, $-4.9$ points. **The tightest stress window was the FTX collapse (November 2022 to January 2023), not May 2021 or Luna as we had expected.** It is the only window in which the drawdown spec was violated (1 daily bar, 444 four-hourly, 1,741 hourly). In May 2021 and Luna the system made money (7% to 16%, drawdown in the window at most $-8.5\%$) and derisk did not act. In FTX derisk acts: on four-hourly bars the window drawdown falls from $-8.5\%$ to $-2.0\%$ and volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%).

### 12.6 Results, part B (a stealthy liar on real data)

| Run | Sharpe | Final equity | Return in window | Unsafe solves | Held |
|---|---|---|---|---|---|
| No liar | 1.257 | 3.56 | 11.7% | 8 (all in 2025) | 0 |
| Liar, hold supervisor | 1.033 | 2.77 | 6.7% | 15 | 15 |
| Liar, no defence | stopped (amendment 1) | | | | |

**B1: fail.** All six rebalances inside the window were held (relative residual 1.18 to 1.62), but nine *honest* rebalances in 2025 (residuals 0.0013 to 0.0059, slow convergence of the decentralised solve) were held too, and the same slow solves exist in the clean run. The frozen positions drifted to an ex-ante volatility of up to 31%, and the whole-period Sharpe fell from 1.26 to 1.03. The residuals of the attack and of slow honest convergence differ by a factor of about 300, so a better limit exists; that is a follow-up and was not changed after seeing the result.

### 12.7 What we learned

1. The monitor makes the safety margin visible bar by bar and found a stress window we had not predicted.
2. Derisk does what it is built for (shallower drawdowns, 4 to 9 points) at a Sharpe cost of 0.02 to 0.20, with two gates failed (daily drawdown counts; hourly volatility spec).
3. Hold stops a stealthy liar but, with its pre-fixed limit, also freezes the system on slow honest solves, and the frozen positions cost more than the attack did.
4. An undefended noise liar does not just bias the decentralised solve, it makes it diverge, so some supervisor is needed: detect-and-isolate (Phase 11) catches consistent liars and hold catches noisy ones.

Decision 0044: accepted as a monitor and as optional supervisors, off by default; derisk usable; hold needs its limit re-argued before it is switched on.

## 13. Phase 13: the final comparison and the correction for multiple testing (9 November, experiment 023, commit `b086e9c`)

### 13.1 Why

To collect everything on the development period in one place against the centralised reference, as the proposal asks (financial and multi-agent properties, performance and risk, convergence, consensus behaviour, safety), and to apply the multiple-testing correction that had been pending since experiment 013.

### 13.2 What we built: the deflated Sharpe ratio

Trying many strategies and reporting the best inflates the best Sharpe ratio. The *deflated Sharpe ratio* (Bailey and López de Prado, 2014) corrects this. Let $\widehat{\mathrm{SR}}$ be the per-period Sharpe ratio of the best strategy over $T$ periods with skewness $\hat\gamma_3$ and kurtosis $\hat\gamma_4$ (3 for a normal distribution), $V$ the variance of Sharpe ratios across the $N$ trials, and $\gamma_{\mathrm E}\approx0.5772$ Euler's constant. Then
$$\mathrm{SR}_0=\sqrt V\Big[(1-\gamma_{\mathrm E})\Phi^{-1}\!\big(1-\tfrac1N\big)+\gamma_{\mathrm E}\,\Phi^{-1}\!\big(1-\tfrac1{Ne}\big)\Big],\qquad
\mathrm{DSR}=\Phi\!\left(\frac{(\widehat{\mathrm{SR}}-\mathrm{SR}_0)\sqrt{T-1}}{\sqrt{1-\hat\gamma_3\widehat{\mathrm{SR}}+\tfrac{\hat\gamma_4-1}4\widehat{\mathrm{SR}}^2}}\right).$$
$\mathrm{SR}_0$ is the Sharpe ratio that the best of $N$ strategies with no skill would show by chance, and DSR is the probability that the observed Sharpe ratio exceeds it. We require $\mathrm{DSR}\ge0.95$.

### 13.3 Rules (committed before the table was computed)

No new engine run and no new setting: the table only reads saved runs of experiments 018 to 022 and the trial log. *Counting trials (fixed in advance):* a trial is one (strategy variant, bar size). The strategy variants on real data are carry in three calibrations (013), carry ladder rung 1 (014), momentum unrestricted and restricted (015a, 015b), the market of two with each, timed momentum (016), reversal alone and the market of three (017), and the re-runs after the volatility fix of carry, momentum, reversal, the market of two and the market of three (018): 15 variants on each of three bar sizes, **$N=45$**. Engineering variants (019 to 022) add 29 distinct names for $N=74$, the conservative count. $V$ is the variance of the annualised Sharpe ratios of the 15 strategy runs of experiment 018, divided by the periods per year; skewness, kurtosis and length are those of the main system's returns. **C1 (consistency):** every number shared with an earlier write-up reproduces to 0.001. **C2 (verdict):** the deflated Sharpe of the market of two is at least 0.95 at $N=45$ on a bar size.

### 13.4 Results

**C1: pass.**

| Net Sharpe [90% interval] | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [−0.03, 1.44] |
| Reversal | −0.66 [−1.29, −0.03] | −1.17 [−1.81, −0.48] | −0.99 [−1.63, −0.32] |
| **Main system: carry + momentum market** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 blend, carry + momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2%, 29.8%, 29.2%; volatility 21%, 19%, 18%; maximum drawdown $-23.7\%$, $-24.4\%$, $-25.9\%$.

**Centralised against decentralised, and failures (daily).** Market of three: hub 1.258, complete graph 1.257, line 1.256 (final equity within 0.3%). Eight agents: every topology within 0.002 Sharpe and 0.22% of the hub's final equity; iterations 1,427 (hub) to 2,949 (line); messages 46,160 (ring, one round) to 123,854 (line); capped rebalances 27 to 122. Thirty per cent link failures 1.239 and 1.239 against 1.240; the largest agent offline 1.225 against 1.225; a constant liar with the detector 1.182 against 1.182. Noise liar with hold 1.033 against 1.257 (−22% final equity, mostly false alarms in 2025).

**C2: fail on every bar size.**

| Bar | Sharpe | Skewness | Kurtosis | DSR at $N=45$ | DSR at $N=74$ |
|---|---|---|---|---|---|
| Daily | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 |
| 4-hourly | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 |
| Hourly | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 |

The annual variance of trial Sharpe ratios is 0.82 (the 15 strategy runs of experiment 018, from $-1.17$ to $1.48$). The deflated Sharpe exceeds 0.95 only for $N\le2$ trials (0.98 to 0.99) and is 0.47 to 0.55 at $N=10$.

### 13.5 What we learned

1. **The multi-agent mechanisms reproduce the central reference** to within 0.002 Sharpe; what they cost is communication (up to 2.7 times the messages and 4.5 times the capped rebalances on a line).
2. **The return result does not survive multiple testing on the development period alone.** A Sharpe of 1.4 to 1.5 among 45 trials of widely spread quality is what chance would show with probability about 90%. This is a statement about the evidence, not proof of no edge: carry's interval is above zero on every bar size, and the sealed final year is the independent test.
3. **The market's value is protection and not return.**
4. The proposal's trade-offs in one line: decentralisation and resilience cost messages, safety costs return, the market of agents buys protection against a bad agent.

## 14. Synthesis

### 14.1 The path in one view

| Step | What we believed before | What the evidence said | What we did next |
|---|---|---|---|
| Phase 1 | Consensus plus trust should beat its agents | It did not; it reduced risk and resisted one attacker | Move to crypto |
| Phase 2 | Crypto will show the value of the system | Only carry earned money; no combiner helped | Add safety |
| Phase 3 | Safety needs a shield | It works, at a small cost, but sits after the optimiser | Look at all the evidence |
| Phase 4 | The combination layer is the problem | The agents lacked information; the "multi-agent" layer was a central solve | Rebuild around hypotheses, a capital market and prices |
| Phases 5 to 7 | A market plus ADMM will work | It does on simulation; carry reproduced; momentum marginal; timing and reversal rejected | Re-check |
| Phase 8 | Volatility is 20% in every year | A bug; numbers moved and one decision flipped | Re-run everything, then decentralise |
| Phases 9 to 12 | A decentralised, resilient, safe version | Same portfolio; failures absorbed; W-MSR works only as a detector; safety partly works | Final comparison |
| Phase 13 | The system has an edge | Not established after multiple-testing correction | Open the sealed year |

### 14.2 Answers to the research questions

- **RQ1.** Yes: the neighbour-only optimiser matches the hub to 0.002 Sharpe and 0.3% of final equity (019, 020).
- **RQ2.** Topology governs communication cost, not the outcome. The mixing rate $\lvert\lambda_2(W)\rvert$ predicts iterations at 8 and 16 agents but not reliably at 4, and predicts better than algebraic connectivity.
- **RQ3.** Link failures and dropout are absorbed because the sum invariant survives them. W-MSR trimming fails inside the optimiser because it breaks that invariant; as a detector it isolates a consistent liar on robust graphs but not on a non-robust ring and not against random noise.
- **RQ4.** The monitor shows the safety margin and found an unexpected stress window; derisk shortens drawdowns at a Sharpe cost; hold needs a better limit.
- **RQ5.** Carry is a solid edge, momentum is marginal and concentrated in 2020 and 2021, reversal does not pay after costs. The market equals a fixed mix of good agents and beats it when one agent is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone.

### 14.3 The register of failed gates

We report these as failures; none was changed after the result was seen.

| Where | What failed |
|---|---|
| 012 | an over-confident agent is not punished reliably when a 2% wealth floor is used (6 of 20 seeds) |
| 013 | the first carry run (Sharpe 0.48): a belief whose sign could flip, and an unenforced volatility limit |
| 014 | the funding-forecast gate on daily and four-hourly bars (forecast significantly worse) |
| 015a | momentum's admission and the market's acceptance, because the agent held coins its card forbids |
| 016 | timing momentum was worse than the untimed twin |
| 017 | reversal's stand-alone admission, and market acceptance with reversal |
| 018 | momentum's admission after the volatility-limit correction (narrow fail) |
| 020 | gate A1 at four agents (correlation 0.60 against 0.7) |
| 021 | A3 (plain ring, predicted); trimmed mixing; the noise liar mostly not caught |
| 022 | A1 on hourly bars; A2 on daily bars; B1 (hold freezes on slow honest solves) |
| 023 | C2, the deflated Sharpe (0.07 to 0.10 against 0.95) |

## 15. Mistakes found, process lessons and limitations

### 15.1 Mistakes found and corrected

1. **A belief whose size was estimated from noise** (Phase 6): it flipped sign half the time. Fix: the card fixes the size; evidence can only switch the agent off.
2. **An agent holding positions its card forbids** (Phase 7). Fix: the engine enforces each agent's coin set; both runs count as trials; the fix came after seeing the failure, which is a forking path we disclose.
3. **The volatility limit measured against starting equity** (Phase 8). Fix: share of current equity; every result re-run.
4. **Two experiments could not be re-run** after that fix (carry improvement and timing) because their code had been deleted when rejected; their verdicts are comparisons under the old limit.
5. **A monitoring bug** (Phase 12): the monitor recorded the volatility of the rejected solve. Fix, with a test that fails on the old code.
6. **A gate that was too blunt** (Phase 12): the fixed residual limit of hold. Reported as failed.
7. **Runs lost to hardware** (a machine restart in the middle of experiment 017) and **runs abandoned because they would not finish** (the undefended liar on real data, 3 hours 40 minutes and 9 hours 38 minutes). Each is recorded in an amendment.

### 15.2 What worked as a way of working

- **Rules before runs.** Writing the pass or fail rule first made it easy to accept failures: they were never negotiated afterwards.
- **A single trial log.** The deflated Sharpe at the end was only possible because every variant had been logged from the start.
- **Deleting rejected code and recording the commit that holds it.** It kept the repository small and the history intact.
- **Cross-checks.** Re-running a baseline on the changed code (the carry re-run in Phase 7) and a table that reproduces its inputs (gate C1) caught inconsistencies early.

### 15.3 Limitations

- **Short sample, one regime.** Five and a half years, mostly one bull market, momentum's profit concentrated in 2020 and 2021. The sealed year has not been seen. Nothing was traded live.
- **Multiple testing.** The deflated Sharpe is below its threshold at 45 strategy trials, and what counts as one trial needs judgement.
- **Assumptions not varied.** The impact coefficient, the information coefficients on the cards (momentum's 0.05 is an assumption), the one-million-dollar scale and the taker fee were fixed and not stress-tested.
- **Provisional momentum.** The agent covers two coins and failed its own admission rule narrowly; it was kept to study coordination, not to claim an edge.
- **Risk-model gap.** Reversal still runs at 24% to 29% volatility against the 20% limit; a one-factor beta model underprices books that are not tightly neutral.
- **Cost of decentralisation.** Each agent solves the system step itself, so work grows with the number of agents (the sixteen-agent study took about three hours); some real-data rebalances reach the iteration cap (21 to 27 of about 135, even for the hub), with a small effect on profit.
- **Central pieces in simulation.** The step sizes, the stopping test and the simultaneous restart after an isolation are evaluated centrally.
- **Only three hypotheses were tested** on real data in the new engine; four more (cross-sectional momentum, size and illiquidity, low volatility, a machine-learning trend model) were planned and not built, and the second and third rungs of the carry ladder were not run.

## 16. Conclusion and future work

We started with a consensus system on US stocks and ended with a decentralised, resilient, formally monitored multi-agent trading system on crypto perpetuals. The path included three dead ends that taught us what mattered (a consensus layer that added nothing over an average, combiners that could not create information, a safety layer placed after the optimiser) and a decision, taken from ten experiments, to rebuild around agents as hypotheses, a capital market and prices. The claim that survives scrutiny is about mechanisms: the decentralised system reproduces the centralised one, failures cost communication and not return, the capital market protects against a bad agent, and the monitor shows where the system was in danger. The return claim is weaker. Carry is a real edge, and the combined system earns a Sharpe ratio of about 1.4 to 1.5 at its risk limit, but after correcting for the number of variants tried the development data alone cannot establish it.

**Future work.**
1. Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged.
2. Re-argue the hold supervisor's limit and lengthen the volatility-price search for fast bar sizes.
3. Add a second, alt-coin-market risk factor to close the risk-model gap.
4. Test further established hypotheses one at a time, each with a card and rules written first, and run the remaining carry rungs (crowding from open interest, a tail cap from high and low prices).
5. Move towards deployment: pre-agreed step sizes, a max-consensus stopping test, flooded isolation notices and a communication model with delays.

## References

*Prepared from memory of the primary sources. Verify details before submission.*

1. Boyd, S., Parikh, N., Chu, E., Peleato, B., Eckstein, J. (2011). Distributed optimization and statistical learning via the alternating direction method of multipliers. *Foundations and Trends in Machine Learning* 3(1).
2. Olfati-Saber, R., Murray, R. M. (2004). Consensus problems in networks of agents with switching topology and time-delays. *IEEE Transactions on Automatic Control* 49(9).
3. Xiao, L., Boyd, S., Lall, S. (2005). A scheme for robust distributed sensor fusion based on average consensus. *IPSN* (Metropolis weights).
4. Zhu, M., Martínez, S. (2010). Discrete-time dynamic average consensus. *Automatica* 46(2).
5. LeBlanc, H. J., Zhang, H., Koutsoukos, X., Sundaram, S. (2013). Resilient asymptotic consensus in robust networks. *IEEE Journal on Selected Areas in Communications* 31(4).
6. Chang, T.-H., Hong, M., Wang, X. (2015). Multi-agent distributed optimization via inexact consensus ADMM. *IEEE Transactions on Signal Processing* 63(2).
7. Kelly, J. L. (1956). A new interpretation of information rate. *Bell System Technical Journal* 35(4).
8. Beygelzimer, A., Langford, J., Pennock, D. (2012). Learning performance of prediction markets with Kelly bettors. *AAMAS* (arXiv:1201.6655).
9. Maler, O., Nickovic, D. (2004). Monitoring temporal properties of continuous signals. *FORMATS*. Donzé, A., Maler, O. (2010). Robust satisfaction of temporal logic over real-valued signals. *FORMATS*.
10. Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management* 15(3).
11. Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
12. Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). Carry. *Journal of Financial Economics* 127(2). He, S., Manela, A., Ross, O., von Wachter, V. (2022). Fundamentals of perpetual futures, arXiv:2212.06888.
13. Moskowitz, T., Ooi, Y. H., Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics* 104(2).
14. Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of Finance* 45(3).
15. Course lecture notes (AI3403): Consensus Theory, ADMM, Distributed Learning, Resilient Consensus, Temporal Logics. Epistemic logic and infection models were part of the course and are not used here.

## Appendix A. Every experiment

| No. | Date | Question | Outcome |
|---|---|---|---|
| 001 | 18 Oct | Does the consensus system beat its agents (US stocks)? | No: 0.81 against 0.90 for the naive average |
| 002 | 18 Oct | W-MSR against ADMM consensus | Different problems; ADMM close to its one-node optimum |
| 003 | 18 Oct | One compromised agent | Plain 0.46; W-MSR 0.74 (clean 0.81); protection from trimming |
| 004 | 1 Nov | Flat against hierarchical capital | Same Sharpe, lower risk; less resilient |
| 005 | 1 to 5 Nov | The v1 system on crypto, against Bitcoin | No edge; 57% to 80% volatility; shield halves drawdown |
| 006 | 1 Nov | Which v2 agents and combiners earn money | Only carry (and weakly Bitcoin timing); no combiner beats inverse volatility |
| 007 | 5 Nov | Decentralised ADMM combiner with true costs | Did not lower cost drag |
| 008 | 5 Nov | STL monitor, shield and central baseline (stocks) | Violations halved or better at almost no Sharpe cost |
| 009 | 5 Nov | Checks between rebalances | Adopted: worst volatility breach down by two thirds |
| 010 | 5 Nov | How the shield's cut is split | Uniform kept; risk-based cuts worse with an attacker |
| 011 | 6 Nov | Data audit; funding rule | Verified |
| 012 | 6 Nov | Both levels on simulated markets | Mostly pass; floor blunts selection; unlimited over-confident agent can ruin the system |
| 013 | 7 Nov | Carry in the new engine | Pass after fixing belief calibration (0.48 to 1.27, 1.12, 1.00) |
| 014 | 7 Nov | Funding forecast for carry | Rejected at the mechanical gate; code deleted |
| 015 | 7 Nov | Momentum and the market | 015a fail (agent broke its card); 015b admitted; market equals a fixed mix |
| 016 | 7 Nov | Timing momentum | Rejected; code deleted |
| 017 | 7 to 8 Nov | Reversal and the market of three | Reversal not admitted; market protects against it |
| 018 | 8 Nov | Re-run after the volatility-limit fix | Numbers changed; momentum's admission now fails (decision 0041) |
| 019 | 8 Nov | Neighbour-only optimiser on real data | Pass: equals the hub |
| 020 | 8 Nov | Topology and communication budget | Shape sets communication, not outcome; A1 failed at 4 agents |
| 021 | 8 Nov | Link failures, dropout, liar, W-MSR | Absorbed or isolated on robust graphs; trimming rejected |
| 022 | 8 to 9 Nov | STL monitor and supervisors | Partly: derisk usable; hold needs a better limit |
| 023 | 9 Nov | Final comparison; deflated Sharpe | Mechanisms match; return claim fails the correction |

## Appendix B. Every decision

Superseded decisions are the ones about the first system, replaced by decision 0032.

| No. | Decision | Status |
|---|---|---|
| 0001 | Start on 20 US large caps, daily data from yfinance | Superseded by 0032 |
| 0002 | Six simple forecasting agents with long-short portfolios | Superseded by 0032 |
| 0003 | Trust = forecast probability that an agent is profitable | Superseded by 0032 |
| 0004 | Consensus: trust-weighted W-MSR with pinning | Superseded by 0032 |
| 0005 | ADMM consensus as an alternative mode | Superseded by 0032 |
| 0006 | Agents own capital; it moves through W transpose | Superseded by 0032 |
| 0007 | Execution: system position nets agents' trades; costs on the net trade | Superseded by 0032 |
| 0008 | No lookahead is a tested invariant | Accepted |
| 0009 | Tooling: uv, data and results out of git | Accepted |
| 0010 | Two-level hierarchy: per-asset subagents inside each strategy | Superseded by 0032 |
| 0011 | Optional risk- and cost-aware reallocation speed | Superseded by 0032 |
| 0012 | Generalise the engine to 24/7 perpetual futures | Superseded by 0032 |
| 0013 | Crypto data: Binance USD-M, point-in-time and survivorship-free | Accepted |
| 0014 | v1 crypto benchmark protocol | Superseded by 0032 |
| 0015 | Start a second engine (v2) judged in absolute terms | Superseded by 0032 |
| 0016 | v2 books: rank-gauss scores, dollar- and beta-neutral, vol-targeted | Superseded by 0032 |
| 0017 | v2 combiners: compare several ways to mix agent books | Superseded by 0032 |
| 0018 | v2 costs: fee + square-root impact, and a liquidity floor | Accepted |
| 0019 | v2 cost-aware partial adjustment (opt-in) | Superseded by 0032 |
| 0020 | v2 research hygiene: sealed holdout, trial log, deflated Sharpe | Accepted |
| 0021 | v2: decentralised consensus-ADMM combiner on a ring | Superseded by 0032 |
| 0022 | Build the proposal's system on the v1 consensus engine; freeze v2 | Superseded by 0032 |
| 0023 | Hand-written quantitative STL, robustness normalised by each limit | Accepted |
| 0024 | The STL monitor always runs; the shield is opt-in | Superseded by 0032 |
| 0025 | Shield mechanism: scale the portfolio toward cash | Superseded by 0032 |
| 0026 | Safety limits | Superseded by 0036 |
| 0027 | Centralised baseline = the optimum of the ADMM problem | Superseded by 0032 |
| 0028 | Shield checks every bar between rebalances (de-risk only) | Superseded by 0032 |
| 0029 | How the shield's cut is split across agents | Superseded by 0032 |
| 0030 | Universe: a day missing for every symbol is a dump hole, not a market halt | Accepted |
| 0031 | Crypto drawdown limit consistent with the crypto vol limit | Superseded by 0032 |
| 0032 | Replace v1 and v2 with one new implementation | Accepted |
| 0033 | Two MAS levels: a wealth-staked market of hypothesis agents, ADMM asset cells | Accepted |
| 0034 | One agent per established hypothesis; timing inside the belief | Accepted |
| 0035 | W-MSR and belief-averaging between agents dropped; model averaging inside agents | Accepted |
| 0036 | Factor risk model, priced limits inside the ADMM, STL placements | Accepted |
| 0037 | Extended data store | Accepted |
| 0038 | Belief scale comes from the hypothesis card, evidence can only switch an agent off; the system volatility limit is enforced through the risk aversion | Accepted |
| 0039 | Timing inside H2's belief: two mechanism-based states, a shrunk and sign-constrained coefficient, kept only if it beats the untimed twin | Rejected by experiment 016 |
| 0040 | H4, residual reversal as the third agent, and the full admission gate | Accepted |
| 0041 | H2 (BTC/ETH momentum) stays in the roster as a provisional agent | Accepted |
| 0042 | Decentralised cell ADMM over a communication graph (dynamic average consensus) | Accepted |
| 0043 | Resilience of the decentralised optimiser: link failures, offline agents, and detect-and-isolate for a misbehaving agent | Accepted |
| 0044 | STL safety monitor and supervisor of the system | Accepted |
| 0045 | Interactive dashboard for the final demonstration | Accepted |

## Appendix C. Glossary

| Term | Meaning |
|---|---|
| Agent | an autonomous trading hypothesis with its own belief, capital and positions |
| Card | the written hypothesis of an agent: claim, mechanism, coins, expected edge, switch-off rule |
| Cell | an (agent, coin) pair |
| Hub | the central node of the centralised optimiser |
| Gossip round | one exchange of values between neighbours |
| Mixing rate | $\lvert\lambda_2(W)\rvert$; smaller means faster agreement |
| Perpetual future | a futures contract with no expiry; longs and shorts pay each other funding |
| Funding | a payment between longs and shorts every 8 hours that keeps the contract near the spot price |
| Sharpe ratio | annualised return divided by annualised volatility |
| Net | after fees, price impact and funding |
| Alpha | the part of a return not explained by a benchmark |
| Information coefficient (IC) | rank correlation between a score and the next return |
| Kelly fraction | the share of the optimal bet size actually used (here one half) |
| Drawdown | fall from the previous peak |
| Ex-ante volatility | volatility predicted by the risk model before trading |
| Pre-registered gate | a pass or fail rule written and committed before the runs it judges |
| Deflated Sharpe | the probability that a Sharpe of this size is real after allowing for the number of variants tried |
| Sealed holdout | data reserved for one final look: the last twelve months |
| W-MSR | the lecture's resilient consensus rule that discards extreme neighbour values |
| STL | signal temporal logic |

## Appendix D. How to reproduce a step from git

The repository is the record. `git tag legacy-v1-v2` marks the last commit of the consensus system and the v2 engine (`cf16351`); `git checkout legacy-v1-v2` reproduces experiments 001 to 010. Commits on branch `engine-rebuild` run in order from `7467db3` (the rebuild, 6 November) to the final comparison (`b086e9c`, 9 November); the commit hashes in each phase heading above locate each step. Each experiment write-up in `docs/experiments/` gives its exact command and its committed result tables in `docs/experiments/data/`; each design choice has a record in `docs/decisions/`. Rejected code is reproducible from the commit named in the experiment (for example the funding forecast at `8360532`). Raw data and run outputs are not in git.
