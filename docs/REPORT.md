# Resilient Decentralised Portfolio Consensus

*A multi-agent system for crypto perpetual futures: design, analysis and empirical evaluation*

AI3403 Multi-Agent Systems, project report. Empirical evidence is drawn from the development period April 2020 to November 2025; the final twelve months of data were sealed before the study began and have not been examined. The system has not been run live.

## Abstract

**Background.** A portfolio managed by several analysts is a multi-agent system: agents hold different beliefs, share capital, risk limits and trading costs, and must keep working when a participant fails or misbehaves. The usual implementation, a single optimiser that receives every forecast, is a single point of failure, hides disagreement between beliefs, and cannot be analysed with the tools of distributed computation.

**Method.** We design and evaluate a two-level multi-agent system for Binance USD-M perpetual futures. At the first level, agents are documented trading hypotheses (funding carry, time-series momentum, short-term reversal) that stake capital on their own beliefs in a Kelly-bet market, so that wealth follows each agent's results. At the second level, all stakes are converted into one portfolio by a convex optimisation solved with the alternating direction method of multipliers (ADMM), in which transaction costs on the net trade, margin, gross exposure, market-beta exposure and a volatility limit enter as prices. We replace the central node of this optimisation by dynamic average consensus over a communication graph, prove that this preserves the sum of the agents' positions exactly, and add link failures, agent dropout and a detect-and-isolate defence built from the W-MSR test. A signal-temporal-logic (STL) monitor with two supervisors (de-risking and hold) provides formal safety. Every mechanism is validated on simulated markets and evaluated against the centralised optimiser on five and a half years of real data under pre-registered pass or fail rules, with a correction for multiple testing.

**Results.** The decentralised optimiser reproduces the centralised portfolio to within 0.002 Sharpe on every network topology, under 30% random link failures, with the largest agent offline for four months, and with a consistent liar isolated. Network shape determines the communication cost and not the outcome; the mixing rate of the graph predicts iterations at eight and sixteen agents but not, against our pre-registered threshold, at four. W-MSR trimming cannot replace averaging inside the optimiser because it destroys the sum invariant, but its test detects a consistent liar on a sufficiently robust graph. The capital market equals a fixed-weight mix when all agents are good, and outperforms it by about 0.9 Sharpe when one agent is bad. The STL monitor identifies the November 2022 collapse as the most severe stress window, and de-risking shortens the worst drawdown at a Sharpe cost of 0.02 to 0.20. The main system earns a net Sharpe ratio of about 1.4 to 1.5 at a 20% volatility limit, but its deflated Sharpe ratio, corrected for the 45 strategy variants tried, is about 0.1 against a threshold of 0.95.

**Conclusion.** The mechanisms are verified against a centralised reference; the return claim is not established on the development data alone. Pre-registered gates that failed are reported as failures.

## 1. Introduction

### 1.1 Motivation

Portfolio management has the structure of a multi-agent problem. Analysts, each with a distinct hypothesis about what drives returns, draw on a common pool of capital, operate under one risk budget and trade in one market that charges them for impact. The system as a whole has to remain correct when individual participants are wrong, offline or dishonest. The conventional design collects all forecasts at one node and solves a single optimisation problem. Three properties of that design motivate a multi-agent treatment. First, the central node is a single point of failure. Second, forecasts are merged before their disagreement can be used, although disagreement is the reason for having several analysts. Third, the design offers no handle on questions that distributed computation studies directly: how fast agents agree, how much communication agreement costs, and how agreement degrades under faults.

### 1.2 Problem statement

We seek a system of agents that jointly trade a portfolio of cryptocurrency perpetual futures such that (i) agents with heterogeneous beliefs coordinate through local exchanges only and attain the same portfolio as a centralised optimiser; (ii) transaction cost, shared limits and capital allocation are handled by prices on which the agents agree; (iii) the system remains correct under link failures, agent dropout and false messages; (iv) formal safety requirements are monitored and, when necessary, enforced; and (v) performance and risk are assessed against a centralised benchmark with correction for the number of variants examined.

### 1.3 Research questions and hypotheses

| | Research question | Hypothesis tested |
|---|---|---|
| RQ1 | Does a neighbour-only optimiser reproduce the centralised portfolio on real data? | H1: the portfolios coincide up to solver tolerance, for every connected graph |
| RQ2 | How do topology and communication budget affect convergence and the result? | H2: iterations to convergence increase with the mixing rate $\lvert\lambda_2\rvert$ of the graph; the result does not depend on topology |
| RQ3 | Does the decentralised consensus remain correct under link failures, dropout and a lying agent, and does W-MSR protect it? | H3: failures that preserve a doubly stochastic mixing are absorbed; a consistent liar is isolated on a robust graph |
| RQ4 | Does an STL monitor with supervisors keep the system within its specifications in stress periods, and at what cost? | H4: de-risking reduces drawdown breaches; a hold rule prevents trading on corrupted solutions |
| RQ5 | What do the agents and the capital market add in money and risk, and does the result survive correction for multiple testing? | H5: the market is at least as good as a fixed mix and protects against a bad agent; H6: the main system's deflated Sharpe ratio is at least 0.95 |

### 1.4 Contributions

1. A two-level architecture in which a capital-staked market of hypothesis agents sits above a joint ADMM over (agent, coin) cells; shared limits and the cost of the net trade are prices (Sections 5.1 to 5.4).
2. A neighbour-only version of this optimisation, with a proof that it preserves the sum of positions, and a quantitative study of convergence against graph mixing rate (Sections 5.5, 11, 12).
3. A resilience analysis with a negative result, that W-MSR trimming is incompatible with the optimiser, and a positive one, that the W-MSR test works as a detector on robust graphs (Sections 5.6, 13).
4. An STL safety monitor with two supervisors whose limits are derived from a written risk mandate (Sections 5.7, 14).
5. A pre-registered, multiple-testing-aware evaluation, in which failed gates and revisions of earlier results are reported (Sections 6, 10, 15).

### 1.5 Structure and conventions

Section 2 reviews the background. Section 3 reports the preliminary study that motivated the design. Section 4 formulates the problem and Section 5 gives the methods. Section 6 describes the experimental methodology. Sections 7 to 15 report nine studies, each of which states its hypotheses, design, results, analysis and implications, and closes by stating the question it leaves open. Section 16 discusses the evidence as a whole and Section 17 concludes. Returns are net of fees, market impact and funding throughout; intervals are 90% moving-block bootstrap intervals; "daily", "four-hourly" and "hourly" refer to the bar size at which the system observes the market and rebalances.

## 2. Background and related work

**2.1 Consensus and resilient consensus.** In average consensus, agents on a connected undirected graph repeatedly replace their value by a weighted average of their neighbours' values; with a doubly stochastic weight matrix $W$ every agent converges to the average of the initial values, at a rate governed by the second-largest eigenvalue modulus $\lvert\lambda_2(W)\rvert$ [2]. Metropolis weights give a doubly stochastic $W$ from the graph alone [3]. When the quantity to be averaged changes over time, dynamic average consensus adds each agent's own change before mixing, so that the sum of the estimates tracks the sum of the true values [4]. Resilient consensus protocols such as W-MSR discard, coordinate by coordinate, up to $F$ neighbour values above and $F$ below an agent's own before averaging; if at most $F$ agents are malicious and the graph is sufficiently robust, honest agents agree inside the range of the honest initial values [5]. Robustness is a property of the graph beyond connectivity.

**2.2 Distributed optimisation.** ADMM solves convex problems with separable structure by alternating local minimisations with a coordination step and a price update, and its dual variables are prices of the coupling constraints [1]. Variants run it over networks without a central node, through consensus on the dual variable [6] or on the shared variable. A recurring difficulty is that robustness mechanisms designed for consensus on values do not obviously carry over to optimisation, where the quantity that must be preserved is a sum.

**2.3 Markets as learning mechanisms.** A Kelly bettor stakes the fraction of wealth that maximises expected log growth [7]. In a market of Kelly bettors, wealth moves according to Bayes' rule and the market's aggregate belief is a wealth-weighted average [8]; evolutionary models of asset markets reach similar conclusions about which rules survive [9]. Such results concern idealised betting markets. Their transfer to leveraged positions in correlated assets with transaction costs is not guaranteed and is examined empirically here.

**2.4 Temporal-logic monitoring.** Signal temporal logic specifies properties of real-valued signals, and its quantitative semantics yields a robustness value, the signed distance from violation [10, 11]. Robustness supports both monitoring (how close was the system to violating a requirement?) and supervision (act when the margin shrinks).

**2.5 Quantitative portfolio construction.** Expected returns can be written as the product of an information coefficient, a volatility and a standardised score [12]. Perpetual futures pay funding between longs and shorts, so a perpetual's expected return decomposes into carry and expected price change [13, 14]. Time-series momentum [15] and short-term reversal [16] are established effects, with replicated evidence in crypto assets mainly for the former [17]. Transaction cost models with a square-root impact term are standard for portfolio implementation [18].

**2.6 Multiple testing in backtests.** The best of many backtests overstates the expected Sharpe ratio of a strategy. The deflated Sharpe ratio corrects the observed value for the number of trials, the dispersion of their results and the non-normality of returns [19]; related work gives multiple-testing thresholds for factor discovery [20].

## 3. Preliminary study and design rationale

Two earlier systems were built and evaluated before the design reported here. The findings fix the requirements that the design must meet.

### 3.1 The preliminary systems

*S1: a trust-weighted consensus of forecasting agents.* Six simple forecasting agents (momentum, mean reversion, a shrinkage mean, a first-order autoregression, an exponentially weighted trend, a low-volatility tilt), each proposing a long-short portfolio $w_i=\mu_i/\sum_a\lvert\mu_{ia}\rvert$. Each agent's trust is the forecast probability that it makes money over the next holding period, $s_i=\Phi\big(m_i\sqrt H/\mathrm{sd}_i\big)$ with $m_i$ and $\mathrm{sd}_i$ the exponentially weighted mean and standard deviation of its stand-alone returns. Agents run $K=10$ rounds of W-MSR consensus with weights $W_{ij}\propto a_{ij}s_j$ and pinning to their own view; capital moves between agents through $c\leftarrow(1-\eta)c+\eta W^\top c$, which conserves total capital; the system trades the sum of the agents' positions and pays costs on the net change only. A compromised agent (all capital in one random asset, ignoring others) was part of the model from the start.

*S2: an absolute-return engine.* Four cross-sectional agents (momentum, residual reversal, funding carry, size) and a Bitcoin-timing agent, each producing a rank-Gaussian, dollar- and beta-neutral, volatility-targeted book; five ways of combining books (equal weight, inverse volatility, an online-learning combiner, risk budgeting, information-coefficient-calibrated view fusion); a fee-plus-square-root-impact cost model with a liquidity floor; and a decentralised ADMM combiner whose local objective contained the true trading cost. The evaluation protocol of S2 introduced the research discipline used throughout this report: a sealed final-year holdout, an append-only log of every variant evaluated, and the deflated Sharpe ratio.

*A temporal-logic shield* was added to S1: STL specifications for drawdown, volatility, recovery and concentration, with robustness normalised by each limit, and a supervisor that scaled the portfolio towards cash when a specification was about to be violated. Limits were derived from a written risk mandate and not from performance.

### 3.2 Findings

**F1. One idea earned money after costs.** In S2 on the full universe, funding carry had a net Sharpe ratio of 1.03, 0.99 and 0.88 (daily, four-hourly, hourly), Bitcoin timing 0.57, 0.46 and 0.80, and the other agents were negative:

| Net Sharpe | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Funding carry | 1.03 | 0.99 | 0.88 |
| Bitcoin timing | 0.57 | 0.46 | 0.80 |
| Cross-sectional momentum | −0.42 | −0.23 | −0.15 |
| Residual reversal | −0.68 | −1.11 | −1.24 |
| Size and liquidity | −0.14 | −0.22 | −0.32 |
| Equal-weight combiner | 0.22 | −0.09 | −0.09 |
| Inverse-volatility combiner | 0.27 | −0.04 | 0.18 |

The rank information coefficient of residual reversal was positive (0.025, 0.039, 0.049) while its net Sharpe was negative: a signal can be real and not tradable after costs. The coefficient of the size agent was significantly negative on every bar size ($t\approx-2.1$ to $-2.3$) and that of cross-sectional momentum was about zero. After counting every variant, no row had a significant deflated Sharpe ratio.

**F2. Combiners could not create information.** No combiner beat the inverse-volatility average, and every combiner was worse than carry alone, because three of the four agents carried no net edge. Diversification multiplies information; it does not create it.

**F3. The coordination layer added little over a central solve.** The consensus system did not beat the naive average of its own agents (Sharpe 0.81 against 0.90 on the equity test universe, with higher turnover); ADMM consensus with ten iterations already approached its one-node optimum (Sharpe 0.33 against 0.27, turnover 8.8 against 8.9); and putting the true trading cost into the decentralised combiner's objective did not lower cost drag. The one clear multi-agent result was resilience: with one compromised agent, plain consensus lost 43% of its Sharpe (0.81 to 0.46) whereas W-MSR with $F=1$ recovered most of it (0.74), and the protection came from trimming portfolios, not from capital flow.

**F4. Safety placed after the optimiser re-trades the book.** The shield reduced violations by half or more at almost no Sharpe cost on equities, and daily checks reduced the worst volatility breach by two thirds. On crypto perpetuals S1 ran at 57% to 80% volatility with no edge over Bitcoin (Sharpe $-0.03$, 0.25, 0.61 against about 1.0), and the shield brought volatility to 20% to 26% and halved the maximum drawdown. Two lessons followed: limits must be internally consistent (a 40% volatility limit with a 15% drawdown limit left the drawdown specification violated on about 60% of bars), and scaling a finished, cost-optimised portfolio re-trades the whole book. Allocating the shield's cut by risk contribution instead of uniformly worsened the outcome when an attacker was present, because risk contribution measures how much variance would fall if an agent were cut, not which agent is misbehaving.

**F5. Calibration and costs dominate.** A signal's usefulness after costs was decided by turnover and impact, not by the signal's information coefficient alone.

### 3.3 Design requirements

| Requirement | Source | Consequence for the design |
|---|---|---|
| R1. Agents must embody distinct, documented hypotheses with explicit expected edge | F1, F2 | Hypothesis agents with a written card (Section 5.1) |
| R2. Relative capital between agents must follow their results, with a defence against over-confident agents | F3 | Kelly-staked capital market with a floor and calibration check (Section 5.2) |
| R3. Costs and shared limits must be inside the optimisation, and the multi-agent structure must do something a central solve does not | F3, F4, F5 | Joint convex problem over (agent, coin) cells with cost on the net trade and priced limits (Section 5.3) |
| R4. The optimiser must run without a central node and degrade gracefully | proposal | Decentralised ADMM and a resilience study (Sections 5.5, 5.6) |
| R5. Safety must be formal, monitored over time, and act through the optimiser | F4 | STL monitor and supervisors acting through the volatility price (Section 5.7) |
| R6. Conclusions must be robust to the number of variants tried | F1 | Sealed holdout, trial log, deflated Sharpe, pre-registration (Section 6) |

W-MSR consensus on beliefs between agents was removed from the core design: a trimmed mean or a belief-magnitude check gives comparable protection with less machinery, and Section 13 revisits W-MSR in the optimiser, where its role turns out to be different.

## 4. Problem formulation

### 4.1 Market and data

The market is Binance USD-M perpetual futures: contracts on coins that never expire. A long position pays, and a short receives, a funding payment (every eight hours, occasionally at shorter intervals when the funding cap binds) that anchors the contract to the spot price. Binance computes the funding of an interval as
$$F=P+\operatorname{clamp}\!\big(I-P,\ \pm c\big),\qquad I=0.01\%\ \text{per 8 hours},\ \ c=0.05\%,$$
where $P$ is the time-weighted average of the premium index over the interval. On Bitcoin (89 events, one month of one-minute premium data) the time-weighted version reproduced actual funding with correlation 0.995 and mean absolute error $9\times10^{-7}$, about 1% of the typical level; an equal-weighted average was less accurate (0.936). The system uses open, high, low and close prices, volume, taker volume, funding events, the premium index, spot prices and open interest, in bars of one day, four hours and one hour. Funding is always summed per bar from event times.

**Universe.** Point-in-time and free of survivorship bias. A coin enters when its rank by the 90-day median daily dollar volume, computed strictly before the day, is within the top 50, stays while within the top 75, and the ranking is refreshed every 30 days. Delisted coins are included. In total 243 coins appear, with about 63 members on a typical day. A coin is tradable at a rebalance only if its trailing median daily dollar volume is at least one million dollars and its history window is complete. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded. Open interest and long-short data exist only from late 2020 (Bitcoin) or late 2021 (most coins) and have gaps; liquidation data are not public.

**Rebalancing.** The system rebalances every 14 days on daily bars, every 5 days on four-hourly bars and every 48 hours on hourly bars. All quantities for a rebalance at time $t$ use only information strictly before $t$; this is a tested invariant.

### 4.2 Costs

Trading $d_a$ in coin $a$ costs
$$C_a(d_a)=c_f\,\lvert d_a\rvert+\kappa_a\,\lvert d_a\rvert^{3/2},\qquad\kappa_a=\frac{k\,\sigma_a}{\sqrt{\mathrm{ADV}_a}},$$
with a taker fee $c_f=5$ basis points, daily volatility $\sigma_a$, average daily dollar volume $\mathrm{ADV}_a$ and impact coefficient $k=1$ (an assumption). The second term is square-root impact: slippage per dollar is $k\sigma_a\sqrt{\lvert d_a\rvert/\mathrm{ADV}_a}$. The total $C(d)=\sum_aC_a(d_a)$ is convex. Assets under management are one million dollars, and a position may be at most 5% of a coin's daily volume.

### 4.3 Notation

| Symbol | Meaning |
|---|---|
| $i=1,\dots,M$; $a=1,\dots,N$ | agents; tradable coins |
| $\mu_i\in\mathbb{R}^N$ | belief of agent $i$: expected net return on a unit position over one holding period |
| $x_i\in\mathbb{R}^N$ | position of agent $i$ in units of initial equity; $X=\sum_ix_i$ is the net position; $h$ the net position currently held |
| $\Sigma=\operatorname{diag}(d)+F\beta\beta^\top$ | return covariance over one holding period: idiosyncratic variances $d$, one market factor with variance $F$ and betas $\beta$ |
| $W_i$, $E=\sum_iW_i$ | wealth of agent $i$ and total equity |
| $f=0.5$, $\gamma_i=1/(fW_i)$ | Kelly fraction and the resulting risk aversion of agent $i$ |
| $C(\cdot)$ | trading cost, charged on the net trade $X-h$ |
| $\lambda\ge0$ | price on system variance |
| $G=(V,\mathcal{E})$, $W$ | communication graph over the agents and its doubly stochastic mixing matrix |
| $r$ | gossip rounds per iteration |
| $\rho_\varphi(t)$ | STL robustness of specification $\varphi$ at time $t$ |

### 4.4 Objective

The criterion is the annualised net Sharpe ratio $\mathrm{SR}=\sqrt{P}\,\bar r/s_r$ against zero, where $P$ is the number of bars per year and $\bar r$ and $s_r$ are the mean and standard deviation of per-bar net returns. Mechanisms (decentralisation, resilience, safety) are judged against the same agents solved by the centralised optimiser, or against the reference that is correct for the failure considered.

## 5. Methods

### 5.1 Hypothesis agents and beliefs

An agent is a trading hypothesis specified on a *card* written before any test: the claim, the mechanism, the allowed coin set $\mathcal{U}_i$, the predicted sign $s_i\in\{+1,-1\}$ and size $\mathrm{IC}_i$ of its edge, and a switch-off rule.

*Belief.* Let $z_{ia}$ be a standardised score of the hypothesis for coin $a$, with unit variance across coins, and $\mathrm{IC}_i$ the expected rank correlation between score and next return. If the score is the only information, the conditional mean return is $\mathrm{IC}_i\,\sigma_{H,a}\,z_{ia}$, where $\sigma_{H,a}$ is the volatility of the coin over one holding period (the fundamental law of active management). The belief is
$$\mu_{ia}=s_i\;\mathrm{IC}_i\;\sigma_{H,a}\;z_{ia}.$$
The size $\mathrm{IC}_i$ is fixed by the card; it is not estimated from recent results (Study 2 shows why). Evidence acts only through a *kill rule*. Let $\overline{\mathrm{IC}}_n$ and $s_n$ be the mean and standard deviation of the agent's realised per-period skill over $n$ periods and $t_n=\overline{\mathrm{IC}}_n/(s_n/\sqrt n)$. If $n\ge20$ and $s_it_n<-2$ the belief is set to zero; the agent never takes the opposite position. Relative stakes of agents are decided by wealth.

*The agents.*

| Agent | Score $z_{ia}$ | Coins | Neutral | $\mathrm{IC}_i$ |
|---|---|---|---|---|
| **Funding carry** | rank-Gaussian of $-\overline{\text{funding}}_{14\text{d}}(a)$ (long low funding, short high funding) | all tradable | yes | 0.02 |
| **Time-series momentum** | $\operatorname{clip}\!\big(\sum_{\tau\in30\text{d}}r_{a\tau}\big/(\operatorname{sd}(r_a)\sqrt{L}),-2,2\big)$ | Bitcoin, Ethereum | no (owns net exposure) | 0.05 (assumed) |
| **Residual reversal** | rank-Gaussian of $-\sum_{\tau\in7\text{d}}e_{a\tau}\big/(\operatorname{sd}(e_a)\sqrt n)$, $e_{a\tau}=r_{a\tau}-\hat\beta_ar_{\mathrm{BTC},\tau}$ | all tradable | yes | 0.02 |

The rank-Gaussian transform is $z_a=\Phi^{-1}\big((\operatorname{rank}_a-0.5)/N\big)$. The mechanism of carry is that funding is a transfer from the crowded side, so a perpetual's expected return is its carry plus its expected price change; momentum rests on slow diffusion of information, and reversal on temporary price pressure from demand for immediacy. For momentum, $\mathrm{IC}_i=0.05$ is an assumption, set by a mechanical check without profit: at 0.10 the agent's ex-ante Sharpe ratio at its own belief on daily bars was 1.17, more than a two-coin time-series strategy can be expected to deliver, while 0.05 gave about 0.6.

### 5.2 Level 1: the capital market

For one asset with expected return $\mu$ and variance $\sigma^2$, the log-growth of wealth when a fraction $f$ is invested is approximately $g(f)=f\mu-\tfrac12f^2\sigma^2$. It is maximised at $f^\star=\mu/\sigma^2$ and equals zero at $2f^\star$, so over-confident agents are penalised by the mathematics. We use half the Kelly size. Minimising $-\mu x+\tfrac\gamma2\sigma^2x^2$ gives $x=\mu/(\gamma\sigma^2)$, so a bet of $fW\mu/\sigma^2$ corresponds to risk aversion $\gamma=1/(fW)$.

The system trades the sum of the agents' positions. Each agent has an *account* that earns the profit and loss of its own positions less its allocated share of cost and funding, so the accounts sum exactly to the real result. Wealth compounds with the account return $r_i(t)$:
$$W_i(t+1)=\max\!\Big(W_i(t)\big(1+r_i(t)\big),\ \omega\textstyle\sum_jW_j(t)\Big),\qquad\omega=0.02.$$
The floor keeps a failed agent alive so the market can still reallocate; a loss beyond an agent's wealth is borne by the others. Beliefs are not averaged between agents: they act only through the wealth that backs them. Two protections against over-confidence are included. The system limits of Section 5.3 bound every agent's stake, and an agent-level *calibration check* scales an agent's Kelly fraction down when the slope of realised returns on its past beliefs falls below 0.5. Because a card-sized belief makes the slope estimate very noisy (a standard error above 1 over 3,000 observations), the check acts on the upper confidence bound of the slope (slope plus 1.645 standard errors), that is, only on demonstrable over-confidence. A *belief-sanity* check zeroes a belief that is not a finite number within a bound set by the volatility-standardised history of the agent's own beliefs.

### 5.3 Level 2: the joint portfolio problem

At each rebalance the system solves one convex problem over all positions:
$$\min_{x_1,\dots,x_M}\ \sum_{i=1}^M\Big[-\mu_i^\top x_i+\tfrac{\gamma_i}2\,x_i^\top\Sigma\,x_i\Big]+C\big(X-h\big)+\tfrac\lambda2\,X^\top\Sigma X\tag{P}$$
$$\text{subject to}\quad x_i\in\mathcal{X}_i\ \ (i=1,\dots,M),\qquad X=\sum_ix_i\in\mathcal{G}.$$
The agent sets $\mathcal{X}_i$ collect the constraints of one agent:

- allowed coins: $x_{ia}=0$ for $a\notin\mathcal{U}_i$;
- capacity: $\lvert x_{ia}\rvert\le u_a$, where $u_a$ is 5% of the coin's daily volume;
- margin: $\lVert x_i\rVert_1\le3W_i$;
- neutrality, for agents whose hypothesis is market-neutral: $\mathbf1^\top x_i=0$ and $\beta^\top x_i=0$.

The system set $\mathcal{G}$ collects the constraints of the whole system: a gross cap $\lVert X\rVert_1\le3E$ and a market-beta band $\lvert\beta^\top X\rvert\le0.25E$. A pair (agent, coin) is a *cell*.

*Cost on the net trade.* $C$ acts on $X-h$, not on each $x_i$: two agents trading opposite ways in the same coin cancel and pay only for the difference.

*Volatility limit as a price.* The last term of (P) prices system variance. After each solve the annual ex-ante volatility of the net position, $\hat\sigma=\sqrt{P\,X^\top\Sigma X/H}$ with $H$ bars per holding period, is compared with the 20% target. If it exceeds the target by more than 2%, $\lambda$ is raised and (P) is solved again, up to five times; if the volatility is more than 2% under the target and $\lambda>0$, it is lowered. The agent that adds risk then pays for it. In a test at equal total volatility this priced limit left the market-neutral agent 97% of its unconstrained position (0.073 against 0.075), where a uniform shrink of all positions left it 45% (0.034): a uniform rescale makes the agent that adds no variance subsidise the one that does.

*Prices.* (P) is convex, so it has multipliers. Those of the neutrality, beta, margin, gross, capacity and net-trade terms are prices of exposure, scarce capital, scarce gross exposure and trading. Each agent reacts to prices and never needs another agent's belief.

### 5.4 Solving (P) by sharing ADMM

Write $f_i(x_i)=-\mu_i^\top x_i+\tfrac{\gamma_i}2x_i^\top\Sigma x_i+\iota_{\mathcal{X}_i}(x_i)$ and $g(X)=C(X-h)+\tfrac\lambda2X^\top\Sigma X+\iota_{\mathcal{G}}(X)$, with $\iota$ the indicator function of a set. Then (P) is the sharing problem $\min\sum_if_i(x_i)+g(\sum_ix_i)$. With $\bar x=\frac1M\sum_ix_i$, penalty $\rho>0$ and scaled price $u$, ADMM iterates [1, Section 7.3]
$$x_i^{k+1}=\arg\min_{x_i}\ f_i(x_i)+\tfrac\rho2\big\lVert x_i-x_i^k+\bar x^k-z^k+u^k\big\rVert^2\qquad(\text{each agent, in parallel})$$
$$z^{k+1}=\arg\min_{z}\ g(Mz)+\tfrac{M\rho}2\big\lVert z-\bar x^{k+1}-u^k\big\rVert^2\qquad(\text{system step})$$
$$u^{k+1}=u^k+\bar x^{k+1}-z^{k+1}\qquad(\text{price update})$$
Because (P) is convex the iteration converges, and the scaled price $u$ is, up to the factor $\rho$, the price of the net position in each coin.

*The cost step.* The cost term has a closed-form proximal operator. For a coin with target trade $t$ (the point towards which the quadratic penalty pulls) the minimiser of $C_a(d)+\tfrac\rho2(d-t)^2$ is $d=0$ if $\lvert t\rvert\le c_f/\rho$, and otherwise $d=\operatorname{sign}(t)\,s^2$ with
$$s=\frac{-\tfrac32\kappa_a+\sqrt{\tfrac94\kappa_a^2-4\rho\,(c_f-\rho\lvert t\rvert)}}{2\rho},$$
the positive root of $\rho s^2+\tfrac32\kappa_as+(c_f-\rho\lvert t\rvert)=0$, obtained from the first-order condition with $s=\sqrt{\lvert d\rvert}$. The constrained agent step needs the multipliers of the margin, gross and beta constraints, found by nested bracketed one-dimensional root searches, and an exact projection onto an $\ell_1$-ball with box constraints. Termination uses primal and dual residuals relative to the size of the positions (tolerance $10^{-6}$). At this tolerance the net position is accurate to about $10^{-6}$ while the split of the net position between agents is accurate to about 9%, so per-agent accounts carry that noise and the system result does not. A one-node solver is kept as a reference for verification.

### 5.5 Removing the hub: decentralised ADMM

In Section 5.4 three quantities are global: the average position $\bar x$, the system step $z$ and the price $u$. In the decentralised version agent $i$ holds its own copies: an estimate $s_i$ of the group average, a system-step solution $z_i$ and a price $u_i$. System data (cost parameters, limits) are public. Let the graph be undirected with edge set $\mathcal{E}$ and let $W$ be its *Metropolis* mixing matrix,
$$W_{ij}=\frac1{1+\max(\deg i,\deg j)}\ \ \text{for }\{i,j\}\in\mathcal{E},\qquad W_{ii}=1-\sum_{j\ne i}W_{ij},$$
which is symmetric with rows summing to one, hence doubly stochastic. One iteration is:

> **Algorithm 1 (decentralised ADMM, one iteration).**
> 1. Each agent $i$ solves its local step against its own price $u_i$, giving $x_i^{\text{new}}$.
> 2. Tracking: $\;s\leftarrow W^{r}\big(s+x^{\text{new}}-x^{\text{old}}\big)$, mixing the stacked estimates over $r$ gossip rounds.
> 3. Each agent solves the system step from its own estimate $s_i$, giving $z_i$.
> 4. Price: $\;u\leftarrow W^{r}\big(u+s-z\big)$.

with $s_i=x_i^0$ at the start.

> **Proposition 1 (sum invariant).** For every iteration $k$, $\sum_is_i^k=\sum_ix_i^k$.
>
> *Proof.* Let $\mathbf1$ be the all-ones vector. Since $W$ is doubly stochastic, $\mathbf1^\top W^r=\mathbf1^\top$. Hence $\mathbf1^\top s^{k+1}=\mathbf1^\top(s^k+x^{k+1}-x^k)=\mathbf1^\top s^k+\mathbf1^\top x^{k+1}-\mathbf1^\top x^k$. With $s^0=x^0$ the claim follows by induction. $\square$

**Corollary 1.** If the iteration reaches a fixed point, then $x^{k+1}=x^k$; mixing drives every $s_i$ to the common value $\bar s=\frac1M\sum_is_i=\bar x$ (Proposition 1) and the prices agree for the same reason. The fixed point satisfies the optimality conditions of Section 5.4, so it is the optimum of (P). On the complete graph with exact mixing, Algorithm 1 coincides with the hub algorithm.

*Convergence and communication cost.* With no new input, one gossip round multiplies the disagreement $s-\mathbf1\bar s^\top$ by at most $\lvert\lambda_2(W)\rvert$, so the number of rounds needed to reduce it by a factor $\varepsilon$ is $\ln\varepsilon/\ln\lvert\lambda_2\rvert$. Messages per rebalance equal (iterations)$\times r\times2\lvert\mathcal{E}\rvert$. The stopping test requires, besides the usual residuals, agreement between the agents' estimates and between their prices: without this a run can stop while agents still disagree by about 10%. Over-relaxation, used in the hub version, oscillated under slow mixing and is switched off.

*Elements that remain central in the experiments.* The step sizes use the mean risk aversion, a number the agents could agree on before trading; the stopping test is evaluated by the simulator, where a deployment would run a max-consensus over the graph's diameter; and the decision to restart after an isolation (Section 5.6) is applied to all agents simultaneously, where a deployment would flood it over the graph.

### 5.6 Resilience

Three faults are considered.

*Link failures.* In each gossip round each edge is down independently with probability $q$. The weights are recomputed by the Metropolis rule on the edges that are up. The recomputed matrix is again symmetric with unit row sums, hence doubly stochastic, so Proposition 1 still holds and the optimum is still reached: failures cost iterations, not correctness.

*Agent dropout.* The agent's positions are closed and the others solve (P) without it, on the graph without its node. Proposition 1 applies to the smaller system.

*Misbehaving agent.* A liar $\ell$ sends values that differ from those its algorithm would send. In W-MSR each agent drops up to $F$ larger and $F$ smaller neighbour values and averages the rest. The resulting weight matrix depends on the data and is generally not doubly stochastic, so $\mathbf1^\top s$ is not preserved and Proposition 1 fails: used as the mixing rule inside the optimiser, W-MSR cannot be expected to preserve the optimum. We therefore use the W-MSR test as a *detector*. At iteration $k$ agent $i$ compares each neighbour's values $v_j$ (the estimate and the price) with its own. For coordinate $c$ let $e_{ijc}=1$ if $v_{jc}$ is the largest value above $v_{ic}$ or the smallest below it, that is, the value W-MSR would discard first, and let $\pi_{ij}=\frac1n\sum_ce_{ijc}$. Agent $i$ flags $j$ when $\pi_{ij}\ge0.9$ for both estimates and prices for 50 consecutive iterations. An agent flagged by more than half of its neighbours is *isolated* and the others restart without it; plain averaging is used otherwise, so with no attacker the solver is exactly Algorithm 1. The parameters (0.9, 50, majority) were fixed on development problems before the evaluation. A consistent offset puts a liar's value beyond the honest values in nearly every coordinate, which is what $\pi_{ij}$ measures; a liar whose values stay inside the honest range is not expected to be detected. For $F=1$, W-MSR requires the graph to be $(2,2)$-robust. A ring is connected but not $(2,2)$-robust, whereas a ring in which each agent is linked to its two nearest neighbours on each side (here "ring2") is sparse and robust.

### 5.7 Safety: STL monitor and supervisors

For a real-valued signal $y$ and a limit $c$, the predicate $y\ge c$ has robustness $\rho(t)=y(t)-c$: positive means satisfied by that margin, negative means violated by that much. The operators are $\rho(\mathbf G_{[a,b]}\varphi,t)=\min_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (always) and $\rho(\mathbf F_{[a,b]}\varphi,t)=\max_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (eventually). Let $\hat\sigma_t$ be the ex-ante volatility at a rebalance, $\sigma^\ast_t$ the volatility target in force, $\mathrm{DD}_t=E_t/\max_{s\in[t-365\mathrm d,t]}E_s-1$ the drawdown, and $\sigma^{\mathrm{real}}_t$ the realised 30-day volatility. The specifications are:

| Spec | Statement | Limit and mandate |
|---|---|---|
| $\varphi_{\mathrm{vol}}$ | $\mathbf G\,(\hat\sigma_t\le1.05\,\sigma^\ast_t)$ | 5% tolerance; the priced limit's own search accepts 2% |
| $\varphi_{\mathrm{dd}}$ | $\mathbf G\,(\mathrm{DD}_t\ge-0.15)$ | 15% over 365 days, about half of what an equity market lost in its worst stretch within a year |
| $\varphi_{\mathrm{rvol}}$ | $\mathbf G\big(\sigma^{\mathrm{real}}_t>0.4\Rightarrow\mathbf F_{[0,14\mathrm d]}\,\sigma^{\mathrm{real}}_t\le0.4\big)$ | 40% and 14 days, twice the 20% target |
| $\varphi_{\mathrm{solve}}$ | $\mathbf G\,(\text{relative residual}\le10^{-3})$ | a portfolio off by 0.1% of its size is immaterial against one rebalance's fee; clean central solves reach $10^{-6}$ |

All limits come from a written risk mandate fixed before any run and are not chosen by comparing returns. The *monitor* records the robustness of every specification for every bar and summarises it over three stress windows (May to July 2021, the May 2022 Luna collapse, and November 2022 to January 2023, the FTX collapse). Two *supervisors* act on it and are off by default.

*Derisk.* Let $m_t=(\mathrm{DD}_t+0.15)/0.15\in[0,1]$ be the share of the drawdown budget remaining. The volatility target is multiplied by
$$\kappa(m_t)=\begin{cases}1&m_t\ge0.5,\\0.2+1.6\,m_t&0\le m_t<0.5,\end{cases}$$
so de-risking starts with half the budget left and never goes below 20% of the target. It acts through the volatility price of Section 5.3, so (P) is re-solved with the tighter target and the costs included; it is not a post-hoc rescale of a finished portfolio.

*Hold.* If the solve is unsafe (it did not converge and its relative residual exceeds $10^{-3}$) the system trades nothing and keeps its current positions, a fail-safe against a corrupted solution.

## 6. Experimental methodology

**6.1 Data and period.** The development period runs from April 2020 to November 2025, with all agents using a warm-up of ninety days before trading. The last twelve months are sealed: they are reported only once, after the design is frozen. No tuning, and no statistic that includes them, is allowed before then.

**6.2 Reference systems.** Every decentralised, resilient or supervised variant is compared with the centralised optimiser with the same agents, data, costs and limits, or with the reference that is correct for the failure considered (for example, the centralised system without an agent that is offline). Multi-agent mechanisms are also compared with fixed-weight blends of the agents' stand-alone returns.

**6.3 Pre-registration.** For each study the pass or fail rules, with thresholds, and where stated the expected outcome, were written before the runs. Amendments carry their date and say whether any result had been seen. Where a rule was changed after a result, we say so. Rejected variants are retained in the record and in the trial count.

**6.4 Statistics.** Intervals are 90% moving-block bootstrap intervals: blocks of 7 days are resampled with replacement ($B=500$ draws) and the 5th and 95th percentiles of the statistic are reported. Comparisons between strategies use the same resampled blocks for both (a paired difference). To separate skill from market exposure we regress a strategy's return on Bitcoin's, $r_t=\alpha+\beta r^{\mathrm{BTC}}_t+\epsilon_t$, and also on Bitcoin and the carry agent's return, and report the annualised $\alpha$ with a block-bootstrap interval. The skill of a score is its rank information coefficient (IC): the Spearman correlation between the score and the next return across coins, averaged over rebalances, with its $t$-statistic.

**6.5 Deflated Sharpe ratio.** Let $\widehat{\mathrm{SR}}$ be the per-period Sharpe ratio of the best strategy over $T$ periods with skewness $\hat\gamma_3$ and kurtosis $\hat\gamma_4$ (3 for a normal distribution), $V$ the variance of Sharpe ratios across the $N$ trials, and $\gamma_{\mathrm E}\approx0.5772$ Euler's constant. Then [19]
$$\mathrm{SR}_0=\sqrt V\Big[(1-\gamma_{\mathrm E})\,\Phi^{-1}\!\big(1-\tfrac1N\big)+\gamma_{\mathrm E}\,\Phi^{-1}\!\big(1-\tfrac1{Ne}\big)\Big],\qquad
\mathrm{DSR}=\Phi\!\left(\frac{(\widehat{\mathrm{SR}}-\mathrm{SR}_0)\sqrt{T-1}}{\sqrt{1-\hat\gamma_3\widehat{\mathrm{SR}}+\tfrac{\hat\gamma_4-1}4\widehat{\mathrm{SR}}^2}}\right).$$
$\mathrm{SR}_0$ is the Sharpe ratio that the best of $N$ strategies with no skill would show by chance, and $\mathrm{DSR}$ is the probability that the observed Sharpe ratio exceeds it. We require $\mathrm{DSR}\ge0.95$.

**6.6 Trial accounting.** Every variant evaluated is appended to a log. A strategy trial is one pair (strategy variant, bar size). Exact repeats count once. Engineering variants (consensus form, topology, resilience, safety) are counted separately, giving a more conservative total. The trial-Sharpe variance $V$ is that of the annualised Sharpe ratios of the strategy runs in Study 4, divided by the number of periods per year.

**6.7 Disclosure of revisions.** Two revisions affected earlier results and are reported where they occur. In Study 3 an agent's positions were found to violate its declared coin set and the constraint was enforced; both runs count as trials. In Study 4 the normalisation of the volatility limit was found to use initial and not current equity; every affected study was repeated, and only corrected results are reported in the later studies.

## 7. Study 1: Validation of the mechanisms on simulated markets

### 7.1 Objective

Section 5 introduces several mechanisms whose behaviour in real data would be hard to attribute: a convex solver with many couplings, a capital market, a model-averaging step, STL checks and an estimator for state-dependent skill. Before any of them is applied to market data, we test each on simulated markets in which the correct answer is known. The study asks whether every mechanism does what it was designed to do, and where it does not, which design constraints follow.

### 7.2 Design

*Level 2 (joint optimiser).* Random problems with 3 to 4 agents and 6 to 10 coins, five random seeds per configuration, with each coupling studied on its own and all together: cost on the net trade (fee and impact), capacity boxes, margin, gross cap, market-beta band, and combinations. Reference: a one-node general-purpose solver applied to the same problem.

*Level 1 (market).* A simulated market of 60 coins with a common factor, planted cross-sectional skill (the standard deviation of the true alpha is 0.5% per period, the idiosyncratic standard deviation 6%) and agents whose belief equals $\rho$ times the true alpha plus noise, so that $\rho$ is the agent's calibration. A skilled agent has $\rho=0.3$; a noise agent has $\rho=0$. The Kelly fraction is $f=0.5$. Horizons are derived analytically: if the expected log-growth difference between a skilled and a noise agent is $\Delta g$ per period, selection is expected after $T_{\mathrm{end}}=3/\Delta g$ periods (here $\Delta g=0.0188$, so $T_{\mathrm{end}}=160$). An *over-confident* agent has its belief multiplied by 4, giving an effective Kelly fraction of 2, at which the expected log-growth is zero.

*Other components.* Model averaging with members whose error variances differ by a factor of 4 or more; STL recovery and deadline operators checked against brute force; and a state-dependent skill estimator on planted regime-dependent skill (skill 0.3 in the "on" state and 0 in the "off" state, regimes of about 33 periods, a noisy observable state).

*Criteria fixed before implementation.* The criteria are listed with the results in Table 7.1. Each was written before the corresponding code.

### 7.3 Results

**Table 7.1.** Pass criteria and outcomes.

| Mechanism | Criterion | Outcome |
|---|---|---|
| Joint optimiser | maximum $\lvert X_{\mathrm{ADMM}}-X_{\mathrm{ref}}\rvert\le10^{-3}$ of a typical position and relative objective gap $\le10^{-5}$ on 7 coupling configurations $\times$ 5 seeds | pass; typical error $10^{-7}$; the hardest case (gross cap and beta band binding together) needs about 1,100 iterations, single couplings 20 to 250 |
| Prices | non-negative; zero when slack; margin and gross prices equal the finite-difference marginal value of the limit within 5% | pass |
| Netting | two agents with opposite views on a coin pay the cost of the net trade, strictly below the sum of separate costs | pass |
| Capital follows its price | a tighter margin raises the best coin's share of an agent's capital | pass |
| Market selects skill | skilled agents' combined wealth share exceeds 0.5 at $T_{\mathrm{end}}$ in at least 90% of 20 seeds | pass at 160 periods |
| Market drops decayed skill | an agent whose skill vanishes after $T_{\mathrm{end}}$ has a lower share at $2T_{\mathrm{end}}$ | pass |
| Accounting | account profits, cell positions, wealth and costs add up to the real values to $10^{-9}$; the floor holds | pass |
| Over-confidence is penalised | the calibrated agent ends with more wealth than the over-confident agent in at least 90% of seeds | pass without a floor (18 of 20); **fail** with the 2% floor (6 of 20) |
| Model averaging | error-weighted beats equal weights when member errors differ 4 times, and is no worse when equal | pass: correlation with the true alpha 0.849 against 0.814 (+4.3%); 0.854 against 0.858 ($-0.4\%$) |
| Guard against a corrupt member | fused belief changes by less than 10% | restated (see below); with the guard on the fused belief equals the honest average to $10^{-12}$ |
| STL operators | recovery and deadline specifications match brute force; corrupt beliefs (NaN, infinite, 100 times) are zeroed and honest ones untouched | pass |
| State-dependent skill | on planted regime skill the timed agent beats its untimed twin with a 90% interval above 0; with no dependence it is not worse by more than 10% | pass: +0.0020 per period (interval 0.0009 to 0.0033; wins in 14 of 20 seeds); $-5.9\%$ with no dependence |

*Restated criteria.* One criterion (capital follows its price) was reformulated before any result was read, because the first wording became ill-posed when a position reached exactly zero. Two were reformulated after an unsuccessful run (over-confidence with a floor; the corrupt-member guard), each with its diagnosis recorded: for the guard, no filter can satisfy a 10% bound when merely dropping one of eight honest members changes the fused belief by about 13%, so the criterion was restated in terms of exactness against the honest average.

### 7.4 Analysis

**The wealth floor blunts selection.** To diagnose the failed criterion, single-agent runs of 3,000 periods were examined. The calibrated agent's realised log-growth was 0.0141 per period, equal to the theoretical value. The over-confident agent's was $-0.0258$: the continuous-time approximation gives zero at an effective fraction of 2, but with discrete compounding the growth is negative, and a ruinous period (a return of $-169\%$) occurred in every run. Selection therefore works. What blunts it is the floor: it re-seeds a ruined agent with 2% of total wealth and so acts as a rebalancing rule, which leaves the over-confident agent with a persistent share of 14% to 41% and makes the ordering of final wealth close to a coin flip. A limited-liability rule (a loss beyond an agent's wealth is borne by the others) was added to the market after this diagnosis, because wealth had previously become negative.

**An unlimited over-confident agent can ruin the system.** At an effective Kelly fraction of 2 the per-period return has a standard deviation of about 0.39, and in 5 of 20 seeds with a floor, and 2 of 20 without, the entire system was wiped out. Wealth dynamics select too slowly to prevent this. The defences are the priced margin and gross limits inside the joint problem (tested in Level 2) and the agent calibration check of Section 5.2. With the calibration check in its first form (acting on the point estimate of the slope) ruin disappeared entirely in the simulation, but it does not restore selection: the guarded over-confident agent bets about as much as the calibrated one, so their wealth is similar (10 of 20 seeds each way). The check is a risk control and not a selector. Applied to real data it fired spuriously, because a card-sized belief makes the slope's standard error exceed 1; the version in Section 5.2 acts on the upper confidence bound, and in simulation reduces ruin after period 150 from 3 of 40 runs to 1 of 40. Early ruin, before there is evidence, remains and is the job of the margin and gross limits.

**Numerical finding.** The net-position step of the optimiser has a closed form (Section 5.4); replacing a bisection of the one-dimensional proximal problem by it made binding system limits 20 to 40 times faster with identical results.

### 7.5 Implications

The mechanisms behave as designed in the controlled setting, with two constraints on the design: margin and gross limits are always active, the Kelly fraction does not exceed 0.5, and the wealth floor is a liveness device whose cost is a weaker selection of agents. Five years of real data cannot test the speed of selection, which is why it was tested here. The open question is whether the full stack reproduces a known result on real data.

## 8. Study 2: A single-agent baseline: calibration of beliefs and the limits of forecasting funding

### 8.1 Objective and hypotheses

With one agent the market is trivial, so this study tests the engine (beliefs, joint optimiser with cost on the net trade, accounts) against a known benchmark. The agent is funding carry, the one idea with a net edge in the preliminary study (net Sharpe 1.03, 0.99, 0.88). **Hypothesis:** the engine reproduces a net Sharpe ratio of about 1.0 on every bar size, with a market component near zero and costs near 2% a year. The study then asks whether a better *forecast* of funding improves the carry belief.

### 8.2 Design

Universe of 243 coins, development period April 2020 to November 2025, one agent (carry, Section 5.1), all settings fixed and not tuned: Kelly fraction 0.5, margin 3, gross cap 3, capacity 5% of volume, volatility limit 20%, fee 5 basis points, impact coefficient 1, assets of one million dollars, minimum liquidity of one million dollars of daily volume. The preliminary carry book (Sharpe 1.03 / 0.99 / 0.88) is the regression target. Several belief designs were tried in sequence; each is a trial and is recorded as such.

### 8.3 Development sequence: how the belief should be calibrated

Table 8.1 gives the development sequence on daily bars (values marked † were obtained before the volatility-limit revision of Study 4 and are used only for within-study comparison).

**Table 8.1.** Calibration of the carry belief (daily net Sharpe unless stated).

| Belief design | Sharpe | Volatility | Max drawdown | Comment |
|---|---|---|---|---|
| (a) IC estimated from a trailing window and shrunk towards zero; no volatility limit | 0.48† | 37% | −63% | sign of the belief flips |
| (b) as (a) with a sign clip and the volatility limit | 1.24† | | | evidence cannot move the belief |
| (c) **card-fixed size, evidence only through the kill rule** | 1.27† | 15.1% | −16.6% | final design |

*Why design (a) fails.* Carry's per-period rank IC has mean 0.035 and a hit rate of only 53%. From its $t$-statistic ($t=2.2$ over 141 periods) the standard deviation of the per-period IC is about $0.035\sqrt{141}/2.2\approx0.19$. An exponentially weighted mean with at most about 18 effective observations then has a standard error of about $0.19/\sqrt{18}\approx0.045$, larger than the signal. A belief proportional to such an estimate changes sign about half the time: it injects noise of the same order as the signal into the stake, and the trading cost of following it falls on the book. The first run also lacked a volatility limit (half-Kelly on about 60 coins implies roughly 50% annual volatility).

*Why design (b) is not a solution.* It shrank the estimate towards the card's prior with 50 pseudo-observations, while the exponentially weighted estimate carries at most about 18 effective observations, so the prior always held at least 74% of the posterior; 300 periods of IC $-0.04$ still gave a positive belief. The improvement from (a) to (b) came from the sign clip alone, and the volatility re-solve rescaled the book and masked the lack of a scale. This was found by inspection of the design and is the reason for (c).

*Design (c).* The belief is $\mu_{ia}=s_i\,\mathrm{IC}_i\,\sigma_{H,a}\,z_{ia}$ with $\mathrm{IC}_i=0.02$ fixed by the card, and evidence acts only through the kill rule of Section 5.1 (a $t$-statistic below $-2$ after 20 periods switches the agent off). The rank IC of carry's score was 0.035 ($t=2.2$), 0.031 ($t=3.5$) and 0.019 ($t=3.4$) on daily, four-hourly and hourly bars, with hit rates of 53% to 57%. Relative stakes between agents are then decided by wealth.

### 8.4 Results for the final design

**Table 8.2.** Carry alone, net Sharpe ratio (daily 90% interval) and risk.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Net Sharpe, corrected configuration | **1.14** [0.36, 1.90] | **1.12** | **0.94** |
| Preliminary carry book | 1.03 | 0.99 | 0.88 |
| Volatility | 22.6% | 19.5% | 19.0% |
| Maximum drawdown | −27.7% | −29.8% | −31.1% |
| Annual cost | 3.4% | 3.0% | 2.5% |

The corrected values (Study 4) are within or above the preliminary range on all bar sizes. In the development configuration the annual profit decomposed into funding collected (+8.8%, +10.6%, +12.4% a year†), selection of the right coins (+11.8%, +8.6%, +6.1%†) and a market component of about zero, because the agent is dollar- and beta-neutral. Yearly net returns on daily bars were +25%, +32%, +8%, +25%, +5% and +16% for 2020 to 2025†, with 2024 negative on four-hourly and hourly bars. Every cell solve converged. The 90% intervals exclude zero on every bar size but are wide (lower bounds 0.25 to 0.36 in the corrected configuration): five years cannot distinguish a Sharpe of 1.0 from 1.2.

### 8.5 Analysis

**Calibration matters more than combination.** With an identical signal, a belief of estimated size that can change sign forfeits about 60% of the Sharpe ratio (0.48 against 1.2). This repeats, with different machinery, a finding of the preliminary study: effort spent on combining agents is worth less than effort spent on making each agent's belief the right size.

**Carry is not only a funding harvest.** The selection component is as large as the funding component, so the profit comes from choosing coins whose price moves are favourable as well as from collecting funding.

### 8.6 Extension: does a better forecast of funding help?

*Rationale.* Carry could profit from predicting the size of the funding that will be paid, not only the ranking of coins. A mechanistic forecast, built from the premium index and the funding rule of Section 4.1, was tested.

*Model (fixed in advance).* The premium follows an AR(1) process in hours around its trailing 30-day mean, $P(h)=\mu+\varphi^h(p_t-\mu)$, with $\varphi$ pooled over coins on the history window (information before $t$ only). The funding rate per hour is $g(h)=[P(h)+\operatorname{clamp}(I-P(h),\pm c)]/8$, and the forecast funding over a holding period is the sum of $g$ over its hours.

*Pre-registered mechanical test (no profit).* On the development period and at every rebalance, compare the forecast funding sum with the realised sum for every tradable coin. The new forecast is accepted only if its cross-sectional mean squared error is lower than that of the baseline (the trailing 14-day mean funding times the horizon) with a 90% bootstrap lower bound above zero on at least two of three bar sizes.

**Table 8.3.** Forecast accuracy ($R^2$ is one minus the ratio of the mean squared error to that of a zero forecast, on cross-sectionally demeaned funding).

| Bar size | Rebalance dates | $R^2$ baseline | $R^2$ funding forecast | Outcome |
|---|---|---|---|---|
| Daily | 141 | −0.068 | −0.905 | forecast significantly worse |
| 4-hourly | 399 | +0.069 | −0.293 | forecast significantly worse |
| Hourly | 995 | +0.084 | +0.159 | not significant |

The test is passed on none of the bar sizes, so the forecast was rejected before any profit was computed. At holding periods of two to fourteen days, the forecast adds variance without information, while at the shortest horizon it improves $R^2$ but not significantly. The baseline itself explains almost none of the variation in funding differences ($R^2$ between $-0.07$ and $0.08$), so **carry earns its return from the ranking of coins, not from forecasting the size of funding**. A plausible explanation, which we did not test, is that the AR(1) state is the premium of the last hour only, which is noisy; a filtered state would be a new variant with its own pre-registration and trial.

### 8.7 Implications

The engine reproduces the only known net-positive hypothesis with exact accounting and costs of 2% to 3.4% a year. The agent's belief must be sized by its card. The study leaves open whether further agents add anything and how a market of agents behaves with more than one agent.

## 9. Study 3: The agent roster and the capital market

### 9.1 Objective and hypotheses

A capital market, per-agent neutrality and shared limits are only meaningful with several agents of different kinds. Following the hypothesis-per-agent design, two further hypotheses were added. All figures in this section are from the corrected configuration of Study 4 unless marked †. The pre-registered expectations were stated before the runs: with fixed card scales and wealth moving slowly, the market should behave roughly like a fixed-weight mix, so "no significant gain over carry" was the expected result; and the strong upward drift of 2020 to 2025 favours any long-biased trend rule, so a stand-alone Sharpe for momentum is not evidence of timing skill and admission must be judged on the beta-adjusted intercept.

**Hypotheses.** H5a: time-series momentum on Bitcoin and Ethereum is an admissible agent (its alpha against Bitcoin, and against Bitcoin and carry, has a lower bound above zero on at least two of three bar sizes). H5b: the market of carry and momentum beats carry alone. H5c: the market is at least as good as a fixed-weight blend of the stand-alone runs. H5d: timing the momentum agent by market state improves it. H5e: residual reversal is an admissible third agent and the market of three beats the market of two.

### 9.2 Design

*Engine requirements for non-neutral agents.* Momentum owns net market exposure, so the system needs per-agent neutrality rows, a system limit on net beta (a priced constraint), a calibration check that works for a two-coin agent, and a volatility limit that is a price (Section 5.3) so that the agent adding risk pays for it.

*Admission rule for momentum (before any run).* The annualised intercept of a regression of the agent's net return on Bitcoin's has a 90% block-bootstrap lower bound above zero on at least two of three bar sizes; the same holds in a regression on Bitcoin and the carry agent's return.

*Market acceptance.* Carry plus momentum against carry alone by the paired Sharpe difference, with the carry-ladder rule (lower bound above zero on at least two of three bar sizes and no upper bound below zero).

*Control.* A fixed-weight blend of the stand-alone returns of the same agents (50/50, and inverse-volatility weights), against which the market is compared by the same paired statistic.

### 9.3 Momentum and a constraint violation

In the first run momentum had negative stand-alone returns and the market of carry and momentum was worse than carry alone. Inspection of what the agent *held*, and not only of what it earned, showed that its positions did not match its card: on daily bars the mean gross position was 0.63 of equity, of which only 0.35 was in Bitcoin and Ethereum (mean absolute positions 0.24 and 0.11) and about 0.28 was in other coins. The optimiser had used a diversified basket of other coins to neutralise the beta band and variance of the Bitcoin and Ethereum trend bet, because a diversified basket looks cheap in a one-factor risk model that ignores the common residual of alt-coins. The book was therefore a Bitcoin and Ethereum trend position plus a short alt basket, with realised volatility far above the limit, which is a known limitation of a one-factor risk model for non-neutral agents. The constraint that an agent may hold only the coins of its card (Section 5.3) was enforced and the study repeated, with the card and all rules unchanged. The amendment was recorded before the repeated runs and both runs count as trials. The corrected results are in Table 9.1.

**Table 9.1.** Momentum (Bitcoin and Ethereum) and its market with carry, corrected configuration.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Momentum alone, net Sharpe | 0.96 [0.24, 1.61] | 0.80 | 0.76 |
| Volatility of the momentum book | 13.3% | 14.5% | 15.3% |
| Alpha against Bitcoin (annualised) | +9.2% [+0.2%, +17.7%] | +9.1% [−0.9%, +18.5%] | +9.2% [−2.7%, +19.7%] |
| Alpha against Bitcoin and carry | +8.6% [−0.3%, +17.3%] | +8.5% [−1.5%, +18.0%] | +9.0% [−2.8%, +19.4%] |
| Carry alone | 1.14 | 1.12 | 0.94 |
| Carry plus momentum (market) | 1.39 [0.61, 2.09] | 1.48 | 1.48 |
| Paired difference, market minus carry alone | +0.26 [+0.04, +0.47] | +0.36 [+0.04, +0.68] | +0.55 [+0.13, +0.92] |
| Paired difference, market minus fixed inverse-volatility blend | −0.07 [−0.45, +0.32] | +0.14 [−0.19, +0.48] | +0.29 [−0.05, +0.65] |

**H5a is not supported by the pre-registered rule.** The alpha estimates are stable at about +9% a year, but the lower bound exceeds zero only on daily bars, so the two-of-three requirement fails. Both admission tests fail. (Before the corrected normalisation of Study 4 they passed on two bar sizes with lower bounds of +0.3% to +1.7% and none to spare on the hourly bars; the intervals widened because the book now runs at 13% to 15% volatility instead of 11% to 12%.) We did not override the rule. Momentum is retained as a *provisional* agent in the roster, recorded as not admitted, because the coordination studies that follow need a realistic second agent, and no result claims a stand-alone edge for it. Its status is re-judged in the final study with the rule unchanged.

**H5b is supported:** the market of carry and momentum beats carry alone on all three bar sizes.

**H5c is not rejected but not supported either:** the market is ahead of the fixed blend on the two faster bar sizes by 0.14 and 0.29, but no interval excludes zero. The gain of the market over carry alone is therefore due to *diversification*, which a fixed mix provides equally.

*Caveats.* The momentum agent covers two coins over one period with strong upward drift, and most of its profit arises in 2020 and 2021; the repeated run is a forking path; the card's magnitude (0.05) is an assumption and is not horizon-neutral (ex-ante Sharpe at its actual gross is 0.30, 0.47 and 0.70 on daily, four-hourly and hourly bars).

### 9.4 Timing the momentum agent

*Hypothesis H5d.* Time-series momentum is concentrated in bull markets and crashes after high-volatility rebounds, so a belief that varies with a market state should improve it.

*Design.* The card's IC is made state-dependent, $\mathrm{IC}(s_t)=\mathrm{IC}_0+c\cdot s_t$, truncated to $[0,2\,\mathrm{IC}_0]$, with two states computed from Bitcoin returns over the history window: a *bull* state (the $t$-statistic of the trailing return; predicted coefficient $c_1\ge0$) and a *panic* state (the logarithm of the ratio of 30-day to window volatility; predicted $c_2\le0$). The coefficient is a ridge regression of each past period's skill (the slope of the volatility-standardised returns on the score) on the standardised states, with a Bayesian prior $c\sim N(0,\tau^2)$, $\tau=\mathrm{IC}_0/2$, so that a one-standard-deviation move of a state shifts the skill by at most about half the card. The ridge parameter is $\lambda_{\mathrm{ridge}}=\operatorname{var}(y)/\tau^2$ pseudo-periods, about 800 on daily bars, so the coefficient is shrunk by about three quarters at 280 periods; a coefficient of the wrong predicted sign is set to zero; the first 30 periods use the untimed card. Nothing was chosen by looking at profit. *Rule (before any run):* timing is kept only if the timed Sharpe exceeds the untimed twin's with a paired lower bound above zero on at least two of three bar sizes and no upper bound below zero. *Expectation stated beforehand:* the state dependence is estimated from a few hundred noisy periods under heavy shrinkage, so no significant difference was the likely result.

**Table 9.2.** Timed against untimed momentum (initial normalisation†; both runs share one engine).

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Untimed momentum alone | 1.06 | 0.95 | 0.90 |
| Timed momentum alone | 1.03 | 0.90 | 0.86 |
| Paired difference [90% interval] | −0.03 [−0.05, −0.01] | −0.05 [−0.09, −0.02] | −0.05 [−0.13, +0.04] |
| Carry plus momentum, untimed → timed | 1.594 → 1.597 | 1.619 → 1.629 | 1.567 → 1.580 |

**H5d is rejected.** Timing is slightly but significantly worse on two bar sizes, and the pair with carry is unchanged (differences between +0.002 and +0.013). The test has little power: a few hundred noisy periods and a handful of bull and panic episodes in five years. The finding is that this estimator, with these two states, detects nothing in this sample; it does not show that skill is state-independent. The year with a drawdown (2022) was not improved.

### 9.5 Residual reversal and the market of three

*Card.* Residual reversal as in Section 5.1, with $\mathrm{IC}=0.02$, below the 0.025 to 0.049 measured in the preliminary study (those values come from the same data and are not independent evidence). *Admission (before any run), on two of three bar sizes:* (a) the stand-alone Sharpe has a 90% lower bound above zero; (b) the rank IC has $t>2$; (c) the alpha against Bitcoin, carry and momentum has a lower bound above zero. *Market acceptance:* the market of three beats the market of two. *Reported with equal weight:* the market of three against a fixed inverse-volatility blend of the three stand-alone runs; the rank IC by liquidity tercile. *Expectation stated beforehand:* reversal fails (a) on daily bars at least, because its information is short-lived (the IC at twice the holding period was 0.003 on daily bars, in the preliminary study) while the daily rebalance interval is 14 days.

**Table 9.3.** Reversal and the market of three, corrected configuration.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Reversal alone, net Sharpe | −0.66 [−1.29, −0.03] | −1.17 [−1.82, −0.48] | −0.99 [−1.63, −0.32] |
| Rank IC ($t$) | 0.025 (1.5) | 0.042 (4.4) | 0.046 (7.3) |
| Annual trading cost; turnover (times equity) | 5.9%; 45 | 8.9%; 79 | 9.5%; 91 |
| Realised volatility | 28.7% | 24.7% | 24.1% |
| Alpha against Bitcoin, carry and momentum | −12% to −23% a year | | |
| Market of three | 1.26 [0.52, 1.97] | 1.34 | 1.33 |
| Market of three minus market of two | −0.14 [−0.29, +0.02] | −0.14 [−0.31, +0.02] | −0.15 [−0.27, −0.04] |
| Market of three minus fixed blend of the three | +0.35 [−0.17, +0.84] | +0.86 [+0.31, +1.35] | +0.88 [+0.34, +1.39] |
| Reversal's final wealth share | 1.9% | 1.8% | 2.0% |

**H5e is rejected.** Gate (a) fails on every bar size and gate (c) fails on all of them; gate (b) passes on four-hourly and hourly bars only (the daily rank IC is 1.5 standard errors from zero). The market of three is worse than the market of two on every bar size. The rank IC is highest in the *middle* liquidity tercile on every bar size (for example 0.048 against 0.037 and −0.024 on daily bars), so the mechanism "stronger in less liquid coins" is not supported in the liquid universe used here.

**The market protects against a bad agent.** The market of three is, however, clearly better than a fixed blend that contains reversal: by 0.86 and 0.88 on four-hourly and hourly bars, intervals above zero. The market reduced reversal to the 2% floor (final share 1.8% to 2.0%) and its account lost 7% to 9% of initial equity a year, whereas a fixed blend kept paying for its losses. The market's trading cost was 2.4% to 2.9% a year against 2.5% to 3.5% for the blend.

### 9.6 Analysis: when does a capital market help?

The two results fit one explanation. A fixed blend holds each agent at a constant weight; the market holds agent $i$ at a weight that follows $W_i(t)/\sum_jW_j(t)$, and since each wealth compounds with its own account return, an agent with a persistently negative return loses share geometrically until it reaches the floor. When all agents are good, wealth shares move slowly (selection speed is proportional to the growth gap between agents, which is small compared with sampling noise over five years), and the market behaves like a fixed mix, as expected. When one agent is bad, the growth gap is large and the market removes it from the portfolio within the sample, whereas the fixed blend cannot. The benefit of the market in this study is therefore *protection from failure*. It is not an enhancement of return, and it depends on the selection mechanism acting faster than the agent's losses accumulate, which the simulation study (Study 1) bounds.

### 9.7 Implications

Carry is admitted; momentum is provisional; timing and reversal are rejected. The market contributes protection and no extra return over a fixed mix of good agents. Because the volatility limit and the headline numbers had not been examined independently of the engine, the next study examines whether the conclusions are sensitive to the specification of the risk limit.

## 10. Study 4: Sensitivity of the conclusions to the specification of the risk limit

### 10.1 Objective

The mandate for the system is a volatility of 20% a year. A review of realised volatility by calendar year showed that the system did not meet it: on daily bars, the realised volatility of carry plus momentum fell from 20% in 2021 to 8% in 2025. The study identifies the cause, repeats every affected study under the corrected specification, and determines which conclusions change. Its purpose is also methodological: to show how sensitive each earlier decision was to a specification that is easy to get wrong.

### 10.2 The specification error

The volatility limit was imposed by comparing the ex-ante annual volatility of the net position, expressed in units of the *initial* equity, with the 20% target. The stakes of Kelly-sized agents, the gross cap and the beta band all scale with *current* wealth. When wealth has grown by a factor $m$, a position that is a given share of current equity has a volatility, measured in initial-equity units, that is $m$ times larger, so the effective limit was $20\%/m$. A system that had made money was held to less and less risk, while an agent that had lost money, with shrunken equity, was granted a limit far above 20% of what it had left. The corrected specification measures volatility as a share of current equity; turnover is likewise normalised by current equity. Nothing else was changed: agents, cards, gates, settings, data and period are identical.

### 10.3 Design

Each affected run of Studies 2 and 3 (carry, momentum, reversal, the market of carry and momentum, and the market of all three) was repeated once on all three bar sizes, with the pre-registered rules applied as written. Two earlier tests were not repeated because they do not depend on the specification: the forecast-accuracy test of Study 2 (a statistical comparison of forecasts) and the timing comparison of Study 3 (a comparison of two variants within one engine, whose verdict is a within-engine statement). The previous values are retained for comparison and marked †.

### 10.4 Results

**Table 10.1.** Net Sharpe ratio before (†) and after the correction (daily, 4-hourly, hourly).

| Run | Before † | After | Daily interval after |
|---|---|---|---|
| Carry | 1.26 / 1.15 / 1.00 | **1.14 / 1.12 / 0.94** | [0.36, 1.90] |
| Momentum | 1.06 / 0.95 / 0.90 | **0.96 / 0.80 / 0.76** | [0.24, 1.61] |
| Reversal | −0.57 / −1.08 / −0.83 | **−0.66 / −1.17 / −0.99** | [−1.29, −0.03] |
| Carry + momentum (market of two) | 1.59 / 1.62 / 1.57 | **1.39 / 1.48 / 1.48** | [0.61, 2.09] |
| Market of three | 1.42 / 1.39 / not run | **1.26 / 1.34 / 1.33** | [0.52, 1.97] |

After the correction, every multi-agent run sits at 18% to 21% realised volatility in every calendar year. Compound annual growth of carry plus momentum rose to 29% to 31% a year from 18% to 22%; the maximum drawdown is −22% to −26%.

**Re-applied verdicts.**

| Decision | Before | After |
|---|---|---|
| Carry baseline reproduces the preliminary result | pass | pass |
| Momentum admission (alpha lower bound above zero on two of three bar sizes) | pass (two bar sizes, margins +0.3% to +1.7%) | **fail** (daily bar only) |
| Market of carry and momentum beats carry alone | pass | pass (+0.26, +0.36, +0.55) |
| Market of carry and momentum against a fixed blend | not distinguishable | not distinguishable (−0.07, +0.14, +0.29) |
| Reversal admission | fail | fail |
| Market of three beats market of two | fail | fail (−0.14, −0.14, −0.15) |
| Market of three against a fixed blend of three | +0.33 / +0.75 on daily and four-hourly | **+0.35 / +0.86 / +0.88**, with lower bounds above zero on four-hourly and hourly |

### 10.5 Analysis

**Effect on performance.** Sharpe ratios fell by 0.03 to 0.20 and returns rose. Running at the mandated risk is more expensive, because the impact term is superlinear ($\lvert d\rvert^{3/2}$), and it holds more of the weaker part of each signal, so the Sharpe of a book is not invariant to its scale when costs are nonlinear. The pattern is consistent across agents.

**Effect on inference.** The only decision that changed is momentum's admission. Its alpha estimates barely moved (about +9% a year in both versions), but the intervals widened because the book now runs at 13% to 15% volatility, not 11% to 12%, and the lower bounds fell below zero on two bar sizes. Admission by a rule that requires an interval bound above zero is thus fragile when the estimate is near its threshold; the earlier "admitted" decision had in any case no margin on hourly bars. When the rule and the market result disagreed, we did not resolve the disagreement by choosing the rule that passed: momentum was retained as a provisional agent (Section 9.3).

**Re-interpretation of the risk-model gap.** The earlier studies had suggested that the one-factor risk model underestimates the risk of books that are not tightly neutral, with reversal running at 45% volatility against a 20% limit. Most of this was the specification error: reversal was losing money, its equity shrank and the limit, measured against initial equity, became large relative to it. In the corrected configuration reversal runs at 24% to 29%, still above 20%, so a smaller gap remains, consistent with the omission of a common residual factor among alt-coins.

**Evidence for the capital market.** The corrected results strengthen the finding of Study 3 that the market's main contribution is protection against a failing agent.

### 10.6 Implications

All later studies use the corrected specification, and only corrected values are reported from here on. The headline numbers of Studies 2 and 3 are now the corrected ones. The result that an inferential decision can flip under a plausible change in a risk specification is an argument for the multiple-testing and robustness analysis of Study 9. The next studies address the questions the project was designed around: whether the optimiser can run without a central node, and what happens when the network or an agent fails.

## 11. Study 5: Decentralised optimisation on real data

### 11.1 Objective and hypothesis

The joint optimiser of Section 5.4 uses a hub. This study tests **H1**: the decentralised version of Section 5.5, in which agents exchange values only with their neighbours, reproduces the centralised portfolio on real data, on every connected graph.

### 11.2 Design

*Development problems.* Before the real-data test, the algorithm was verified on random problems with 3 and 8 agents. On the complete graph the result equals the hub's to $10^{-15}$; on a three-agent ring and line it equals it to $10^{-8}$. With eight agents and all limits binding, one gossip round per iteration needed about 2,700 iterations on a ring ($\lvert\lambda_2\rvert=0.81$) and more than 3,000 on a line (0.95); three rounds brought the ring to about 400 and ten rounds the line to about 600. Two ablations showed that two elements of Algorithm 1 are necessary: mixing the estimates *before* adding the agent's own change ($s\leftarrow Ws+\Delta x$) leaves each estimate off by its own last move and failed when the gross cap bound, and leaving the prices unmixed allowed agents to settle on different prices and stop at a wrong point. Both follow from Proposition 1: the sum invariant requires that each agent's change enter before the doubly stochastic mixing, and the prices must be mixed for the fixed point to be common.

*Real-data test.* Three agents (carry, momentum, reversal), daily bars, development period, the same data and settings as the hub run. Graphs: the complete graph and the line (the least connected graph on three agents; the ring on three agents is the complete graph), with 1 and 3 gossip rounds. *Rule, before the runs:* the graph runs reproduce the hub run's net Sharpe within 0.01 and its final equity within 1%.

### 11.3 Results

**Table 11.1.** Hub against decentralised runs (daily, three agents).

| Run | Net Sharpe | CAGR | Volatility | Max drawdown | Final equity | Rebalances at the iteration cap (of about 137) | Mean solver iterations |
|---|---|---|---|---|---|---|---|
| Centralised hub | 1.258 | 25.9% | 19.9% | −22.1% | 3.564 | 21 | not recorded |
| Graph, complete | 1.257 | 25.9% | 19.9% | −22.1% | 3.560 | 22 | 1,504 |
| Graph, line, 1 round | 1.256 | 25.8% | 19.9% | −22.1% | 3.554 | 43 | 2,011 |
| Graph, line, 3 rounds | 1.257 | 25.9% | 19.9% | −22.1% | 3.559 | 24 | 1,554 |

Every agent's account is the same to three decimals in every run (annual profit in initial equity: carry 0.427 to 0.429, momentum 0.101, reversal $-0.066$; final wealth shares 0.738 / 0.243 / 0.019). The largest daily return difference to the hub is $6\times10^{-4}$ and the mean $7\times10^{-6}$.

### 11.4 Analysis

**H1 is supported:** the Sharpe ratio is within 0.002 and final equity within 0.3% of the hub on every topology. The residual differences (0.001% a day on average) arise from solves stopped at the iteration cap, not from topology. The cap is reached at 21 of about 137 rebalances even by the hub, so non-convergence at the cap is a property of the problem (slow convergence of the split of the net position between agents) and not of decentralisation. Its effect on profit is small because a capped solve is close to the optimum. The effect of communication is visible in the counts of capped rebalances: on the line with one round the cap is reached twice as often as on the complete graph, and three rounds bring it back to the hub's level, which is the effect predicted by the mixing rate.

### 11.5 Implications

With three agents most graphs coincide, so topology cannot be studied on the real roster as it stands. The next study uses simulated problems with more agents, then real data with eight agents.

## 12. Study 6: Network topology and communication budget

### 12.1 Objective and hypotheses

**H2.** The number of iterations needed to converge increases with the mixing rate $\lvert\lambda_2(W)\rvert$ of the communication graph, and the portfolio does not depend on the topology. The study also quantifies the communication needed, and the loss in return when communication is cut short.

### 12.2 Theoretical background

By Section 5.5, one gossip round multiplies the disagreement by at most $\lvert\lambda_2\rvert$, so reducing it tenfold takes $\ln10/\!\ln(1/\lvert\lambda_2\rvert)$ rounds. Table 12.1 gives this for the graphs used. It predicts a strong penalty for poorly connected graphs at larger sizes: the line on sixteen agents needs more than 200 rounds for each tenfold reduction, against 45 for a ring.

**Table 12.1.** Gossip rounds needed to reduce disagreement tenfold, by mixing rate (the complete graph mixes exactly in one round).

| Graph (agents) | $\lvert\lambda_2(W)\rvert$ | Rounds per tenfold reduction |
|---|---|---|
| Random (8) | 0.68 | 6.0 |
| Ring (8) | 0.80 | 10.3 |
| Star (8) | 0.88 | 18.0 |
| Line (8) | 0.95 | 44.9 |
| Random (16) | 0.79 | 9.8 |
| Star (16) | 0.94 | 37.2 |
| Ring (16) | 0.95 | 44.9 |
| Line (16) | 0.99 | 229 |

The algebraic connectivity (second-smallest Laplacian eigenvalue) is the other standard connectivity measure. For the star it is larger than for the ring (1.0 against 0.59 at eight agents), whereas its mixing rate is worse (0.88 against 0.80); with Metropolis weights the centre of a star is a bottleneck, so the mixing rate is the better predictor.

### 12.3 Design (rules fixed before any run)

*Part A: simulated problems.* The random test problems of Study 1 with every limit binding (fee, capacity, margin, gross cap, beta band); tolerance $10^{-8}$; cap 4,000 iterations; five problems per cell. The optimum is the hub solution at tolerance $10^{-10}$. Agents $M\in\{4,8\}$ with topologies complete, ring, line, star, random (Erdős–Rényi with $p=0.4$, connected) and gossip rounds $r\in\{1,3,10\}$; at $M=16$ only $r=3$ with three problems, because each agent solves the system step itself, so computation grows with the number of agents (this reduction was fixed before any result was seen).
- **A1 (gate):** at $r=3$ the Spearman rank correlation between $\lvert\lambda_2(W)\rvert$ and iterations to converge is at least 0.7 for each $M$ (non-converged runs enter at the cap).
- **A2 (sanity gate):** the complete graph takes exactly the hub's iterations.
- **A3, A4 (reported):** the number of rounds that minimises messages; the error of the net position after a fixed budget of $K\in\{25,50,100,200,400\}$ iterations.

*Part B: real data (daily).* Eight agents that are parameter variants of the three hypotheses, used only to study coordination: carry with 7, 14 and 30-day funding windows; momentum with 15, 30 and 60-day lookbacks; reversal with 3 and 7-day lookbacks. Runs: hub; graph complete (1 round); ring (1 and 3 rounds); line (3 rounds); star (3 rounds); and a communication budget, the hub and the ring with 3 rounds capped at 200 iterations.
- **B1 (gate):** every uncapped graph run reproduces the hub's Sharpe within 0.02 and final equity within 2%.
- **Recommendation rule:** the default topology for later studies is the one with the fewest messages per rebalance that passes B1 with no more capped rebalances than the hub plus 10% of rebalances.

*Expectation stated beforehand.* A1 passes (convergence speed is governed by $\lambda_2$); the line is the slowest and the complete graph the fastest; with a short budget poorly connected graphs leave agents in disagreement; on real data B1 passes for uncapped runs and capped runs lose a little.

### 12.4 Results: simulated problems

**Table 12.2.** Median iterations to converge at three gossip rounds (five problems; three at $M=16$; cap 4,000), with the mixing rate in brackets.

| Agents | Complete | Ring | Random | Star | Line |
|---|---|---|---|---|---|
| 4 | 151 (0) | 165 (0.33) | 228 (0.75) | 264 (0.75) | 389 (0.80) |
| 8 | 386 (0) | 499 (0.80) | 883 (0.68) | 1,183 (0.88) | not converged (0.95) |
| 16 | 1,000 (0) | 3,709 (0.95), 2 of 3 converged | 1,000 (0.79) | not converged (0.94) | not converged (0.99) |

- **A1 fails.** The correlations are 0.60 at four agents, 0.90 at eight and 0.78 at sixteen. The failure at four agents has a clear cause. Differences between graphs of four agents are small, and the intrinsic difficulty of the individual problem dominates: one problem required about 830 iterations on every topology, including the complete graph, so the slow convergence is that of ADMM on that problem and not of consensus. Pooling seeds therefore confuses problem difficulty with topology. Within each problem the ordering is as predicted (mean within-problem correlation 0.79, 0.96 and 0.82), but that is not the pre-registered statistic and the gate is reported as failed.
- **A2 passes.**
- **A3.** One gossip round minimises the messages on the complete graph and (at four agents) the ring; three rounds are cheapest elsewhere, because one round needs so many more iterations that the extra messages per iteration pay for themselves; ten rounds waste messages once mixing is no longer the bottleneck. Median messages at eight agents: complete graph 21,616 (one round), ring 23,952, star 49,686, random 52,980 (three rounds each); the line does not converge at one or three rounds and needs 91,840 at ten.
- **A4.** At three rounds, the error of the net position after $K$ iterations is almost the same on every topology (eight agents: about 0.40 at $K=25$, 0.16 at 100, 0.03 to 0.05 at 200, below 0.001 at 400; sixteen agents: 0.76 at 100, 0.16 at 200, 0.012 to 0.015 at 400). The early iterations are limited by ADMM itself, not by communication; topology decides how long the final, precise part takes.

*Check with the priced volatility term (eight agents, three rounds, three problems).* The ring converged in 797 to 1,076 iterations (hub: 165 to 749); the line reached the iteration cap on all three problems, with a net-position error of at most $4.3\times10^{-6}$ of a typical position.

### 12.5 Results: real data

**Table 12.3.** Eight agents, daily bars (135 rebalances; engine cap 3,000 iterations unless stated).

| Run | Net Sharpe | CAGR | Final equity vs hub | Rebalances at cap | Mean iterations | Messages per rebalance |
|---|---|---|---|---|---|---|
| Hub | 1.240 | 26.0% | 3.578 | 27 | 1,427 | (hub) |
| Graph, complete, 1 round | 1.239 | 26.0% | −0.02% | 29 | 1,459 | 81,716 |
| Graph, ring, 1 round | 1.238 | 26.0% | −0.16% | 114 | 2,885 | 46,160 |
| Graph, ring, 3 rounds | 1.239 | 26.0% | −0.08% | 43 | 1,870 | 89,755 |
| Graph, line, 3 rounds | 1.238 | 25.9% | −0.22% | 122 | 2,949 | 123,854 |
| Graph, star, 3 rounds | 1.240 | 26.0% | −0.01% | 96 | 2,743 | 115,194 |
| Hub, 200-iteration cap | 1.217 | 25.3% | −2.8% | 135 | 200 | (hub) |
| Graph, ring, 3 rounds, 200-iteration cap | 1.212 | 25.2% | −3.5% | 135 | 200 | 9,600 |

Volatility was 20.2% to 20.3% and maximum drawdown $-29.8\%$ to $-30.0\%$ in every run. Messages per rebalance equal mean iterations $\times r\times2\lvert\mathcal{E}\rvert$ (28 edges for the complete graph, 8 for the ring, 7 for the line and the star), and the mean counts only the last solve of each rebalance.

**B1 passes:** every uncapped graph run is within 0.002 Sharpe and 0.23% of final equity of the hub. The recommendation rule allows at most 27 + 13.5 = 40.5 capped rebalances: only the complete graph with one round qualifies (29); the ring with three rounds just misses (43), and the ring with one round, which uses the fewest messages (46,160), reaches the cap at 114 rebalances. The default topology for later studies is therefore the complete graph with one round of gossip.

### 12.6 Analysis

1. **Network shape governs the communication, not the outcome.** On real data every uncapped topology gives the same system as the hub; the price of a sparse graph is paid in iterations and messages. On simulated problems with eight agents the line needs more than ten times the iterations of the complete graph, and on real data the line and the one-round ring run out of iterations at four times as many rebalances.
2. **The link between mixing rate and iterations is conditional.** It holds when the graphs in the comparison differ enough (eight and sixteen agents) and fails when problem difficulty dominates (four agents). Table 12.1 gives the mechanism, and the failure of A1 is a statement about a pre-registered pooled statistic, not about the mechanism.
3. **The mixing rate predicts better than algebraic connectivity,** as Table 12.1 and the star-ring comparison show.
4. **Removing the hub costs computation that grows with the number of agents,** because each agent solves the system step itself.
5. **A short communication budget costs money, but little, on any topology.** Capping every solve at 200 iterations loses about 3% of final equity and 0.025 Sharpe over five and a half years, the ring slightly more than the hub; the error after 200 iterations is similar across topologies (A4).

### 12.7 Implications

The default for the resilience study is the complete graph with one round. Because a complete graph offers many alternative paths, link failures on it are a weak test, so the next study also uses a sparse graph: the ring with three rounds, which only just missed the recommendation rule, and a sparse but robust graph (ring2), both specified before any run.

## 13. Study 7: Resilience to link failures, agent dropout and misbehaving agents

### 13.1 Objective and hypotheses

**H3.** (i) Link failures and agent dropout, which preserve a doubly stochastic mixing, are absorbed: the optimum is still reached, at a cost in communication. (ii) A consistent liar is isolated on a robust graph, and the remaining agents reach the optimum of the problem without it. (iii) W-MSR, as the lecture states it, does not preserve the optimum when used as the averaging rule (Section 5.6), so we also test it as a detector.

### 13.2 Design (rules fixed before any run)

*Disclosure.* The mechanisms and detector parameters (90% of coordinates, 50 iterations, majority of neighbours) were fixed on development problems before the rules were written. The study uses fresh problems and real data and changes no parameter.

*Part A: simulated problems* (eight agents, every limit binding, tolerance $10^{-8}$, cap 4,000 iterations, fresh problems; graphs: the complete graph with one round, ring2 with three rounds and the ring with three rounds). The liar is agent 3 and holds nothing, so the correct answer is the optimum of the problem without it; the error is the maximum of $\lvert X-X^\ast\rvert$ divided by the mean $\lvert X^\ast\rvert$.
- **A1 (gate):** with each edge down with probability $q\in\{0.1,0.3\}$ in every round, every run on every graph converges with error at most $10^{-4}$; $q=0.5$ is reported.
- **A2 (gate):** on the complete graph and ring2, with the detector on: with no liar nobody is isolated; with a liar adding a constant $d\in\{0.001,0.01,1.0\}$ to everything it sends, the liar and only the liar is isolated, the run converges and the error is at most $10^{-4}$.
- **A3 (reported, predicted to fail):** the same on the plain ring.
- **A4 (reported):** the undefended liar (plain mixing); a noise liar (normal noise of standard deviation 0.01, new each iteration) with the detector.
- **A5 (reported, decides the code):** W-MSR trimmed mixing ($F=1$) with no attacker, on the complete graph and ring2. If the error exceeds $10^{-2}$ in most runs, the trimmed mixing is rejected.

*Part B: real data* (daily, the eight agents of Study 6; references: the hub, the complete graph with one round and the ring with three rounds of Study 6).
- **B1 (gate):** with 30% of links down, the complete graph with one round and the ring with three rounds reproduce the hub's Sharpe within 0.02 and final equity within 2%.
- **B2 (gate):** with the largest agent (a carry variant) offline from 1 May to 31 August 2022 (the Luna collapse and its aftermath), the graph runs reproduce the hub with the same agent offline, and the highest ex-ante volatility at any rebalance inside the window is no higher than the highest outside it (the risk limit works as well while an agent is missing).
- **B3 (gate):** with a momentum variant lying (adding 0.01 to everything it sends), the detector isolates it at every rebalance, no other agent is ever isolated, and the run reproduces the hub without that agent within 0.02 Sharpe and 2% final equity; with the detector on and no liar, nobody is isolated and the run reproduces Study 6's complete-graph run within 0.002 Sharpe.
- **B4 (reported):** the cost of the offline agent and of the missing liar, and the iterations and capped rebalances of every run.

*Expectation stated beforehand.* A1, A2, B1 to B3 pass; A3 fails as the robustness condition predicts; the noise liar is mostly not caught; the undefended liar spoils the solve and costs money; trimmed mixing is rejected.

### 13.3 Results: simulated problems

**Table 13.1.** Median iterations to converge under link failures (eight agents).

| Graph | $q=0$ | $q=0.1$ | $q=0.3$ | $q=0.5$ |
|---|---|---|---|---|
| Complete, 1 round | 187 | 215 | 262 | 288 |
| Ring2, 3 rounds | 193 | 214 | 235 | 265 |
| Ring, 3 rounds | 439 | 513 | 700 | 1,075 |

**Table 13.2.** Gate outcomes (simulated problems).

| Gate | Outcome |
|---|---|
| **A1** link failures | **pass**; error at most $5.4\times10^{-6}$; every run converged even at $q=0.5$ |
| **A2** constant liar, detector on | **pass**; 18 of 18 runs: only the liar isolated, every run converged, error at most $4.4\times10^{-6}$; with no liar nobody isolated |
| **A3** plain ring | **fail**, as predicted: in all nine liar runs an honest agent was isolated as well (mostly the agent two steps from the liar) and the graph fell apart; with no liar the ring isolated nobody |
| A4 undefended constant liar ($d=0.01$) | error after 1,000 iterations 5.5 to 5.9 typical positions on every graph; no convergence |
| A4 noise liar, detector on | isolated in 1 of 6 runs (complete graph, one problem, after which the result was exact); in the other five, no isolation, no convergence in 4,000 iterations, error 12.5 to 14.8 typical positions |
| **A5** trimmed mixing, no attacker | no run converged; error 0.50 to 4.8 typical positions in all six runs; **rejected** |

### 13.4 Results: real data

**Table 13.3.** Resilience on real data (daily, eight agents, 135 rebalances).

| Run | Net Sharpe | Final equity | Capped rebalances | Mean iterations | Against the reference |
|---|---|---|---|---|---|
| Hub | 1.240 | 3.578 | 27 | 1,427 | |
| Complete graph, 1 round | 1.239 | 3.577 | 29 | 1,459 | |
| Ring, 3 rounds | 1.239 | 3.575 | 43 | 1,870 | |
| Complete, 30% of links down | 1.239 | 3.577 | 31 | 1,692 | within 0.001 of the hub (B1 pass) |
| Ring, 3 rounds, 30% of links down | 1.239 | 3.575 | 56 | 2,155 | within 0.001 of the hub (B1 pass) |
| Hub, largest agent offline | 1.225 | 3.476 | 28 | 1,440 | cost of the missing agent |
| Complete, largest agent offline | 1.225 | 3.476 | 29 | 1,468 | equals the hub with the same agent offline (B2 pass) |
| Ring, largest agent offline (a line without it) | 1.225 | 3.474 | 46 | 1,902 | equals the hub (B2 pass) |
| Complete, detector on, no liar | 1.239 | 3.577 | 29 | 1,459 | nobody isolated (B3 pass) |
| Complete, liar (momentum variant), detector on | 1.182 | 3.391 | 30 | 1,541 | isolated at the first rebalance, nobody else ever (B3 pass) |
| Hub, without that momentum variant | 1.182 | 3.392 | 29 | 1,512 | the correct reference |

B2: in all three offline runs the highest ex-ante volatility inside the offline window was 17.5%, against 20.9% outside it. The largest agent, offline for four months including the Luna collapse, held 38% of final wealth; its absence cost 0.015 Sharpe and 2.8% of final equity relative to the full hub. Leaving out the lying agent costs 0.058 Sharpe and 5.2% of final equity relative to the full hub, mostly because its capital then sits idle. The undefended liar on real data was not completed: with the lie every solve ran to the iteration cap and the volatility search repeated it up to five times, so the cost of an undefended liar is shown on simulated problems (A4).

### 13.5 Analysis

**Link failures and dropout are absorbed (H3 i).** With weights recomputed on the surviving links the optimiser reaches the same answer in every case: on simulated problems every run converged even with half of the links down, and on real data the Sharpe ratio is within 0.001 of the hub. The cost is communication: on the ring, 30% failures raise the iterations by about 60% on simulated problems and 15% on real data. The mechanism is Proposition 1: the recomputed Metropolis matrix is again doubly stochastic, so the sum of the estimates stays equal to the sum of the positions. An agent going offline is the same problem with one fewer agent, and the graph runs equal the hub with the same agent offline.

**W-MSR cannot be the averaging rule here (H3 iii).** Trimmed mixing failed to converge even with no attacker, with errors of 50% to 480% of a typical position, because it discards part of the sum that the agents are tracking: the weight matrix it induces is data-dependent and not doubly stochastic, so the invariant of Proposition 1 is lost and the agents agree on a value that is not the average of the positions. This is a negative result about combining resilient consensus (which guarantees agreement inside the range of honest values) with optimisation (which needs the exact sum).

**W-MSR works as a detector on robust graphs (H3 ii).** On the complete graph and on ring2 (four neighbours each) a consistent liar was caught at every size from 4% of a typical position, with no false alarm, on simulated and real data, and the result was exactly that of the system without it. The detector reads the share of coordinates in which a neighbour's value is the extreme one beyond one's own; a consistent offset pushes the liar's value beyond the honest values in nearly every coordinate, so the share is near one. On the plain ring (two neighbours) honest agents were isolated too, as the robustness condition predicts. A plausible explanation, not separately tested, is that with only two neighbours a single deviating neighbour is already a majority, so an honest agent next to the liar, whose own values are pulled by it, can be flagged by its other neighbour. The *robustness of the graph, not only its connectivity,* decides whether the system can defend itself. The distinction is practical: the complete graph is robust and expensive, the ring is cheap and not robust, and ring2 is sparse and robust.

**A stealthy liar gets through.** A noise liar whose values stay inside the range of the honest values was caught only once in six runs; otherwise the result is far from the optimum and the solver does not converge. Non-convergence is observable, which motivates a supervisor that refuses to act on a solve that did not converge (Study 8). The undefended liar's effect on convergence is severe: the solver does not converge even when the lie is a constant offset of 0.01, about 40% of a typical position.

**The cost of resilience.** Every defended failure on real data is within 0.001 Sharpe of its matching reference. The money lost comes from what is missing (an agent out, or idle capital), not from the coordination.

### 13.6 Implications

The decentralised optimiser, with its failure handling, behaves as the central one at the price of communication and detection work. The remaining requirement of the design is formal safety: a record of whether the specifications hold over time and a supervisor that reacts to losses and to corrupted solves.
## 14. Study 8: Formal safety monitoring and supervision

### 14.1 Objective and hypotheses

The priced limits of Section 5.3 act on *ex-ante* risk; nothing yet reacts to realised losses, and nothing records over time whether the system's specifications hold. Study 7 also showed that a noise liar produces a wrong portfolio from a solve that does not converge. **H4:** (i) the STL monitor documents the system's margin to its specifications through stress periods; (ii) the derisk supervisor reduces breaches of the drawdown specification; (iii) the hold supervisor prevents the system from trading on corrupted solutions, without acting on honest ones.

### 14.2 Why a monitor and supervisors, and not a post-hoc shield or a drawdown constraint

A post-hoc shield that scales the finished portfolio towards cash re-trades the whole book of a cost-optimised portfolio (Section 3.2, F4). A drawdown constraint inside the optimiser has no clean form, because a drawdown is a property of a path, not of the next portfolio. The chosen design leaves the optimiser unchanged: a monitor records the robustness of each specification, and the supervisors act through what the optimiser already has, the volatility target (derisk) and the decision to trade (hold).

### 14.3 Design (rules fixed before any run)

*Limits* are those of Section 5.7, derived from the risk mandate before any run; none was chosen by a backtest. *Disclosure:* the implementation was checked on the first 900 days of the daily data in a smoke test (carry plus momentum, hub), in which derisk acted (target down to 0.32) and hold never triggered (worst relative residual $10^{-6}$); no setting was changed afterwards, and the smoke test is not counted as a trial.

*Part A: the main system* (carry plus momentum, centralised, development period) on all three bar sizes with safety off and derisk, and on daily bars also hold; seven runs.
- **A1 (gate):** in every run with safety off, the solver-health specification holds at every rebalance and the volatility specification ($\le1.05\times$ target) at at least 95% of rebalances.
- **A2 (gate):** on each bar size, derisk has fewer bars violating the drawdown specification (365-day drawdown below $-15\%$) than off, and a shallower worst 365-day drawdown.
- **A3 (reported):** for each run and stress window: return, worst drawdown, volatility, minimum robustness, violating bars, lowest volatility multiplier; whole-period Sharpe, CAGR and maximum drawdown of derisk against off (the cost, which is not a criterion: limits are never chosen by Sharpe).

*Part B: a stealthy liar on real data* (daily, carry plus momentum plus reversal, the complete graph with one round). Reversal is the misbehaving agent from 1 May to 31 July 2022 only: it holds nothing and adds normal noise of standard deviation 0.01, newly drawn at every iteration, to everything it sends. Runs: (a) no liar; (b) the liar, no defence; (c) the liar with the hold supervisor.
- **B1 (gate):** in (c) every unsafe solve is held, every held rebalance is inside the liar's window, and no rebalance outside the window is unsafe; in (b) at least one rebalance in the window trades on an unsafe solve.
- **B2 (reported):** money and risk of (b) and (c) against (a): Sharpe, final equity, return, worst drawdown and trading cost inside the window.

*Expectation stated beforehand.* A1 passes; A2 passes on every bar size at a cost of a little return; the specifications are tightest in May 2021 and Luna; B1 passes; in (b) the corrupted solves trade a wrong portfolio inside the window and in (c) the system holds its positions through it.

### 14.4 Results: the main system

**Table 14.1.** Safety modes on the main system (centralised, carry plus momentum).

| Mode | Metric | Daily | 4-hourly | Hourly |
|---|---|---|---|---|
| Off | Sharpe | 1.394 | 1.478 | 1.483 |
| | CAGR | 31.2% | 29.8% | 29.2% |
| | worst 365-day drawdown | −23.7% | −24.4% | −25.9% |
| | bars with drawdown below −15% | 211 | 2,223 | 7,695 |
| | rebalances with ex-ante volatility within $1.05\times$ target | 97.8% | 97.6% | **94.3%** |
| | worst volatility margin | −0.5% | −3.0% | −10.0% |
| | unsafe solves | 0 | 0 | 0 |
| Derisk | Sharpe | 1.277 | 1.275 | 1.462 |
| | CAGR | 23.9% | 21.0% | 24.3% |
| | worst 365-day drawdown | −19.7% | −18.8% | −16.7% |
| | bars with drawdown below −15% | 229 | 2,159 | 5,135 |
| | lowest volatility multiplier | 0.2 | 0.2 | 0.2 |
| Hold (daily only) | Sharpe | 1.394 | | |
| | rebalances held | 0 | | |

(The volatility margin is the limit minus the ex-ante volatility, relative to the limit; bars are of the run's own size, so bar counts are not comparable across bar sizes.)

**A1 fails on hourly bars.** The solver-health specification holds at every rebalance of every run (the few unconverged solves on four-hourly and hourly bars stopped below the $10^{-3}$ residual). The volatility specification holds at 97.8% and 97.6% of rebalances on daily and four-hourly bars, but at 94.3% on hourly bars (54 of 955 rebalances), with breaches up to 10% above the limit. The cause is the volatility-price search, which uses at most five re-solves and a 2% band, and on hourly data the covariance moves faster between rebalances than the warm-started price follows. It is a limitation of the search, not of the specification.

**A2 passes on four-hourly and hourly bars and fails on daily bars.** Derisk always makes the worst 365-day drawdown shallower (by 4 to 9 points), and on four-hourly and hourly bars it also reduces the number of bars below $-15\%$ (2,159 against 2,223; 5,135 against 7,695). On daily bars it has *more* such bars (229 against 211): with smaller positions after a loss the account recovers more slowly, so it stays below the line longer even though it never falls as far. The count of violating bars therefore penalises a supervisor that shortens deep drawdowns but lengthens shallow ones.

**A3: cost and stress windows.** Derisk costs Sharpe 0.12, 0.20 and 0.02 and CAGR 7.3, 8.8 and 4.9 percentage points on daily, four-hourly and hourly bars. In the stress windows the specifications are tightest in the **FTX collapse (November 2022 to January 2023)**, not in May to July 2021 or in the Luna collapse as expected. In May 2021 and in the Luna collapse the system made money (7% to 16%), the drawdown inside the window was at most 8.5% and derisk did not act. The FTX window is the only one in which the drawdown specification is violated (1 daily bar, 444 four-hourly, 1,741 hourly, with safety off). There derisk acts: on four-hourly bars the drawdown inside the window falls from 8.5% to 2.0% and volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%); on hourly bars the drawdown falls from 12.6% to 2.8%. The realised-volatility specification with its 14-day recovery is violated only on daily bars (34 bars off and 28 with derisk), and never inside a stress window.

### 14.5 Results: a stealthy liar

**Table 14.2.** Hold supervisor against a noise liar (daily).

| Run | Sharpe | Final equity | CAGR | Return in the window | Worst drawdown in the window | Trading cost in the window | Unsafe solves | Held |
|---|---|---|---|---|---|---|---|---|
| (a) no liar | 1.257 | 3.56 | 25.9% | 11.7% | −3.0% | 0.86% | 8 (all in 2025) | 0 |
| (c) liar, hold | 1.033 | 2.77 | 20.3% | 6.7% | −5.8% | 0 | 15 | 15 |
| (b) liar, no defence | divergent | | | | | | first attacked solve unsafe | |

*Run (b).* Without a supervisor the corrupted solve diverges. A profile of the first attacked rebalance shows a relative residual of 1.32 against the limit of $10^{-3}$, iterates growing from 0.4 to 44 within 700 iterations, and the time per agent step growing from 0.02 s to 0.3 s, so one 3,000-iteration solve takes about 45 minutes. A complete undefended run on real data was not obtained for this reason. Runs (b) and (c) are identical up to the first attacked rebalance, where the undefended system would trade an unsafe solve, which is the second part of B1; B2 for (b) is not measured.

**B1 fails.** Every attacked rebalance in the window was held (six of six; relative residual 1.18 to 1.62), but nine *honest* rebalances in 2025, with no liar, were also held (residuals 0.0013 to 0.0059, due to slow convergence of the decentralised solve). The same slow solves occur in the clean run (a), eight of them, which with no supervisor it traded. The pre-fixed limit of $10^{-3}$ therefore cannot distinguish an attack, with residuals above 1, from slow honest convergence, with residuals around 0.003: the two differ by a factor of about 300, so a better limit exists, but it was not tuned after seeing the result. The consequences of the false alarms were larger than those of the attack. Inside the window (c) earns 6.7% against 11.7% for (a), with a deeper drawdown (5.8% against 3.0%), because it keeps pre-attack positions through the Luna collapse (their ex-ante volatility, 12% to 15%, is inside the limit). Frozen for most of May to October 2025, the stale positions drifted to an ex-ante volatility of up to 31%, which violates the volatility specification at five held rebalances, and the whole-period Sharpe ratio falls from 1.26 to 1.03.

### 14.6 Analysis

1. **The monitor is informative.** A single record per bar of the distance of each specification from violation shows where the system was in danger. It identified a window that we had not predicted (FTX); our prior expectation, that Luna would be the tightest, was wrong because the system was positioned for a falling market in that episode and profited.
2. **Derisk behaves as designed and exposes a trade-off between depth and duration.** It limits the worst drawdown at a Sharpe cost of 0.02 to 0.20; the daily failure of A2 is a consequence of the supervisor's own mechanism and not a defect of the estimator.
3. **The volatility price search lags on fast bars.** A longer or better-initialised search is the obvious remedy and is a separate variant.
4. **Hold stops a stealthy liar, but a threshold chosen in advance also freezes the system on honest slow solves.** Detect-and-isolate catches consistent liars and hold catches noisy ones; each alone is incomplete.
5. **An undefended noise liar makes the decentralised solve diverge,** so some supervisor is needed in practice.

### 14.7 Demonstration tool

An interactive dashboard accompanies the study. It runs the real decentralised optimiser live on simulated problems (graph, gossip rounds, link failures, a liar with or without the detector) and shows saved results on topology, performance and wealth, the safety record, resilience and the final comparison. It reads saved results only and uses no sealed data.

### 14.8 Implications

The monitor is adopted in every run; derisk is usable (it passes on two of three bar sizes at a cost); hold is available but stays off until its limit is re-argued. The final study consolidates everything on the development period and applies the multiple-testing correction.

## 15. Study 9: Consolidated evaluation and the multiple-testing verdict

### 15.1 Objective

To collect, against the centralised reference, what each component contributes in money, risk, convergence, communication and safety, and to test **H6**: the deflated Sharpe ratio of the main system is at least 0.95. The study runs no new simulation and uses no new setting: it reads the saved runs of Studies 4 to 8 and the trial log.

### 15.2 Design (rules fixed before the table was computed)

*Tables.* T1: money and risk per bar size for the three agents, the markets of two and three, and a 50/50 blend of carry and momentum (Sharpe with intervals, CAGR, volatility, maximum drawdown, Calmar ratio, turnover). T2: centralised against decentralised runs (Sharpe, final equity against the hub, iterations, capped rebalances, messages). T3: each failure against its correct reference. T4: safety (violations, robustness, cost). T5: the deflated Sharpe of the main system.

*Trial counting for T5.* A trial is a pair (strategy variant, bar size). The strategy variants on real data are: carry in three belief designs (Study 2), carry with the funding forecast (Study 2), momentum before and after enforcing its coin set, the market of two with each, timed momentum with its market, reversal alone, the market of three, and the corrected re-runs of carry, momentum, reversal, the market of two and the market of three (Study 4): 15 variants on each of three bar sizes, **$N=45$**. The engineering variants (consensus form, topology, resilience, safety) add 29 distinct names, giving a conservative total of $N=74$. The variance $V$ of trial Sharpe ratios is that of the 15 corrected strategy runs.

*Gates.* **C1 (consistency):** every number that T1 to T4 share with an earlier study reproduces to its rounding (0.001 in Sharpe); otherwise the table is wrong and is fixed before anything is reported. **C2 (verdict):** the deflated Sharpe ratio of the market of two is at least 0.95 at $N=45$ on a bar size.

*Expectation stated beforehand.* C1 passes. C2 may well fail: the trial Sharpe ratios range from $-1.2$ to 1.5, a spread that raises the bar the best trial must clear, and five and a half years of data may not suffice for a Sharpe of 1.4 to 1.5 to clear it. A failure would mean the development period alone does not establish the edge after multiple testing; it would not affect the comparison of mechanisms, which is made on the same strategy.

### 15.3 Results: money, risk and mechanisms

**C1 passes.**

**Table 15.1 (T1).** Net Sharpe ratio, 90% interval.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [−0.03, 1.44] |
| Reversal | −0.66 [−1.29, −0.03] | −1.17 [−1.81, −0.48] | −0.99 [−1.63, −0.32] |
| **Main system: market of carry and momentum** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 blend, carry plus momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2%, 29.8%, 29.2%; volatility 21%, 19%, 18%; maximum drawdown −23.7%, −24.4%, −25.9%.

**T2: centralised against decentralised (daily).** Market of three: hub 1.258, complete graph 1.257, line 1.256, with final equity within 0.3% of the hub. Eight agents: every topology within 0.002 Sharpe and 0.22% of the hub's final equity; mean iterations 1,427 (hub) to 2,949 (line); messages 46,160 (ring, one round) to 123,854 (line); capped rebalances 27 to 122; a 200-iteration budget costs 2.8% (hub) and 3.5% (ring) of final equity.

**T3: resilience (daily), each against its reference.** Thirty per cent link failures: 1.239 and 1.239 against 1.240. The largest agent offline: 1.225 against 1.225. A constant liar with the detector: 1.182 against 1.182, liar isolated. In every case final equity is within 0.1% of the reference's. Noise liar: no defence not measured; with hold, 1.033 against 1.257 ($-22\%$ final equity, mostly false alarms in 2025).

**T4: safety.** As in Study 8: derisk worst 365-day drawdown −19.7%, −18.8%, −16.7% against −23.7%, −24.4%, −25.9%, at a Sharpe cost of 0.12, 0.20 and 0.02.

### 15.4 Results: the multiple-testing correction

**Table 15.2 (T5).** Deflated Sharpe ratio of the main system (gate C2: at least 0.95).

| Bar | Sharpe | Skewness | Kurtosis | DSR at $N=45$ | DSR at $N=74$ | Gate C2 |
|---|---|---|---|---|---|---|
| Daily | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 | fail |
| 4-hourly | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 | fail |
| Hourly | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 | fail |

The annual variance of trial Sharpe ratios is 0.82 (the 15 corrected strategy runs, from $-1.17$ to 1.48). The deflated Sharpe ratio exceeds 0.95 only for $N\le2$ trials (0.98 to 0.99) and is 0.47 to 0.55 at $N=10$.

### 15.5 Analysis

**Multiple testing.** At $N=45$, a Sharpe ratio of 1.4 to 1.5 is what the best of that many trials with spread this wide would produce by chance with probability about 90%. The correction is large because the trial Sharpe ratios are widely dispersed (the roster contains deliberately bad agents) and because five and a half years of daily data provide a limited number of independent observations. Skewness lies between 0.09 and 0.62 and kurtosis between 11 and 29, and the denominator of the DSR penalises fat tails. H6 is rejected.

**What this does and does not say.** It is a statement about the evidence on the development period, not a proof that the system has no edge: carry's interval is above zero on every bar size, and the sealed final year, never examined, is the independent test that the correction cannot replace. It is also sensitive to the trial count: the deflated Sharpe stays above 0.95 only for two trials, so no plausible accounting of the number of variants would reach the threshold on these data.

**Mechanisms.** The decentralised system, every topology, link failures, an offline agent and an isolated liar all reproduce the centralised portfolio to within 0.002 Sharpe. Their costs are up to 2.7 times the messages and 4.5 times the capped rebalances (on a line). The proposal's trade-offs can be put in one line: decentralisation and resilience cost messages, safety costs return, and the market of agents buys protection against a bad agent.

## 16. Discussion

### 16.1 What the evidence supports

| RQ | Answer |
|---|---|
| RQ1 | Yes. The neighbour-only optimiser matches the hub to 0.002 Sharpe and 0.3% of final equity (Study 5), and the decentralised, resilient and supervised variants stay within 0.002 Sharpe of their references (Study 9). |
| RQ2 | Topology governs communication cost and not the outcome. The mixing rate predicts the iterations needed at 8 and 16 agents but not reliably at 4, and predicts better than algebraic connectivity. With a short budget, sparse graphs leave agents in disagreement and cost about 3% of final equity (Study 6). |
| RQ3 | Link failures and dropout are absorbed because the sum invariant survives them. W-MSR trimming fails inside the optimiser because it breaks that invariant; as a detector it isolates a consistent liar exactly and without false alarms on robust graphs, but not on a non-robust ring and not against random noise (Study 7). |
| RQ4 | The monitor shows the safety margin and found a stress window we had not predicted; derisk shortens the worst drawdown at a Sharpe cost of 0.02 to 0.20, with two failed gates; hold needs a better limit (Study 8). |
| RQ5 | Carry is a solid edge; momentum is marginal and concentrated in 2020 and 2021; reversal does not pay after costs. The market equals a fixed mix of good agents and beats it when one agent is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone (Studies 3, 4, 9). |

### 16.2 Interpretation

*Information limits what combination can achieve.* Across the preliminary study and Studies 2 and 3, the value of the system was bounded by the information in its agents: carry has an information coefficient of about 0.02 to 0.035, and it is the only agent whose profit survives costs and scale. Reversal has a larger IC and loses, because turnover is 45 to 91 times equity and impact is superlinear. This is the quantitative form of the preliminary finding that a real signal is not necessarily a tradable one.

*The invariant is the heart of the decentralised design.* Every result about decentralisation is a consequence of Proposition 1. Failures that keep the mixing doubly stochastic (link failures, dropout) leave the optimum intact; a mixing rule that does not (W-MSR trimming) destroys it. The same observation explains why a robust graph is needed for detection and not for convergence.

*Prices coordinate without exposing beliefs.* Agents interact only through prices of exposure, capital and trading. Pricing the volatility limit removes a cross-subsidy that a uniform rescale creates, and costing the net trade lets opposing agents cancel.

*Capital as a selection mechanism has a specific benefit.* It does not add return over a fixed mix of good agents because wealth shares move slowly relative to sampling noise. Its benefit is the rapid removal of a failing agent, and it is limited by the floor, which retains a small stake in every agent.

### 16.3 Negative and null results

The study yields several well-posed negative results. A funding forecast built from the premium index does not improve carry (Study 2). Timing momentum by bull and panic states does not help (Study 3). Reversal does not pay after costs, and its liquidity tercile pattern does not support the "less liquid" mechanism (Study 3). The lecture's W-MSR rule cannot be the averaging rule in the optimiser (Study 7). Hold on a fixed residual limit freezes honest solves (Study 8). The main system does not clear the deflated Sharpe threshold (Study 9). Each followed a pre-registered rule, and none was altered after the result.

### 16.4 Threats to validity

*Internal validity.* The system is complex and the volatility limit was initially mis-specified (Study 4). We mitigated this by cross-checks (baselines re-run on changed code, tables that reproduce their inputs) and by re-running all affected studies; residual specification errors cannot be excluded. The constraint violation of the first momentum run (Study 3) is a forking path: the correction followed a failed result and both runs count as trials. Several quantities (step sizes, the stopping test, the restart after an isolation) are evaluated centrally in the experiments.

*Construct validity.* The information coefficient of the momentum card (0.05) is an assumption, chosen by a mechanical check rather than from the literature, and it is not horizon-neutral. The impact coefficient, the one-million-dollar scale and the taker fee were fixed and not varied. A one-factor risk model underprices books that are not tightly neutral: reversal runs at 24% to 29% volatility against a 20% limit.

*External validity.* Five and a half years of data, mostly one bull market, from one exchange; momentum's profit is concentrated in 2020 and 2021. Only three hypotheses were tested in the final engine; four more (cross-sectional momentum, size and illiquidity, low volatility, a machine-learning trend model) were planned and not implemented, and two further steps of the carry ladder (a crowding term from open interest, a tail cap from high and low prices) were not run.

*Statistical validity.* Intervals are wide and the number of independent periods is limited, particularly on daily bars; a block bootstrap addresses autocorrelation but not regime change. The trial count in the deflated Sharpe ratio involves judgement about what counts as one trial, though the conclusion is insensitive to it.

*Computational limits.* The decentralised solver does work proportional to the number of agents; the sixteen-agent study took about three hours. Some real-data solves stop at the iteration cap even for the hub (21 to 27 of about 135 rebalances) with a small effect on profit.

### 16.5 Reproducibility

The software, the pre-registered rules, the result tables and the trial log are in the project repository. Raw data come from the exchange's public data archive and can be re-downloaded; the results are deterministic for fixed data and settings. The development procedure follows four rules throughout: no lookahead, a sealed final year, an append-only trial log, and pass or fail rules written before the runs.

## 17. Conclusion and future work

We designed and evaluated a multi-agent trading system in which heterogeneous hypothesis agents stake capital in a market, are coordinated by prices in a joint ADMM optimisation, can do so without a central node, tolerate link failures, dropout and a lying agent, and are monitored by formal safety specifications. The decentralised system reproduces the centralised one under every network and failure condition tested; failures cost communication and not return; the capital market protects against a bad agent; and the monitor shows where the system was in danger. The return claim is weaker: carry is a real edge and the combined system earns a Sharpe ratio of about 1.4 to 1.5 at its risk limit, but after correction for the number of variants tried, the development data alone cannot establish it. Pre-registered gates that failed are reported as failures; none was changed after the result was known.

**Future work.**
1. Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged.
2. Re-argue the hold supervisor's limit, for example by a rule that distinguishes a diverging solve from a slowly converging one, and lengthen the volatility-price search for fast bar sizes.
3. Add a second, alt-coin-market risk factor to close the risk-model gap for non-neutral books.
4. Test further established hypotheses, each with a card and rules written first, and run the remaining carry steps (crowding from open interest, a tail cap from high and low prices).
5. Move towards deployment: pre-agreed step sizes, a max-consensus stopping test, flooded isolation notices and a communication model with delays.

## References

*Prepared from memory of the primary sources. Verify details before submission.*

1. Boyd, S., Parikh, N., Chu, E., Peleato, B., Eckstein, J. (2011). Distributed optimization and statistical learning via the alternating direction method of multipliers. *Foundations and Trends in Machine Learning* 3(1).
2. Olfati-Saber, R., Murray, R. M. (2004). Consensus problems in networks of agents with switching topology and time-delays. *IEEE Transactions on Automatic Control* 49(9).
3. Xiao, L., Boyd, S., Lall, S. (2005). A scheme for robust distributed sensor fusion based on average consensus. *IPSN*.
4. Zhu, M., Martínez, S. (2010). Discrete-time dynamic average consensus. *Automatica* 46(2).
5. LeBlanc, H. J., Zhang, H., Koutsoukos, X., Sundaram, S. (2013). Resilient asymptotic consensus in robust networks. *IEEE Journal on Selected Areas in Communications* 31(4).
6. Chang, T.-H., Hong, M., Wang, X. (2015). Multi-agent distributed optimization via inexact consensus ADMM. *IEEE Transactions on Signal Processing* 63(2).
7. Kelly, J. L. (1956). A new interpretation of information rate. *Bell System Technical Journal* 35(4).
8. Beygelzimer, A., Langford, J., Pennock, D. (2012). Learning performance of prediction markets with Kelly bettors. *AAMAS* (arXiv:1201.6655).
9. Blume, L., Easley, D. (1992). Evolution and market behavior. *Journal of Economic Theory* 58(1). Evstigneev, I., Hens, T., Schenk-Hoppé, K. R. (2016). *Evolutionary Behavioral Finance*.
10. Maler, O., Nickovic, D. (2004). Monitoring temporal properties of continuous signals. *FORMATS*.
11. Donzé, A., Maler, O. (2010). Robust satisfaction of temporal logic over real-valued signals. *FORMATS*.
12. Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management* 15(3).
13. Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). Carry. *Journal of Financial Economics* 127(2).
14. He, S., Manela, A., Ross, O., von Wachter, V. (2022). Fundamentals of perpetual futures. arXiv:2212.06888.
15. Moskowitz, T., Ooi, Y. H., Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics* 104(2).
16. Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of Finance* 45(3).
17. Liu, Y., Tsyvinski, A. (2021). Risks and returns of cryptocurrency. *Review of Financial Studies* 34(6).
18. Tóth, B., Lempérière, Y., Deremble, C., de Lataillade, J., Kockelkoren, J., Bouchaud, J.-P. (2011). Anomalous price impact and the critical nature of liquidity in financial markets. *Physical Review X* 1, 021006.
19. Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
20. Harvey, C. R., Liu, Y., Zhu, H. (2016). … and the cross-section of expected returns. *Review of Financial Studies* 29(1).

## Appendix A. Settings used throughout

| Setting | Value |
|---|---|
| Development period | April 2020 to November 2025; final twelve months sealed |
| Universe | 243 coins over the period, about 63 members a day; point-in-time top 50 by 90-day median dollar volume, retained while within the top 75 |
| Tradability | trailing median daily dollar volume at least one million dollars; complete history window |
| Bars and rebalancing | daily (every 14 days), four-hourly (every 5 days), hourly (every 48 hours) |
| Costs | taker fee 5 basis points; square-root impact with coefficient 1; assets of one million dollars; capacity 5% of daily volume |
| Kelly fraction | 0.5 |
| Margin; gross cap; beta band | 3 times wealth; 3 times equity; 0.25 of equity |
| Volatility target | 20% a year, as a price on system variance; at most five re-solves; 2% band |
| Wealth floor | 2% of total wealth |
| Information coefficients (cards) | carry 0.02; momentum 0.05; reversal 0.02 |
| Calibration check | slope floor 0.5; window 52 rebalances; at least 1,500 observations; upper confidence bound |
| Belief sanity | volatility-standardised belief within 6 robust standard deviations of the agent's own history |
| Burn-in | 90 days |
| Solver tolerance | $10^{-6}$ relative (central); $10^{-8}$ (simulated topology and resilience studies) |
| Bootstrap | 7-day blocks, 500 draws, 90% interval |
| Detector | extreme in at least 90% of coordinates for 50 consecutive iterations; isolated by a majority of neighbours |
| STL limits | drawdown 15% over 365 days; volatility 1.05 times target; realised volatility 40% with 14-day recovery; residual $10^{-3}$ |
| Derisk | multiplier 1 above half of the drawdown budget, falling linearly to 0.2 at the limit |

## Appendix B. Correspondence with the project records

The project repository holds a numbered write-up for each experiment, with the exact command and the committed result tables. The studies of this report correspond to them as follows.

| Study | Section | Project experiment records |
|---|---|---|
| Preliminary study | 3 | 001 to 010 |
| 1. Simulated markets | 7 | 011 (data audit), 012 |
| 2. Single-agent baseline | 8 | 013, 014 |
| 3. Agent roster and market | 9 | 015, 016, 017 |
| 4. Risk-limit sensitivity | 10 | 018 |
| 5. Decentralised optimisation | 11 | 019 |
| 6. Topology and communication | 12 | 020 |
| 7. Resilience | 13 | 021 |
| 8. Safety monitoring | 14 | 022 |
| 9. Consolidated evaluation | 15 | 023 |

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
| Funding | a payment between longs and shorts every eight hours that keeps the contract near the spot price |
| Sharpe ratio | annualised return divided by annualised volatility |
| Net | after fees, price impact and funding |
| Alpha | the part of a return not explained by a benchmark |
| Information coefficient (IC) | rank correlation between a score and the next return |
| Kelly fraction | the share of the optimal bet size actually used (here one half) |
| Drawdown | fall from the previous peak |
| Ex-ante volatility | volatility predicted by the risk model before trading |
| Pre-registered gate | a pass or fail rule written before the runs it judges |
| Deflated Sharpe | the probability that a Sharpe of this size is real after allowing for the number of variants tried |
| Sealed holdout | data reserved for one final look: the last twelve months |
| W-MSR | the resilient consensus rule that discards extreme neighbour values |
| STL | signal temporal logic |
