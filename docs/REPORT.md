# Resilient Decentralised Portfolio Consensus
## A multi-agent system for trading Binance perpetual futures

**Project report.** Course: Multi-Agent Systems (AI3403). Evidence base: development period April 2020 to November 2025. The final twelve months of data were sealed before the work began and have not been examined. The system has not been run live.

This report is self-contained: it assumes the multi-agent-systems background of the course and no knowledge of the software. Names of software modules are deliberately not used; every mechanism is described in terms of agents, communication, optimisation and logic. The experiment write-ups in the project repository (numbered 011 to 023) contain the full detail and the exact commands, and are cited as "experiment N" so every number here can be traced.

---

## Abstract

We study how a team of autonomous agents, each following a different, documented trading hypothesis, can jointly manage one portfolio of cryptocurrency perpetual futures without a central coordinator, while remaining correct under communication failures, agent dropout and misbehaving agents, and while satisfying formal safety specifications. The system has two levels. At the first level the agents are hypotheses (funding carry, time-series momentum, short-term reversal) that stake capital in a Kelly-bet market, so that capital migrates towards agents whose beliefs pay. At the second level the stakes of all agents on all coins are turned into one portfolio by a joint optimisation, solved by the alternating direction method of multipliers (ADMM), in which shared constraints and the cost of the net trade appear as prices. We replace the central node of this optimisation by dynamic average consensus over a communication graph, and add link failures, offline agents, a detect-and-isolate defence based on the W-MSR test, and a signal-temporal-logic (STL) safety monitor with two supervisors. Everything is evaluated against a centralised optimiser as the reference, on simulated markets where the truth is known and on five and a half years of real data, under pre-registered pass/fail rules and with the sealed final year untouched.

The main findings are: (1) the decentralised optimiser reproduces the centralised portfolio to within 0.002 Sharpe on every network shape tested, under 30% random link failures, with the largest agent offline for four months, and with a consistent liar isolated; the cost of decentralisation is communication and computation, not return; (2) network shape determines how many messages are needed, predicted by the mixing rate of the graph at eight and sixteen agents but not, as pre-registered, at four; (3) the lecture's trimmed-mean W-MSR rule cannot replace the averaging inside this optimiser (it destroys convergence even without an attacker), but its test works as a detector of a consistent liar on a sufficiently robust graph; a liar who hides inside the honest range is not caught; (4) the wealth-staked market of agents equals a fixed-weight mix when all agents are good but beats it by about 0.9 Sharpe on four-hourly and hourly data when one agent is bad, because it withdraws capital from the loser; (5) the STL monitor identifies the November 2022 collapse as the most severe stress window, a de-risking supervisor makes the worst drawdown shallower at a Sharpe cost of 0.02 to 0.20, and a hold-on-unsafe-solve supervisor stops corrupted solves but also freezes the system on slow honest ones; (6) the main system (carry and momentum) earns a net Sharpe ratio of about 1.4 to 1.5 at its 20% volatility limit, but its deflated Sharpe ratio, corrected for the 45 strategy variants tried, is about 0.1 against a threshold of 0.95, so the money result is not conclusive on the development data alone. Several pre-registered gates failed, and are reported as failures.

---

## 1. Introduction

### 1.1 Motivation

Constructing and managing a portfolio is a natural multi-agent problem. Different analysts hold different beliefs about what drives returns; they share one pool of capital, one set of risk limits and one market that charges them for trading; and the system has to keep working when a participant is wrong, offline or dishonest. The conventional engineering answer is a single optimiser that receives all forecasts and returns one portfolio. That design has three weaknesses that motivate a multi-agent treatment: it is a single point of failure, it hides the differences between the beliefs (which are the point of having several analysts), and it cannot be analysed with the tools of distributed computation (consensus speed, communication cost, robustness to faults).

### 1.2 Problem statement

Design and evaluate a system of agents that jointly trade a portfolio of cryptocurrency perpetual futures such that:
1. agents with heterogeneous beliefs coordinate without a central node and reach the same portfolio as a centralised optimiser;
2. the cost, the shared limits and the capital allocation are handled by prices that the agents agree on;
3. the system keeps working when links fail, agents drop out, or an agent sends false values;
4. formal safety requirements (volatility, drawdown, recovery, solver health) are monitored and, when necessary, enforced;
5. financial performance and risk are assessed honestly, with a centralised optimiser as the benchmark and with multiple-testing correction.

### 1.3 Research questions

| | Question |
|---|---|
| RQ1 | Does the decentralised (neighbour-only) optimiser reproduce the centralised portfolio on real data? |
| RQ2 | How does the communication topology affect convergence, communication cost and the result? |
| RQ3 | Does the decentralised consensus remain correct under link failures, agent dropout and a misbehaving agent, and does W-MSR protect it? |
| RQ4 | Does an STL monitor with a supervisor keep the system inside its safety specifications in stress periods, and at what cost? |
| RQ5 | What do the agents, and the market of agents, contribute in money and risk, and does the result survive correction for the number of variants tried? |

### 1.4 Contributions

1. A two-level multi-agent architecture: a capital-staked market of hypothesis agents above a joint ADMM over (agent, coin) cells, in which the shared limits and the transaction cost of the net trade are prices.
2. A neighbour-only version of that optimisation (dynamic average consensus inside sharing ADMM) that is equivalent to the central version on the complete graph, with an analysis of convergence against graph mixing rate and communication budget.
3. A resilience study: link failures, agent dropout, a detect-and-isolate defence built from the W-MSR test, and a documented negative result for W-MSR trimmed mixing inside the optimiser.
4. An STL safety monitor with two supervisors, with limits argued from a mandate before any run.
5. A pre-registered, multiple-testing-aware empirical evaluation that reports failures, including a bug found in the risk limit and the re-run of every earlier result after correcting it.

---

## 2. Background: the multi-agent concepts used

### 2.1 Agents and multi-agent systems
An agent perceives, holds an internal state, and acts to pursue an objective. Here an agent is a trading hypothesis: it perceives past prices, volumes and funding; its internal state includes a belief about the next return of each coin and its own capital; its action is a desired position in each coin. Agents are heterogeneous (different hypotheses), partially coupled (they share capital limits, market impact and a risk budget) and have no common objective beyond the portfolio.

### 2.2 Average consensus
For agents connected by an undirected graph with a doubly stochastic mixing matrix $W$, the iteration $x \leftarrow W x$ drives all agents to the average of their initial values, provided the graph is connected. The speed is governed by the second-largest eigenvalue modulus $|\lambda_2(W)|$: the error shrinks like $|\lambda_2|^k$ after $k$ rounds. Metropolis weights, $W_{ij} = 1/(1+\max(d_i,d_j))$ for neighbours with degrees $d_i, d_j$, give a doubly stochastic $W$ from the graph alone. Dynamic average consensus tracks the average of values that change over time: each agent adds its own change before mixing, so the sum of the estimates always equals the sum of the true values. The algebraic connectivity (second-smallest Laplacian eigenvalue) is the other standard measure of how well connected a graph is.

### 2.3 Distributed optimisation: ADMM
For a "sharing" problem, minimise $\sum_i f_i(x_i) + g\big(\sum_i x_i\big)$, ADMM alternates three steps: each agent minimises its own $f_i$ plus a quadratic penalty towards a consensus target (in parallel); a coordinator solves the shared term $g$ using the agents' average; and a price (dual variable) is updated by the accumulated disagreement. At convergence the price is the marginal value of the shared resource, which makes ADMM a mechanism design as much as an algorithm: agents are coordinated by a price, not by being told what to do. Convergence is monitored through primal and dual residuals.

### 2.4 Markets and distributed learning
In a prediction market of Kelly bettors, each agent stakes a fraction of its wealth proportional to its edge; wealth then compounds with the agent's own results, so wealth shifts to better-calibrated beliefs (a Bayes-like update), and the market's aggregate view is a wealth-weighted average. This is a decentralised learning rule: no agent evaluates another; the market does it through capital. Over-confident agents are punished by Kelly's own mathematics (growth turns negative above twice the optimal fraction).

### 2.5 Resilient consensus and W-MSR
In W-MSR (weighted mean subsequence reduced), each agent discards, coordinate by coordinate, up to $F$ neighbour values larger than its own and up to $F$ smaller, then averages the rest. If at most $F$ agents are malicious and the graph is sufficiently robust (for $F=1$, $(2,2)$-robust), honest agents still reach agreement inside the range of the honest initial values. Robustness is a property of the graph beyond connectivity: a ring is connected but not $(2,2)$-robust.

### 2.6 Signal temporal logic
STL specifies properties of real-valued signals, for example "always, the drawdown stays above $-15\%$" or "if volatility exceeds 40% it returns below within 14 days". Its quantitative semantics gives a robustness value: positive means satisfied with that margin, negative means violated by that much. A monitor computes the robustness over time; a supervisor can act on the margin.

### 2.7 Topics of the course that were not used
Epistemic logic and infection/epidemic models were part of the course and are not used in this project.

---

## 3. Problem formulation

### 3.1 Environment
The environment is the Binance USD-M perpetual futures market: contracts on coins that never expire. A long position pays, and a short receives, a funding payment (settled every eight hours, occasionally at shorter intervals) that anchors the contract to the spot price. Observations: open, high, low, close prices, traded volume, taker volume, funding events, the premium of the perpetual over the index, spot prices and open interest, available as bars of one day, four hours and one hour.

**Universe.** Point-in-time and survivorship-free: a coin enters when its rank by the 90-day median of daily dollar volume (computed strictly before the day) is within the top 50, stays while within the top 75, and is re-evaluated every 30 days; delisted coins are included. 243 distinct coins appear over the sample. A coin is tradable at a rebalance only if its trailing median daily dollar volume is at least one million dollars and it has a complete history window. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded.

**Costs.** A taker fee of 5 basis points on traded notional, plus a square-root market impact: slippage equals the coin's daily volatility times the square root of the traded share of its average daily volume (impact coefficient 1, an assumption; sensitivity to it is not reported). Funding is paid and received exactly as incurred. Assets under management are one million dollars and a position may be at most 5% of a coin's daily volume.

**Timing.** The system rebalances every 14 days on daily bars, every 5 days on four-hourly bars and every 48 hours on hourly bars. Anything computed at bar $t$ uses only information before $t$.

### 3.2 Agents
Agent $i$ holds wealth $W_i$ and for each coin $a$ a belief $\mu_{ia}$: its expected net return of a unit position over one holding period. Its action is a position $x_{ia}$ (notional) in coin $a$.

### 3.3 The joint portfolio problem
Let $X_a=\sum_i x_{ia}$ be the net position in coin $a$ and $h_a$ the currently held net position. The system solves, at each rebalance,

$$\min_{\{x_{ia}\}}\ \sum_{i,a} \Big[-\mu_{ia}x_{ia} + \tfrac{\gamma_i}{2}d_a x_{ia}^2\Big] + \sum_i \tfrac{\gamma_i}{2}\,(B^\top x_i)^\top F\,(B^\top x_i) + \sum_a C_a(X_a-h_a) + \tfrac{\lambda}{2}\,\mathrm{Var}(X)$$

where $\gamma_i = 1/(f_i W_i)$ is agent $i$'s risk aversion (Kelly fraction $f_i = 0.5$), $d_a$ the idiosyncratic variance of coin $a$, $B$ and $F$ the loadings and covariance of a one-factor market-beta risk model, and $C_a(d)=\text{fee}\,|d|+\kappa_a|d|^{3/2}$ the trading cost, charged on the **net** trade: two agents trading opposite ways in the same coin cancel and pay only for the difference. Subject to:

| Constraint | Scope | Form |
|---|---|---|
| Dollar and beta neutrality | agents whose hypothesis is market-neutral | $\sum_a x_{ia}=0$, $\sum_a \beta_a x_{ia}=0$ |
| Capacity | each cell | $\lvert x_{ia}\rvert \le 5\%\times$ the coin's daily volume |
| Margin | each agent | $\sum_a\lvert x_{ia}\rvert \le 3\,W_i$ |
| Gross cap | system | $\sum_a\lvert X_a\rvert \le 3\times$ equity |
| Beta band | system | $\lvert\sum_a \beta_a X_a\rvert \le 0.25\times$ equity |
| Allowed coins | each agent | $x_{ia}=0$ outside the agent's declared coin set |
| Volatility limit | system | a price $\lambda$ on system variance, searched until ex-ante volatility is 20% a year |

A pair $(i,a)$ is a **cell**, a sub-agent that manages one coin for one agent. The dual variables of the constraints are prices: of dollar neutrality, of market beta, of margin (capital), of the net trade per coin, and of variance. These prices are the coordination signal.

### 3.4 Objective for evaluation
Out-of-sample net return per unit of risk (annualised Sharpe ratio) against zero, with every cost included; the benchmark for any mechanism is the same agents solved by the centralised optimiser.

---

## 4. System design

### 4.1 Level 1: hypothesis agents and the capital-staked market

Each agent implements one documented hypothesis described on a **hypothesis card** written before testing: the claim, the mechanism, the allowed coins, the predicted sign and size of its edge, and the rule that switches it off. The belief follows the fundamental law of active management:

$$\mu_{ia} = \text{sign}_i\cdot IC_i \cdot \sigma_{H,a}\cdot z_{ia}$$

where $\sigma_{H,a}$ is coin $a$'s volatility over one holding period, $z_{ia}$ a standardised score of the hypothesis, and $IC_i$ the card's information coefficient (the expected rank correlation between score and next return), a small fixed number. Crucially, **the size of the belief is the card's, not an estimate from recent results**: a trailing information coefficient is so noisy that its sign flips about half the time (this was observed, and cost a first version of the carry agent more than half its Sharpe). Evidence can only switch an agent off: if the expanding-window mean of its realised skill has a $t$-statistic below $-2$ after 20 periods, its belief is set to zero; it never bets the opposite.

The three agents:

| Agent | Hypothesis | Mechanism | Score | Coins | Neutral? | Card $IC$ |
|---|---|---|---|---|---|---|
| **Funding carry** | Holders of the crowded side pay the other side; coins with low trailing funding outperform coins with high funding | Funding is a transfer; expected return = carry + expected price change | rank of the negative 14-day mean funding | all tradable | yes (dollar and beta) | 0.02 |
| **Time-series momentum** | A coin's own trailing 30-day return, in units of its volatility, predicts the sign of its next return | Slow diffusion of information, liquidation dynamics | clipped $t$-statistic of the 30-day return | Bitcoin and Ethereum only | no (owns net exposure) | 0.05 (assumption) |
| **Residual reversal** | A coin that fell more than the market over the last 7 days rebounds | Liquidity provision: demand for immediacy moves prices temporarily | rank of the negative 7-day beta-removed return | all tradable | yes | 0.02 |

Each agent stakes half-Kelly on its own belief. The **market** works as follows: the system trades the netted sum of the agents' positions; each agent's account earns the profit and loss of its own positions minus its share of the cost and funding, so the accounts sum exactly to the real result; each agent's wealth compounds with its own account return. A small floor (2% of total wealth) keeps a failed agent alive so the market stays able to re-allocate. There is no averaging of beliefs between agents: the agents "vote" only through capital.

### 4.2 Level 2: the joint optimisation by ADMM

Section 3.3 is a sharing problem: the agents' local terms (belief, own risk, neutrality, margin, capacity) are separable across agents, and they are coupled through the net position $X$ (cost, gross cap, beta band, variance). The centralised ("hub") ADMM proceeds, until residuals fall below tolerance, as follows:

1. **Local step (each agent, in parallel):** minimise its own cost plus a quadratic penalty towards the current consensus. This is a convex problem with a closed form for the cost term and a nested one-dimensional root search for the constrained agent step.
2. **System step (hub):** from the average position, solve the shared problem: the net trade cost, gross cap, beta band and variance price, giving the consensus net position.
3. **Price update:** the dual variable, one price per coin, is increased by the discrepancy between the average position and the consensus.

The coordination is by prices: the margin price tells an agent how scarce its capital is, the net-trade price tells it what its trade costs the system, the neutrality and beta prices tell it what exposure costs. A test of the solver against a slow, exact one-node reference showed identical solutions (Section 6.1).

The 20% volatility limit is enforced as a price: after each solve, if the ex-ante volatility of the net position exceeds 20% the variance price $\lambda$ is raised and the problem re-solved (at most five times). This lets the agent that adds risk pay for it, instead of scaling everyone down uniformly. In a test at equal total volatility the priced limit left the market-neutral agent 97% of its unconstrained position where a uniform shrink left it 45%.

### 4.3 Removing the hub: dynamic average consensus inside ADMM

The hub does three global things: it averages positions, it solves the system step, and it broadcasts the price. In the decentralised version each agent keeps local copies of all three: an estimate $s_i$ of the average position, its own system-step solution $z_i$ and its own price $u_i$ (the system data, costs and limits, are public). Each iteration:

(a) every agent performs its local step against its own price, exactly as before;
(b) it adds its change of position to its estimate and mixes with its neighbours: $s \leftarrow W^r\,(s + x_{\text{new}} - x_{\text{old}})$ with $r$ gossip rounds;
(c) it solves the system step from its own estimate;
(d) prices are updated and mixed likewise: $u \leftarrow W^r\,(u + \hat s - z)$.

Because $W$ is doubly stochastic and each agent adds its own change before mixing, the sum of the estimates always equals the sum of the true positions, so at a fixed point all estimates equal the true average and all prices agree: the fixed point is the hub's, hence the optimum. On the complete graph with exact mixing the algorithm **is** the hub algorithm. The stopping test also requires agreement between agents' estimates and prices (a run once stopped "converged" while agents still disagreed by about 10%). The network is a parameter of the mixing matrix only: complete, ring, line, star and random graphs were used.

What remains central in the experiments, and is stated as such: the step sizes depend on the mean risk aversion (a number agents would agree on once before trading), and the stopping test is evaluated by the simulator (a deployment would flood a max-consensus over the graph's diameter).

### 4.4 Resilience mechanisms

| Fault | Mechanism |
|---|---|
| **Link failure** | Each edge is down with probability $q$ in every gossip round; Metropolis weights are recomputed on the edges that are up. The mixing stays doubly stochastic, so the sum invariant of Section 4.3 holds and the optimum is still reached. |
| **Agent dropout** | The agent's positions are closed and the others solve the same problem on the graph without its node. |
| **Misbehaving agent (liar)** | Detect and isolate. Each agent counts, per neighbour, the share of coordinates in which that neighbour's value is the most extreme beyond its own (the value W-MSR would discard first), for both the average estimates and the prices. A neighbour that is extreme in at least 90% of the coordinates of both for 50 consecutive iterations is flagged; an agent flagged by more than half of its neighbours is isolated, and the others restart without it. Plain averaging is used otherwise. |

W-MSR trimming was first tried as the mixing rule inside the optimiser and abandoned (Section 6.5): trimming discards part of the sum that the agents track, so the invariant is lost and they agree on a wrong average.

### 4.5 Formal safety: the STL monitor and supervisors

**Specifications** (limits fixed from a written mandate before any run, never chosen by comparing returns):

| Spec | Meaning | Limit |
|---|---|---|
| $\varphi_{\text{vol}}$ | ex-ante volatility at a rebalance stays within the target in force | at most 1.05 × target |
| $\varphi_{\text{dd}}$ | drawdown from the peak of the last 365 days stays above the limit | $-15\%$ |
| $\varphi_{\text{rvol}}$ | realised 30-day volatility stays below a ceiling and any breach recovers | 40%, recovery within 14 days |
| $\varphi_{\text{solve}}$ | the optimisation solve converged (relative residual small) | residual at most $10^{-3}$ |

The **monitor** records, for each bar, the quantitative robustness of each spec (the signed distance from violation), summarised for three stress windows (May to July 2021, the May 2022 Luna collapse, and the November 2022 to January 2023 FTX collapse). Two **supervisors**, off by default:
- **Derisk:** multiplies the volatility target by a factor that equals 1 while half the drawdown budget is left and falls linearly to 0.2 at the limit. It acts through the existing volatility price, so the optimiser re-solves with a tighter target and costs included, instead of a post-hoc rescale.
- **Hold:** when a solve is unsafe (it did not converge and its residual exceeds $10^{-3}$) the system trades nothing and keeps its current positions. This is the fail-safe against a corrupted solve.

---

## 5. Evaluation methodology

1. **Reference.** The centralised optimiser with the same agents, data and costs. Every decentralised or resilience result is reported against it, or against the reference that would be right for the failure (for example, the centralised system without the agent that is offline).
2. **Data discipline.** No lookahead (an invariant that is tested); the development period ends in November 2025 and the last twelve months are sealed, to be opened once, after the design is frozen.
3. **Pre-registration.** The pass/fail rules of each experiment, with thresholds, were written and committed before its runs. Amendments are dated and state whether any result had been seen. Rejected code is deleted and the commit that holds it is recorded.
4. **Statistics.** Net annualised Sharpe ratio with a 90% moving-block bootstrap interval (7-day blocks); paired block-bootstrap Sharpe differences for comparisons; the intercept ("alpha") of a regression on benchmark returns, with a block-bootstrap interval; rank information coefficient with its $t$-statistic; the **deflated Sharpe ratio** of Bailey and López de Prado, which gives the probability that the best of $N$ trials has a true Sharpe above zero given the spread of trial Sharpes, the skewness and kurtosis of returns and the sample length.
5. **Trial accounting.** Every variant evaluated is appended to a log. A strategy trial is one (strategy variant, bar size); exact repeats count once; engineering variants (topology, resilience, safety) are counted separately as the conservative total.
6. **Metrics reported.** Financial: net Sharpe, compound annual growth, volatility, maximum drawdown, turnover, cost. Multi-agent: iterations to convergence, rebalances that hit the iteration cap, messages per rebalance, agreement between agents, error against the central optimum, who was isolated. Safety: robustness per spec, violating bars, held rebalances.

---

## 6. Results

All returns are net of fees, price impact and funding. Sharpe = annualised return per unit of volatility. Intervals are 90%.

### 6.1 Validation on simulated markets (experiment 012)
The mechanisms were first tested on simulated markets where the truth is known.

| Mechanism | Criterion | Result |
|---|---|---|
| Joint optimiser | Matches an exact one-node solver on every coupling (35 random problems; cost on net trade, capacity, margin, gross cap, beta band, and combined) | Pass (typical error $10^{-7}$; the hardest case needs about 1,100 iterations) |
| Prices | Non-negative, zero when slack; equal to the marginal value of the limit within 5% | Pass |
| Netting | Opposite views on a coin are charged on the net trade, which is cheaper than the sum | Pass |
| Capital follows its price | A tighter margin moves capital to the best-edge coin | Pass |
| Market selects skill | A skilled agent's share passes 0.5 at the analytically computed horizon in at least 90% of seeds | Pass (160 periods) |
| Market drops decayed skill | Share falls after skill vanishes | Pass |
| Accounting | Account P&Ls, cells and wealth sum to the real values exactly | Pass ($10^{-9}$) |
| Market punishes over-confidence | Over-confident agent ends with less wealth | **Fails with the 2% floor** (6 of 20 seeds); passes without a floor (18 of 20) |
| Trimmed mean / sanity guard against a corrupt member | Change below 10% | Restated after a failed run; the guard equals the honest average exactly |
| Timing on planted regime skill | Timed beats untimed; costs little when no dependence | Pass |

Two findings shaped the design: **the wealth floor blunts selection** (it re-seeds a ruined agent, acting as a rebalancing rule), and **an unlimited over-confident agent can ruin the whole system** (2 to 5 of 20 seeds wiped out at an effective Kelly fraction of 2), since wealth dynamics are too slow to prevent it. Hence the priced margin and gross limits and an agent-level calibration check are always on, Kelly fractions stay at or below 0.5, and the floor is justified as a liveness device, not as a selector.

### 6.2 The agents on real data (experiment 018, after the correction of Section 7.2)
Net Sharpe (daily / four-hourly / hourly) with the daily 90% interval:

| Agent | Net Sharpe | Volatility | Verdict |
|---|---|---|---|
| Carry | 1.14 / 1.12 / 0.94 (daily $[0.36, 1.90]$) | about 19% to 23% | Works. Rank IC about 0.02 to 0.035 |
| Momentum (BTC, ETH) | 0.96 / 0.80 / 0.76 (daily $[0.24, 1.61]$) | 13% to 15% | Profitable, about +9% a year above what Bitcoin explains, but its pre-registered admission rule (alpha lower bound above zero on at least two of three bar sizes) narrowly fails: only daily passes. Kept as a *provisional* agent, with no claim of its stand-alone edge |
| Reversal | $-0.66$ / $-1.17$ / $-0.99$ | 24% to 29% | The signal is real (rank IC 0.025 / 0.042 / 0.046, $t$ = 1.5 / 4.4 / 7.3) but costs exceed the gain (annual cost 5.9% to 9.5%, turnover 45 to 91 times equity); not admitted |

Two further hypotheses were examined and rejected: a funding-forecast improvement to carry did not help (experiment 014), and timing momentum with a bull/panic state estimated from data was slightly worse than the plain agent (Sharpe 1.03 / 0.90 / 0.86 against 1.06 / 0.95 / 0.90 before the correction; experiment 016). Their code was deleted.

### 6.3 What the market of agents adds (experiments 015 and 018)
| Comparison (paired Sharpe difference, daily / 4h / hourly) | Result |
|---|---|
| Market of carry + momentum vs carry alone | $+0.26$ / $+0.36$ / $+0.55$; intervals above zero |
| Market of carry + momentum vs a fixed-weight blend of the two stand-alone runs | $-0.07$ / $+0.14$ / $+0.29$; no interval excludes zero |
| Market of three (with reversal) vs market of two | $-0.14$ / $-0.14$ / $-0.15$ (adding a bad agent hurts) |
| Market of three vs a fixed inverse-volatility blend of the three stand-alone runs | $+0.35$ $[-0.17, 0.84]$ / $+0.86$ $[0.31, 1.35]$ / $+0.88$ $[0.34, 1.39]$ |

With good agents the market is indistinguishable from a fixed mix: the gain over carry alone is diversification. With a failing agent present the market clearly beats a fixed mix, because it moves capital: reversal's final wealth share was 1.9% / 1.8% / 2.0% (the floor), while a fixed blend kept paying for its losses. **This is the most important real-data evidence for the capital-staked market: protection against a bad agent, not extra return.** (The fixed blend used full-sample volatilities for its weights.) The market also cost 2.4% to 3.2% a year in trading cost.

### 6.4 RQ1: the decentralised optimiser equals the centralised one (experiment 019)
Three agents, daily bars, same data and settings:

| Run | Net Sharpe | Final equity | Rebalances at the iteration cap |
|---|---|---|---|
| Centralised hub | 1.258 | 3.564 | 21 of about 137 |
| Graph, complete | 1.257 | 3.560 | 22 |
| Graph, line, 1 gossip round | 1.256 | 3.554 | 43 |
| Graph, line, 3 gossip rounds | 1.257 | 3.559 | 24 |

Pre-registered rule: Sharpe within 0.01 and final equity within 1% of the hub. **Pass**: the largest difference is 0.002 in Sharpe and 0.3% in equity; every agent's account is identical to three decimals. The cost of a poor topology is visible in the cap counts: the line with one round hits the iteration cap twice as often.

### 6.5 RQ2: topology and communication budget (experiment 020)
**Part A: simulated problems** (all limits binding; tolerance $10^{-8}$; iteration cap 4,000). Median iterations to converge at three gossip rounds, with the mixing rate $|\lambda_2(W)|$ in brackets in column order:

| Agents | Complete | Ring | Random | Star | Line |
|---|---|---|---|---|---|
| 4 (0 / 0.33 / 0.75 / 0.75 / 0.80) | 151 | 165 | 228 | 264 | 389 |
| 8 (0 / 0.80 / 0.68 / 0.88 / 0.95) | 386 | 499 | 883 | 1,183 | not converged |
| 16 (0 / 0.95 / 0.79 / 0.94 / 0.99) | 1,000 | 3,709 (2 of 3 converged) | 1,000 | not converged | not converged |

- Gate A1: the Spearman correlation between $|\lambda_2(W)|$ and iterations should be at least 0.7 at each size. Result: 0.60 at 4 agents (**fail**), 0.90 at 8, 0.78 at 16. At four agents the difficulty of the individual problem (one problem takes about 830 iterations on every topology, including the complete graph) dominates; within each problem the ordering is as predicted (mean 0.79 at 4, 0.96 at 8, 0.82 at 16). We report the failure as pre-registered.
- Gate A2: the complete graph takes exactly the hub's iterations: **pass** (it is the hub algorithm).
- The star has higher algebraic connectivity than the ring (1.0 against 0.59 at eight agents) but is slower (1,183 against 499 iterations): **$|\lambda_2(W)|$ predicts better than algebraic connectivity** because, with Metropolis weights, the centre of a star is a bottleneck.
- Fewest messages: one gossip round on the complete graph, and on the ring at four agents; three rounds elsewhere. Ten rounds waste messages.
- The error after a fixed iteration budget is almost the same on every topology early on (about 0.40 at 25 iterations and 0.16 at 100 at eight agents); topology decides how long the last, precise part takes.

**Part B: real data, eight agents** (carry with 7, 14 and 30-day windows; momentum with 15, 30 and 60-day lookbacks; reversal with 3 and 7-day lookbacks, used only as parameter variants to study coordination):

| Run | Net Sharpe | Final equity (vs hub) | Rebalances at cap | Mean iterations | Messages per rebalance |
|---|---|---|---|---|---|
| Hub | 1.240 | 3.578 | 27 | 1,427 | (hub) |
| Complete graph, 1 round | 1.239 | $-0.02\%$ | 29 | 1,459 | 81,716 |
| Ring, 1 round | 1.238 | $-0.16\%$ | 114 | 2,885 | 46,160 |
| Ring, 3 rounds | 1.239 | $-0.08\%$ | 43 | 1,870 | 89,755 |
| Line, 3 rounds | 1.238 | $-0.22\%$ | 122 | 2,949 | 123,854 |
| Star, 3 rounds | 1.240 | $-0.01\%$ | 96 | 2,743 | 115,194 |
| Hub, 200-iteration cap | 1.217 | $-2.8\%$ | 135 | 200 | (hub) |
| Ring, 3 rounds, 200-iteration cap | 1.212 | $-3.5\%$ | 135 | 200 | 9,600 |

Gate B1 (every uncapped graph run within 0.02 Sharpe and 2% equity of the hub): **pass** (within 0.002 and 0.23%). **Network shape governs the communication, not the outcome.** A short communication budget costs about 0.025 Sharpe and 3% of final equity. By the pre-registered recommendation rule, the default for later experiments is the complete graph with one gossip round. A caveat recorded in advance: link failures on a complete graph are a weak test, so resilience experiments also used a sparse graph.

### 6.6 RQ3: resilience (experiment 021)
**Simulated problems** (eight agents; fresh problems not used to set any parameter):

| Gate | Result |
|---|---|
| A1: with each link down with probability 0.1 or 0.3, every run on the complete graph, a two-neighbour-each-side ring ("ring2") and the ring converges with error at most $10^{-4}$ | **Pass** (error at most $5.4\times10^{-6}$; still converged at 0.5; the ring needs 60% more iterations at $q=0.3$) |
| A2: on complete and ring2, a constant liar of size 0.001 to 1.0 (from 4% of a typical position) is isolated, only the liar is isolated, and the error against the optimum without the liar is at most $10^{-4}$; with no liar nobody is isolated | **Pass** (18 of 18 runs; error at most $4.4\times10^{-6}$) |
| A3 (predicted to fail): the same on the plain ring | **Fails as predicted**: in all 9 liar runs an honest agent was also isolated and the graph fell apart (the ring is not $(2,2)$-robust) |
| A4 (reported): undefended constant liar; noise liar with the detector | Undefended: error 5.5 to 5.9 times a typical position, no convergence. Noise liar: isolated in 1 of 6 runs; otherwise no convergence and error 12.5 to 14.8 times a typical position |
| A5 (decides the code): W-MSR trimmed mixing with no attacker | No run converged; error 0.50 to 4.8 times a typical position in all six runs. **Rejected and deleted** |

**Real data, daily, eight agents:**

| Run | Net Sharpe | Final equity | Reference |
|---|---|---|---|
| Hub | 1.240 | 3.578 | |
| Complete graph, 30% of links down each round | 1.239 | 3.577 | within 0.001 of the hub (gate B1: pass) |
| Ring, 3 rounds, 30% of links down | 1.239 | 3.575 | mean iterations 1,870 to 2,155; capped rebalances 43 to 56 |
| Largest agent (a carry variant, 38% of final wealth) offline May to August 2022 (Luna), hub / complete / ring | 1.225 / 1.225 / 1.225 | 3.476 / 3.476 / 3.474 | graph equals the hub with that agent offline (gate B2: pass); highest ex-ante volatility inside the window 17.5% against 20.9% outside |
| A momentum variant lies (adds 0.01 to everything), detector on | 1.182 | 3.391 | equals the hub without that agent, 1.182 (gate B3: pass); liar isolated at the first rebalance, nobody else ever |

Dropping the largest agent for four months costs 0.015 Sharpe and 2.8% of final equity, and leaving the lying agent out costs 0.058 Sharpe and 5.2% of final equity relative to the full hub; **the cost is what is missing (its capital sits idle), not the coordination.** The undefended liar on real data was not completed: its solves diverge and each would need hours (amendment recorded).

Conclusions: link failures and dropped agents are absorbed at the price of extra communication; the lecture's trimmed W-MSR cannot be placed inside this optimiser, but its test works as a detector, and what decides whether the system can defend itself is the **robustness of the graph, not only its connectivity**; a liar that hides in the honest range is not caught.

### 6.7 RQ4: the STL monitor and supervisors (experiment 022)
**The main system** (carry and momentum, centralised, daily / four-hourly / hourly):

| Safety mode | Sharpe | CAGR | Worst 365-day drawdown | Ex-ante volatility within 1.05 × target |
|---|---|---|---|---|
| Off | 1.394 / 1.478 / 1.483 | 31.2% / 29.8% / 29.2% | $-23.7\%$ / $-24.4\%$ / $-25.9\%$ | 97.8% / 97.6% / **94.3%** of rebalances |
| Derisk | 1.277 / 1.275 / 1.462 | 23.9% / 21.0% / 24.3% | $-19.7\%$ / $-18.8\%$ / $-16.7\%$ | 100% / 97.6% / 94.3% |

- **Gate A1** (solver health holds at every rebalance, and the volatility spec at at least 95% of rebalances): solver health always holds; the volatility spec **fails on hourly** (94.3%). The price search is limited to five re-solves and a 2% band, and on hourly data the covariance moves faster than the warm-started price follows. A limitation of the search, not a bug.
- **Gate A2** (derisk has fewer bars violating the drawdown spec and a shallower worst drawdown): the worst drawdown is shallower on all three bar sizes, and the violating bars fall on four-hourly (2,159 against 2,223) and hourly (5,135 against 7,695), but **rise on daily** (229 against 211): smaller positions after a loss recover more slowly. **A2 fails on daily.**
- The cost of derisk: Sharpe $-0.12$ / $-0.20$ / $-0.02$, CAGR $-7.3$ / $-8.8$ / $-4.9$ points. Limits are never chosen by Sharpe, so this is the price, not a criterion.
- **Stress windows.** The tightest was not May 2021 or Luna (the system made money in both, drawdown within the window at most $-8.5\%$) but the **FTX collapse (November 2022 to January 2023)**, the only window in which the drawdown spec was violated (1 daily bar, 444 four-hourly, 1,741 hourly). There derisk acts: on four-hourly the window drawdown falls from $-8.5\%$ to $-2.0\%$ and volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%).

**A stealthy liar on real data** (carry, momentum and reversal; reversal sends noise from May to July 2022; complete graph):

| Run | Sharpe | Final equity | Return inside window | Unsafe solves | Held |
|---|---|---|---|---|---|
| No liar | 1.257 | 3.56 | 11.7% | 8 (all in 2025) | |
| Liar, hold | 1.033 | 2.77 | 6.7% | 15 | 15 |
| Liar, no defence | stopped: the corrupted solve diverges (the largest iterate grows from 0.4 to 44 in 700 iterations; one solve takes about 45 minutes) | | | | |

Gate B1 (every unsafe solve held, all inside the liar's window, none outside) **fails**: all six rebalances in the window were held (relative residual 1.18 to 1.62), but nine honest, slowly converging solves in 2025 (residuals 0.0013 to 0.0059) were also held, and the frozen positions drifted to up to 31% volatility, lowering the whole-period Sharpe from 1.26 to 1.03. The residuals of the attack and of slow honest convergence differ by a factor of about 300, so a better limit exists; it is a follow-up and was not changed after seeing the result. Decision: the monitor is on in every run; derisk is usable; hold stays off until its limit is re-argued.

### 6.8 RQ5: the final comparison and the multiple-testing verdict (experiment 023)
No new run: a consistency table over experiments 018 to 022 (every shared figure reproduces to 0.001, gate C1: pass).

| Net Sharpe [90% interval] | Daily | Four-hourly | Hourly |
|---|---|---|---|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [$-0.03$, 1.44] |
| Reversal | $-0.66$ [$-1.29$, $-0.03$] | $-1.17$ [$-1.81$, $-0.48$] | $-0.99$ [$-1.63$, $-0.32$] |
| **Main system (carry + momentum market)** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 blend carry + momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2% / 29.8% / 29.2%, volatility 21% / 19% / 18%, maximum drawdown $-23.7\%$ / $-24.4\%$ / $-25.9\%$.

**Deflated Sharpe (gate C2: at least 0.95).** With $N = 45$ strategy trials (15 variants on each of three bar sizes; trial-Sharpe variance 0.82) the deflated Sharpe of the main system is **0.070 / 0.100 / 0.101** (0.031 / 0.046 / 0.047 counting all 74 engineering variants): **fail on every bar size**. It exceeds 0.95 only for $N \le 2$ trials, and is about 0.5 at $N=10$. This says that a best Sharpe of 1.4 to 1.5 among 45 trials of widely spread quality (from $-1.2$ to 1.5) is what chance would deliver with probability about 90%. It does not say there is no edge: carry's interval is above zero on every bar size. The sealed final year is the independent test.

**Safety and mechanism summary.** Decentralised consensus, every topology, link failures, an offline agent and an isolated liar all reproduce the centralised portfolio to within 0.002 Sharpe; their costs are up to 2.7 times the messages and 4.5 times the capped rebalances (on a line).

---

## 7. Discussion

### 7.1 Answers to the research questions
- **RQ1 (decentralised equals centralised):** Yes, on real data, to within 0.002 Sharpe and 0.3% of final equity (experiments 019, 020).
- **RQ2 (topology):** It governs communication, not the outcome. The mixing rate $|\lambda_2(W)|$ predicts the iterations needed at eight and sixteen agents, not reliably at four, and predicts better than algebraic connectivity. With a short budget, sparse graphs leave agents in disagreement and cost about 3% of final equity.
- **RQ3 (resilience and W-MSR):** Link failures and agent dropout are absorbed at extra communication. The lecture's W-MSR as a mixing rule fails inside this optimiser; as a detector it isolates a consistent liar exactly and without false alarms on robust graphs (complete, ring2), but fails on a non-robust ring and against random noise, which is why a supervisor is needed.
- **RQ4 (STL):** The monitor makes the safety margin visible bar by bar and identified a window we had not predicted. De-risking limits the worst drawdown at a Sharpe cost; its drawdown-breach-count gate fails on daily bars and the volatility-spec gate fails on hourly; the hold supervisor needs a better-argued limit.
- **RQ5 (money and agents):** Carry is a solid edge; momentum is marginal and concentrated in 2020 to 2021; reversal does not pay after costs. The market of agents equals a fixed mix of good agents and beats it when one agent is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone.

### 7.2 Mistakes found and corrected (reported as part of the result)
1. **An agent held positions its own card forbids.** Momentum's first run held hedge positions in other coins (the optimiser neutralised market exposure with an alt-coin basket), giving 39% volatility and a Sharpe of $-0.45$ on daily bars. The system now enforces each agent's coin set; the corrected agent has positive Sharpe. Both runs count as trials; the correction came after seeing the failure, which is a forking path that we disclose.
2. **The volatility limit used starting equity, not current equity.** As the system grew, its effective limit fell (about 8% by 2025 on daily bars), and a losing agent's limit became large relative to its remaining equity. After correcting it every system runs at 18% to 21% in every year; Sharpe ratios fell by 0.03 to 0.2, returns rose, momentum's admission flipped from pass to a narrow fail, and the worry that "the risk model underestimates risk" turned out to be mostly this bug. Every earlier experiment was re-run.
3. **A monitoring bug:** on a held rebalance the monitor recorded the volatility of the rejected solve instead of the held positions; fixed, with a test that fails on the old code.
4. **A gate that was too blunt:** the fixed residual limit of the hold supervisor cannot tell an attack from slow honest convergence. It was reported as failed, not tuned away.

### 7.3 Limitations and threats to validity
- **Short sample, one regime.** Five and a half years, mostly one bull market; momentum's profit is concentrated in 2020 to 2021. The sealed final year has not been seen. Nothing has been traded live.
- **Multiple testing.** The deflated Sharpe is below the threshold at 45 strategy trials; the count itself requires judgement (what counts as one trial).
- **Assumptions not varied.** The impact coefficient, the information coefficients of the cards (momentum's 0.05 is an assumption), the one-million-dollar scale and the taker-fee assumption were fixed, not stress-tested.
- **The momentum agent is two coins** and is "provisional": it failed its own admission rule narrowly after the correction, and was kept to study coordination, not to claim an edge.
- **Residual risk-model gap.** Reversal still runs at 24% to 29% volatility against the 20% limit; a one-factor beta model underprices books that are not tightly neutral.
- **Decentralisation costs.** Every agent solves the system step itself (work grows with the number of agents; the sixteen-agent topology study took about three hours), and some real-data rebalances stop at the iteration cap (21 to 27 of about 135 even for the hub), though the effect on profit is small.
- **What remains central in the simulation:** the step-size constants, the stopping test and the simultaneous restart after an isolation are evaluated centrally; a deployment would use a pre-agreed constant, a max-consensus over the graph's diameter and a flooded isolation notice.
- **Two earlier experiments (carry improvement and timing) were not re-run** after the volatility fix, because their code had been deleted when they were rejected; their verdicts are comparisons under the old limit.

### 7.4 Observations that connect to the theory
- **Prices as coordination.** The agents never see each other's beliefs; they see prices (margin, net trade, neutrality, beta, variance). The system-wide volatility limit as a price removed a cross-subsidy that a uniform rescale creates.
- **Consensus and optimisation interact.** The dynamic-tracking invariant is what lets an optimiser run on a graph; any mixing rule that breaks it (W-MSR trimming) breaks the optimiser.
- **Robustness is structural.** Whether a defence works depends on a property of the graph (robustness), exactly as the resilient-consensus theory states, and was observed directly (ring against ring2).
- **Capital as a learning signal.** The market learns which agent to trust without any agent evaluating another, but its main practical benefit here is protection from failure, not return.

---

## 8. Conclusion and future work

We built and evaluated a multi-agent trading system in which heterogeneous hypothesis agents stake capital in a market, are coordinated by prices in a joint ADMM optimisation, can do so without a central node, tolerate link failures, dropouts and a lying agent, and are monitored by formal safety specifications. The central claim that survives scrutiny is about mechanisms: the decentralised system reproduces the centralised one, and what it costs is communication, not return. The financial claim is weaker: carry is a real edge and the combined system earns a Sharpe ratio of about 1.4 to 1.5 at its risk limit, but after correcting for the number of variants tried the development data alone cannot establish it. We report the failed gates as failed.

**Future work.**
1. Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged.
2. Re-argue the hold supervisor's limit (the residuals of an attack and of slow honest convergence differ by about 300 times) and lengthen the volatility-price search for fast bar sizes.
3. Add a second, alt-coin-market risk factor to close the residual risk-model gap.
4. Test further established hypotheses one at a time, each with a card and rules written first (low volatility, a machine-learning trend model, carry variants using open interest or high and low prices).
5. Deployment-oriented decentralisation: pre-agreed step sizes, a max-consensus stopping test, flooded isolation, and a communication model with delays.

---

## References

(Prepared from memory of the primary sources; verify details before submission.)
- Boyd, S., Parikh, N., Chu, E., Peleato, B., Eckstein, J. (2011). Distributed optimization and statistical learning via the alternating direction method of multipliers. *Foundations and Trends in Machine Learning* 3(1).
- Olfati-Saber, R., Murray, R. M. (2004). Consensus problems in networks of agents with switching topology and time-delays. *IEEE Transactions on Automatic Control* 49(9).
- Xiao, L., Boyd, S., Lall, S. (2005). A scheme for robust distributed sensor fusion based on average consensus. *IPSN* (Metropolis weights).
- Zhu, M., Martínez, S. (2010). Discrete-time dynamic average consensus. *Automatica* 46(2).
- LeBlanc, H. J., Zhang, H., Koutsoukos, X., Sundaram, S. (2013). Resilient asymptotic consensus in robust networks. *IEEE Journal on Selected Areas in Communications* 31(4).
- Kelly, J. L. (1956). A new interpretation of information rate. *Bell System Technical Journal* 35(4).
- Beygelzimer, A., Langford, J., Pennock, D. (2012). Learning performance of prediction markets with Kelly bettors. *AAMAS* (arXiv:1201.6655).
- Maler, O., Nickovic, D. (2004). Monitoring temporal properties of continuous signals. *FORMATS*; Donzé, A., Maler, O. (2010). Robust satisfaction of temporal logic over real-valued signals. *FORMATS*.
- Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management* 15(3).
- Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
- Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). Carry. *Journal of Financial Economics* 127(2); He, S., Manela, A., Ross, O., von Wachter, V. (2022). Fundamentals of perpetual futures, arXiv:2212.06888.
- Moskowitz, T., Ooi, Y. H., Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics* 104(2).
- Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of Finance* 45(3).
- Course lecture notes: Consensus Theory; ADMM; Distributed Learning; Resilient Consensus; Temporal Logics (AI3403).

## Appendix A. Glossary
*Agent*: an autonomous trading hypothesis with its own belief, capital and positions. *Belief*: the expected net return per coin over one holding period. *Cell*: an (agent, coin) pair managed jointly. *Hub*: the central node of the centralised optimiser. *Gossip round*: one exchange of values between neighbours. *Mixing rate*: $|\lambda_2(W)|$ of the mixing matrix; smaller is faster. *Sharpe ratio*: annualised return divided by annualised volatility. *Net*: after fees, price impact and funding. *Alpha*: the part of a return not explained by a benchmark. *Information coefficient (IC)*: rank correlation between a score and the next return. *Kelly fraction*: share of the optimal bet size actually used (here one half). *Drawdown*: fall from the previous peak. *Ex-ante volatility*: volatility predicted by the risk model before trading. *Pre-registered gate*: a pass/fail rule written and committed before the runs it judges. *Deflated Sharpe*: the probability that a Sharpe of this size is real after allowing for the number of variants tried. *Sealed holdout*: data reserved for one final look.

## Appendix B. Where the evidence is
The experiment write-ups (numbered 011 to 023) and decision records (0032 to 0045) in the project repository give, for each result above, the exact command, the pre-registered rule and the committed result tables. Section 6.1: experiment 012. Section 6.2: 013 to 018. Section 6.3: 015 and 018. Section 6.4: 019. Section 6.5: 020. Section 6.6: 021. Section 6.7: 022. Section 6.8: 023.
