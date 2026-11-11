# Resilient Decentralised Portfolio Consensus

*A multi-agent system for crypto perpetual futures: capital-staked hypothesis agents, ADMM coordination without a central node, resilience, and formal safety*

AI3403 Multi-Agent Systems, project report. Empirical evidence is drawn from the development period April 2020 to November 2025; the final twelve months of data were sealed before the study began and have not been examined. The system has not been run live.

## Abstract

A portfolio managed by several analysts is a multi-agent system: the agents hold different beliefs, share capital, risk limits and transaction costs, and the system must remain correct when a participant fails or misbehaves. We study how far the central node of such a system can be removed without changing the portfolio or its safety. The system has two levels. At the first, agents are documented trading hypotheses that stake capital on their own beliefs in a Kelly-bet market, so that wealth follows each agent's results. At the second, all stakes are converted into one portfolio by a convex optimisation solved by the alternating direction method of multipliers (ADMM), in which transaction costs on the net trade, margin, gross exposure, market-beta exposure and a volatility limit enter as prices. Replacing the central node by dynamic average consensus on a communication graph preserves the sum of the agents' positions exactly (Proposition 1); the same invariant explains which failures the decentralised solver absorbs (link failures, agent dropout; Proposition 2) and why the W-MSR trimming rule cannot be used inside it (Proposition 3), although the W-MSR test is an effective detector of a consistent liar on a robust graph. A signal-temporal-logic (STL) monitor with de-risking and hold supervisors provides formal safety.

All mechanisms are validated on simulated markets and evaluated against a centralised optimiser on five and a half years of Binance perpetual-futures data under pre-registered pass or fail rules. The decentralised system reproduces the centralised portfolio to within 0.002 Sharpe on every network topology, under 30% link failures, with the largest agent offline for four months, and with a lying agent isolated. Topology determines communication cost and not the outcome. The capital market equals a fixed-weight mix when all agents are good and outperforms it by about 0.9 Sharpe when one agent is bad. De-risking shortens the worst drawdown at a Sharpe cost of 0.02 to 0.20. The main system earns a net Sharpe ratio of 1.4 to 1.5 at a 20% volatility limit, but its deflated Sharpe ratio, corrected for 45 strategy variants, is about 0.1 against a threshold of 0.95: the mechanisms are verified, the return claim is not established on the development data alone.

**Keywords:** multi-agent systems, ADMM, consensus, resilient consensus, signal temporal logic, Kelly betting, perpetual futures, deflated Sharpe ratio.

## 1. Introduction

**1.1 Motivation.** Portfolio management has the structure of a multi-agent problem. Analysts, each with a distinct hypothesis about what drives returns, draw on a common pool of capital, operate under one risk budget, and trade in one market that charges them for impact. The system must remain correct when individual participants are wrong, offline or dishonest. The conventional design collects all forecasts at one node and solves one optimisation problem. This design has a single point of failure; it merges forecasts before their disagreement can be used, although disagreement is the reason for having several analysts; and it offers no handle on the questions that distributed computation studies directly: how fast agents agree, how much agreement costs in communication, and how agreement degrades under faults.

**1.2 Preliminary evidence.** The present design follows two earlier systems that were built and evaluated first: a trust-weighted consensus of simple forecasting agents with W-MSR resilient averaging, and an absolute-return engine with four cross-sectional agents, a Bitcoin-timing agent and five ways of combining them. Their evaluation fixed the requirements of the design (Table 1). Only funding carry earned a net return after costs on the perpetual futures universe; the other agents had negative net Sharpe ratios, and residual reversal had a positive rank information coefficient (0.025, 0.039, 0.049) but lost money, so a real signal was not a tradable one. No combiner beat the inverse-volatility average, and every combiner was worse than carry alone, because the agents combined carried no net information: combination multiplies information and does not create it. The coordination layer of the first system added little over a central solve (a Sharpe ratio of 0.81 against 0.90 for the naive average of its agents on its equity test universe), its consensus ADMM approached its one-node optimum after ten iterations, and the one clear multi-agent effect was resilience: with one compromised agent plain consensus lost 43% of its Sharpe ratio (0.81 to 0.46) and W-MSR with $F=1$ recovered most of it (0.74), through trimming of portfolios and not through capital flow. A temporal-logic shield that scaled finished portfolios towards cash halved violations at a small cost, but it acted after the optimiser and so re-traded the whole book, and its limits had to be derived from a mandate and be mutually consistent.

**Table 1.** Net Sharpe ratio of the preliminary absolute-return engine (daily, four-hourly, hourly bars).

| Agent or combiner | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Funding carry | 1.03 | 0.99 | 0.88 |
| Bitcoin timing | 0.57 | 0.46 | 0.80 |
| Cross-sectional momentum | −0.42 | −0.23 | −0.15 |
| Residual reversal | −0.68 | −1.11 | −1.24 |
| Size and liquidity | −0.14 | −0.22 | −0.32 |
| Equal-weight combiner | 0.22 | −0.09 | −0.09 |
| Inverse-volatility combiner | 0.27 | −0.04 | 0.18 |

**1.3 Problem statement and research questions.** We seek a system of agents that jointly trade a portfolio of cryptocurrency perpetual futures such that (i) agents with heterogeneous beliefs coordinate through local exchanges only and attain the portfolio of a centralised optimiser; (ii) transaction cost, shared limits and capital allocation are handled by prices on which the agents agree; (iii) the system remains correct under link failures, agent dropout and false messages; (iv) formal safety requirements are monitored and, when necessary, enforced; and (v) performance is assessed against a centralised benchmark with correction for the number of variants examined. This yields five research questions and six hypotheses (Table 2).

**Table 2.** Research questions and hypotheses.

| | Research question | Hypothesis |
|---|---|---|
| RQ1 | Does a neighbour-only optimiser reproduce the centralised portfolio on real data? | H1: the portfolios coincide up to solver tolerance on every connected graph |
| RQ2 | How do topology and communication budget affect convergence and result? | H2: iterations to convergence increase with the mixing rate $\varsigma$ of the graph; the result does not depend on topology |
| RQ3 | Does the decentralised consensus remain correct under link failures, dropout and a lying agent, and does W-MSR protect it? | H3: failures that preserve doubly stochastic mixing are absorbed; a consistent liar is isolated on a robust graph |
| RQ4 | Does an STL monitor with supervisors keep the system within its specifications in stress periods, and at what cost? | H4: de-risking reduces drawdown breaches; a hold rule prevents trading on corrupted solutions |
| RQ5 | What do the agents and the capital market add in money and risk, and does the result survive correction for multiple testing? | H5: the market is at least as good as a fixed mix and protects against a bad agent; H6: the main system's deflated Sharpe ratio is at least 0.95 |

**1.4 Contributions.** (i) A two-level architecture in which a capital-staked market of hypothesis agents sits above a joint ADMM over (agent, coin) cells, with shared limits and the cost of the net trade as prices (Sections 3.2 to 3.5). (ii) A neighbour-only version of this optimisation with a proof that it preserves the sum of the agents' positions, and a quantitative account of convergence in terms of the mixing rate of the graph (Sections 3.6, 5.5, 5.6). (iii) A unified account of resilience: one invariant explains which failures are absorbed (Proposition 2) and why W-MSR trimming is incompatible with the optimiser (Proposition 3), while the W-MSR test serves as a detector on robust graphs (Sections 3.7, 5.7). (iv) An STL monitor with two supervisors whose limits derive from a written risk mandate (Sections 3.8, 5.8). (v) A pre-registered, multiple-testing-aware evaluation in which failed gates and revisions of earlier results are reported (Sections 4, 5.4, 5.9).

**1.5 Organisation.** Section 2 reviews related work, describes the setting and fixes the notation used throughout. Section 3 presents the methods in the order in which they build on one another. Section 4 describes the experimental protocol, Section 5 the experiments and results, Section 6 discusses them, and Section 7 concludes.

## 2. Background and notation

### 2.1 Related work

*Consensus.* In average consensus, agents on a connected undirected graph repeatedly replace their value by a weighted average of their neighbours' values. With a doubly stochastic weight matrix $W$ every agent converges to the average of the initial values at a rate governed by the second-largest eigenvalue modulus of $W$ [2]. Metropolis weights give a doubly stochastic $W$ from the graph alone [3]. When the averaged quantity changes over time, dynamic average consensus lets each agent add its own change before mixing, so that the sum of the estimates tracks the sum of the true values [4]. Resilient consensus protocols such as W-MSR discard, coordinate by coordinate, up to $F$ neighbour values above and $F$ below an agent's own value before averaging; if at most $F$ agents are malicious and the graph is sufficiently robust, honest agents agree inside the range of the honest initial values [5]. Robustness is a property of the graph beyond connectivity.

*Distributed optimisation.* ADMM solves convex problems with separable structure by alternating local minimisations with a coordination step and a price update, and its dual variables are prices of the coupling constraints [1]. Variants run it over networks without a central node, by consensus on the dual variable [6] or on the shared variable. Robustness mechanisms designed for consensus on values do not obviously carry over to optimisation, where the quantity that must be preserved is a sum.

*Markets as learning mechanisms.* A Kelly bettor stakes the fraction of wealth that maximises expected log growth [7]. In a market of Kelly bettors wealth moves according to Bayes' rule and the market's aggregate belief is a wealth-weighted average [8]; evolutionary models of asset markets reach similar conclusions about which rules survive [9]. These results concern idealised betting markets; their transfer to leveraged positions in correlated assets with transaction costs is examined empirically here.

*Temporal-logic monitoring.* Signal temporal logic specifies properties of real-valued signals, and its quantitative semantics yields a robustness value, the signed distance from violation [10, 11]. Robustness supports monitoring (how close was the system to violating a requirement?) and supervision (act when the margin shrinks).

*Quantitative portfolio construction.* Expected returns can be written as the product of an information coefficient, a volatility and a standardised score [12]. A perpetual future pays funding between longs and shorts, so its expected return decomposes into carry and expected price change [13, 14]. Time-series momentum [15] and short-term reversal [16] are established effects, with replicated evidence in crypto assets mainly for the former [17]. Square-root market impact is a standard description of the cost of trading [18].

*Multiple testing in backtests.* The best of many backtests overstates the expected Sharpe ratio of a strategy. The deflated Sharpe ratio corrects the observed value for the number of trials, the dispersion of their results and the non-normality of returns [19]; related work provides multiple-testing thresholds for factor discovery [20].

### 2.2 Setting

**Market and data.** The market is Binance USD-M perpetual futures: contracts on coins that never expire. A long position pays, and a short receives, a funding payment (every eight hours, occasionally at shorter intervals when the funding cap binds) that anchors the contract to the spot price. For an interval with time-weighted average premium $\Pi$ over the index price, the funding rate is
$$\mathrm{FR}=\Pi+\operatorname{clamp}\!\big(\iota-\Pi,\ \pm\epsilon\big),\qquad\iota=0.01\%\ \text{per 8 hours},\ \ \epsilon=0.05\%,\tag{1}$$
and on Bitcoin (89 events, one month of one-minute premium data) this reproduced actual funding with correlation 0.995 and mean absolute error $9\times10^{-7}$, about 1% of the typical level; an equal-weighted average of the premium was less accurate (correlation 0.936). The system uses open, high, low and close prices, volume, taker volume, funding events, the premium index, spot prices and open interest, in bars of one day, four hours and one hour; funding is always summed per bar from event times. Open interest and long-short data exist only from late 2020 (Bitcoin) or late 2021 (most coins) and have gaps, and liquidation data are not public.

**Universe.** Point-in-time and free of survivorship bias: a coin enters when its rank by the 90-day median daily dollar volume, computed strictly before the day, is within the top 50, stays while within the top 75, and the ranking is refreshed every 30 days. Delisted coins are included. In total 243 coins appear, about 63 on a typical day. A coin is tradable at a rebalance only if its trailing median daily dollar volume is at least one million dollars and its history window is complete. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded.

**Rebalancing and information.** The system rebalances every 14 days on daily bars, every 5 days on four-hourly bars and every 48 hours on hourly bars; $H$ denotes the number of bars in a holding period. Every quantity used at a rebalance at time $t$ depends only on information strictly before $t$, a tested invariant.

**Transaction costs.** Trading $d_a$ in coin $a$ costs
$$C_a(d_a)=c_f\,\lvert d_a\rvert+\psi_a\,\lvert d_a\rvert^{3/2},\qquad\psi_a=\frac{k\,\sigma_a}{\sqrt{\mathrm{ADV}_a}},\tag{2}$$
with a taker fee $c_f=5$ basis points, daily volatility $\sigma_a$, average daily dollar volume $\mathrm{ADV}_a$ and impact coefficient $k=1$ (an assumption). The second term is square-root impact: slippage per dollar traded is $k\sigma_a\sqrt{\lvert d_a\rvert/\mathrm{ADV}_a}$. The total $C(d)=\sum_aC_a(d_a)$ is convex. Assets under management are one million dollars and a position may be at most 5% of a coin's daily volume.

### 2.3 Notation

All symbols are defined once, in Table 3, and keep the same meaning throughout the report.

**Table 3.** Notation.

| Symbol | Meaning |
|---|---|
| $\mathcal{A}=\{1,\dots,M\}$, $\mathcal{C}=\{1,\dots,N\}$ | agents; tradable coins; $\mathcal{U}_i\subseteq\mathcal{C}$ is the coin set allowed to agent $i$ |
| $t$, $k$, $H$, $P$ | rebalance time; iteration index; bars per holding period; bars per year |
| $r\in\mathbb{R}^N$, $\sigma_H\in\mathbb{R}^N$ | coin returns over a holding period; their volatilities |
| $\beta\in\mathbb{R}^N$, $\Sigma=\operatorname{diag}(d)+\nu\,\beta\beta^\top$ | market betas; return covariance over a holding period (idiosyncratic variances $d$, one market factor with variance $\nu$) |
| $z_i\in\mathbb{R}^N$, $\theta_i$ | score of agent $i$, oriented so that its card predicts a positive correlation with the next return; information coefficient fixed by its card |
| $\mu_i=\theta_i\,\sigma_H\odot z_i$ | belief of agent $i$: expected net return of a unit position over a holding period ($\odot$ is the elementwise product) |
| $x_i\in\mathbb{R}^N$, $X=\sum_ix_i$, $h$ | position of agent $i$ (in units of initial equity); net position; net position held before the rebalance |
| $V_i$, $E=\sum_iV_i$, $q$, $\gamma_i=1/(qV_i)$, $\omega$ | wealth of agent $i$; total equity; Kelly fraction ($q=\tfrac12$); risk aversion; wealth floor ($\omega=0.02$) |
| $C(\cdot)$, $c_f$, $\psi_a$ | trading cost (2); fee rate; impact coefficient of coin $a$ |
| $\mathcal{X}_i$, $\mathcal{S}$ | constraint set of agent $i$; constraint set of the system |
| $\lambda$, $\rho$, $u$, $\bar x$, $\zeta$ | price on system variance; ADMM penalty; scaled price of the net position; average position; system-step variable |
| $\mathcal{G}=(\mathcal{A},\mathcal{E})$, $W$, $g$ | communication graph; doubly stochastic mixing matrix; gossip rounds per iteration |
| $\varsigma=\lvert\lambda_2(W)\rvert$ | mixing rate: second-largest eigenvalue modulus of $W$ (smaller is faster) |
| $s_i$, $\zeta_i$, $u_i$ | agent $i$'s local estimate of the average position, system-step variable and price (decentralised algorithm) |
| $F$, $\pi_{ij}$, $\vartheta$, $T_d$ | W-MSR trimming parameter; share of coordinates in which neighbour $j$ is extreme for agent $i$; detection threshold (0.9); persistence (50 iterations) |
| $\varrho_\varphi(t)$, $\mathrm{DD}_t$, $\hat\sigma_t$, $\sigma^\ast_t$, $m_t$, $\kappa(m_t)$ | STL robustness of specification $\varphi$; drawdown; ex-ante volatility; volatility target in force; remaining share of the drawdown budget; de-risking multiplier |
| $\mathrm{SR}$, $\alpha$, $\beta_{\mathrm{s}}$, $\mathrm{rIC}$ | annualised net Sharpe ratio; intercept and slope of a regression on Bitcoin's return; rank information coefficient of a score |
| $\widehat{\mathrm{SR}}$, $g_3$, $g_4$, $V_{\mathrm{SR}}$, $L$, $T$ | per-period Sharpe ratio of the best strategy; skewness; kurtosis; variance of trial Sharpe ratios; number of trials; number of periods (Section 4.4) |

### 2.4 Formal problem statement

At each rebalance the agents hold beliefs $\{\mu_i\}_{i\in\mathcal{A}}$ and wealths $\{V_i\}$. The *centralised problem* (P) of Section 3.4 maps them to positions $\{x_i^\ast\}$ and a net position $X^\ast$. The *decentralised problem* is to design a procedure in which each agent $i$ uses only its own data and messages from neighbours in $\mathcal{G}$ and obtains $X^\ast$ (RQ1, RQ2), under a fault model in which edges fail, agents drop out or send false values (RQ3), and such that the resulting portfolio process satisfies a set of STL specifications on volatility, drawdown, recovery and solver health (RQ4). The *performance criterion* is the annualised net Sharpe ratio $\mathrm{SR}=\sqrt{P}\,\bar y/s_y$ against zero, with $\bar y$ and $s_y$ the mean and standard deviation of per-bar net returns $y_t$, evaluated with correction for multiple testing (RQ5).


## 3. Methods

The methods are presented in the order in which each builds on the previous one: hypothesis agents with calibrated beliefs (3.2); a capital market that allocates wealth among agents (3.3); a joint optimisation that turns all stakes into one portfolio (3.4, 3.5); its decentralised form (3.6); the fault model and defences for the decentralised form (3.7); and formal safety (3.8). Section 3.1 states the design principles that the preliminary evidence imposes, and Figure 1 summarises the resulting architecture.

### 3.1 Design principles

The findings of Section 1.2 give six requirements, each met by one of the methods below.

| Requirement | Source | Method |
|---|---|---|
| R1. Agents embody distinct, documented hypotheses with explicit expected edge | combination cannot create information | hypothesis agents with a card (3.2) |
| R2. Relative capital follows results, with a defence against over-confidence | coordination layer added little | Kelly-staked capital market with a floor and a calibration check (3.3) |
| R3. Costs and shared limits are inside the optimisation, and the multi-agent structure does something a central solve does not | signal not equal to tradable signal; shield re-traded the book | joint convex problem over (agent, coin) cells; cost on the net trade; priced limits (3.4, 3.5) |
| R4. The optimiser runs without a central node and degrades gracefully | the course proposal | decentralised ADMM and a fault model (3.6, 3.7) |
| R5. Safety is formal, monitored over time, and acts through the optimiser | shield placement | STL monitor and supervisors that act through the volatility price (3.8) |
| R6. Conclusions are robust to the number of variants tried | combiners had no significant edge after correction | sealed holdout, trial log, deflated Sharpe, pre-registration (Section 4) |

Consensus on beliefs between agents (the W-MSR layer of the first system) is not part of the core: a trimmed mean or a belief-magnitude check gives comparable protection with less machinery, and Section 3.7 shows that the role of W-MSR in the present design is different.

### 3.2 Hypothesis agents and calibrated beliefs

**Definition 1 (hypothesis agent).** A hypothesis agent $i$ is specified by a *card* written before any test: the claim, the mechanism, the allowed coin set $\mathcal{U}_i$, whether the book is market-neutral, a score $z_i$ oriented so that the claim predicts a positive correlation with the next return, an information coefficient $\theta_i>0$ (the expected rank correlation of the score with the next return), and a switch-off rule.

*Belief.* If the score has unit variance across coins and is the only information, the conditional mean of the return of coin $a$ is $\theta_i\sigma_{H,a}z_{ia}$ (the fundamental law of active management [12]). The belief is therefore
$$\mu_{ia}=\theta_i\,\sigma_{H,a}\,z_{ia}.\tag{3}$$
The size $\theta_i$ is fixed by the card and not estimated from recent results. The reason is statistical and is stated as a remark because it determines the design.

**Remark 1 (a trailing estimate of $\theta_i$ is too noisy to size a bet).** Let a hypothesis have a per-period rank information coefficient with mean $\theta$ and standard deviation $s_\theta$ across periods. An exponentially weighted estimate with $n_{\mathrm{eff}}$ effective observations has standard error $s_\theta/\sqrt{n_{\mathrm{eff}}}$. For funding carry, $\theta\approx0.035$ with a $t$-statistic of 2.2 over 141 periods, so $s_\theta\approx0.035\sqrt{141}/2.2\approx0.19$; with at most about 18 effective observations the standard error is about 0.045, larger than the quantity estimated. A belief proportional to such an estimate injects noise of the order of the signal into the stake and changes sign frequently (the hit rate of the per-period coefficient is only 53%). Section 5.2 verifies this empirically.

Evidence therefore acts only through a *kill rule*. Let $\overline{\mathrm{rIC}}_n$ and $s_n$ be the mean and standard deviation of the agent's realised per-period rank information coefficient over $n$ periods and $\tau_n=\overline{\mathrm{rIC}}_n/(s_n/\sqrt n)$. If $n\ge20$ and $\tau_n<-2$ the agent's belief is set to zero; the agent never takes the opposite position. For an agent holding few coins the same rule is applied to the pooled slope of returns on the score. Relative stakes of agents are decided by wealth (Section 3.3).

*The agents.* Three hypotheses are implemented.

| Agent | Score $z_{ia}$ | Coins | Neutral | $\theta_i$ |
|---|---|---|---|---|
| **Funding carry** | rank-Gaussian of $-\overline{\mathrm{FR}}_{14\text{d}}(a)$: long low funding, short high funding | all tradable | yes | 0.02 |
| **Time-series momentum** | $\operatorname{clip}\!\big(\sum_{\tau\in30\text{d}}r_{a\tau}\big/(\operatorname{sd}(r_a)\sqrt L),-2,2\big)$ | Bitcoin, Ethereum | no (owns net exposure) | 0.05 (assumed) |
| **Residual reversal** | rank-Gaussian of $-\sum_{\tau\in7\text{d}}e_{a\tau}\big/(\operatorname{sd}(e_a)\sqrt n)$, $e_{a\tau}=r_{a\tau}-\hat\beta_ar^{\mathrm{BTC}}_{\tau}$ | all tradable | yes | 0.02 |

The rank-Gaussian transform is $z_a=\Phi^{-1}\big((\operatorname{rank}_a-\tfrac12)/N\big)$. Carry rests on funding being a transfer from the crowded side, so that a perpetual's expected return is its carry plus its expected price change; momentum on slow diffusion of information; reversal on temporary price pressure from demand for immediacy. The momentum magnitude $\theta=0.05$ is an assumption fixed by a mechanical check that uses no profit: at $\theta=0.10$ the agent's ex-ante Sharpe ratio at its own belief on daily bars was 1.17, more than a two-coin time-series strategy can be expected to deliver, while $\theta=0.05$ gave about 0.6.

### 3.3 Level 1: the capital-staked market

*Kelly sizing.* For one asset with expected return $\mu$ and variance $\sigma^2$ the log-growth of wealth when a fraction $f$ is invested is approximately
$$G(f)=f\mu-\tfrac12f^2\sigma^2,\tag{4}$$
maximised at $f^\star=\mu/\sigma^2$ and equal to zero at $2f^\star$: over-confident agents are penalised by the mathematics. The system uses half the Kelly size, $q=\tfrac12$. Minimising $-\mu x+\tfrac{\gamma}{2}\sigma^2x^2$ gives $x=\mu/(\gamma\sigma^2)$, so a stake $qV\mu/\sigma^2$ corresponds to the risk aversion $\gamma=1/(qV)$ used in (6).

*Accounts and wealth.* The system trades the sum of the agents' positions. Each agent has an *account* that earns the profit and loss of its own positions less its allocated share of cost and funding, so that accounts add up exactly to the real result. Wealth compounds with the account return $y_i(t)$:
$$V_i(t+1)=\max\!\Big(V_i(t)\,\big(1+y_i(t)\big),\ \omega\textstyle\sum_jV_j(t)\Big),\qquad\omega=0.02.\tag{5}$$
The floor keeps a failed agent alive so that the market can still reallocate, and a loss beyond an agent's wealth is borne by the others (limited liability). Beliefs are not averaged between agents; they act only through the wealth that backs them, so that capital moves to the agents whose beliefs pay, as in prediction markets of Kelly bettors [8].

*Protections against over-confidence.* Wealth dynamics alone select too slowly to prevent ruin (Section 5.1), so two further protections are used. The system limits of Section 3.4 bound every agent's stake. An agent-level *calibration check* regresses realised returns on the agent's past beliefs over the last 52 rebalances and, once at least 1,500 (period, coin) observations exist, scales the agent's Kelly fraction down (by a factor between 1 and 0.2) when the slope falls below 0.5. Because a belief of the size in (3) gives a slope with a standard error above 1 over 3,000 observations, the check uses the upper confidence bound of the slope (slope plus 1.645 standard errors) and so acts only on demonstrable over-confidence. A *belief-sanity check* sets a belief to zero when it is not a finite number or when its volatility-standardised value exceeds six robust standard deviations of the agent's own past beliefs.

### 3.4 Level 2: the joint portfolio problem

**Definition 2 (cell).** A cell is a pair (agent $i$, coin $a$): the sub-agent that manages one coin for one agent.

At each rebalance the system solves one convex problem over all positions:
$$\min_{x_1,\dots,x_M}\ \sum_{i=1}^{M}\Big[-\mu_i^\top x_i+\tfrac{\gamma_i}{2}\,x_i^\top\Sigma\,x_i\Big]+C\big(X-h\big)+\tfrac{\lambda}{2}\,X^\top\Sigma X\qquad\text{s.t.}\quad x_i\in\mathcal{X}_i\ \ (i\in\mathcal{A}),\quad X=\textstyle\sum_ix_i\in\mathcal{S}.\tag{6}$$
The agent sets $\mathcal{X}_i$ collect the constraints of one agent: allowed coins ($x_{ia}=0$ for $a\notin\mathcal{U}_i$); capacity ($\lvert x_{ia}\rvert\le u_a$ with $u_a$ equal to 5% of the coin's daily volume); margin ($\lVert x_i\rVert_1\le3V_i$); and, for market-neutral agents, dollar and beta neutrality ($\mathbf1^\top x_i=0$, $\beta^\top x_i=0$). The system set $\mathcal{S}$ collects the constraints of the whole system: a gross cap $\lVert X\rVert_1\le3E$ and a market-beta band $\lvert\beta^\top X\rvert\le0.25E$.

Three features of (6) carry the multi-agent content.

*Cost on the net trade.* $C$ acts on $X-h$ and not on each $x_i$: two agents trading opposite ways in the same coin cancel and pay only for the difference, so that the cost of coordination is visible to the optimiser.

*The volatility limit as a price.* The last term of (6) prices system variance. After each solve the annual ex-ante volatility of the net position, $\hat\sigma=\sqrt{P\,X^\top\Sigma X/H}$, is compared with the 20% target. If it exceeds the target by more than 2%, $\lambda$ is raised and (6) is solved again (at most five times); if it is more than 2% below the target and $\lambda>0$, $\lambda$ is lowered. The agent that adds risk then pays for it. In a test at equal total volatility the priced limit left the market-neutral agent 97% of its unconstrained position (0.073 against 0.075), where a uniform shrink of all positions left it 45% (0.034): a uniform rescale makes the agent that adds no variance subsidise the one that does.

*Prices as the coordination signal.* Problem (6) is convex, so it has multipliers. Those of the neutrality, beta, margin, gross, capacity and net-trade terms are prices of exposure, of scarce capital, of scarce gross exposure and of trading. Each agent reacts to prices and never needs another agent's belief.

### 3.5 Solution by sharing ADMM

Write $f_i(x_i)=-\mu_i^\top x_i+\tfrac{\gamma_i}{2}x_i^\top\Sigma x_i+\iota_{\mathcal{X}_i}(x_i)$ and $g(X)=C(X-h)+\tfrac\lambda2X^\top\Sigma X+\iota_{\mathcal{S}}(X)$, with $\iota$ the indicator function of a set. Problem (6) is then the sharing problem $\min\sum_if_i(x_i)+g(\sum_ix_i)$. With $\bar x=\tfrac1M\sum_ix_i$, penalty $\rho>0$ and scaled price $u$, ADMM iterates [1, Section 7.3]:
$$x_i^{k+1}=\arg\min_{x_i}\ f_i(x_i)+\tfrac\rho2\big\lVert x_i-x_i^k+\bar x^k-\zeta^k+u^k\big\rVert^2\quad(\text{each agent}),\tag{7}$$
$$\zeta^{k+1}=\arg\min_{\zeta}\ g(M\zeta)+\tfrac{M\rho}2\big\lVert\zeta-\bar x^{k+1}-u^k\big\rVert^2\quad(\text{system step}),\tag{8}$$
$$u^{k+1}=u^k+\bar x^{k+1}-\zeta^{k+1}\quad(\text{price update}).\tag{9}$$
Because (6) is convex the iteration converges, and $\rho u$ is the price of the net position in each coin. In the *hub* form one node computes $\bar x$, (8) and (9) and returns $u$ to the agents.

*The cost step.* The proximal operator of $C_a$ has a closed form. For a target trade $\delta_a$ (the point towards which the quadratic penalty pulls) the minimiser of $C_a(d)+\tfrac\rho2(d-\delta_a)^2$ is $d=0$ if $\lvert\delta_a\rvert\le c_f/\rho$, and otherwise $d=\operatorname{sign}(\delta_a)\,\xi_a^2$, where $\xi_a$ is the positive root of $\rho\xi^2+\tfrac32\psi_a\xi+(c_f-\rho\lvert\delta_a\rvert)=0$:
$$\xi_a=\frac{-\tfrac32\psi_a+\sqrt{\tfrac94\psi_a^2-4\rho\,(c_f-\rho\lvert\delta_a\rvert)}}{2\rho}.\tag{10}$$
This follows from the first-order condition with $\xi=\sqrt{\lvert d\rvert}$. The constrained agent step needs the multipliers of the margin, gross and beta constraints, found by nested bracketed one-dimensional root searches, and an exact projection onto an $\ell_1$-ball with box constraints. Termination uses primal and dual residuals relative to the size of the positions (tolerance $10^{-6}$). At this tolerance the net position is accurate to about $10^{-6}$ while the split of the net position between agents is accurate to about 9%, so per-agent accounts carry that noise and the system result does not. A one-node general-purpose solver serves as the reference for verification.

### 3.6 Removing the hub: decentralised ADMM

In the hub form three quantities are global: the average position $\bar x$, the system step $\zeta$ and the price $u$. In the decentralised form agent $i$ holds its own copies: an estimate $s_i$ of the group average, a system-step variable $\zeta_i$ and a price $u_i$. The system data (cost parameters, limits) are public. Let $\mathcal{G}=(\mathcal{A},\mathcal{E})$ be undirected and let $W$ be its *Metropolis* mixing matrix,
$$W_{ij}=\frac1{1+\max(\deg i,\deg j)}\ \ \text{for }\{i,j\}\in\mathcal{E},\qquad W_{ii}=1-\sum_{j\ne i}W_{ij},\tag{11}$$
which is symmetric with rows summing to one, hence doubly stochastic. One iteration is:

> **Algorithm 1 (decentralised ADMM, one iteration).** Initialise $s_i=x_i^0$.
> 1. Each agent $i$ solves its local step (7) against its own price $u_i$, obtaining $x_i^{\mathrm{new}}$.
> 2. *Tracking:* $s\leftarrow W^{g}\big(s+x^{\mathrm{new}}-x^{\mathrm{old}}\big)$, mixing the stacked estimates over $g$ gossip rounds.
> 3. Each agent solves the system step (8) from its own estimate $s_i$, obtaining $\zeta_i$.
> 4. *Price:* $u\leftarrow W^{g}\big(u+s-\zeta\big)$.

<!-- -->

> **Proposition 1 (sum invariant).** For every iteration $k$, $\sum_is_i^k=\sum_ix_i^k$.
>
> *Proof.* Let $\mathbf1$ be the all-ones vector. Since $W$ is doubly stochastic, $\mathbf1^\top W^g=\mathbf1^\top$. Hence $\mathbf1^\top s^{k+1}=\mathbf1^\top(s^k+x^{k+1}-x^k)=\mathbf1^\top s^k+\mathbf1^\top x^{k+1}-\mathbf1^\top x^k$. With $s^0=x^0$ the claim follows by induction. $\square$

<!-- -->

> **Corollary 1.** If Algorithm 1 reaches a fixed point, then $x^{k+1}=x^k$; mixing drives every $s_i$ to the common value $\tfrac1M\sum_is_i=\bar x$ (Proposition 1), and the prices agree for the same reason. The fixed point satisfies the optimality conditions of (7) to (9), hence it is the optimum of (6). On the complete graph with exact mixing Algorithm 1 coincides with the hub algorithm.

*Why both mixing steps are necessary.* Proposition 1 requires each agent's change of position to enter *before* the doubly stochastic mixing; mixing first ($s\leftarrow Ws+\Delta x$) leaves each estimate off by its own last change, and on development problems it failed when the gross cap bound. The prices must also be mixed: otherwise the agents settle on different prices and stop at a wrong point. Both observations were obtained by ablation on random problems with three and eight agents and are consistent with the proposition.

*Convergence and cost.* With no new input, one gossip round multiplies the disagreement $s-\mathbf1\bar x^\top$ by at most $\varsigma=\lvert\lambda_2(W)\rvert$, so the number of rounds needed to reduce it by a factor $\eta$ is
$$n_\eta=\frac{\ln\eta}{\ln\varsigma}.\tag{12}$$
For $\eta=\tfrac1{10}$ this is 6.0 rounds for $\varsigma=0.68$, 10.3 for 0.80, 18.0 for 0.88, 44.9 for 0.95 and 229 for 0.99. Messages per rebalance equal (iterations)$\,\times g\times2\lvert\mathcal{E}\rvert$. The stopping test requires, besides the usual residuals, agreement between the agents' estimates and between their prices: without it a run can stop while agents still disagree by about 10%. Over-relaxation, used in the hub form, oscillated under slow mixing and is switched off.

*Elements that remain central in the experiments.* The step sizes use the mean risk aversion, a number the agents could agree on before trading; the stopping test is evaluated by the simulator, where a deployment would run a max-consensus over the graph's diameter; and the restart after an isolation (Section 3.7) is applied to all agents at once, where a deployment would flood it over the graph.

### 3.7 Resilience

**Fault model.** Three faults are considered: (a) *link failure*, each edge being down independently with probability $q_\ell$ in each gossip round; (b) *dropout*, an agent leaving the system; (c) a *misbehaving agent*, which sends values that differ from those its algorithm would send.

> **Proposition 2 (failures that preserve double stochasticity are absorbed).** Suppose that in every gossip round the mixing matrix used is doubly stochastic. Then Proposition 1 and Corollary 1 hold unchanged.
>
> *Proof.* The proof of Proposition 1 uses only $\mathbf1^\top W_{(g)}=\mathbf1^\top$ for the matrix applied in each round. $\square$

*Link failures.* The Metropolis weights (11) are recomputed on the edges that are up. The recomputed matrix is symmetric with unit row sums, hence doubly stochastic, so by Proposition 2 the optimum is still reached: failures cost iterations and not correctness. *Dropout.* The agent's positions are closed and the others solve (6) without it on the graph without its node; Proposition 2 applies to the smaller system. The centralised solver can handle dropout as well; what differs is that a hub is itself a single point of failure.

*W-MSR as an averaging rule.* In W-MSR each agent discards up to $F$ neighbour values strictly above its own (the largest) and up to $F$ strictly below (the smallest) and averages the retained values.

<!-- -->

> **Proposition 3 (trimmed mixing does not preserve the sum).** There exist initial values on the complete graph for which one round of W-MSR with $F=1$ and equal weights on retained values does not preserve $\sum_is_i$.
>
> *Proof.* Take three agents with values $(0,1,10)$. Agent 1 (value 0) discards 10 and retains $\{0,1\}$, giving $0.5$. Agent 2 (value 1) discards both 10 and 0 and keeps $1$. Agent 3 (value 10) discards 0 and retains $\{10,1\}$, giving $5.5$. The sum falls from $11$ to $7$. $\square$

The weight matrix implied by trimming depends on the data and is generally not doubly stochastic, so the sum invariant is lost, the agents agree on a value that is not the average of the positions, and the fixed point is not the optimum of (6). Resilient consensus guarantees agreement inside the range of honest values; optimisation needs the exact sum. The two requirements are incompatible, and W-MSR is therefore not used as the averaging rule (Section 5.7 confirms this empirically).

*W-MSR as a detector.* The same test can be used to *identify* a liar. At iteration $k$ agent $i$ compares each neighbour's values $v_j$ (the estimate and the price) with its own. For coordinate $c$ let $e_{ijc}=1$ if $v_{jc}$ is the largest value above $v_{ic}$ or the smallest below it, that is, the value W-MSR would discard first, and define
$$\pi_{ij}=\frac1n\sum_{c=1}^{n}e_{ijc}.\tag{13}$$
Agent $i$ *flags* $j$ when $\pi_{ij}\ge\vartheta=0.9$ for both estimates and prices for $T_d=50$ consecutive iterations. An agent flagged by more than half of its neighbours is *isolated* and the others restart without it. Plain averaging is used otherwise, so with no attacker the solver is exactly Algorithm 1. The parameters $(\vartheta,T_d,\text{majority})$ were fixed on development problems before the evaluation. A consistent offset places a liar's value beyond the honest values in nearly every coordinate, which is what $\pi_{ij}$ measures; a liar whose values stay inside the honest range is not expected to be detected. For $F=1$ the guarantees of W-MSR require the graph to be $(2,2)$-robust [5]. A ring is connected but not $(2,2)$-robust, whereas a ring in which each agent is linked to its two nearest neighbours on each side ("ring2") is sparse and robust.

### 3.8 Safety: STL monitor and supervisors

For a real-valued signal $y$ and a limit $c$, the predicate $y\ge c$ has robustness $\varrho(t)=y(t)-c$: positive means satisfied by that margin, negative violated by that much. The operators are
$$\varrho(\mathbf G_{[a,b]}\varphi,t)=\min_{t'\in[t+a,t+b]}\varrho(\varphi,t'),\qquad\varrho(\mathbf F_{[a,b]}\varphi,t)=\max_{t'\in[t+a,t+b]}\varrho(\varphi,t'),\tag{14}$$
(always and eventually). Let $\hat\sigma_t$ be the ex-ante volatility at a rebalance, $\sigma^\ast_t$ the target in force, $E_t$ the equity, $\mathrm{DD}_t=E_t/\max_{s\in[t-365\mathrm d,t]}E_s-1$ the drawdown, and $\sigma^{\mathrm{real}}_t$ the realised 30-day volatility. The specifications are listed in Table 4.

**Table 4.** STL specifications and limits.

| Specification | Statement | Limit and mandate |
|---|---|---|
| $\varphi_{\mathrm{vol}}$ | $\mathbf G\,(\hat\sigma_t\le1.05\,\sigma^\ast_t)$ | 5% tolerance; the priced limit's own search accepts 2% |
| $\varphi_{\mathrm{dd}}$ | $\mathbf G\,(\mathrm{DD}_t\ge-0.15)$ | 15% over 365 days: about half of what an equity market lost in its worst stretch within a year |
| $\varphi_{\mathrm{rvol}}$ | $\mathbf G\big(\sigma^{\mathrm{real}}_t>0.4\Rightarrow\mathbf F_{[0,14\mathrm d]}\,\sigma^{\mathrm{real}}_t\le0.4\big)$ | 40% and 14 days: twice the 20% target |
| $\varphi_{\mathrm{solve}}$ | $\mathbf G\,(\text{relative residual}\le10^{-3})$ | a portfolio off by 0.1% of its size is immaterial against one rebalance's fee; clean central solves reach $10^{-6}$ |

All limits come from a written risk mandate fixed before any run; none is chosen by comparing returns. The *monitor* records $\varrho_\varphi(t)$ for every specification and bar and summarises it over three stress windows (May to July 2021; the May 2022 Luna collapse; November 2022 to January 2023, the FTX collapse). Two *supervisors* act on the robustness and are off by default.

*Derisk.* Let $m_t=(\mathrm{DD}_t+0.15)/0.15\in[0,1]$ be the share of the drawdown budget remaining. The volatility target is multiplied by
$$\kappa(m_t)=\begin{cases}1,&m_t\ge\tfrac12,\\0.2+1.6\,m_t,&0\le m_t<\tfrac12,\end{cases}\tag{15}$$
so that de-risking starts with half the budget left and never goes below 20% of the target. It acts through the volatility price of Section 3.4, so (6) is re-solved with the tighter target and the costs included; it is not a post-hoc rescale of a finished portfolio.

*Hold.* If the solve is unsafe (it did not converge and its relative residual exceeds $10^{-3}$) the system trades nothing and keeps its positions, a fail-safe against a corrupted solution.


## 4. Experimental protocol

**4.1 Data and period.** The development period runs from April 2020 to November 2025; agents use a ninety-day warm-up before trading. The last twelve months are sealed: they are to be reported once, after the design is frozen, and no tuning, and no statistic that includes them, is permitted before then. All settings of Sections 2.2 and 3 are fixed in advance and none is tuned on returns (Appendix A).

**4.2 Reference systems.** Every decentralised, resilient or supervised variant is compared with the centralised optimiser with the same agents, data, costs and limits, or with the reference that is correct for the failure considered (for example, the centralised system without an agent that is offline). Multi-agent mechanisms are also compared with fixed-weight blends of the agents' stand-alone returns.

**4.3 Pre-registration and disclosure.** For each experiment the pass or fail rules, with their thresholds, and where stated the expected outcome, were written before the runs. Amendments carry their date and state whether any result had been seen. Rejected variants remain in the record and in the trial count. Two revisions affected earlier results and are reported where they occur: in E3 an agent's positions were found to violate its declared coin set and the constraint was enforced (both runs count as trials); in E4 the normalisation of the volatility limit was found to use initial and not current equity, and every affected experiment was repeated. Values obtained before the second revision are marked † and used only for comparisons within one experiment.

**4.4 Statistics.** Intervals are 90% moving-block bootstrap intervals: blocks of seven days are resampled with replacement ($B=500$ draws) and the 5th and 95th percentiles of the statistic are reported. Comparisons between two strategies resample the same blocks for both (a paired difference). To separate skill from market exposure, a strategy's net return is regressed on Bitcoin's, $y_t=\alpha+\beta_{\mathrm s}\,y^{\mathrm{BTC}}_t+e_t$, and also on Bitcoin's and the carry agent's, and the annualised $\alpha$ is reported with its block-bootstrap interval. The skill of a score is its rank information coefficient $\mathrm{rIC}$: the Spearman correlation between the score and the next return across coins, averaged over rebalances, with its $t$-statistic.

*Deflated Sharpe ratio.* Let $\widehat{\mathrm{SR}}$ be the per-period Sharpe ratio of the best strategy over $T$ periods with skewness $g_3$ and kurtosis $g_4$ (3 for a normal distribution), $V_{\mathrm{SR}}$ the variance of the Sharpe ratios of the $L$ trials, and $\gamma_{\mathrm E}\approx0.5772$ Euler's constant. Then [19]
$$\mathrm{SR}_0=\sqrt{V_{\mathrm{SR}}}\Big[(1-\gamma_{\mathrm E})\,\Phi^{-1}\!\big(1-\tfrac1L\big)+\gamma_{\mathrm E}\,\Phi^{-1}\!\big(1-\tfrac1{Le}\big)\Big],\qquad
\mathrm{DSR}=\Phi\!\left(\frac{(\widehat{\mathrm{SR}}-\mathrm{SR}_0)\sqrt{T-1}}{\sqrt{1-g_3\widehat{\mathrm{SR}}+\tfrac{g_4-1}4\widehat{\mathrm{SR}}^2}}\right).\tag{16}$$
$\mathrm{SR}_0$ is the Sharpe ratio that the best of $L$ strategies with no skill would show by chance, and $\mathrm{DSR}$ is the probability that the observed Sharpe ratio exceeds it. We require $\mathrm{DSR}\ge0.95$.

**4.5 Trial accounting.** Every variant evaluated is written to an append-only log. A strategy trial is one pair (strategy variant, bar size); exact repeats count once. Engineering variants (consensus form, topology, resilience, safety) are counted separately, giving a more conservative total. $V_{\mathrm{SR}}$ is the variance of the annualised Sharpe ratios of the strategy runs of E4, divided by the number of periods per year.

## 5. Experiments and results

Nine experiments test the methods of Section 3 in the order of their development (Table 5). Each is reported with its hypothesis or criterion, the protocol fixed in advance, the results, and an interpretation. Sharpe ratios are net of fees, impact and funding; "daily", "4-hourly" and "hourly" refer to bar size; intervals are 90%.

**Table 5.** Overview of the experiments.

| Experiment | Methods tested | Hypothesis or criterion | Section |
|---|---|---|---|
| E1 Simulated markets | 3.2 to 3.5, 3.8 | each mechanism meets criteria fixed before implementation | 5.1 |
| E2 Single-agent baseline | 3.2, 3.4, 3.5 | the engine reproduces the preliminary carry result; funding forecast | 5.2 |
| E3 Roster and market | 3.2 to 3.4 | H5 | 5.3 |
| E4 Specification sensitivity | 3.4 | conclusions are robust to the normalisation of the volatility limit | 5.4 |
| E5 Decentralised equivalence | 3.6 | H1 | 5.5 |
| E6 Topology and budget | 3.6 | H2 | 5.6 |
| E7 Resilience | 3.7 | H3 | 5.7 |
| E8 Safety | 3.8 | H4 | 5.8 |
| E9 Consolidated evaluation | all | H6 | 5.9 |

### 5.1 E1: Validation of the mechanisms on simulated markets

**Protocol.** Each mechanism is tested where the correct answer is known. *Joint optimiser:* random problems with 3 to 4 agents and 6 to 10 coins, five seeds per configuration, each coupling alone and all together (cost on the net trade, capacity, margin, gross cap, beta band), against a one-node reference solver. *Market:* 60 simulated coins with a common factor, planted skill (the standard deviation of the true alpha is 0.5% per period, the idiosyncratic standard deviation 6%) and agents whose belief is $\varpi$ times the true alpha plus noise, so that $\varpi$ is the agent's calibration (skilled: $\rho_c=0.3$; noise agent: $0$; over-confident: the belief of a skilled agent multiplied by 4, an effective Kelly fraction of 2 at which expected log-growth is zero). Selection is expected after $T_{\mathrm{end}}=3/\Delta G$ periods, where $\Delta G$ is the analytic growth gap between skilled and noise agents ($\Delta G=0.0188$, $T_{\mathrm{end}}=160$). *Other components:* model averaging with member error variances differing 4 times; the STL operators against brute force; the state-dependent skill estimator on planted regime skill (0.3 in the "on" state, 0 in the "off" state, regimes of about 33 periods).

**Results.** Table 6 lists the criteria, fixed before implementation, and the outcomes.

**Table 6.** E1 criteria and outcomes.

| Mechanism | Criterion | Outcome |
|---|---|---|
| Joint optimiser | maximum $\lvert X_{\mathrm{ADMM}}-X_{\mathrm{ref}}\rvert\le10^{-3}$ of a typical position and relative objective gap $\le10^{-5}$ on 7 configurations $\times$ 5 seeds | pass; typical error $10^{-7}$; hardest case (gross cap and beta band together) about 1,100 iterations, single couplings 20 to 250 |
| Prices | non-negative, zero when slack, equal to the marginal value of the limit within 5% | pass |
| Netting | opposite views on a coin pay the cost of the net trade, strictly below the sum | pass |
| Capital follows its price | a tighter margin raises the best coin's share of capital | pass |
| Market selects skill | skilled agents' wealth share exceeds 0.5 at $T_{\mathrm{end}}$ in at least 90% of 20 seeds | pass at 160 periods |
| Market drops decayed skill | share falls after skill vanishes | pass |
| Accounting | profits, cells, wealth and costs add up to $10^{-9}$ | pass |
| Over-confidence penalised | the calibrated agent ends with more wealth in at least 90% of seeds | pass without a floor (18 of 20); **fail** with a 2% floor (6 of 20) |
| Model averaging | error-weighted beats equal weights when errors differ, not worse when equal | pass: correlation with the true alpha 0.849 against 0.814 (+4.3%); 0.854 against 0.858 ($-0.4\%$) |
| Guard against a corrupt member | fused belief changes by less than 10% | restated: with the guard on, the fused belief equals the honest average to $10^{-12}$ |
| STL operators | match brute force; corrupt beliefs zeroed, honest untouched | pass |
| State-dependent skill | timed beats untimed on planted skill; costs little when absent | pass: $+0.0020$ per period (interval 0.0009 to 0.0033; 14 of 20 seeds); $-5.9\%$ with no dependence |

Three criteria were reformulated, each recorded with its diagnosis: one before any result was read (a ratio that became ill-posed when a position reached zero), two after an unsuccessful run (over-confidence with a floor; the corrupt-member guard, for which no filter can satisfy a 10% bound when merely dropping one of eight honest members changes the fused belief by about 13%).

**Interpretation.** Two findings constrain the design. First, *the floor blunts selection.* In single-agent runs of 3,000 periods the calibrated agent's log-growth was 0.0141 per period, equal to theory, whereas the over-confident agent's was $-0.0258$ (the continuous approximation gives zero at an effective fraction of 2; with discrete compounding it is negative) and suffered a ruinous period (a return of $-169\%$) in every run. Selection therefore works; the floor re-seeds a ruined agent with 2% of total wealth and so acts as a rebalancing rule, leaving the over-confident agent a persistent share of 14% to 41% and making the final-wealth ordering close to a coin flip. Second, *an unlimited over-confident agent can ruin the system:* at an effective fraction of 2 the per-period return has a standard deviation of about 0.39, and 5 of 20 seeds with a floor, and 2 of 20 without, were wiped out. Selection is too slow to prevent this, and the defences are the priced margin and gross limits and the calibration check. In its first form (acting on the point estimate of the slope) the check eliminated ruin entirely but did not restore selection (the guarded over-confident agent bets about as much as the calibrated one, so their wealth is similar in 10 of 20 seeds), so it is a risk control and not a selector. On real data the point-estimate form fired spuriously, because a belief of the size in (3) has a slope standard error above 1, which motivated the upper-confidence-bound form of Section 3.3; in simulation this reduced ruin after period 150 from 3 of 40 runs to 1 of 40. Consequently margin and gross limits are always active, the Kelly fraction does not exceed 0.5, and the floor is a liveness device whose cost is weaker selection.

### 5.2 E2: A single-agent baseline: calibration and the limits of forecasting funding

**Hypothesis.** With one agent the market is trivial, so E2 tests the engine against a known benchmark: funding carry, with a preliminary net Sharpe ratio of 1.03, 0.99 and 0.88. The engine is expected to reproduce a Sharpe ratio of about 1.0 on every bar size, with a market component near zero and costs near 2% a year. Belief designs were tried in sequence; each is a trial.

**Protocol.** One agent, 243-coin universe, development period, all settings of Appendix A.

**Results: calibration.** Table 7 gives the development sequence on daily bars.

**Table 7.** Calibration of the carry belief (daily). † Before the revision of E4; used only for the comparison within the table.

| Belief design | Sharpe | Volatility | Max drawdown | Comment |
|---|---|---|---|---|
| (a) $\theta$ estimated from a trailing window and shrunk towards zero; no volatility limit | 0.48† | 37% | −63% | belief changes sign |
| (b) as (a), with a sign clip and the volatility limit | 1.24† | | | evidence cannot move the belief |
| (c) **$\theta$ fixed by the card; evidence only through the kill rule** | 1.27† | 15.1% | −16.6% | final design |

Design (a) fails for the statistical reason of Remark 1: the standard error of the estimate exceeds the signal. Design (b) shrinks towards the card's value with 50 pseudo-observations, whereas an exponentially weighted estimate carries at most about 18 effective observations, so the prior always holds at least 74% of the posterior; 300 periods of rank information coefficient $-0.04$ still gave a positive belief. The improvement from (a) to (b) came from the sign clip alone, and the volatility re-solve rescaled the book and concealed the missing scale; this was found by inspection of the design. Design (c) is (3) with the kill rule of Section 3.2. The rank information coefficient of the carry score was 0.035 ($t=2.2$), 0.031 ($t=3.5$) and 0.019 ($t=3.4$) on daily, 4-hourly and hourly bars, with hit rates of 53% to 57%.

**Results: final design.** Table 8 gives the corrected values (E4).

**Table 8.** Carry alone.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Net Sharpe | **1.14** [0.36, 1.90] | **1.12** | **0.94** |
| Preliminary carry book | 1.03 | 0.99 | 0.88 |
| Volatility | 22.6% | 19.5% | 19.0% |
| Maximum drawdown | −27.7% | −29.8% | −31.1% |
| Annual cost | 3.4% | 3.0% | 2.5% |

The corrected values lie within or above the preliminary range on all bar sizes. In the development configuration profit decomposed into funding collected (+8.8%, +10.6%, +12.4% a year†), selection of the right coins (+11.8%, +8.6%, +6.1%†) and a market component near zero, as expected of a dollar- and beta-neutral book; yearly net returns on daily bars were +25%, +32%, +8%, +25%, +5% and +16% for 2020 to 2025†. Every solve converged. The 90% intervals exclude zero but are wide (lower bounds 0.25 to 0.36 in the corrected configuration): five years cannot distinguish a Sharpe of 1.0 from 1.2.

**Results: a better forecast of funding?** Carry might profit from predicting the size of funding as well as ranking coins. A mechanistic forecast was built from (1): the premium follows an AR(1) process in hours around its trailing 30-day mean $\bar\Pi$, $\Pi(h)=\bar\Pi+a_\Pi^{\,h}(\Pi_t-\bar\Pi)$ with $a_\Pi$ pooled over coins on the history window, the funding rate per hour is $[\Pi(h)+\operatorname{clamp}(\iota-\Pi(h),\pm\epsilon)]/8$, and the forecast funding over a holding period is the sum over its hours. *Pre-registered mechanical test (no profit):* at each rebalance the forecast of the funding sum is compared with the realised sum for every tradable coin; the forecast is accepted only if its cross-sectional mean squared error is below that of the baseline (the trailing 14-day mean funding times the horizon) with a 90% bootstrap lower bound above zero on at least two of three bar sizes.

**Table 9.** Forecast accuracy ($R^2$ relative to a zero forecast on cross-sectionally demeaned funding).

| Bar size | Rebalances | $R^2$ baseline | $R^2$ forecast | Outcome |
|---|---|---|---|---|
| Daily | 141 | −0.068 | −0.905 | forecast significantly worse |
| 4-hourly | 399 | +0.069 | −0.293 | forecast significantly worse |
| Hourly | 995 | +0.084 | +0.159 | not significant |

The test is passed on no bar size, so the forecast was rejected before any profit was computed.

**Interpretation.** Two conclusions follow. First, *calibration matters more than combination*: with an identical signal, a belief of estimated size that can change sign forfeits about 60% of the Sharpe ratio (0.48 against 1.2). This repeats, with different machinery, the preliminary finding that effort spent on combining agents is worth less than effort spent on making each agent's belief the right size. Second, *carry earns its return from the ranking of coins, not from forecasting the size of funding*: the baseline explains almost none of the variation in funding differences ($R^2$ between $-0.07$ and $0.08$), and the selection component is as large as the funding component, so the profit comes from choosing coins whose price moves are favourable as well as from collecting funding. A plausible explanation of the forecast's failure, not tested, is that its state is the premium of the last hour only, which is noisy.

### 5.3 E3: The agent roster and the capital market

**Hypotheses.** H5a: time-series momentum on Bitcoin and Ethereum is an admissible agent (its alpha against Bitcoin, and against Bitcoin and carry, has a lower bound above zero on at least two of three bar sizes). H5b: the market of carry and momentum beats carry alone (paired Sharpe difference with lower bound above zero on at least two bar sizes and no upper bound below zero). H5c: the market is at least as good as a fixed-weight blend. H5d: timing the momentum agent by market state improves it. H5e: residual reversal is admissible and the market of three beats the market of two. *Expectations stated beforehand:* with fixed card scales and wealth moving slowly, the market should behave like a fixed mix, so "no significant gain over carry" was the likely result; and since 2020 to 2025 was a strong bull market, a stand-alone Sharpe ratio for a trend rule is not evidence of timing skill, so admission is judged on the beta-adjusted intercept. Figures in this section are from the corrected configuration (E4) unless marked †.

**Momentum.** In the first run the agent's stand-alone returns were negative and the market of carry and momentum was worse than carry alone. Inspecting what the agent *held*, not only what it earned, showed that its positions did not match its card: on daily bars the mean gross position was 0.63 of equity, of which only 0.35 was in Bitcoin and Ethereum and about 0.28 in other coins. The optimiser used a diversified alt-coin basket to neutralise the beta band and the variance of the trend bet, because such a basket appears cheap in a one-factor risk model that omits the common residual of alt-coins; the book was a Bitcoin and Ethereum trend position plus a short alt basket with realised volatility far above the limit. The constraint $x_{ia}=0$ for $a\notin\mathcal{U}_i$ was then enforced and the experiment repeated, with the card and all rules unchanged; the amendment was recorded before the repeated runs and both runs count as trials. Table 10 gives the corrected results.

**Table 10.** Momentum and its market with carry.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Momentum alone, net Sharpe | 0.96 [0.24, 1.61] | 0.80 | 0.76 |
| Volatility of the momentum book | 13.3% | 14.5% | 15.3% |
| $\alpha$ against Bitcoin (annualised) | +9.2% [+0.2%, +17.7%] | +9.1% [−0.9%, +18.5%] | +9.2% [−2.7%, +19.7%] |
| $\alpha$ against Bitcoin and carry | +8.6% [−0.3%, +17.3%] | +8.5% [−1.5%, +18.0%] | +9.0% [−2.8%, +19.4%] |
| Carry alone | 1.14 | 1.12 | 0.94 |
| Market of carry and momentum | 1.39 [0.61, 2.09] | 1.48 | 1.48 |
| Market minus carry alone | +0.26 [+0.04, +0.47] | +0.36 [+0.04, +0.68] | +0.55 [+0.13, +0.92] |
| Market minus fixed inverse-volatility blend | −0.07 [−0.45, +0.32] | +0.14 [−0.19, +0.48] | +0.29 [−0.05, +0.65] |

H5a is not supported by the pre-registered rule: the alpha estimates are stable at about +9% a year, but the lower bound exceeds zero only on daily bars, so the two-of-three requirement fails and both admission tests fail. Before the revision of E4 they passed on two bar sizes (lower bounds +0.3% to +1.7%, with no margin on hourly bars); the intervals widened because the book now runs at 13% to 15% volatility instead of 11% to 12%. The rule was not overridden: momentum is retained as a *provisional* agent, recorded as not admitted, because the coordination experiments that follow need a realistic second agent, and no result claims a stand-alone edge for it. H5b is supported on all three bar sizes. H5c is not rejected but not supported: the market leads the fixed blend by 0.14 and 0.29 on the two faster bar sizes, but no interval excludes zero, so the gain of the market over carry alone is *diversification*, which a fixed mix provides equally. The caveats are that momentum covers two coins over one period with strong upward drift and earns most of its profit in 2020 and 2021, that the repeated run is a forking path, and that the card magnitude is an assumption that is not horizon-neutral (ex-ante Sharpe at actual gross 0.30, 0.47, 0.70).

**Timing.** *Design (decided before any run).* The card's coefficient is made state-dependent, $\theta(\chi_t)=\theta_0+c^\top\chi_t$, truncated to $[0,2\theta_0]$, with two states from Bitcoin returns over the history window: a *bull* state (the $t$-statistic of the trailing return; predicted $c_1\ge0$, since momentum is concentrated in bull markets) and a *panic* state (the log ratio of 30-day to window volatility; predicted $c_2\le0$, since momentum crashes after high-volatility rebounds). The coefficient is a ridge regression of each past period's skill on the standardised states with a Gaussian prior $c\sim N(0,\tau^2I)$, $\tau=\theta_0/2$, so that a one-standard-deviation move of a state shifts skill by at most about half the card; the ridge weight is $\operatorname{var}(y)/\tau^2$ pseudo-periods (about 800 on daily bars), so the coefficient is shrunk by about three quarters at 280 periods; a coefficient of the wrong predicted sign is set to zero; the first 30 periods use the untimed card. Timing is kept only if the timed Sharpe exceeds the untimed twin's with a paired lower bound above zero on two of three bar sizes and no upper bound below zero; the expectation was no significant difference.

**Table 11.** Timed against untimed momentum (†; both runs share one engine).

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Untimed momentum alone | 1.06† | 0.95† | 0.90† |
| Timed momentum alone | 1.03† | 0.90† | 0.86† |
| Paired difference | −0.03 [−0.05, −0.01] | −0.05 [−0.09, −0.02] | −0.05 [−0.13, +0.04] |
| Carry plus momentum, untimed → timed | 1.594 → 1.597 | 1.619 → 1.629 | 1.567 → 1.580 |

H5d is rejected: timing is slightly but significantly worse on two bar sizes and the pair with carry is unchanged. The test has little power (a few hundred noisy periods and a handful of bull and panic episodes in five years), so the finding is that this estimator, with these two states, detects nothing in this sample; it does not show that skill is state-independent.

**Reversal and the market of three.** The card of Section 3.2 has $\theta=0.02$, below the 0.025 to 0.049 measured in the preliminary study (those values come from the same data and are not independent evidence). *Admission (before any run), on two of three bar sizes:* (a) stand-alone Sharpe lower bound above zero; (b) $\mathrm{rIC}$ with $t>2$; (c) $\alpha$ against Bitcoin, carry and momentum with lower bound above zero. *Acceptance:* the market of three beats the market of two. Reported with equal weight: the market of three against a fixed inverse-volatility blend of the three, and $\mathrm{rIC}$ by liquidity tercile. *Expectation:* reversal fails (a) on daily bars at least, because its information is short-lived (the preliminary information coefficient at twice the holding period was 0.003 on daily bars) while the daily rebalance interval is 14 days.

**Table 12.** Reversal and the market of three.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Reversal alone, net Sharpe | −0.66 [−1.29, −0.03] | −1.17 [−1.82, −0.48] | −0.99 [−1.63, −0.32] |
| $\mathrm{rIC}$ ($t$) | 0.025 (1.5) | 0.042 (4.4) | 0.046 (7.3) |
| Annual cost; turnover (times equity) | 5.9%; 45 | 8.9%; 79 | 9.5%; 91 |
| Realised volatility | 28.7% | 24.7% | 24.1% |
| $\alpha$ against Bitcoin, carry, momentum | −12% to −23% a year | | |
| Market of three | 1.26 [0.52, 1.97] | 1.34 | 1.33 |
| Market of three minus market of two | −0.14 [−0.29, +0.02] | −0.14 [−0.31, +0.02] | −0.15 [−0.27, −0.04] |
| Market of three minus fixed blend of the three | +0.35 [−0.17, +0.84] | +0.86 [+0.31, +1.35] | +0.88 [+0.34, +1.39] |
| Reversal's final wealth share | 1.9% | 1.8% | 2.0% |

H5e is rejected: gates (a) and (c) fail on every bar size, gate (b) passes only on 4-hourly and hourly bars, and the market of three is worse than the market of two on every bar size. The rank information coefficient is highest in the *middle* liquidity tercile on every bar size (on daily bars 0.048 against 0.037 and $-0.024$), so the mechanism "stronger in less liquid coins" is not supported in the liquid universe used here. Against a fixed blend containing reversal, however, the market is clearly better (by 0.86 and 0.88 on 4-hourly and hourly bars, intervals above zero): it reduced reversal to the 2% floor and its account lost 7% to 9% of initial equity a year, whereas the blend kept paying for its losses; trading cost was 2.4% to 2.9% a year for the market against 2.5% to 3.5% for the blend.

**Interpretation: when does a capital market help?** A fixed blend holds each agent at a constant weight; the market holds agent $i$ at the weight $V_i(t)/\sum_jV_j(t)$, and since each wealth compounds with its own account return (5), an agent with a persistently negative return loses share geometrically until it reaches the floor. When all agents are good the wealth shares move slowly relative to sampling noise (selection speed is proportional to the growth gap between agents, which is small), so the market behaves like a fixed mix. When one agent is bad the gap is large and the market removes it within the sample, which a fixed blend cannot do. The benefit of the market in this experiment is therefore *protection from failure*, not an enhancement of return, and it depends on selection acting faster than the agent's losses accumulate, a speed bounded by E1.

### 5.4 E4: Sensitivity of the conclusions to the specification of the volatility limit

**Motivation.** A review of realised volatility by calendar year showed that the system did not meet the 20% mandate: on daily bars the volatility of carry plus momentum fell from 20% in 2021 to 8% in 2025. The cause was the normalisation of the limit: the ex-ante volatility of the net position was expressed in units of *initial* equity, while Kelly stakes, the gross cap and the beta band scale with *current* wealth. After wealth has grown by a factor $m$, a position that is a fixed share of current equity has a volatility, in initial-equity units, that is $m$ times larger, so the effective limit was $20\%/m$. A system that had made money was held to less and less risk, while an agent that had lost money, with shrunken equity, was granted a limit far above 20% of what it had left. The corrected specification measures volatility as a share of current equity; turnover is likewise normalised.

**Protocol.** Each affected run of E2 and E3 (carry, momentum, reversal, the market of carry and momentum, the market of all three) was repeated once on all three bar sizes with the pre-registered rules applied as written. Two earlier tests were not repeated because they do not depend on the specification: the forecast-accuracy test of E2 and the timing comparison of E3 (a comparison of two variants within one engine). Nothing else changed.

**Table 13.** Net Sharpe ratio before (†) and after the correction (daily / 4-hourly / hourly).

| Run | Before † | After | Daily interval after |
|---|---|---|---|
| Carry | 1.26 / 1.15 / 1.00 | **1.14 / 1.12 / 0.94** | [0.36, 1.90] |
| Momentum | 1.06 / 0.95 / 0.90 | **0.96 / 0.80 / 0.76** | [0.24, 1.61] |
| Reversal | −0.57 / −1.08 / −0.83 | **−0.66 / −1.17 / −0.99** | [−1.29, −0.03] |
| Carry + momentum | 1.59 / 1.62 / 1.57 | **1.39 / 1.48 / 1.48** | [0.61, 2.09] |
| Market of three | 1.42 / 1.39 / not run | **1.26 / 1.34 / 1.33** | [0.52, 1.97] |

**Results.** After the correction every multi-agent run sits at 18% to 21% realised volatility in every calendar year; compound annual growth of carry plus momentum rose to 29% to 31% from 18% to 22%; maximum drawdown is −22% to −26%. Of the pre-registered verdicts, one changed: momentum's admission, which passed before (two bar sizes, margins +0.3% to +1.7%) and now fails (daily only; Table 10). The carry baseline, the market's gain over carry alone (+0.26, +0.36, +0.55), the equivalence of the market and a fixed blend of carry and momentum, reversal's rejection and the failure of the market of three against the market of two are unchanged. The market of three against a fixed blend of the three strengthened (+0.33 and +0.75 on daily and 4-hourly bars before, +0.35, +0.86 and +0.88 after).

**Interpretation.** Sharpe ratios fell by 0.03 to 0.20 and returns rose: running at the mandated risk is more expensive because the impact term is superlinear ($\lvert d\rvert^{3/2}$), and it holds more of the weaker part of each signal, so the Sharpe ratio of a book is not invariant to its scale when costs are nonlinear. The only decision that changed was the one that depended on an interval bound near its threshold: momentum's alpha estimates barely moved (about +9% a year in both versions) but the intervals widened with the book's volatility, so admission by a rule that requires a bound above zero is fragile when the estimate lies near the threshold. The earlier suggestion that the one-factor risk model underestimates the risk of books that are not tightly neutral (reversal at 45% volatility against 20%) was largely this specification error, since reversal was losing money and its shrinking equity made a limit measured against initial equity large; after the correction reversal runs at 24% to 29%, still above 20%, which leaves a smaller gap consistent with the omission of a common alt-coin factor. All later experiments use the corrected specification. That one plausible change in a risk specification can flip an inferential decision motivates the robustness and multiple-testing analysis of E9.

### 5.5 E5: Decentralised optimisation on real data (H1)

**Protocol.** *Development problems.* On random problems with 3 and 8 agents the complete-graph result equals the hub's to $10^{-15}$ and the three-agent ring and line results to $10^{-8}$; with eight agents and all limits binding, one gossip round per iteration needed about 2,700 iterations on a ring ($\varsigma=0.81$) and over 3,000 on a line (0.95), three rounds brought the ring to about 400 and ten rounds the line to about 600. *Real-data test.* Three agents (carry, momentum, reversal), daily bars, the same data and settings as the hub run; graphs: the complete graph and the line (the least connected graph on three agents; a three-agent ring is the complete graph) with $g=1$ and $g=3$ gossip rounds. *Rule (before the runs):* Sharpe within 0.01 and final equity within 1% of the hub.

**Table 14.** Hub against decentralised runs (daily, three agents).

| Run | Net Sharpe | CAGR | Volatility | Max drawdown | Final equity | Rebalances at the iteration cap (of about 137) | Mean iterations |
|---|---|---|---|---|---|---|---|
| Hub | 1.258 | 25.9% | 19.9% | −22.1% | 3.564 | 21 | n/a |
| Graph, complete | 1.257 | 25.9% | 19.9% | −22.1% | 3.560 | 22 | 1,504 |
| Graph, line, $g=1$ | 1.256 | 25.8% | 19.9% | −22.1% | 3.554 | 43 | 2,011 |
| Graph, line, $g=3$ | 1.257 | 25.9% | 19.9% | −22.1% | 3.559 | 24 | 1,554 |

**Results and interpretation.** H1 is supported: Sharpe is within 0.002 and final equity within 0.3% of the hub on every topology, and every agent's account is the same to three decimals (annual profit in initial equity: carry 0.427 to 0.429, momentum 0.101, reversal $-0.066$; final wealth shares 0.738, 0.243, 0.019). The largest daily return difference to the hub is $6\times10^{-4}$ and the mean $7\times10^{-6}$. The residual differences come from solves stopped at the iteration cap, not from topology, and the cap is reached at 21 of about 137 rebalances even by the hub, so non-convergence at the cap is a property of the problem (slow convergence of the split of the net position between agents) and not of decentralisation; its effect on profit is small because a capped solve lies close to the optimum. Communication shows in the cap counts: on the line with $g=1$ the cap is reached twice as often as on the complete graph, and $g=3$ restores the hub's level, as the mixing rate predicts. With three agents most graphs coincide, so topology is studied next on problems with more agents.


### 5.6 E6: Network topology and communication budget (H2)

**Theory.** By (12), the rounds needed to shrink disagreement tenfold are $\ln(1/10)/\ln\varsigma$ (Section 3.6): 6.0 (random graph, 8 agents, $\varsigma=0.68$), 10.3 (ring, 0.80), 18.0 (star, 0.88), 44.9 (line, 0.95) at eight agents, and 9.8, 37.2, 44.9 and 229 for the random graph, star, ring and line at sixteen agents (0.79, 0.94, 0.95, 0.99). A poorly connected graph at larger size is thus expected to be heavily penalised. The algebraic connectivity (second-smallest Laplacian eigenvalue) is the other standard measure; for the star it exceeds that of the ring (1.0 against 0.59 at eight agents) while its mixing rate is worse (0.88 against 0.80), because with Metropolis weights the centre of a star is a bottleneck. $\varsigma$ is therefore expected to be the better predictor.

**Protocol (rules fixed before any run).** *Part A, simulated problems:* the random problems of E1 with every limit binding; tolerance $10^{-8}$; cap 4,000 iterations; five problems per cell; reference: the hub solution at tolerance $10^{-10}$. Agents $M\in\{4,8\}$ with topologies complete, ring, line, star and random (Erdős–Rényi with $p=0.4$, connected) and gossip rounds $g\in\{1,3,10\}$; at $M=16$ only $g=3$ with three problems, because each agent solves the system step itself so computation grows with $M$ (this reduction was fixed before any result was seen). *A1 (gate):* at $g=3$ the Spearman correlation between $\varsigma$ and iterations to converge is at least 0.7 for each $M$ (non-converged runs enter at the cap). *A2 (sanity):* the complete graph takes exactly the hub's iterations. A3, A4 (reported): the number of rounds minimising messages; the error of the net position after $K\in\{25,50,100,200,400\}$ iterations. *Part B, real data (daily):* eight agents that are parameter variants of the three hypotheses, used only to study coordination (carry with 7, 14 and 30-day windows, momentum with 15, 30 and 60-day lookbacks, reversal with 3 and 7-day lookbacks); the hub; the complete graph ($g=1$); the ring ($g=1$ and $3$); the line and the star ($g=3$); and the hub and the ring ($g=3$) capped at 200 iterations. *B1 (gate):* every uncapped graph run is within 0.02 Sharpe and 2% final equity of the hub. *Recommendation rule:* the default for later experiments is the topology with the fewest messages that passes B1 with no more capped rebalances than the hub plus 10% of rebalances. *Expectation:* A1 passes; the line is slowest and the complete graph fastest; poorly connected graphs leave agents in disagreement under a short budget; B1 passes and capped runs lose a little.

**Table 15.** Median iterations to converge, $g=3$ (five problems; three at $M=16$), with $\varsigma$ in brackets.

| Agents | Complete | Ring | Random | Star | Line |
|---|---|---|---|---|---|
| 4 | 151 (0) | 165 (0.33) | 228 (0.75) | 264 (0.75) | 389 (0.80) |
| 8 | 386 (0) | 499 (0.80) | 883 (0.68) | 1,183 (0.88) | not converged (0.95) |
| 16 | 1,000 (0) | 3,709 (0.95), 2 of 3 converged | 1,000 (0.79) | not converged (0.94) | not converged (0.99) |

**Results, Part A.** *A1 fails:* the correlations are 0.60 at four agents, 0.90 at eight and 0.78 at sixteen. The failure at four agents has a clear cause: differences between graphs of four agents are small, and the intrinsic difficulty of the individual problem dominates (one problem needed about 830 iterations on every topology, including the complete graph, so its slowness is that of ADMM and not of consensus). Pooling seeds therefore confuses problem difficulty with topology. Within each problem the ordering is as predicted (mean within-problem correlation 0.79, 0.96, 0.82), but that is not the pre-registered statistic and the gate is reported as failed. *A2 passes.* *A3:* one gossip round minimises messages on the complete graph and (at four agents) the ring, and three rounds elsewhere, because a single round needs so many more iterations that the extra messages per iteration pay for themselves; ten rounds waste messages once mixing is no longer the bottleneck (median messages at eight agents: complete graph 21,616 with $g=1$; ring 23,952, star 49,686, random 52,980 with $g=3$; the line does not converge at $g=1$ or 3 and needs 91,840 at $g=10$). *A4:* at $g=3$ the error of the net position after $K$ iterations is almost the same on every topology (eight agents: about 0.40 at $K=25$, 0.16 at 100, 0.03 to 0.05 at 200, below 0.001 at 400; sixteen: 0.76 at 100, 0.16 at 200, 0.012 to 0.015 at 400): early iterations are limited by ADMM itself and not by communication, and topology decides how long the final, precise part takes. With the priced volatility term (eight agents, $g=3$, three problems) the ring converged in 797 to 1,076 iterations (hub: 165 to 749) and the line reached the cap on all three, with a net-position error of at most $4.3\times10^{-6}$ of a typical position.

**Table 16.** Real data, eight agents, daily (135 rebalances; cap 3,000 iterations unless stated).

| Run | Net Sharpe | CAGR | Final equity vs hub | Rebalances at cap | Mean iterations | Messages per rebalance |
|---|---|---|---|---|---|---|
| Hub | 1.240 | 26.0% | 3.578 | 27 | 1,427 | (hub) |
| Graph, complete, $g=1$ | 1.239 | 26.0% | −0.02% | 29 | 1,459 | 81,716 |
| Graph, ring, $g=1$ | 1.238 | 26.0% | −0.16% | 114 | 2,885 | 46,160 |
| Graph, ring, $g=3$ | 1.239 | 26.0% | −0.08% | 43 | 1,870 | 89,755 |
| Graph, line, $g=3$ | 1.238 | 25.9% | −0.22% | 122 | 2,949 | 123,854 |
| Graph, star, $g=3$ | 1.240 | 26.0% | −0.01% | 96 | 2,743 | 115,194 |
| Hub, 200-iteration cap | 1.217 | 25.3% | −2.8% | 135 | 200 | (hub) |
| Graph, ring, $g=3$, 200-iteration cap | 1.212 | 25.2% | −3.5% | 135 | 200 | 9,600 |

**Results, Part B.** Volatility was 20.2% to 20.3% and maximum drawdown $-29.8\%$ to $-30.0\%$ in every run. Messages equal mean iterations $\times g\times2\lvert\mathcal{E}\rvert$ (28 edges for the complete graph, 8 for the ring, 7 for the line and the star). *B1 passes:* every uncapped run is within 0.002 Sharpe and 0.23% of the hub's final equity. The recommendation rule allows at most $27+13.5=40.5$ capped rebalances; only the complete graph with $g=1$ qualifies (29), the ring with $g=3$ just misses (43), and the ring with $g=1$, which uses the fewest messages (46,160), reaches the cap at 114 rebalances. The default for later experiments is therefore the complete graph with one round, with the caveat, recorded in advance, that link failures on a complete graph are a weak test, so E7 also uses a sparse graph.

**Interpretation.** Network shape governs the communication and not the outcome: every uncapped topology reproduces the hub, and the price of a sparse graph is paid in iterations and messages (on simulated problems with eight agents the line needs more than ten times the iterations of the complete graph; on real data the line and the one-round ring run out of iterations at four times as many rebalances). The link between $\varsigma$ and iterations holds when the compared graphs differ enough (8 and 16 agents) and fails when problem difficulty dominates (4 agents); the failure of A1 is a statement about a pooled pre-registered statistic and not about the mechanism of (12). The mixing rate predicts better than algebraic connectivity. Removing the hub costs computation that grows with the number of agents, because each agent solves the system step. A short communication budget costs money but little, on every topology: 200 iterations lose about 3% of final equity and 0.025 Sharpe over five and a half years, the ring slightly more than the hub, and the error after 200 iterations is similar across topologies.

**Figure 2** (below) shows the median iterations to converge by topology.

### 5.7 E7: Resilience to link failures, dropout and misbehaving agents (H3)

**Hypotheses.** H3(i): link failures and dropout, which preserve doubly stochastic mixing, are absorbed (Proposition 2). H3(ii): a consistent liar is isolated on a robust graph and the others reach the optimum of the problem without it. H3(iii): W-MSR trimming does not preserve the optimum (Proposition 3), so it is tested also as a detector.

**Protocol (rules fixed before any run).** The mechanisms and detector parameters ($\vartheta=0.9$, $T_d=50$, majority) were fixed on development problems before the rules were written; the experiment uses fresh problems and real data and changes no parameter. *Part A, simulated problems:* eight agents, every limit binding, tolerance $10^{-8}$, cap 4,000 iterations; graphs: the complete graph ($g=1$), ring2 ($g=3$) and the ring ($g=3$). The liar is agent 3 and holds nothing, so the correct answer is the optimum without it; the error is $\max\lvert X-X^\ast\rvert$ divided by the mean $\lvert X^\ast\rvert$. *A1 (gate):* with each edge down with probability $q_\ell\in\{0.1,0.3\}$ in every round, every run on every graph converges with error at most $10^{-4}$ ($q_\ell=0.5$ is reported). *A2 (gate):* on the complete graph and ring2, with the detector on, a liar adding a constant $d\in\{0.001,0.01,1.0\}$ is isolated, only the liar, with error at most $10^{-4}$, and with no liar nobody is isolated. *A3 (reported, predicted to fail):* the same on the plain ring. *A4 (reported):* the undefended liar; a noise liar (normal noise of standard deviation 0.01, new each iteration) with the detector. *A5 (reported, decides the code):* trimmed mixing ($F=1$) with no attacker; rejected if the error exceeds $10^{-2}$ in most runs. *Part B, real data* (daily; the eight agents of E6): *B1 (gate)* with 30% of links down, the complete graph ($g=1$) and the ring ($g=3$) reproduce the hub within 0.02 Sharpe and 2% final equity. *B2 (gate)* with the largest agent (a carry variant) offline from 1 May to 31 August 2022 (the Luna collapse and its aftermath), the graph runs equal the hub with the same agent offline, and the highest ex-ante volatility at any rebalance inside the window is no higher than outside it. *B3 (gate)* with a momentum variant lying (adding 0.01 to everything it sends), the detector isolates it at every rebalance, no other agent is ever isolated, and the run equals the hub without that agent within 0.02 Sharpe and 2% final equity; with the detector on and no liar nobody is isolated and the run equals the complete-graph run of E6 within 0.002. *Expectation:* A1, A2 and B1 to B3 pass; A3 fails as the robustness condition predicts; the noise liar is mostly not caught; the undefended liar spoils the solve; trimmed mixing is rejected.

**Table 17.** Median iterations under link failures (eight agents, simulated).

| Graph | $q_\ell=0$ | 0.1 | 0.3 | 0.5 |
|---|---|---|---|---|
| Complete, $g=1$ | 187 | 215 | 262 | 288 |
| Ring2, $g=3$ | 193 | 214 | 235 | 265 |
| Ring, $g=3$ | 439 | 513 | 700 | 1,075 |

**Table 18.** E7 Part A: gate outcomes (simulated problems).

| Gate | Outcome |
|---|---|
| **A1** link failures | pass; error at most $5.4\times10^{-6}$; every run converged even at $q_\ell=0.5$ |
| **A2** constant liar, detector on | pass; 18 of 18 runs: only the liar isolated, error at most $4.4\times10^{-6}$; with no liar nobody isolated |
| **A3** plain ring | **fail**, as predicted: in all nine liar runs an honest agent was also isolated and the graph fell apart; with no liar the ring isolated nobody |
| A4 undefended liar ($d=0.01$) | error after 1,000 iterations 5.5 to 5.9 typical positions on every graph; no convergence |
| A4 noise liar, detector on | isolated in 1 of 6 runs (after which the result was exact); in the other five no isolation, no convergence in 4,000 iterations, error 12.5 to 14.8 typical positions |
| **A5** trimmed mixing, no attacker | no run converged; error 0.50 to 4.8 typical positions in all six runs; **rejected** |

**Table 19.** E7 Part B: real data (daily, eight agents, 135 rebalances).

| Run | Net Sharpe | Final equity | Capped rebalances | Mean iterations | Against the reference |
|---|---|---|---|---|---|
| Hub | 1.240 | 3.578 | 27 | 1,427 | |
| Complete graph, $g=1$ | 1.239 | 3.577 | 29 | 1,459 | |
| Ring, $g=3$ | 1.239 | 3.575 | 43 | 1,870 | |
| Complete, 30% of links down | 1.239 | 3.577 | 31 | 1,692 | within 0.001 of the hub (B1 pass) |
| Ring, 30% of links down | 1.239 | 3.575 | 56 | 2,155 | within 0.001 of the hub (B1 pass) |
| Hub, largest agent offline | 1.225 | 3.476 | 28 | 1,440 | cost of the missing agent |
| Complete, largest agent offline | 1.225 | 3.476 | 29 | 1,468 | equals the hub with the same agent offline (B2 pass) |
| Ring, largest agent offline (a line without it) | 1.225 | 3.474 | 46 | 1,902 | equals the hub (B2 pass) |
| Complete, detector on, no liar | 1.239 | 3.577 | 29 | 1,459 | nobody isolated (B3 pass) |
| Complete, momentum variant lies, detector on | 1.182 | 3.391 | 30 | 1,541 | isolated at the first rebalance and nobody else ever (B3 pass) |
| Hub without that momentum variant | 1.182 | 3.392 | 29 | 1,512 | the correct reference |

In all three offline runs the highest ex-ante volatility inside the window was 17.5%, against 20.9% outside it. The largest agent held 38% of final wealth; four months without it, including the Luna collapse, cost 0.015 Sharpe and 2.8% of final equity relative to the full hub; leaving out the lying agent cost 0.058 Sharpe and 5.2%, mostly because its capital then sits idle. The undefended liar on real data was not completed: with the lie every solve ran to the iteration cap and the volatility search repeated it up to five times, so its cost is shown on simulated problems (A4).

**Interpretation.** *(i) Link failures and dropout are absorbed.* With weights recomputed on the surviving links the optimiser reaches the same answer in every case, on simulated problems even with half of the links down and on real data to within 0.001 Sharpe; the cost is communication (on the ring, 30% failures raise iterations by about 60% on simulated problems and 15% on real data). This is Proposition 2 in operation. *(iii) Trimming fails as an averaging rule*, as Proposition 3 predicts: with no attacker at all it did not converge and the error was 50% to 480% of a typical position, because the weight matrix it induces is not doubly stochastic and the agents agree on a value that is not the average of the positions. This is a negative result about combining resilient consensus with optimisation. *(ii) As a detector the same test works on robust graphs:* on the complete graph and on ring2 a consistent liar was caught from 4% of a typical position upward, with no false alarm, on simulated and real data, and the result was exactly that of the system without it; (13) is near one for such a liar because a consistent offset puts its value beyond the honest values in nearly every coordinate. On the plain ring honest agents were isolated too, as the robustness condition predicts; a plausible explanation, not separately tested, is that with only two neighbours a single deviating neighbour is already a majority, so an honest agent next to the liar, whose own values are pulled by it, can be flagged by its other neighbour. The robustness of the graph, and not only its connectivity, decides whether the system can defend itself: the complete graph is robust and expensive, the ring cheap and not robust, and ring2 sparse and robust. A stealthy liar gets through: noise that stays inside the honest range was caught once in six runs, and otherwise the result is far from the optimum and the solver does not converge. Non-convergence is observable, which motivates the hold supervisor of E8. The money lost in defended failures comes from what is missing and not from the coordination: every defended failure on real data is within 0.001 Sharpe of its reference.

### 5.8 E8: Formal safety monitoring and supervision (H4)

**Hypotheses.** H4(i): the monitor documents the system's margin to its specifications through stress periods; H4(ii): derisk reduces breaches of the drawdown specification; H4(iii): hold prevents trading on corrupted solutions without acting on honest ones. *Why supervisors that act through the optimiser:* a shield that scales the finished portfolio re-trades the whole book (Section 1.2), and a drawdown constraint inside the optimiser has no clean form because a drawdown is a property of a path; derisk and hold act through what the optimiser already has, the volatility target and the decision to trade.

**Protocol (rules fixed before any run).** Limits are those of Table 4, derived from the mandate. The implementation was checked on the first 900 days of the daily data in a smoke test (carry plus momentum, hub), in which derisk acted (target down to 0.32) and hold never triggered (worst relative residual $10^{-6}$); no setting was changed afterwards and the smoke test is not counted as a trial. *Part A, the main system* (carry plus momentum, centralised): all bar sizes with safety off and derisk, and daily bars also hold. *A1 (gate):* with safety off, $\varphi_{\mathrm{solve}}$ holds at every rebalance and $\varphi_{\mathrm{vol}}$ at at least 95% of rebalances. *A2 (gate):* on each bar size derisk has fewer bars violating $\varphi_{\mathrm{dd}}$ than off and a shallower worst 365-day drawdown. *A3 (reported):* per run and stress window, return, worst drawdown, volatility, minimum robustness, violating bars, lowest volatility multiplier, and the Sharpe, CAGR and drawdown of derisk against off (the cost, which is not a criterion: limits are never chosen by Sharpe). *Part B, a stealthy liar* (daily; carry, momentum and reversal; complete graph, $g=1$): reversal misbehaves from 1 May to 31 July 2022 only, holding nothing and adding normal noise of standard deviation 0.01 drawn anew at every iteration. Runs: (a) no liar; (b) the liar, no defence; (c) the liar with hold. *B1 (gate):* in (c) every unsafe solve is held, every held rebalance is inside the window and none outside is unsafe; in (b) at least one rebalance inside the window trades on an unsafe solve. *B2 (reported):* money and risk of (b) and (c) against (a). *Expectation:* A1 passes; A2 passes on every bar size at a cost of a little return; the specifications are tightest in May 2021 and Luna; B1 passes.

**Table 20.** Safety modes on the main system.

| Mode | Metric | Daily | 4-hourly | Hourly |
|---|---|---|---|---|
| Off | Sharpe | 1.394 | 1.478 | 1.483 |
| | CAGR | 31.2% | 29.8% | 29.2% |
| | worst 365-day drawdown | −23.7% | −24.4% | −25.9% |
| | bars with drawdown below −15% | 211 | 2,223 | 7,695 |
| | rebalances with $\hat\sigma\le1.05\,\sigma^\ast$ | 97.8% | 97.6% | **94.3%** |
| | worst volatility margin | −0.5% | −3.0% | −10.0% |
| | unsafe solves | 0 | 0 | 0 |
| Derisk | Sharpe | 1.277 | 1.275 | 1.462 |
| | CAGR | 23.9% | 21.0% | 24.3% |
| | worst 365-day drawdown | −19.7% | −18.8% | −16.7% |
| | bars with drawdown below −15% | 229 | 2,159 | 5,135 |
| | lowest volatility multiplier | 0.2 | 0.2 | 0.2 |
| Hold (daily) | Sharpe; rebalances held | 1.394; 0 | | |

(The volatility margin is the limit minus $\hat\sigma$ relative to the limit; bars are of the run's own size, so counts are not comparable across bar sizes.)

**Results, Part A.** *A1 fails on hourly bars only:* $\varphi_{\mathrm{solve}}$ holds at every rebalance, but $\varphi_{\mathrm{vol}}$ holds at 94.3% (54 of 955 rebalances) with breaches up to 10% over the limit, because the volatility-price search (at most five re-solves, a 2% band) lags a covariance that moves faster between hourly rebalances. This is a limitation of the search and not of the specification. *A2 fails on daily bars and passes on the other two:* derisk always makes the worst drawdown shallower (by 4 to 9 points) and on 4-hourly and hourly bars also reduces the bars below $-15\%$, but on daily bars it has more such bars (229 against 211), because smaller positions after a loss recover more slowly and the account stays below the line longer although it never falls as far. *A3:* derisk costs Sharpe 0.12, 0.20 and 0.02 and CAGR 7.3, 8.8 and 4.9 points. The specifications are tightest in the **FTX collapse (November 2022 to January 2023)**, not in May 2021 or Luna as expected: in May 2021 and Luna the system made money (7% to 16%; drawdown inside the window at most 8.5%) and derisk did not act, whereas FTX is the only window in which $\varphi_{\mathrm{dd}}$ is violated (1 daily bar, 444 4-hourly, 1,741 hourly, with safety off). There derisk acts: on 4-hourly bars the drawdown inside the window falls from 8.5% to 2.0% and volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%); on hourly bars the drawdown falls from 12.6% to 2.8%. $\varphi_{\mathrm{rvol}}$ is violated only on daily bars (34 bars off, 28 with derisk) and never inside a stress window.

**Table 21.** E8 Part B: hold against a noise liar (daily).

| Run | Sharpe | Final equity | CAGR | Return in window | Worst drawdown in window | Cost in window | Unsafe solves | Held |
|---|---|---|---|---|---|---|---|---|
| (a) no liar | 1.257 | 3.56 | 25.9% | 11.7% | −3.0% | 0.86% | 8 (all in 2025) | 0 |
| (c) liar, hold | 1.033 | 2.77 | 20.3% | 6.7% | −5.8% | 0 | 15 | 15 |
| (b) liar, no defence | divergent | | | | | | first attacked solve unsafe | |

*Run (b).* Without a supervisor the corrupted solve diverges: at the first attacked rebalance the relative residual is 1.32 against the limit $10^{-3}$, iterates grow from 0.4 to 44 within 700 iterations, and the time per agent step grows from 0.02 s to 0.3 s, so one 3,000-iteration solve takes about 45 minutes. A complete undefended run on real data was therefore not obtained; (b) and (c) are identical up to the first attacked rebalance, where the undefended system would trade an unsafe solve, which is the second half of B1; B2 for (b) is not measured. *B1 fails:* all six attacked rebalances were held (relative residual 1.18 to 1.62), but nine honest rebalances in 2025, with no liar, were held too (residuals 0.0013 to 0.0059, caused by slow convergence of the decentralised solve; the same slow solves occur in the clean run (a), eight of them, which it traded). The fixed limit $10^{-3}$ cannot distinguish an attack, with residuals above 1, from slow honest convergence, with residuals around 0.003: the two differ by a factor of about 300, so a better limit exists, but it was not tuned after seeing the result. The false alarms cost more than the attack: inside the window (c) earns 6.7% against 11.7% for (a) with a deeper drawdown (5.8% against 3.0%), since it keeps pre-attack positions through the Luna collapse (their ex-ante volatility of 12% to 15% is inside the limit); frozen for most of May to October 2025, stale positions drifted to an ex-ante volatility of up to 31%, violating $\varphi_{\mathrm{vol}}$ at five held rebalances, and the whole-period Sharpe fell from 1.26 to 1.03.

**Interpretation.** The monitor is informative: a single record of the distance of each specification from violation shows where the system was in danger and identified a window we had not predicted; the prior expectation that Luna would be the tightest was wrong because the system was positioned for a falling market and profited. Derisk behaves as designed and exposes a trade-off between the depth and the duration of drawdowns, so the daily failure of A2 is a consequence of the supervisor's mechanism and not a defect of its estimator. Hold stops a stealthy liar, but a threshold chosen in advance also freezes the system on honest slow solves, so detect-and-isolate (consistent liars) and hold (noisy ones) are each incomplete alone. An undefended noise liar makes the decentralised solve diverge, so some supervisor is needed in practice. An interactive dashboard accompanies the study: it runs the decentralised optimiser live on simulated problems (graph, rounds, link failures, a liar with or without the detector) and shows saved results; it reads saved results only and uses no sealed data.

### 5.9 E9: Consolidated evaluation and the multiple-testing verdict (H6)

**Protocol (rules fixed before the table was computed).** No new simulation and no new setting: the saved runs of E4 to E8 and the trial log are read. *Tables:* T1 money and risk per bar size (three agents, the markets of two and three, and a 50/50 blend of carry and momentum); T2 centralised against decentralised; T3 each failure against its reference; T4 safety; T5 the deflated Sharpe of the main system. *Trial accounting:* the strategy variants on real data are carry in three belief designs (E2), carry with the funding forecast (E2), momentum before and after enforcing its coin set, the market of two with each, timed momentum with its market, reversal alone, the market of three, and the corrected re-runs of carry, momentum, reversal, the market of two and the market of three (E4): 15 variants on each of three bar sizes, $L=45$ (the written enumeration sums to 16 variants, $L=48$, which lowers the daily deflated Sharpe ratio from 0.070 to about 0.063 and does not change the verdict; see Appendix B); the engineering variants (consensus form, topology, resilience, safety) add 29 distinct names, giving the conservative total $L=74$. *Gates:* C1 every number shared with an earlier experiment reproduces to 0.001 in Sharpe; C2 the deflated Sharpe ratio of the market of two is at least 0.95 at $L=45$ on a bar size. *Expectation:* C1 passes; C2 may well fail, because the trial Sharpe ratios range from $-1.2$ to 1.5, a spread that raises the bar the best trial must clear, and five and a half years may not suffice for a Sharpe of 1.4 to 1.5 to clear it; a failure would mean that the development period alone does not establish the edge, without affecting the comparison of mechanisms, which is made on the same strategy.

**Table 22 (T1).** Net Sharpe ratio, 90% interval.

| | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [−0.03, 1.44] |
| Reversal | −0.66 [−1.29, −0.03] | −1.17 [−1.81, −0.48] | −0.99 [−1.63, −0.32] |
| **Main system: market of carry and momentum** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 blend, carry plus momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

The main system has CAGR 31.2%, 29.8% and 29.2%, volatility 21%, 19% and 18%, and maximum drawdown $-23.7\%$, $-24.4\%$ and $-25.9\%$.

**Results.** *C1 passes.* *T2 (daily):* market of three, hub 1.258, complete graph 1.257, line 1.256, final equity within 0.3%; eight agents, every topology within 0.002 Sharpe and 0.22% of the hub's final equity, mean iterations 1,427 (hub) to 2,949 (line), messages 46,160 to 123,854, capped rebalances 27 to 122, and a 200-iteration budget costing 2.8% (hub) and 3.5% (ring) of final equity. *T3 (daily):* 30% link failures 1.239 and 1.239 against 1.240; the largest agent offline 1.225 against 1.225; a constant liar with the detector 1.182 against 1.182, liar isolated; in every case final equity is within 0.1% of the reference's; a noise liar with hold 1.033 against 1.257 ($-22\%$ final equity, mostly false alarms in 2025). *T4:* as in E8.

**Table 23 (T5).** Deflated Sharpe ratio of the main system (gate C2: at least 0.95).

| Bar | Sharpe | $g_3$ | $g_4$ | DSR, $L=45$ | DSR, $L=74$ | C2 |
|---|---|---|---|---|---|---|
| Daily | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 | fail |
| 4-hourly | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 | fail |
| Hourly | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 | fail |

$V_{\mathrm{SR}}=0.82$ (annualised, the 15 corrected strategy runs, from $-1.17$ to 1.48). The deflated Sharpe ratio exceeds 0.95 only for $L\le2$ trials (0.98 to 0.99) and is 0.47 to 0.55 at $L=10$.

**Interpretation.** *Multiple testing.* A Sharpe ratio of 1.4 to 1.5 among 45 trials of this spread is what chance would produce with probability about 90%. The correction is large because the trial Sharpe ratios are widely dispersed (the roster deliberately contains bad agents) and because five and a half years of data give a limited number of independent observations; the term in the denominator of (16) also penalises fat tails ($g_4$ between 11 and 29). H6 is rejected. This is a statement about the evidence on the development period, not proof that the system has no edge: carry's interval is above zero on every bar size, and the sealed final year, never examined, is the independent test that the correction cannot replace. It is also insensitive to the trial count, since DSR exceeds 0.95 only for two trials. *Mechanisms.* The decentralised system, every topology, link failures, an offline agent and an isolated liar all reproduce the centralised portfolio to within 0.002 Sharpe, at a cost of up to 2.7 times the messages and 4.5 times the capped rebalances (on a line). In one line, the trade-offs are: decentralisation and resilience cost messages, safety costs return, and the market of agents buys protection against a bad agent.

**Figure 3** (below) summarises the Sharpe ratios of the main results.


## 6. Discussion

### 6.1 Summary of the evidence

**Table 24.** Answers to the research questions.

| | Answer | Evidence |
|---|---|---|
| RQ1 | Yes. The neighbour-only optimiser matches the hub to 0.002 Sharpe and 0.3% of final equity, and every decentralised, resilient or supervised variant stays within 0.002 Sharpe of its reference. | E5, E9 |
| RQ2 | Topology governs communication cost and not the outcome. $\varsigma$ predicts iterations at 8 and 16 agents but not reliably at 4, and predicts better than algebraic connectivity. A short budget costs about 3% of final equity. | E6 |
| RQ3 | Link failures and dropout are absorbed because the sum invariant survives them. W-MSR trimming fails inside the optimiser because it breaks the invariant; as a detector it isolates a consistent liar exactly on robust graphs, but not on a non-robust ring and not against noise. | E7 |
| RQ4 | The monitor shows the safety margin and found an unexpected stress window; derisk shortens the worst drawdown at a Sharpe cost of 0.02 to 0.20, with two failed gates; hold needs a better limit. | E8 |
| RQ5 | Carry is a solid edge; momentum is marginal and concentrated in 2020 and 2021; reversal does not pay after costs. The market equals a fixed mix of good agents and beats it when one agent is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone. | E3, E4, E9 |

### 6.2 Interpretation

The experiments support three general statements, each of which connects several results.

*Information bounds what coordination can achieve.* Across the preliminary study and E2 and E3, the value of the system was limited by the information in its agents. Carry, with an information coefficient of about 0.02 to 0.035, is the only agent whose profit survives costs and scale. Reversal has a larger coefficient and loses, because turnover of 45 to 91 times equity meets an impact term that is superlinear: a real signal is not necessarily a tradable one. Calibrating each agent's belief to the size justified by its card (Remark 1) was worth more than any combination scheme, since an estimate of the belief's size cost about 60% of the Sharpe ratio.

*A single invariant organises the decentralised results.* Every result on decentralisation is a consequence of Proposition 1. Failures that keep the mixing doubly stochastic (link failures, dropout) leave the optimum intact (Proposition 2); a mixing rule that does not (trimming) destroys it (Proposition 3). The same observation separates two roles of W-MSR: as an averaging rule it conflicts with optimisation, whereas as a detector it needs the *robustness* of the graph and not convergence. The decentralised algorithm is thus a case in which the structure of the problem (an exact sum) and the structure of the defence (resilient agreement within a range) must be reconciled, and the reconciliation here is to separate detection from averaging.

*Prices coordinate without exposing beliefs, and capital selects without evaluating.* Agents interact only through prices of exposure, capital and trading. Pricing the volatility limit removes the cross-subsidy of a uniform rescale, and costing the net trade lets opposing agents cancel. Capital as a selection mechanism has a specific benefit: it does not add return over a fixed mix of good agents, because wealth shares move slowly relative to sampling noise, but it removes a failing agent quickly, a benefit limited by the floor that retains a small stake in every agent. Evidence for this comes from E3 (+0.86 and +0.88 Sharpe over a fixed blend containing reversal) and is bounded by E1 (the floor blunts selection of over-confident agents).

### 6.3 Negative and null results

The experiments contain several well-posed negative results. A funding forecast built from the premium index does not improve carry (E2). Timing momentum by bull and panic states does not help (E3). Reversal does not pay after costs, and its pattern across liquidity terciles does not support the "less liquid" mechanism (E3). The lecture's W-MSR rule cannot be the averaging rule in the optimiser (E7). A hold rule with a fixed residual limit freezes honest solves (E8). The main system does not clear the deflated-Sharpe threshold (E9). Each followed a pre-registered rule, and none was altered after the result.

### 6.4 Threats to validity

*Internal validity.* The system is complex and the volatility limit was initially mis-specified (E4). We mitigated this with cross-checks (baselines re-run on changed code, tables that reproduce their inputs) and by repeating all affected experiments; residual specification errors cannot be excluded. The constraint violation of the first momentum run (E3) is a forking path: the correction followed a failed result and both runs count as trials. Several quantities (step sizes, the stopping test, the restart after an isolation) are evaluated centrally in the experiments.

*Construct validity.* The momentum card's information coefficient (0.05) is an assumption chosen by a mechanical check and not from the literature, and it is not horizon-neutral. The impact coefficient, the one-million-dollar scale and the taker fee were fixed and not varied. A one-factor risk model underprices books that are not tightly neutral: reversal runs at 24% to 29% volatility against a 20% limit.

*External validity.* Five and a half years of data, mostly one bull market, from one exchange; momentum's profit is concentrated in 2020 and 2021. Only three hypotheses were tested in the final engine; four more (cross-sectional momentum, size and illiquidity, low volatility, a machine-learning trend model) were planned and not implemented, and two further steps of the carry ladder (a crowding term from open interest, a tail cap from high and low prices) were not run.

*Statistical validity.* Intervals are wide and the number of independent periods is limited, particularly on daily bars; a block bootstrap addresses autocorrelation but not regime change. The trial count in the deflated Sharpe ratio involves judgement about what counts as one trial, although the conclusion is insensitive to it.

*Computational limits.* The decentralised solver does work proportional to the number of agents (the sixteen-agent simulations were the most demanding computationally), and some real-data solves stop at the iteration cap even for the hub (21 to 27 of about 135 rebalances) with a small effect on profit.

### 6.5 Reproducibility

The software, the pre-registered rules, the result tables and the trial log are in the project repository. Raw data come from the exchange's public data archive and can be re-downloaded; results are deterministic for fixed data and settings. The development procedure follows four rules throughout: no lookahead, a sealed final year, an append-only trial log, and pass or fail rules written before the runs.

## 7. Conclusion and future work

We designed and evaluated a multi-agent trading system in which heterogeneous hypothesis agents stake capital in a market, are coordinated by prices in a joint ADMM optimisation, can do so without a central node, tolerate link failures, dropout and a lying agent, and are monitored by formal safety specifications. The decentralised system reproduces the centralised one under every network and failure condition tested, because a single invariant (the sum of the agents' positions) is preserved by every admissible mixing and destroyed by trimming; failures cost communication and not return; the capital market protects against a bad agent; and the monitor shows where the system was in danger. The return claim is weaker: carry is a real edge and the combined system earns a Sharpe ratio of 1.4 to 1.5 at its risk limit, but after correction for the number of variants tried, the development data alone cannot establish it. Pre-registered gates that failed are reported as failures, and none was changed after the result was known.

**Future work.** (1) Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged. (2) Re-argue the hold supervisor's limit, for example by a rule that distinguishes a diverging solve from a slowly converging one, and lengthen the volatility-price search for fast bar sizes. (3) Add a second, alt-coin-market risk factor to close the risk-model gap for non-neutral books. (4) Test further established hypotheses, each with a card and rules written first, and run the remaining carry steps. (5) Move towards deployment: pre-agreed step sizes, a max-consensus stopping test, flooded isolation notices and a communication model with delays.

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
| Universe | 243 coins over the period, about 63 a day; point-in-time top 50 by 90-day median dollar volume, retained while within the top 75 |
| Tradability | trailing median daily dollar volume at least one million dollars; complete history window |
| Bars and rebalancing | daily (every 14 days), 4-hourly (every 5 days), hourly (every 48 hours) |
| Costs | taker fee 5 basis points; square-root impact with coefficient $k=1$; assets of one million dollars; capacity 5% of daily volume |
| Kelly fraction $q$ | 0.5 |
| Margin; gross cap; beta band | $3V_i$; $3E$; $0.25E$ |
| Volatility target | 20% a year, as a price $\lambda$ on system variance; at most five re-solves; 2% band |
| Wealth floor $\omega$ | 2% of total wealth |
| Card information coefficients $\theta_i$ | carry 0.02; momentum 0.05; reversal 0.02 |
| Calibration check | slope floor 0.5; window 52 rebalances; at least 1,500 observations; upper confidence bound |
| Belief sanity | volatility-standardised belief within six robust standard deviations of the agent's own history |
| Burn-in | 90 days |
| ADMM tolerance | $10^{-6}$ relative (real data); $10^{-8}$ (simulated topology and resilience experiments) |
| Bootstrap | 7-day blocks, $B=500$, 90% interval |
| Detector | extreme in at least $\vartheta=90\%$ of coordinates for $T_d=50$ iterations; isolation by a majority of neighbours |
| STL limits | Table 4 |
| Derisk | multiplier (15) |

## Appendix B. Correspondence with the project records

The project repository holds a numbered write-up for each experiment, with the exact command and the committed result tables.

| Experiment of this report | Project experiment records |
|---|---|
| Preliminary study (Section 1.2) | 001 to 010 |
| E1 Simulated markets | 011 (data audit), 012 |
| E2 Single-agent baseline | 013, 014 |
| E3 Roster and market | 015, 016, 017 |
| E4 Specification sensitivity | 018 |
| E5 Decentralised equivalence | 019 |
| E6 Topology and budget | 020 |
| E7 Resilience | 021 |
| E8 Safety | 022 |
| E9 Consolidated evaluation | 023 |
