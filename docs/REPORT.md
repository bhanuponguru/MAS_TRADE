# Resilient Decentralised Portfolio Consensus

*A decentralised, resilient and safe multi-agent system for trading crypto perpetual futures*

AI3403: Multi-Agent Systems, course project, Fall 2026. Team BackPropeers: Krishna Teja (CS23BTECH11028), Hruthik (CS23BTECH11043), Bhanu (CS23BTECH11046), Manoj (CS23BTECH11047), Jaya Prakash (CS23BTECH11015), Sandeep (CS23BTECH11027). Course instructor: Dr. Venkatraman Renganathan. Code: <https://github.com/bhanuponguru/MAS_TRADE>.

This is the Markdown version of the submitted report [report/MAS_PROJECT_REPORT.pdf](../report/MAS_PROJECT_REPORT.pdf); section, table, figure and equation numbers match the PDF.

## Abstract

A portfolio run by several analysts is a multi-agent system: the agents hold different beliefs, share capital, risk limits and trading costs, and the system must stay correct when one of them fails or lies. We ask how far the central node of such a system can be removed without changing the portfolio or its safety.

The system has two levels. First, each agent is a documented trading hypothesis that stakes its own capital in a Kelly-bet market, so wealth follows results. Second, all stakes become one portfolio through a convex problem solved by the alternating direction method of multipliers (ADMM), in which costs and shared limits act as prices. Replacing the central node by dynamic average consensus keeps the sum of the agents' positions exact (Proposition 1). The same invariant explains which failures are absorbed (Proposition 2) and why the W-MSR trimming rule cannot be used inside the optimiser (Proposition 3), although the W-MSR test detects a consistent liar on a robust graph. A signal temporal logic (STL) monitor with two supervisors provides formal safety.

On five and a half years of Binance perpetual-futures data, under pass or fail rules written before each run, the decentralised system reproduces the centralised portfolio to within 0.002 Sharpe on every network, with 30% of links failing, with the largest agent offline for four months, and with a lying agent isolated. Network shape changes the communication, not the outcome. The market of agents equals a fixed mix when all agents are good and beats it by about 0.9 Sharpe on 4-hourly and hourly bars when one agent is bad. De-risking makes the worst drawdown shallower at a cost of 0.02 to 0.20 Sharpe. The main system earns a net Sharpe ratio of 1.4 to 1.5, but its deflated Sharpe ratio, corrected for 45 strategy trials, is about 0.1 against a pass mark of 0.95: the mechanisms are verified, the return claim is not established on the development data alone.

**Keywords:** multi-agent systems, ADMM, consensus, resilient consensus, signal temporal logic, Kelly betting, perpetual futures, deflated Sharpe ratio.

## 1. Introduction

### 1.1 Overview

This chapter states why portfolio management is a multi-agent problem, what earlier systems taught us, the questions this project answers, and what it contributes. It ends with the division of the work among the six team members.

### 1.2 Motivation

Analysts with different views of what drives returns draw on one pool of capital, share one risk budget and trade in one market that charges them for impact. The usual design collects every forecast at one node and solves one optimisation problem. That node is a single point of failure, it merges the forecasts before their disagreement can be used, and it says nothing about the questions distributed computation studies directly: how fast agents agree, what agreement costs in communication, and how it degrades when links fail or an agent lies.

### 1.3 Lessons from earlier systems

Two earlier systems were built and evaluated before this one: a trust-weighted consensus of forecasting agents with W-MSR averaging, and an engine with five agents and six ways of combining them. Four lessons shaped the present design.

1. Only funding carry (net Sharpe 0.88 to 1.03) and Bitcoin timing (0.46 to 0.80) earned money after costs. Residual reversal predicted returns (rank correlation 0.025 to 0.049) but lost money (Sharpe $-0.68$ to $-1.24$): a real signal is not always a tradable one.
2. Every combiner was worse than carry alone. Combination multiplies information; it does not create it.
3. The coordination layer added little over a central solve (Sharpe 0.81 against 0.90). The one clear multi-agent effect was resilience: with one compromised agent, plain consensus lost 43% of its Sharpe ratio and W-MSR recovered most of it.
4. A temporal-logic shield that scaled finished portfolios halved violations, but it acted after the optimiser and so re-traded the whole book.

### 1.4 Problem statement and research questions

We seek agents that jointly trade a portfolio of crypto perpetual futures such that (i) agents with different beliefs coordinate through local exchanges only and reach the portfolio of a centralised optimiser; (ii) costs, shared limits and capital allocation are handled by prices the agents agree on; (iii) the system stays correct under link failures, agent dropout and false messages; (iv) formal safety requirements are monitored and, when needed, enforced; and (v) performance is measured against a centralised benchmark with correction for the number of variants tried. Table 1.1 lists the resulting questions and hypotheses.

**Table 1.1.** Research questions and hypotheses.

|   | Research question | Hypothesis |
|:--|:--|:--|
| RQ1 | Does a neighbour-only optimiser reproduce the centralised portfolio on real data? | H1: the portfolios coincide up to solver tolerance on every connected graph. |
| RQ2 | How do network shape and communication budget affect convergence and result? | H2: iterations grow with the mixing rate $\varsigma$ of the graph; the result does not depend on the shape. |
| RQ3 | Does the system stay correct under link failures, dropout and a lying agent, and does W-MSR protect it? | H3: failures that keep the mixing doubly stochastic are absorbed; a consistent liar is isolated on a robust graph. |
| RQ4 | Does an STL monitor with supervisors keep the system within its specifications in stress periods, and at what cost? | H4: de-risking reduces drawdown breaches; a hold rule prevents trading on corrupted solutions. |
| RQ5 | What do the agents and the market add in money and risk, and does the result survive correction for multiple testing? | H5: the market is at least as good as a fixed mix and protects against a bad agent. H6: the main system's deflated Sharpe ratio is at least 0.95. |

### 1.5 Contributions of this work

1. A two-level architecture: a capital-staked market of hypothesis agents above one joint ADMM over (agent, coin) cells, with shared limits and the cost of the net trade as prices (Sections 3.3 to 3.5).
2. A neighbour-only version of that optimiser, a proof that it preserves the sum of the agents' positions, and a measured account of its convergence in terms of the graph's mixing rate (Sections 3.6, 6.2, 6.3).
3. One invariant that explains which failures are absorbed and why W-MSR trimming breaks the optimiser, with the W-MSR test reused as a detector (Sections 3.7, 6.4).
4. An STL monitor and two supervisors whose limits come from a written risk mandate (Sections 3.8, 6.5).
5. A pre-registered evaluation that counts every variant tried and reports failed tests and revised results (Chapters 4 and 7).

### 1.6 Organisation of the report

Chapter 2 gives the background, the market and the notation. Chapter 3 presents the system, component by component. Chapter 4 fixes the evaluation protocol. Chapters 5 and 6 report the experiments on the agents and the market, and on coordination, resilience and safety. Chapter 7 brings everything into one final comparison. Chapter 8 discusses the findings, including what we cannot explain, and Chapter 9 concludes.

### 1.7 Team contributions

The work was divided into six parts that follow the structure of the system, and each part had one owner. Table 1.2 gives the division and the sections where each part is described; the paragraphs after it summarise each member's contribution.

**Table 1.2.** Division of the work among the team members.

| Member | Part | Contribution | Described in |
|:--|:--|:--|:--|
| Krishna Teja {CS23BTECH11028} | Data and research rules | Market data pipeline, trial log and tests | Sections 2.3, 4.2, 4.4 to 4.6 |
| Hruthik {CS23BTECH11043} | Trading agents | Carry, momentum and reversal agents, with their calibrated beliefs | Sections 3.3, 5.3, 5.4, 5.6 |
| Bhanu {CS23BTECH11046} | Coordination | Joint optimiser (ADMM), neighbour-to-neighbour agreement, network shapes | Sections 3.5, 3.6, 6.2, 6.3 |
| Manoj {CS23BTECH11047} | Resilience | Link failures, offline agents and the liar detector (W-MSR) | Sections 3.7, 6.4 |
| Jaya Prakash {CS23BTECH11015} | Safety | Safety rules (STL), the safety monitor and supervisor | Sections 3.8, 6.5 |
| Sandeep {CS23BTECH11027} | Market of agents and results | The market that funds the agents and its tests, the final comparison, the skill-or-luck test and the dashboard | Sections 3.4, 5.2 and 5.5 (the market), Chapter 7 |

- **Krishna Teja (data and research rules)** built the data pipeline for 243 Binance perpetual futures, including delisted coins, and the rules that keep the evaluation honest: pass or fail rules written before each experiment, a sealed final year, an append-only trial log (45 strategy trials) and a test suite of 183 passing tests.
- **Hruthik (trading agents)** built the three agents (funding carry, momentum on Bitcoin and Ethereum, short-term reversal), with beliefs whose size is fixed by a written card, and tested each against its own admission rule.
- **Bhanu (coordination)** built the joint ADMM that turns all stakes into one portfolio, the neighbour-only version that removes the central node, and the study of network shapes and communication cost.
- **Manoj (resilience)** built the handling of link failures and offline agents and the W-MSR liar detector, and showed why W-MSR trimming cannot be used inside the optimiser.
- **Jaya Prakash (safety)** wrote the four STL safety rules, the monitor that records how far each rule is from breaking, and the derisk and hold supervisors.
- **Sandeep (market of agents and results)** built the Kelly-bet market that moves capital between agents and tested it, produced the final comparison of all systems and the skill-or-luck (deflated Sharpe) test, and built the dashboard.

### 1.8 Summary

Portfolio management fits the multi-agent setting, but earlier systems showed that coordination adds value only if agents carry real information, costs and limits sit inside the optimiser, and safety acts through the optimiser. The project tests five questions on one system, built in six parts by six owners. The next chapter introduces the tools and the market.

## 2. Background and Setting

### 2.1 Overview

This chapter reviews the methods the system builds on, describes the market and the data, and fixes the notation and the formal problem used in the rest of the report.

### 2.2 Related work

**Consensus.**  In average consensus, agents on a connected undirected graph repeatedly replace their value by a weighted average of their neighbours' values. With a doubly stochastic weight matrix $W$ every agent converges to the average of the initial values, at a rate set by the second-largest eigenvalue modulus of $W$ [2]. Metropolis weights give such a $W$ from the graph alone [3]. When the averaged quantity changes over time, dynamic average consensus lets each agent add its own change before mixing, so the sum of the estimates tracks the sum of the true values [4]. Resilient protocols such as W-MSR discard up to $F$ extreme neighbour values on each side before averaging; if at most $F$ agents are malicious and the graph is robust enough, the honest agents agree inside the range of honest values [5]. The consensus, ADMM and STL material follows the course notes [24].

**Distributed optimisation.**  ADMM solves convex problems with separable structure by alternating local minimisations, a coordination step and a price update; its dual variables are prices of the coupling constraints [1]. Variants run it without a central node by consensus on the dual or the shared variable [6]. Robustness tools built for consensus on values do not obviously carry over to optimisation, where the quantity that must be preserved is a sum.

**Markets of agents.**  A Kelly bettor stakes the fraction of wealth that maximises expected log growth [7]. In a market of Kelly bettors, wealth moves according to Bayes' rule and the market's belief is a wealth-weighted average [8]; evolutionary models of asset markets reach similar conclusions about which rules survive [9, 10]. These results concern idealised betting markets; we test them with leveraged positions in correlated assets and real trading costs.

**Temporal-logic monitoring.**  Signal temporal logic specifies properties of real-valued signals over time. Its quantitative semantics gives a robustness value, the signed distance from violation [11, 12], which supports both monitoring and supervision.

**Portfolio construction and backtests.**  Expected returns can be written as an information coefficient times a volatility times a standardised score [13]. A perpetual future's expected return splits into carry and expected price change [14, 15]. Time-series momentum [16] and short-term reversal [17] are established effects; the evidence in crypto is stronger for the first [18]. Square-root market impact is a standard cost model [19]. The best of many backtests overstates the expected Sharpe ratio; the deflated Sharpe ratio corrects for the number of trials, their spread and fat tails [20, 21].

### 2.3 Market, data and trading costs

**Market.**  Binance USD-M perpetual futures are contracts on coins that never expire. Every eight hours (sooner when the funding cap binds) a long position pays, and a short receives, a funding payment that anchors the contract to the spot price. For an interval with time-weighted average premium $\Pi$ over the index price,

$$
\mathrm{FR} = \Pi + \operatorname{clamp}(i_0 - \Pi,\, \pm\epsilon),
\qquad i_0 = 0.01%, \epsilon = 0.05% . \tag{2.1}
$$

On Bitcoin (89 funding events) this reproduced actual funding with correlation 0.995 and mean absolute error $9\times10^{-7}$. Funding is always summed per bar from its event times.

**Universe.**  The universe is free of survivorship bias.

- **Entry and exit.** A coin enters when its rank by 90-day median daily dollar volume, computed strictly before the day, is in the top 50, and stays while it is in the top 75; the ranking is refreshed every 30 days.
- **Size.** Delisted coins are included: 243 coins appear in total, about 63 on a typical day.
- **Tradability.** A coin is tradable only if its trailing median daily volume is at least one million dollars. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded.
- **Gaps.** Gaps of up to seven days in a coin's history are filled with the last price, and days on which no coin has data are skipped.

Spot prices, open interest and long/short ratios are also downloaded but are not used by any agent.

**Rebalancing.**  Every 14 days on daily bars, every 5 days on 4-hourly bars and every 48 hours on hourly bars. Everything used at a rebalance at time $t$ depends only on information strictly before $t$; a test checks this.

**Costs.**  Trading $d_a$ dollars of coin $a$ costs

$$
C_a(d_a) = c_f\,|d_a| + \psi_a\,|d_a|^{3/2},
\qquad \psi_a = \frac{c_{\mathrm{imp}}\,\sigma_a}{\sqrt{\mathrm{ADV}_a}}, \tag{2.2}
$$

with a taker fee $c_f = 5$ basis points, daily volatility $\sigma_a$, average daily dollar volume $\mathrm{ADV}_a$ and impact constant $c_{\mathrm{imp}}=1$ (an assumption). The second term is square-root impact. The total cost $C(d)=\sum_a C_a(d_a)$ is convex. Capital is one million dollars and a position may be at most 5% of a coin's daily volume.

**Financial terms.**  The following terms are used throughout.

- **Time and prices.** A *bar* is one time step of the price data (a day, four hours or one hour); returns, funding and costs are summed per bar. The *spot price* is the price of the coin itself, the *index price* an average of spot prices across exchanges, and the *premium* how far the futures price sits above the index.
- **Trading.** A *long* position gains when the price rises and a *short* position gains when it falls. A *taker fee* is paid by an order that trades immediately. A *basis point* is 0.01%. *Turnover* is the amount traded in a year as a multiple of equity.
- **Books.** A *book* is the set of positions held by one agent or by the system. Its *gross exposure* is the sum of the absolute sizes of its positions, *leverage* is gross exposure as a multiple of equity, and *margin* is the equity the exchange requires behind it.
- **Market exposure.** A coin's *beta* is how much it moves on average when Bitcoin moves by one unit. A book is *market-neutral* when its longs and shorts balance in dollars (dollar neutrality) and in beta (beta neutrality), so a move of the whole market leaves it unchanged. A strategy's *alpha* is the part of its return left after removing the market part. An *alt-coin* is any coin other than Bitcoin.
- **Skill of a score.** The *information coefficient* is the correlation between a score and the next return across coins; the rank version (rIC) uses ranks; the *hit rate* is the share of periods in which it is positive.
- **Risk.** *Ex-ante* volatility is what the risk model predicts before trading; *realised* volatility is measured afterwards from returns. *Skewness* measures how lopsided returns are and *kurtosis* how often extreme returns occur (3 for a normal distribution); high kurtosis means *fat tails*.
- **Data.** *Survivorship bias* is the error of testing only on coins that still exist today, which hides the losses on coins that failed. A liquidity *tercile* is one third of the coins ranked by trading volume.

**Performance measures.**  All measures are computed on net returns $y_t$, after fees, impact and funding; $P$ is the number of bars per year.

- **Sharpe ratio.** $\mathrm{SR}=\sqrt{P}\,\bar y/s_y$, the mean per-bar return $\bar y$ over its standard deviation $s_y$, annualised. It is return per unit of risk: 1 means one unit of annual return for each unit of annual volatility; a negative value means the strategy loses money.
- **CAGR and volatility.** CAGR is the compound annual growth rate of equity, $(E_T/E_0)^{P/T}-1$ over $T$ bars; volatility is $\sqrt{P}\,s_y$.
- **Drawdown.** The *maximum drawdown* is the largest fall of equity from an earlier peak, $\min_t\bigl(E_t/\max_{s\le t}E_s-1\bigr)$. The safety rules of Section 3.8 use the 365-day drawdown, the fall from the highest equity of the past year.
- **90% interval.** The range in which the statistic falls in 90% of resampled histories (Section 4.5).
- **Deflated Sharpe ratio.** The best of many tried strategies looks better than it is by luck alone. The deflated Sharpe ratio (Section 4.5) is the probability that a Sharpe ratio beats the best that the same number of strategies without skill would show by chance; we require at least 95%.

### 2.4 Notation

Table 2.1 lists the symbols used across several chapters. Symbols that appear in only one equation are defined where they appear.

**Table 2.1.** Notation.

| Symbol | Meaning |
|:--|:--|
| *Market and data* |  |
| $\mathcal{A}=\{1,\dots,M\}$, $\mathcal{C}=\{1,\dots,N\}$ | agents; tradable coins; $\mathcal{U}_i\subseteq\mathcal{C}$ is the coin set allowed to agent $i$ |
| $t$, $H$, $P$ | bar or rebalance time; bars per holding period; bars per year |
| $r$, $\sigma_H$, $\beta$ | coin returns over a holding period; their volatilities; coin betas to Bitcoin |
| $\Sigma$ | return covariance, one market factor plus idiosyncratic variances |
| $C(\cdot)$, $c_f$, $\psi_a$ | trading cost (2.2); fee rate; impact coefficient of coin $a$ |
| $E$, $E_t$ | total equity (the sum of the agents' wealth); equity at bar $t$ |
| *Agents and the market* |  |
| $z_i$, $\theta_i$, $\mu_i$ | score of agent $i$; information coefficient fixed by its card; belief (3.1) |
| $V_i$, $q$, $\gamma_i$, $\omega$ | wealth of agent $i$; Kelly fraction ($\tfrac12$); risk aversion $1/(qV_i)$; wealth floor (0.02) |
| *Joint optimiser* |  |
| $x_i$, $X$, $h$ | position of agent $i$; net position $\sum_i x_i$; net position before the rebalance |
| $\mathcal{X}_i$, $\mathcal{S}$ | constraint set of agent $i$; of the whole system |
| $k$, $\rho$, $u$, $\bar x$, $\zeta$ | ADMM iteration; penalty; scaled price; average position; system-step variable |
| $\lambda$ | price on system variance (the volatility limit) |
| *Communication and resilience* |  |
| $\mathcal{G}$, $W$, $g$ | communication graph; doubly stochastic mixing matrix; gossip rounds per iteration (not the function $g(\cdot)$ of Section 3.5) |
| $\varsigma$ | mixing rate $\|\lambda_2(W)\|$ (smaller is faster) |
| $s_i$, $\zeta_i$, $u_i$ | agent $i$'s own estimate of the average position, system step and price |
| $F$, $\pi_{ij}$ | W-MSR trimming parameter; share of coordinates in which neighbour $j$ is extreme for agent $i$ |
| *Safety* |  |
| $\varrho_\varphi(t)$ | STL robustness of rule $\varphi$ at time $t$ |
| $\mathrm{DD}_t$, $\sigma^{\mathrm{real}}_t$ | drawdown over 365 days; realised 30-day volatility |
| $\hat\sigma_t$, $\sigma^\ast_t$, $\kappa$ | ex-ante volatility; volatility target in force; derisk multiplier |
| *Statistics* |  |
| $\mathrm{SR}$, rIC | annualised net Sharpe ratio; rank information coefficient |
| $\alpha$, $\beta_s$ | intercept and slope of a regression on Bitcoin's return |
| $L$, $\mathrm{DSR}$ | number of trials; deflated Sharpe ratio |

### 2.5 Formal problem statement

At each rebalance the agents hold beliefs $\{\mu_i\}$ and wealths $\{V_i\}$. The centralised problem (Section 3.5) maps them to positions $\{x_i^\ast\}$ and a net position $X^\ast$. The *decentralised problem* is to obtain $X^\ast$ when each agent uses only its own data and messages from its neighbours in $\mathcal{G}$ (RQ1, RQ2), when edges fail, agents drop out or send false values (RQ3), and so that the portfolio satisfies STL specifications on volatility, drawdown, recovery and solver health (RQ4). Performance is the annualised net Sharpe ratio (Section 2.3), judged with correction for multiple testing (RQ5).

### 2.6 Summary

The system draws on five bodies of work: consensus, distributed ADMM, markets of Kelly bettors, STL monitoring and multiple-testing correction. It trades a survivorship-free universe of Binance perpetual futures with realistic costs. The next chapter builds the system from these parts.

## 3. System Design

### 3.1 Overview

The system is presented in the order in which its parts build on one another (Figure 3.1): hypothesis agents form beliefs; a market gives each agent capital; a joint optimiser turns all stakes into one portfolio; the optimiser runs without a central node; it is protected against faults; and an STL monitor keeps it safe.

**Figure 3.1.** Architecture, from beliefs to safety. (diagram drawn in the LaTeX report)

### 3.2 Design principles

The lessons of Section 1.3 give six requirements, each met by one component (Table 3.1).

**Table 3.1.** Requirements and the components that meet them.

| Requirement | Component |
|:--|:--|
| R1. Agents carry distinct, documented hypotheses with an explicit expected edge. | Hypothesis agents with a card (Section 3.3) |
| R2. Capital follows results, with a defence against over-confidence. | Kelly-staked market with a floor and a calibration check (Section 3.4) |
| R3. Costs and shared limits sit inside the optimisation. | Joint convex problem over (agent, coin) cells (Section 3.5) |
| R4. The optimiser runs without a central node and degrades gracefully. | Decentralised ADMM and a fault model (Sections 3.6, 3.7) |
| R5. Safety is formal and acts through the optimiser. | STL monitor and supervisors (Section 3.8) |
| R6. Conclusions survive the number of variants tried. | Sealed final year, trial log, deflated Sharpe, pre-registration (Chapter 4) |

### 3.3 Hypothesis agents and calibrated beliefs

**Definition 1 (Hypothesis agent).** An agent is specified by a *card* written before any test: the claim, the mechanism, the allowed coins $\mathcal{U}_i$, whether the book is market-neutral, a score $z_i$ oriented so that the claim predicts a positive correlation with the next return, an information coefficient $\theta_i>0$, and a switch-off rule.

If the score has unit variance across coins and is the only information, the expected return of coin $a$ is $\theta_i\sigma_{H,a}z_{ia}$, the fundamental law of active management [13]. The belief is therefore

$$
\mu_{ia} = \theta_i\,\sigma_{H,a}\,z_{ia}. \tag{3.1}
$$

The size $\theta_i$ is fixed by the card and is not estimated from recent results, for a statistical reason.

**Remark 1 (A trailing estimate of $\theta_i$ is too noisy to size a bet).** For carry the per-period rank information coefficient has mean about 0.035 and standard deviation about 0.19. An estimate from about 18 effective observations has standard error about 0.045, larger than the quantity estimated, so a belief built on it changes sign often (the per-period hit rate is only 53%). Section 5.3 confirms this on data.

Evidence therefore acts only through a *kill rule*: if, after at least 20 periods, the $t$-statistic of the agent's realised information coefficient falls below $-2$, its belief is set to zero. It never takes the opposite position.

**The three agents.**  Table 3.2 summarises them; the scores are

$$
z^{\text{carry}}_a = \mathrm{RG}\bigl(-\overline{\mathrm{FR}}_{14\mathrm{d}}(a)\bigr),
$$

$$
z^{\text{mom}}_a = \operatorname{clip}\Bigl(\tfrac{\sum_{\tau\in 30\mathrm{d}} r_{a\tau}}{\operatorname{sd}(r_a)\sqrt{\ell}},\,-2,\,2\Bigr),
$$

$$
z^{\text{rev}}_a = \mathrm{RG}\Bigl(-\tfrac{\sum_{\tau\in 7\mathrm{d}} e_{a\tau}}{\operatorname{sd}(e_a)\sqrt{\ell'}}\Bigr),
\qquad e_{a\tau} = r_{a\tau} - \hat\beta_a r^{\mathrm{BTC}}_\tau ,
$$

where $\ell$ and $\ell'$ are the numbers of bars in the 30-day and 7-day windows, and $\mathrm{RG}$ is the rank-Gaussian transform $z_a=\Phi^{-1}\bigl((\mathrm{rank}_a-\tfrac12)/N\bigr)$.

**Table 3.2.** The three hypothesis agents.

| Agent | Idea | Coins | Neutral | $\theta_i$ |
|:--|:--|:--|:--|:--|
| Funding carry | long low funding, short high funding (14-day average) | all tradable | yes | 0.02 |
| Momentum | hold Bitcoin or Ethereum if it rose over 30 days, short if it fell | BTC, ETH | no | 0.05 |
| Residual reversal | buy recent losers, short recent winners, against the market (7 days) | all tradable | yes | 0.02 |

Carry rests on funding being a transfer from the crowded side; momentum on slow diffusion of information; reversal on temporary price pressure. Momentum's $\theta=0.05$ is an assumption fixed by a check that uses no profit: at $\theta=0.10$ its expected Sharpe ratio at its own belief was 1.17, more than a two-coin trend strategy can deliver; at 0.05 it is about 0.6.

### 3.4 Market of agents: capital allocation by Kelly betting

**Kelly sizing.**  For one asset with expected return $\mu$ and variance $\sigma^2$, the log growth of wealth when a fraction $f$ is invested is approximately

$$
G(f) = f\mu - \tfrac12 f^2\sigma^2 , \tag{3.5}
$$

which peaks at $f^\star=\mu/\sigma^2$ and falls to zero at $2f^\star$: the mathematics itself punishes over-confidence. Each agent bets half the Kelly size, $q=\tfrac12$, which corresponds to the risk aversion $\gamma_i=1/(qV_i)$ used in the joint problem.

**Accounts and wealth.**  The system trades the sum of the agents' positions, and each agent keeps an account that earns the profit of its own positions less its share of cost and funding, so the accounts add up exactly to the real result. The cost of the net trade in each coin is charged to the agents trading in the same direction as the net trade, in proportion to the size of their trade; agents trading against it cross internally and pay nothing. Wealth compounds with the account return $y_i(t)$:

$$
V_i(t+1) = \max\Bigl(V_i(t)\bigl(1+y_i(t)\bigr), \omega\sum_j V_j(t)\Bigr),
\qquad \omega = 0.02 . \tag{3.6}
$$

The floor keeps a failed agent alive so the market can still reallocate; losses beyond an agent's wealth are borne by the others. Beliefs are never averaged between agents: they act only through the wealth behind them, so capital moves to the agents whose beliefs pay, as in a market of Kelly bettors [8].

**Protections against over-confidence.**  Wealth alone selects too slowly to prevent ruin (Section 5.2), so the system limits of Section 3.5 bound every stake and two checks are added.

- **Calibration check.** It regresses realised returns on the agent's past beliefs over the last 52 rebalances and, once 1,500 (period, coin) observations exist, scales the Kelly fraction down from 1 (slope at least 0.75) to 0.2 (slope at most 0.5). Because the slope has a standard error above 1, the check uses its upper bound (slope plus 1.645 standard errors) and so acts only on demonstrable over-confidence.
- **Belief-sanity check.** It zeroes any belief that is not finite or exceeds six robust standard deviations of the agent's own past beliefs.

### 3.5 Joint portfolio optimisation by ADMM

**Definition 2 (Cell).** A cell is a pair (agent $i$, coin $a$): the sub-agent that manages one coin for one agent.

At each rebalance the system solves one convex problem over all positions:

$$
\begin{aligned}
\min_{x_1,\dots,x_M} & \sum_{i=1}^{M}\Bigl[-\mu_i^\top x_i
+ \tfrac{\gamma_i}{2}\,x_i^\top\Sigma x_i\Bigr]
+ C(X-h) + \tfrac{\lambda}{2}\,X^\top\Sigma X\\
\text{s.t.} & x_i\in\mathcal{X}_i (i\in\mathcal{A}),\qquad
X=\textstyle\sum_i x_i\in\mathcal{S}.
\end{aligned} \tag{3.7}
$$

The agent set $\mathcal{X}_i$ holds one agent's constraints: allowed coins, capacity (5% of daily volume), margin ($\|x_i\|_1\le 3V_i$) and, for neutral agents, dollar and beta neutrality. The system set $\mathcal{S}$ holds a gross cap $\|X\|_1\le 3E$ and a market-beta band $|\beta^\top X|\le 0.25E$. Three features carry the multi-agent content.

- **Cost on the net trade.** $C$ acts on $X-h$, not on each $x_i$: two agents trading opposite ways in the same coin pay only for the difference.
- **The volatility limit as a price.** After each solve the annual ex-ante volatility of $X$ is compared with the 20% target; if it is more than 2% above, $\lambda$ is raised and the problem re-solved (at most five times). The agent that adds risk pays for it. In a test at equal total volatility the priced limit left a market-neutral agent 97% of its position, where a uniform shrink left it 45%.
- **Prices as the coordination signal.** The multipliers of neutrality, margin, gross, beta, capacity and cost are prices. Each agent reacts to prices and never needs another agent's belief.

**Sharing ADMM.**  Write $f_i(x_i)=-\mu_i^\top x_i+\tfrac{\gamma_i}{2}x_i^\top\Sigma x_i+\iota_{\mathcal{X}_i}(x_i)$ and $g(X)=C(X-h)+\tfrac{\lambda}{2}X^\top\Sigma X+\iota_{\mathcal{S}}(X)$. The problem becomes $\min\sum_i f_i(x_i)+g(\sum_i x_i)$, and ADMM iterates [1, Sec. 7.3]

$$
x_i^{k+1} = \arg\min_{x_i} f_i(x_i)
+ \tfrac{\rho}{2}\bigl\|x_i - x_i^k + \bar x^k - \zeta^k + u^k\bigr\|^2, \tag{3.8}
$$

$$
\zeta^{k+1} = \arg\min_{\zeta} g(M\zeta)
+ \tfrac{M\rho}{2}\bigl\|\zeta - \bar x^{k+1} - u^k\bigr\|^2, \tag{3.9}
$$

$$
u^{k+1} = u^k + \bar x^{k+1} - \zeta^{k+1}, \tag{3.10}
$$

with $\bar x=\tfrac1M\sum_i x_i$. Because the problem is convex the iteration converges, and $\rho u$ is the price of the net position in each coin. In the *hub* form one node computes $\bar x$, (3.9) and (3.10).

**The cost step.**  For a target trade $\delta_a$ the minimiser of $C_a(d)+\tfrac{\rho}{2}(d-\delta_a)^2$ is $d=0$ if $|\delta_a|\le c_f/\rho$, and otherwise $d=\operatorname{sign}(\delta_a)\,\xi_a^2$ with

$$
\xi_a = \frac{-\tfrac32\psi_a
+ \sqrt{\tfrac94\psi_a^2 - 4\rho\,(c_f-\rho|\delta_a|)}}{2\rho}. \tag{3.11}
$$

The constrained steps use bracketed root searches for the gross and beta multipliers and an exact projection for the margin. A one-node general-purpose solver is the reference for verification.

**Stopping rule.**  With the primal and dual residuals $\Delta_{\mathrm p}^k=\|\bar x^k-\zeta^k\|$ and $\Delta_{\mathrm d}^k=\rho\,\|\zeta^k-\zeta^{k-1}\|$ [1, Sec. 3.3], the *relative residual* is

$$
\mathrm{res}^k=\max\Bigl(\frac{\Delta_{\mathrm p}^k}{\max(\|x^k\|,\|\zeta^k\|)},\
\frac{\Delta_{\mathrm d}^k}{\|\rho\,u^k\|}\Bigr), \tag{3.12}
$$

and the solver stops when $\mathrm{res}^k\le10^{-6}$ or at the iteration cap.

**The volatility price.**  The annual ex-ante volatility of the net position, as a share of equity, is $\hat\sigma=\sqrt{(P/H)\,X^\top\Sigma X}\,/E$. If it lies outside 2% of the target $\sigma^\ast$ (or above it when $\lambda=0$), the price is updated and the problem re-solved, at most five times:

$$
\lambda \leftarrow \max\Bigl(\bar\gamma\Bigl[\bigl(1+\lambda/\bar\gamma\bigr)
\frac{\hat\sigma}{\sigma^\ast}-1\Bigr],\,0\Bigr),
\qquad \bar\gamma=\Bigl(\sum_i 1/\gamma_i\Bigr)^{-1}. \tag{3.13}
$$

Since positions shrink roughly in proportion to $1/(\bar\gamma+\lambda)$, this step scales the total risk aversion by $\hat\sigma/\sigma^\ast$.

### 3.6 Decentralised ADMM without a central node

In the hub form three quantities are global: $\bar x$, $\zeta$ and $u$. In the decentralised form agent $i$ keeps its own copies $s_i$, $\zeta_i$, $u_i$. On an undirected graph $\mathcal{G}$, the Metropolis mixing matrix

$$
W_{ij} = \frac{1}{1+\max(\deg i,\deg j)}  \text{for } \{i,j\}\in\mathcal{E},
\qquad W_{ii} = 1-\sum_{j\ne i}W_{ij} \tag{3.14}
$$

is symmetric with rows summing to one, hence doubly stochastic. Figure 3.2 shows the five graphs used in the experiments.

**Figure 3.2.** The communication graphs of the experiments, with eight agents. They differ in mixing rate $\varsigma$ (how fast agreement spreads) and in robustness (whether honest agents can outvote a liar); only the complete graph and ring2 are robust enough for the W-MSR detector (Section 3.7). (diagram drawn in the LaTeX report)

> **Algorithm 1: Decentralised ADMM (one iteration)**
>
> Initialise $s_i=x_i^0$ for every agent $i$. Then, at each iteration:
>
>
> 1. Each agent solves its local step (3.8) against its own price $u_i$, giving $x_i^{\text{new}}$.
> 2. Tracking: $s\leftarrow W^g\,(s + x^{\text{new}} - x^{\text{old}})$, over $g$ gossip rounds.
> 3. Each agent solves the system step (3.9) from its own estimate $s_i$, giving $\zeta_i$.
> 4. Price: $u\leftarrow W^g\,(u + s - \zeta)$.

**Proposition 1 (Sum invariant).**  For every iteration $k$, $\sum_i s_i^k=\sum_i x_i^k$.

*Proof.* Since $W$ is doubly stochastic, $\mathbf{1}^\top W^g=\mathbf{1}^\top$. Hence $\mathbf{1}^\top s^{k+1}=\mathbf{1}^\top s^k+\mathbf{1}^\top x^{k+1}-\mathbf{1}^\top x^k$, and with $s^0=x^0$ the claim follows by induction. ∎

**Corollary 1.** At a fixed point, mixing drives every $s_i$ to $\tfrac1M\sum_i s_i=\bar x$ and the prices to a common value, so the fixed point satisfies the optimality conditions of (3.8)--(3.10) and is the optimum of (3.7). On the complete graph with exact mixing, Algorithm 1 is the hub algorithm.

**Why both mixing steps are needed.**  Each agent's change must enter *before* mixing; mixing first leaves each estimate off by its own last change, and on development problems this failed when the gross cap bound. The prices must also be mixed, or the agents settle on different prices and stop at a wrong point. Both were found by removing each step on random problems.

**Convergence and cost.**  One gossip round shrinks the disagreement by at most $\varsigma=|\lambda_2(W)|$, so cutting it by a factor $\eta$ takes

$$
n_\eta = \frac{\ln\eta}{\ln\varsigma} \tag{3.15}
$$

rounds: for $\eta=1/10$, 6.0 rounds at $\varsigma=0.68$, 10.3 at 0.80, 44.9 at 0.95 and 229 at 0.99. Messages per rebalance equal iterations $\times g \times 2|\mathcal{E}|$. The stopping test also requires the agents' estimates and prices to agree; without it a run can stop while agents still disagree by about 10%.

**What stays central in our experiments.**  The step sizes use the mean risk aversion (a number agreed before trading), the stopping test is evaluated by the simulator, and the restart after an isolation is applied to all agents at once. A deployment would replace these by a max-consensus over the graph and flooded notices.

### 3.7 Resilience to faults and misbehaving agents

**Fault model.**  (a) *Link failure:* each edge is down independently with probability $q_\ell$ in each gossip round. (b) *Dropout:* an agent leaves. (c) *Misbehaving agent:* an agent sends values that differ from what its algorithm would send.

**Proposition 2 (Failures that keep mixing doubly stochastic are absorbed).**  If the mixing matrix used in every gossip round is doubly stochastic, Proposition 1 and its corollary hold unchanged.

*Proof.* The proof of Proposition 1 uses only $\mathbf{1}^\top W_{(g)}=\mathbf{1}^\top$ for the matrix of each round. ∎

With link failures the Metropolis weights are recomputed on the edges that are up, which keeps them doubly stochastic: failures cost iterations, not correctness. With dropout the agent's positions are closed and the others solve the problem without it.

**W-MSR as an averaging rule.**  Each agent discards up to $F$ neighbour values above its own and up to $F$ below, and averages the rest.

**Proposition 3 (Trimmed mixing does not preserve the sum).**  There are initial values on the complete graph for which one round of W-MSR with $F=1$ changes $\sum_i s_i$.

*Proof.* Take values $(0,1,10)$. Agent 1 discards 10 and averages $\{0,1\}$ to 0.5. Agent 2 discards 10 and 0 and keeps 1. Agent 3 discards 0 and averages $\{10,1\}$ to 5.5. The sum falls from 11 to 7. ∎

Resilient consensus guarantees agreement inside the range of honest values; optimisation needs the exact sum. The two requirements conflict, so W-MSR is not used as the averaging rule (Section 6.4 confirms this).

**W-MSR as a detector.**  The same test can identify a liar. Agent $i$ marks $e_{ijc}=1$ when neighbour $j$'s value in coordinate $c$ is the one W-MSR would discard first, and computes

$$
\pi_{ij} = \frac1n\sum_{c=1}^{n} e_{ijc}. \tag{3.16}
$$

Agent $i$ flags $j$ when $\pi_{ij}\ge 0.9$ for both estimates and prices for 50 consecutive iterations; an agent flagged by more than half of its neighbours is isolated and the others restart without it. With no attacker the solver is exactly Algorithm 1. A consistent lie puts the liar beyond the honest values in nearly every coordinate; a liar whose values stay inside the honest range is not expected to be caught. For $F=1$ the W-MSR guarantees need a $(2,2)$-robust graph [5]: a ring is connected but not robust, whereas "ring2", where each agent links to two neighbours on each side, is sparse and robust.

### 3.8 Formal safety: STL monitor and supervisors

For a signal $y$ and a limit $c$, the predicate $y\ge c$ has robustness $\varrho(t)=(y(t)-c)/|c|$: positive means satisfied, negative violated, and the margin is a share of the limit so that rules are comparable; for $y\le c$ it is $(c-y(t))/|c|$. Negation, "and" and "or" take $-\varrho$, the minimum and the maximum, so an implication has robustness $\varrho(\varphi\Rightarrow\psi)=\max(-\varrho_\varphi,\varrho_\psi)$. The temporal operators are

$$
\varrho(\mathbf{G}_{[a,b]}\varphi,t)=\min_{t'\in[t+a,t+b]}\varrho(\varphi,t'),
\qquad
\varrho(\mathbf{F}_{[a,b]}\varphi,t)=\max_{t'\in[t+a,t+b]}\varrho(\varphi,t'). \tag{3.17}
$$

A $\mathbf{G}$ without an interval holds at every bar of the run. Table 3.3 lists the four rules. Their limits come from a written risk mandate fixed before any run; none was chosen by comparing returns. The signals are the 365-day drawdown and the realised 30-day volatility,

$$
\mathrm{DD}_t=\frac{E_t}{\max_{t-365\mathrm{d}<s\le t}E_s}-1,
\qquad
\sigma^{\mathrm{real}}_t=\sqrt{P}\;\operatorname{sd}\bigl(y_{t-30\mathrm{d}+1},\dots,y_t\bigr), \tag{3.18}
$$

and the solver signal is the relative residual (3.12).

**Table 3.3.** STL specifications and limits ($\hat\sigma_t$ ex-ante volatility, $\sigma^\ast_t$ target in force, $\mathrm{DD}_t$ drawdown over 365 days, $\sigma^{\mathrm{real}}_t$ realised 30-day volatility).

| Rule | Statement | Limit and reason |
|:--|:--|:--|
| $\varphi_{\mathrm{vol}}$ | $\mathbf{G}\,(\hat\sigma_t\le 1.05\,\sigma^\ast_t)$ | 5% tolerance on the 20% target |
| $\varphi_{\mathrm{dd}}$ | $\mathbf{G}\,(\mathrm{DD}_t\ge -0.15)$ | 15% over 365 days, about half of an equity market's worst one-year loss |
| $\varphi_{\mathrm{rvol}}$ | $\mathbf{G}\,(\sigma^{\mathrm{real}}_t>0.4 \Rightarrow \mathbf{F}_{[0,14\mathrm{d}]}\,\sigma^{\mathrm{real}}_t\le 0.4)$ | 40% (twice the target), recovered within 14 days |
| $\varphi_{\mathrm{solve}}$ | $\mathbf{G}\,(\text{relative residual}\le 10^{-3})$ | a portfolio off by 0.1% is immaterial against one rebalance's fee |

The *monitor* records $\varrho_\varphi(t)$ for every rule and bar and summarises it over three stress windows: May to July 2021, the May 2022 Luna collapse, and November 2022 to January 2023 (the FTX collapse). Two *supervisors* act on it and are off by default.

**Derisk.**  Let $m_t=(\mathrm{DD}_t+0.15)/0.15\in[0,1]$ be the share of the drawdown budget left. The volatility target is multiplied by

$$
\kappa(m_t) =
\begin{cases}
1, & m_t\ge \tfrac12,\\[2pt]
0.2 + 1.6\,m_t, & 0\le m_t<\tfrac12,
\end{cases} \tag{3.19}
$$

so de-risking starts with half the budget left and never goes below 20% of the target (Figure 3.3). It acts through the volatility price of Section 3.5, so the optimiser re-solves with costs included; it is not a rescale of a finished portfolio.

**Figure 3.3.** The derisk rule (3.19): the volatility target is unchanged until half of the 15% drawdown budget is used, then shrinks linearly to 20% of the target at the limit. (diagram drawn in the LaTeX report)

**Hold.**  If a solve is unsafe (not converged and relative residual above $10^{-3}$), the system trades nothing and keeps its positions.

### 3.9 One rebalance, end to end

The parts above run in a fixed order at every rebalance $t$, and every step uses only information from before $t$.

1. **Learn from the period that just ended.** Each agent records the realised information coefficient of its score, which feeds its kill rule (Section 3.3), and its (belief, return) pairs, which feed the calibration check (Section 3.4).
2. **Form beliefs.** Each agent computes its score on the tradable coins and its belief (3.1); the belief-sanity check zeroes any belief that is not finite or is extreme against the agent's own history.
3. **Update wealth.** Each account has earned its own profit since the last rebalance, subject to the floor (3.6). Wealth sets the risk aversion $\gamma_i=1/(qV_i)$, and the calibration check lowers the Kelly fraction of an agent that is demonstrably over-confident.
4. **Set the limits.** The agent sets $\mathcal X_i$ (allowed coins, capacity, margin, neutrality) and the system set $\mathcal S$ (gross cap, beta band) are built from current equity. An offline agent gets zero capacity, so its positions are closed.
5. **Set the risk budget.** The volatility target is 20% of current equity, multiplied by $\kappa(m_t)$ when the derisk supervisor is on; the volatility price starts from its value at the previous rebalance.
6. **Solve.** The joint problem (3.7) is solved by ADMM, with a hub or on the graph (Algorithm 1), with the detector when it is enabled; the volatility price is updated by (3.13) and the problem re-solved at most five times.
7. **Check and trade.** If the hold supervisor is on and the solve is unsafe, the old positions are kept. Otherwise the system trades the net trade $X-h$, whose cost is shared among the agents that traded in its direction.
8. **Hold until the next rebalance.** Positions drift with prices and pay or receive funding bar by bar, each account earns the result of its own positions, and the monitor records $\varrho_\varphi(t)$ for every rule.

The agents never see each other's beliefs: from step 6 on they exchange only estimates of the average position and prices, and the only quantity that links one rebalance to the next, apart from the positions, is each agent's wealth. Table 3.4 lists what each agent keeps to itself and what it sends.

**Table 3.4.** What each agent keeps private and what it sends in the decentralised optimiser (Algorithm 1).

| Quantity | Visibility | Role |
|:--|:--|:--|
| Card, score $z_i$, belief $\mu_i$ | private | enters only the agent's own local step (3.8) |
| Wealth $V_i$ and risk aversion $\gamma_i$ | private | sizes the agent's own stake; the step sizes use only the mean risk aversion, agreed before trading |
| Own position $x_i$ | private | enters the mixing only through the change $x_i^{\text{new}}-x_i^{\text{old}}$ added to $s_i$ |
| Estimate of the average position $s_i$ | neighbours | mixed over $g$ gossip rounds per iteration |
| Price $u_i$ | neighbours | mixed over $g$ gossip rounds per iteration |
| System step $\zeta_i$ | private | computed by each agent from its own $s_i$ (3.9) |
| Detector flags $\pi_{ij}$ | neighbours | an agent flagged by more than half of its neighbours is isolated |

### 3.10 Summary

The system is built in six layers, each answering one requirement of Table 3.1.

- **Agents.** Each agent is a written hypothesis with a card. Its belief (3.1) has a size fixed by the card, because a trailing estimate is too noisy to size a bet; evidence acts only through the kill rule, which can switch an agent off but never turn it around.
- **Market.** Each agent bets half the Kelly size of its own wealth, and wealth follows its own account (3.6). The floor keeps a failed agent alive, the calibration check scales down a demonstrably over-confident one, and the belief-sanity check removes impossible beliefs.
- **Joint optimiser.** One convex problem (3.7) turns all stakes into one portfolio. The cost is charged on the net trade, so opposing agents cancel; the volatility limit is a price, so the agent that adds risk pays for it; every shared limit is a price that agents react to without seeing each other's beliefs.
- **No central node.** With dynamic average consensus each agent keeps its own estimate of the average position and its own price. The sum of the estimates stays exact (Proposition 1), so the decentralised fixed point is the centralised optimum, and the graph's mixing rate sets how many rounds agreement takes (3.15).
- **Resilience.** Every failure that keeps the mixing doubly stochastic, such as a lost link or a departed agent, is absorbed (Proposition 2). W-MSR trimming breaks the sum (Proposition 3), so it is used only as a detector that isolates a consistent liar on a robust graph.
- **Safety.** Four STL rules with limits from a written mandate are monitored at every bar. The derisk supervisor lowers the volatility target as the drawdown budget is used up, acting through the optimiser, and the hold supervisor refuses to trade on an unsafe solve.

One rebalance runs these layers in a fixed order (Section 3.9), and every step uses only information from before the rebalance. The next chapter fixes how all of this is evaluated.

## 4. Experimental Protocol

### 4.1 Overview

This chapter fixes the data, the reference systems, the rules written before each experiment, the statistics and the way trials are counted, and lists every pre-registered gate with its outcome. It applies to every experiment in Chapters 5 to 7.

### 4.2 Data and development period

The development period runs from April 2020 to November 2025, with a 90-day warm-up before trading. The last twelve months are sealed: they are to be reported once, after the design is frozen, and no tuning and no statistic that includes them is allowed before then. All settings of Chapters 2 and 3 are fixed in advance (Appendix A).

### 4.3 Reference systems

Every decentralised, resilient or supervised variant is compared with the centralised optimiser on the same agents, data, costs and limits, or with the reference that is correct for the failure considered (for example, the centralised system without an agent that is offline). Multi-agent mechanisms are also compared with fixed-weight blends of the agents' stand-alone returns.

### 4.4 Pre-registration and disclosure

For each experiment the pass or fail rules and, where stated, the expected outcome were written before the runs. Rejected variants stay in the record and in the trial count. Two revisions changed earlier results and are reported where they occur: in E3 an agent's positions broke its declared coin set and the constraint was enforced; in E4 the volatility limit was found to use initial instead of current equity, and every affected experiment was repeated. Values from before the second revision are marked $\dagger$ and are used only for comparisons within one experiment.

### 4.5 Statistical methods

The same statistics are used in every experiment.

- **Intervals.** 90% moving-block bootstrap intervals [23]: blocks of seven days, 500 draws, 5th and 95th percentiles. Comparisons of two strategies resample the same blocks for both.
- **Alpha.** To separate skill from market exposure a strategy's net return is regressed on Bitcoin's, $y_t=\alpha+\beta_s y^{\mathrm{BTC}}_t+e_t$, and the annualised $\alpha$ is reported with its interval.
- **Skill of a score.** Its rank information coefficient (rIC), the Spearman correlation of score and next return across coins, averaged over rebalances.
- **Beta of a coin.** The least-squares slope $\hat\beta_a=\operatorname{Cov}(r_a,r^{\mathrm{BTC}})/\operatorname{Var}(r^{\mathrm{BTC}})$ over the trailing 60 days.

**Agent tests.**  The *kill rule* of Section 3.3 uses the $t$-statistic of the $n$ realised per-period information coefficients $\mathrm{rIC}_1,\dots,\mathrm{rIC}_n$ (for momentum, of the slope of returns on its score),

$$
t=\frac{\overline{\mathrm{rIC}}}{\operatorname{sd}(\mathrm{rIC})/\sqrt{n}}, \tag{4.1}
$$

and switches the agent off when $t<-2$ after $n\ge20$. The *calibration check* of Section 3.4 computes the slope of realised returns on the agent's past beliefs, $\chi_i=\sum\mu r/\sum\mu^2$ over its (period, coin) pairs, takes the upper bound $\bar\chi_i=\chi_i+1.645\,\mathrm{se}(\chi_i)$ and multiplies the agent's Kelly fraction by $\min\bigl(1,\max(0.2, 0.2+3.2\,(\bar\chi_i-0.5))\bigr)$: 1 at a slope of 0.75 or more, 0.2 at 0.5 or less.

**Fixed blends.**  A fixed blend holds the agents' stand-alone net returns at constant weights $w_i$: equal weights in the 50/50 mix, and $w_i=\sigma_i^{-1}/\sum_j\sigma_j^{-1}$ in the inverse-volatility blend, with $\sigma_i$ the stand-alone volatility of agent $i$ over the development period.

**Deflated Sharpe ratio.**  Let $\widehat{\mathrm{SR}}$ be the per-period Sharpe ratio of the best strategy over $T$ periods, with skewness $g_3$ and kurtosis $g_4$ (3 for a normal distribution); let $V_{\mathrm{SR}}$ be the variance of the Sharpe ratios of the $L$ trials and $\gamma_E\approx0.5772$ Euler's constant. Then [20]

$$
\mathrm{SR}_0 = \sqrt{V_{\mathrm{SR}}}\,\Bigl[(1-\gamma_E)\,\Phi^{-1}\bigl(1-\tfrac1L\bigr)
+ \gamma_E\,\Phi^{-1}\bigl(1-\tfrac1{Le}\bigr)\Bigr], \tag{4.2}
$$

$$
\mathrm{DSR} = \Phi\!\left(\frac{(\widehat{\mathrm{SR}}-\mathrm{SR}_0)\sqrt{T-1}}
{\sqrt{1-g_3\widehat{\mathrm{SR}}+\tfrac{g_4-1}{4}\widehat{\mathrm{SR}}^{\,2}}}\right). \tag{4.3}
$$

$\mathrm{SR}_0$ is the Sharpe ratio the best of $L$ strategies with no skill would show by luck, and $\mathrm{DSR}$ is the probability that the observed Sharpe ratio exceeds it. We require $\mathrm{DSR}\ge0.95$.

### 4.6 Trial accounting

Every variant evaluated is written to an append-only log. A strategy trial is one pair (strategy variant, bar size). Engineering variants (consensus form, network, resilience, safety) are counted separately, giving a more conservative total. $V_{\mathrm{SR}}$ is the variance of the annualised Sharpe ratios of the corrected strategy runs, divided by the periods per year.

### 4.7 Overview of the experiments

Nine experiments test the system in the order in which it was built. Table 4.1 maps each one to its hypothesis and to the section that reports it.

**Table 4.1.** The nine experiments.

| Experiment | What it tests | Hypothesis | Section |
|:--|:--|:--|:--|
| E1 | Each mechanism on simulated markets | criteria set in advance | 5.2 |
| E2 | Single-agent baseline (carry) | reproduces earlier carry | 5.3 |
| E3 | Agent roster and the market of agents | H5 | 5.4, 5.5 |
| E4 | Sensitivity to the volatility-limit specification | conclusions robust | 5.6 |
| E5 | Decentralised optimiser on real data | H1 | 6.2 |
| E6 | Network shape and communication budget | H2 | 6.3 |
| E7 | Link failures, dropout, a lying agent | H3 | 6.4 |
| E8 | STL monitoring and supervision | H4 | 6.5 |
| E9 | Final comparison and multiple-testing verdict | H6 | Ch. 7 |

### 4.8 Pre-registered gates at a glance

Table 4.2 lists every pass or fail rule that was written before a run, with its outcome, so that the failures can be found in one place. The reasons behind each outcome are given in the section of each experiment; no rule was changed after its result was known.

**Table 4.2.** Pre-registered gates and their outcomes.

| Exp. | Gate (written before the run) | Outcome |
|:--|:--|:--|
| E1 | criteria of Table 5.1 for each mechanism on simulated markets | **PASS** except over-confidence with a 2% floor (**FAIL**) and the corrupt-member guard (restated) |
| E2 | funding forecast beats the 14-day average on two of three bar sizes | **FAIL**: forecast rejected |
| E3 | H5a: momentum admitted (alpha lower bound above zero on two of three bar sizes) | **FAIL** after E4 (passed narrowly before); kept as provisional |
| E3 | H5b: market of two beats carry alone | **PASS** on all three bar sizes |
| E3 | H5c: market at least as good as the inverse-volatility blend | not rejected, not supported |
| E3 | H5d: timing by market state improves momentum | **FAIL** |
| E3 | H5e: residual reversal admitted | **FAIL** |
| E5 | Sharpe within 0.01 and final equity within 1% of the hub | **PASS** |
| E6 | A1: rank correlation of $\varsigma$ and iterations at least 0.7 for each size | **FAIL** (0.60 at four agents) |
| E6 | A2: complete graph takes exactly the hub's iterations | **PASS** |
| E6 | B1: every uncapped run within 0.02 Sharpe and 2% final equity of the hub | **PASS** |
| E7 | link failures and dropout absorbed; consistent liar isolated on a robust graph | **PASS**; plain ring fails, as predicted |
| E8 | A1: $\varphi_{\mathrm{solve}}$ always and $\varphi_{\mathrm{vol}}$ at 95% of rebalances, safety off | **FAIL** on hourly bars only |
| E8 | A2: derisk has fewer $\varphi_{\mathrm{dd}}$ violations and a shallower worst drawdown | **PASS** on 4-hourly and hourly, **FAIL** on daily |
| E8 | B1: every unsafe solve held and no honest one | **FAIL** (nine honest solves held) |
| E9 | C1: shared numbers reproduce to 0.001 Sharpe | **PASS** |
| E9 | C2: deflated Sharpe ratio at least 0.95 at $L=45$ on some bar size | **FAIL** on every bar size |

### 4.9 Summary

All decisions use the development period only; the last year stays sealed. Every variant is compared with the correct centralised reference, every rule is written before the run, intervals come from a block bootstrap, and the final verdict is corrected for the number of trials. The next three chapters report the nine experiments.

## 5. Results I: Validation, Agents and the Market of Agents

### 5.1 Overview

This chapter first checks every mechanism where the right answer is known (E1), then tests the agents and the market on real data (E2, E3) and finally checks that the conclusions survive a correction of the risk limit (E4). Sharpe ratios are net of fees, impact and funding; "daily", "4-hourly" and "hourly" refer to bar size; intervals are 90%.

### 5.2 E1: Validation on simulated markets

**Protocol.**  Each mechanism is tested where the right answer is known.

- **Joint optimiser.** Random problems with 3 to 4 agents and 6 to 10 coins, five seeds per configuration, against a one-node reference.
- **Market.** 60 simulated coins with a common factor and planted skill. A skilled agent's belief is $0.3$ times the true alpha plus noise, a noise agent's is pure noise, and an over-confident agent's is a skilled belief times 4 (an effective Kelly fraction of 2, at which expected log growth is zero). The true alpha has a standard deviation of 0.5% per period and the idiosyncratic noise 6%. Selection is expected after $T_{\mathrm{end}}=160$ periods, three times the inverse of the analytic growth gap ($\Delta G=0.0188$).
- **Model averaging.** Member error variances differing four times. Model averaging combines several models of the same hypothesis inside one agent, with a guard against a corrupt member; it was validated as a component, but none of the three agents of Section 3.3 uses it.
- **STL operators.** Checked against brute force.
- **State-dependent skill.** The estimator is run on planted regime skill (0.3 in an "on" state, 0 in an "off" state, regimes of about 33 periods).

**Table 5.1.** E1 criteria (fixed before implementation) and outcomes.

| Mechanism | Criterion | Outcome |
|:--|:--|:--|
| Joint optimiser | error $\le10^{-3}$ of a typical position on $7\times5$ problems | **PASS**: typical error $10^{-7}$; hardest case (gross cap and beta band together) about 1,100 iterations |
| Prices | non-negative, zero when slack, equal to the limit's marginal value within 5% | **PASS** |
| Netting | opposite views pay the cost of the net trade only | **PASS** |
| Capital follows its price | a tighter margin raises the best coin's share of capital | **PASS** |
| Market selects skill | skilled agents hold over half the wealth at $T_{\mathrm{end}}$ in $\ge$90% of 20 seeds | **PASS** at 160 periods |
| Market drops decayed skill | share falls after skill vanishes | **PASS** |
| Accounting | profits, cells, wealth and costs add up to $10^{-9}$ | **PASS** |
| Over-confidence punished | calibrated agent ends richer in $\ge$90% of seeds | **PASS** without a floor (18 of 20); **FAIL** with a 2% floor (6 of 20) |
| Model averaging | error-weighted beats equal weights when errors differ, not worse when equal | **PASS**: correlation with the true alpha 0.849 against 0.814; 0.854 against 0.858 |
| Guard against a corrupt member | fused belief changes by less than 10% | restated: with the guard on, the fused belief equals the honest average to $10^{-12}$ |
| STL operators | match brute force; corrupt beliefs zeroed, honest untouched | **PASS** |
| State-dependent skill | timed beats untimed on planted skill; costs little when absent | **PASS**: $+0.0020$ per period (interval 0.0009 to 0.0033); $-5.9\%$ with no dependence |

Three criteria were reformulated, each recorded with its diagnosis: one before any result was read (a ratio that became ill-posed when a position reached zero) and two after an unsuccessful run (over-confidence with a floor, and the corrupt-member guard, for which no filter can meet a 10% bound when dropping one of eight honest members already moves the fused belief by about 13%).

**Interpretation.**  Two findings constrain the design.

1. *The floor blunts selection.* Selection works: the calibrated agent's log growth (0.0141 per period) matched theory and the over-confident agent's was negative ($-0.0258$), with a ruinous period in every run. But the floor re-seeds a ruined agent with 2% of total wealth, leaving it a persistent share of 14% to 41% and making the final ranking close to a coin flip.
2. *An unlimited over-confident agent can ruin the system*: 5 of 20 seeds with a floor and 2 of 20 without were wiped out. Selection is too slow to prevent this.

The calibration check, in its first form (acting on the point estimate of the slope), removed ruin entirely but did not restore selection, so it is a risk control and not a selector. On real data that form fired falsely, because the slope's standard error exceeds 1. This led to the upper-bound form of Section 3.4, which in simulation cut ruin after period 150 from 3 of 40 runs to 1 of 40.

Consequently the margin and gross limits and the calibration check are always on, the Kelly fraction never exceeds 0.5, and the floor is kept only as a liveness device whose cost is weaker selection.

### 5.3 E2: Single-agent baseline with funding carry

**Hypothesis.**  With one agent the market is trivial, so E2 tests the engine against a known benchmark: carry, with an earlier net Sharpe ratio of 1.03, 0.99 and 0.88.

**Table 5.2.** Calibration of the carry belief (daily; $\dagger$ before the E4 correction).

| Belief design | Sharpe | Volatility | Max drawdown |
|:--|:--|:--|:--|
| (a) $\theta$ estimated from a trailing window; no volatility limit | 0.48$\dagger$ | 37% | $-63\%$ |
| (b) as (a), with a sign clip and the volatility limit | 1.24$\dagger$ | -- | -- |
| (c) $\theta$ fixed by the card; evidence only via the kill rule (final) | 1.27$\dagger$ | 15.1% | $-16.6\%$ |

**Table 5.3.** Carry alone (corrected configuration).

|   | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|
| Net Sharpe | 1.14 [0.36, 1.90] | 1.12 | 0.94 |
| Earlier carry book | 1.03 | 0.99 | 0.88 |
| Volatility | 22.6% | 19.5% | 19.0% |
| Maximum drawdown | $-27.7\%$ | $-29.8\%$ | $-31.1\%$ |
| Annual cost | 3.4% | 3.0% | 2.5% |

**Results.**  The three belief designs of Table 5.2:

- Design (a) fails for the reason of Remark 1.
- Design (b) shrinks towards the card's value with 50 pseudo-observations against at most about 18 effective ones, so the prior holds about 74% of the belief: 300 periods of rank correlation $-0.04$ still gave a positive belief, and the gain from (a) to (b) came from the sign clip alone.
- Design (c) is the final one. The carry score's rank correlation was 0.035 ($t=2.2$), 0.031 ($t=3.5$) and 0.019 ($t=3.4$) on daily, 4-hourly and hourly bars, with hit rates of 53% to 57%.

Carry reproduces and slightly exceeds the earlier result on every bar size (Table 5.3). Its profit splits into funding collected and selection of the right coins, with a market component near zero, as expected of a neutral book; it made money in every year 2020 to 2025 on daily bars. The intervals exclude zero but are wide: five years cannot tell a Sharpe of 1.0 from 1.2.

**A better funding forecast?**  A forecast of the size of funding was built from equation (2.1), with the premium following an AR(1) process around its 30-day mean. A pre-registered test with no profit compared its error with the 14-day average; it had to be better, with a bootstrap lower bound above zero, on two of three bar sizes (Table 5.4). It was significantly worse on daily and 4-hourly bars and not significantly better on hourly bars, so it was rejected before any profit was computed. A plausible reason, not tested, is that its state is the last hour's premium only, which is noisy.

**Table 5.4.** Accuracy of the funding forecast ($R^2$ against a zero forecast of cross-sectionally demeaned funding).

| Bar size | Rebalances | $R^2$ baseline | $R^2$ forecast | Outcome |
|:--|:--|:--|:--|:--|
| Daily | 141 | $-0.068$ | $-0.905$ | forecast significantly worse |
| 4-hourly | 399 | $+0.069$ | $-0.293$ | forecast significantly worse |
| Hourly | 995 | $+0.084$ | $+0.159$ | not significant |

**Interpretation.**  *Calibration matters more than combination*: with an identical signal, a belief of estimated size that can change sign loses about 60% of the Sharpe ratio (0.48 against 1.2). *Carry earns from ranking coins, not from forecasting funding*: the selection component is as large as the funding component.

### 5.4 E3a: Admission of the trading agents

**Hypotheses.**  H5a: momentum on Bitcoin and Ethereum is admissible (alpha against Bitcoin, and against Bitcoin and carry, with lower bound above zero on at least two of three bar sizes). H5d: timing momentum by market state improves it. H5e: residual reversal is admissible. Because 2020 to 2025 was a strong bull market, admission is judged on the beta-adjusted alpha, not on the stand-alone Sharpe ratio.

**Momentum.**  In the first run the agent lost money, and inspecting what it held, not only what it earned, showed why: of a mean gross position of 0.63 of equity, only 0.35 was in Bitcoin and Ethereum and about 0.28 in other coins. The optimiser used an alt-coin basket to neutralise its beta, because the one-factor risk model made that basket look cheap. The coin constraint was then enforced and the run repeated with the card unchanged; both runs count as trials. Table 5.5 gives the corrected results.

**Table 5.5.** Momentum alone.

|   | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|
| Net Sharpe | 0.96 [0.24, 1.61] | 0.80 | 0.76 |
| Volatility | 13.3% | 14.5% | 15.3% |
| $\alpha$ vs Bitcoin | +9.2% [+0.2, +17.7] | +9.1% [$-0.9$, +18.5] | +9.2% [$-2.7$, +19.7] |
| $\alpha$ vs Bitcoin and carry | +8.6% [$-0.3$, +17.3] | +8.5% [$-1.5$, +18.0] | +9.0% [$-2.8$, +19.4] |

H5a is *not supported*: the alpha is stable at about +9% a year, but its lower bound is above zero only on daily bars. The rule was not overridden: momentum is kept as a *provisional* agent, recorded as not admitted, because the coordination experiments need a realistic second agent, and no result claims a stand-alone edge for it. Its profit is concentrated in 2020 and 2021.

**Timing.**  The card's coefficient was made state-dependent, with a bull state and a panic state from Bitcoin returns, shrunk towards the card by a ridge prior; a coefficient of the wrong predicted sign is set to zero. H5d is *rejected* (Table 5.6): timed momentum was slightly but significantly worse on two bar sizes, and the pair with carry was unchanged. The test has little power, so the finding is that this estimator detects nothing in this sample, not that skill is state-independent.

**Table 5.6.** Timed against untimed momentum ($\dagger$; both runs share one engine).

|   | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|
| Untimed momentum | 1.06$\dagger$ | 0.95$\dagger$ | 0.90$\dagger$ |
| Timed momentum | 1.03$\dagger$ | 0.90$\dagger$ | 0.86$\dagger$ |
| Paired difference | $-0.03$ [$-0.05$, $-0.01$] | $-0.05$ [$-0.09$, $-0.02$] | $-0.05$ [$-0.13$, $+0.04$] |
| Carry + momentum, untimed $\to$ timed | 1.594 $\to$ 1.597 | 1.619 $\to$ 1.629 | 1.567 $\to$ 1.580 |

**Reversal.**  Admission required, on two of three bar sizes:

- (a) a stand-alone Sharpe lower bound above zero;
- (b) an rIC with $t>2$;
- (c) an alpha against Bitcoin, carry and momentum with lower bound above zero.

H5e is *rejected*: (a) and (c) fail on every bar size and (b) passes only on 4-hourly and hourly bars. The signal is real (rIC 0.025, 0.042, 0.046 with $t$ of 1.5, 4.4 and 7.3), but turnover of 45, 79 and 91 times equity a year meets a superlinear impact cost (5.9% to 9.5% of equity a year), and the agent loses on every bar size (Sharpe $-0.66$, $-1.17$, $-0.99$; alpha $-12\%$ to $-23\%$ a year). Its rIC is highest in the *middle* liquidity tercile (on daily bars 0.048 against 0.037 and $-0.024\dagger$), so the "stronger in less liquid coins" mechanism is not supported here. Reversal is kept as the bad agent against which the market is tested.

### 5.5 E3b: Value of the market of agents

**Hypotheses.**  H5b: the market of carry and momentum beats carry alone. H5c: the market is at least as good as a fixed inverse-volatility blend of the same agents' stand-alone returns. (Chapter 7 also reports a plain 50/50 mix, a different blend.) Stated beforehand: with fixed card sizes and slowly moving wealth, the market should behave like a fixed mix.

**Table 5.7.** The market of agents against its alternatives (paired differences with 90% intervals).

|   | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|
| Carry alone | 1.14 | 1.12 | 0.94 |
| Market of carry and momentum | 1.39 [0.61, 2.09] | 1.48 | 1.48 |
| &nbsp;&nbsp;&nbsp;&nbsp;minus carry alone | +0.26 [+0.04, +0.47] | +0.36 [+0.04, +0.68] | +0.55 [+0.13, +0.92] |
| &nbsp;&nbsp;&nbsp;&nbsp;minus inverse-volatility blend | $-0.07$ [$-0.45$, +0.32] | +0.14 [$-0.19$, +0.48] | +0.29 [$-0.05$, +0.65] |
| Market of three (with reversal) | 1.26 [0.52, 1.97] | 1.34 | 1.33 |
| &nbsp;&nbsp;&nbsp;&nbsp;minus market of two | $-0.14$ [$-0.29$, +0.02] | $-0.14$ [$-0.31$, +0.02] | $-0.15$ [$-0.27$, $-0.04$] |
| &nbsp;&nbsp;&nbsp;&nbsp;minus inverse-volatility blend of three | +0.35 [$-0.17$, +0.84] | +0.86 [+0.31, +1.35] | +0.88 [+0.34, +1.39] |
| Reversal's final wealth share | 1.9% | 1.8% | 2.0% |

**Results.**

- H5b is *supported* on all three bar sizes.
- H5c is *not rejected but not supported*: against a fixed blend of carry and momentum the market leads by 0.14 and 0.29 on the faster bars, but no interval excludes zero, so its gain over carry alone is diversification, which a fixed mix gives equally.

With the losing reversal agent in the roster, however, the market is clearly better than a fixed blend of the same three agents (+0.86 and +0.88 on 4-hourly and hourly bars, intervals above zero): it cut reversal to the 2% floor, where its account lost 7% to 9% of initial equity a year, while the blend kept paying for its losses; trading cost was 2.4% to 2.9% a year for the market against 2.5% to 3.5% for the blend. Figure 5.1 shows the same picture year by year: the main system beat carry alone in five of the six years (all except 2022), while reversal lost money in five of them.

**Figure 5.1.** Yearly net return on daily bars, corrected configuration: the three agents alone and the main system (the market of carry and momentum). Source: experiment 018. (see the PDF report)

**Interpretation: when does a market of agents help?**  A fixed blend holds each agent at a constant weight; the market holds agent $i$ at $V_i/\sum_j V_j$, and by (3.6) an agent with persistently negative returns loses share geometrically until it reaches the floor. When all agents are good the growth gap between them is small and wealth moves slowly compared with noise, so the market behaves like a fixed mix. When one agent is bad the gap is large and the market removes it within the sample. The market's value is therefore *protection from failure, not extra return*, limited by how fast selection acts (E1).

### 5.6 E4: Sensitivity to the volatility-limit specification

**What went wrong.**  A review of realised volatility by year showed that the system did not meet its 20% mandate: carry plus momentum fell from 20% in 2021 to 8% in 2025. The ex-ante volatility was measured in units of *initial* equity while stakes scale with *current* wealth, so a system that had grown by a factor $m$ was held to an effective limit of $20\%/m$, and a losing agent was granted far more.

**What was done.**  Volatility is now measured as a share of current equity, and every affected run of E2 and E3 was repeated on all three bar sizes with the rules applied as written. Two earlier tests were not repeated: the funding-forecast test of E2, whose rejected code had been removed, and the timing comparison of E3, whose verdict stands as a comparison under the old specification.

**Table 5.8.** Net Sharpe ratio before ($\dagger$) and after the correction. Carry's daily value before the correction (1.26) is the re-run on the final solver; Table 5.2 reports the first run of the same design (1.27).

| Run | Before $\dagger$ | After | Daily interval after |
|:--|:--|:--|:--|
| Carry | 1.26 / 1.15 / 1.00 | 1.14 / 1.12 / 0.94 | [0.36, 1.90] |
| Momentum | 1.06 / 0.95 / 0.90 | 0.96 / 0.80 / 0.76 | [0.24, 1.61] |
| Reversal | $-0.57$ / $-1.08$ / $-0.83$ | $-0.66$ / $-1.17$ / $-0.99$ | [$-1.29$, $-0.03$] |
| Carry + momentum | 1.59 / 1.62 / 1.57 | 1.39 / 1.48 / 1.48 | [0.61, 2.09] |
| Market of three | 1.42 / 1.39 / not run | 1.26 / 1.34 / 1.33 | [0.52, 1.97] |

**Results.**  Every multi-agent run now sits at 18% to 21% realised volatility in every year; the main system's annual growth rose from 18--22% to 29--31%. Sharpe ratios fell by 0.03 to 0.20 because running at full risk costs more under a superlinear impact term. Of all pre-registered verdicts, only one changed: momentum's admission, which had passed narrowly and now fails, because its intervals widened with its volatility while its alpha estimate barely moved. That one plausible change in a risk specification can flip a decision motivates the multiple-testing analysis of Chapter 7.

### 5.7 Summary

Every mechanism behaves as designed on simulated markets, except that the 2% floor weakens the selection of over-confident agents. On real data, carry is a solid edge, momentum is marginal and kept as provisional, reversal loses after costs, and timing does not help. The market of agents equals a fixed mix of good agents and protects against a bad one. After the risk-limit correction only momentum's admission changed. Table 5.9 collects the evidence on each agent. The next chapter turns to the multi-agent machinery: coordination, resilience and safety.

**Table 5.9.** The three agents at a glance (corrected configuration; daily / 4-hourly / hourly).

| Agent | Skill of the score | Net Sharpe | Verdict |
|:--|:--|:--|:--|
| Carry | rIC 0.035 / 0.031 / 0.019 ($t$ 2.2 / 3.5 / 3.4) | 1.14 / 1.12 / 0.94 | the solid edge; reproduces the earlier carry book; profitable in every year 2020 to 2025 |
| Momentum | alpha about $+9\%$ a year on every bar size | 0.96 / 0.80 / 0.76 | not admitted (lower bound above zero only on daily bars); kept as a provisional second agent |
| Reversal | rIC 0.025 / 0.042 / 0.046 ($t$ 1.5 / 4.4 / 7.3) | $-0.66$ / $-1.17$ / $-0.99$ | rejected: a real signal eaten by turnover and impact; kept as the bad agent the market is tested against |

## 6. Results II: Coordination, Resilience and Safety

### 6.1 Overview

This chapter tests whether the hub can be removed (E5), how network shape and communication budget matter (E6), how the system survives failures and a lying agent (E7), and whether formal safety monitoring and supervision work (E8).

### 6.2 E5: Decentralised optimisation on real data

**Protocol.**  On development problems with 3 and 8 agents the complete-graph result equalled the hub's to $10^{-15}$. The real-data test uses three agents (carry, momentum, reversal), daily bars and the same data and settings as the hub run. The graphs are the complete graph and the line, with $g=1$ and $g=3$ gossip rounds: with three agents a ring is the complete graph, so the line is the only sparse graph possible. Rule, written before the runs: Sharpe within 0.01 and final equity within 1% of the hub.

**Table 6.1.** Hub against decentralised runs (daily, three agents).

| Run | Sharpe | CAGR | Final equity | Capped | Mean iterations |
|:--|:--|:--|:--|:--|:--|
| Hub | 1.258 | 25.9% | 3.564 | 21 | -- |
| Graph, complete | 1.257 | 25.9% | 3.560 | 22 | 1,504 |
| Graph, line, $g=1$ | 1.256 | 25.8% | 3.554 | 43 | 2,011 |
| Graph, line, $g=3$ | 1.257 | 25.9% | 3.559 | 24 | 1,554 |

**Results.**  H1 is *supported*: Sharpe within 0.002 and final equity within 0.3% of the hub on every graph, and every agent's account is the same to three decimals. The small remaining differences come from solves stopped at the iteration cap, which even the hub reaches at 21 of 135 rebalances, so they are a property of the problem and not of decentralisation. On the line with one round the cap is reached twice as often; three rounds restore the hub's level, as the mixing rate predicts.

### 6.3 E6: Network topology and communication budget

**Theory.**  By (3.15), cutting disagreement tenfold takes 5.9 rounds on a random graph of eight agents ($\varsigma=0.68$), 10.6 on a ring (0.80), 17.2 on a star (0.88) and 44.2 on a line (0.95). With Metropolis weights the centre of a star is a bottleneck, so its algebraic connectivity overstates its speed; $\varsigma$ is expected to predict better.

**Protocol.**

- **Part A.** Simulated problems with every limit binding: 4, 8 and 16 agents; complete, ring, line, star and random graphs; 1, 3 and 10 rounds. Gate A1: at $g=3$, the rank correlation between $\varsigma$ and iterations is at least 0.7 for each size.
- **Part B.** Real data, daily, with eight agents that are parameter variants of the three hypotheses (carry with 7, 14 and 30 days; momentum with 15, 30 and 60 days; reversal with 3 and 7 days), used only to study coordination. Gate B1: every uncapped graph run is within 0.02 Sharpe and 2% final equity of the hub.

**Figure 6.1.** Median iterations to converge on simulated problems, three gossip rounds (cap 4,000). Hatched bars did not converge within the cap. Source: E6 Part A. (see the PDF report)

**Results, Part A.**  Gate A1 *fails*: the correlations are 0.60, 0.90 and 0.78 at 4, 8 and 16 agents. At four agents the graphs differ little and the difficulty of each problem dominates (one problem needed about 830 iterations on every graph, including the complete one). Within each problem the ordering is as predicted (mean correlation 0.79, 0.96, 0.82), but that was not the pre-registered statistic, so the gate is reported as failed.

Figure 6.1 shows the pattern at 8 and 16 agents: sparse graphs need far more iterations, and the line does not converge. The sanity check A2 passes: the complete graph takes exactly the hub's iterations. One round minimises messages on the complete graph and three rounds elsewhere; ten rounds waste messages once mixing is no longer the bottleneck.

After a fixed number of iterations the error of the net position is almost the same on every graph (eight agents: about 0.40 after 25 iterations, 0.16 after 100, below 0.001 after 400): early iterations are limited by ADMM itself, and the graph decides how long the final, precise part takes.

**Figure 6.2.** Real data, eight agents, daily: every network gives the hub's Sharpe ratio (left, dashed line); what changes is the communication (right). Source: E6 Part B. (see the PDF report)

**Table 6.2.** Real data, eight agents, daily (135 rebalances; cap 3,000 iterations unless stated).

| Run | Sharpe | Equity vs hub | Capped | Iterations | Messages |
|:--|:--|:--|:--|:--|:--|
| Hub | 1.240 | -- | 27 | 1,427 | -- |
| Complete, $g=1$ | 1.239 | $-0.02\%$ | 29 | 1,459 | 81,716 |
| Ring, $g=1$ | 1.238 | $-0.16\%$ | 114 | 2,885 | 46,160 |
| Ring, $g=3$ | 1.239 | $-0.08\%$ | 43 | 1,870 | 89,755 |
| Line, $g=3$ | 1.238 | $-0.22\%$ | 122 | 2,949 | 123,854 |
| Star, $g=3$ | 1.240 | $-0.01\%$ | 96 | 2,743 | 115,194 |
| Hub, 200-iteration cap | 1.217 | $-2.8\%$ | 135 | 200 | -- |
| Ring, $g=3$, 200-iteration cap | 1.212 | $-3.5\%$ | 135 | 200 | 9,600 |

**Results, Part B.**  Gate B1 *passes*: every uncapped run is within 0.002 Sharpe and 0.23% of the hub's final equity (Figure 6.2, Table 6.2). Messages vary 2.7 times between the ring with one round and the line. The pre-registered recommendation rule picks the graph with the fewest messages whose capped rebalances stay within the hub's count plus 10% of rebalances, that is at most $27+13.5=40.5$. Only the complete graph with one round qualifies (29); the ring with three rounds just misses (43), and the ring with one round, which uses the fewest messages, is capped 114 times. The complete graph with one round is therefore the default for later experiments, and because link failures on a complete graph are a weak test, E7 also uses a sparse graph. A 200-iteration budget costs about 3% of final equity.

**Interpretation.**  *Network shape governs the communication, not the outcome.* The mixing rate predicts iterations when graphs differ enough (8 and 16 agents) and predicts better than algebraic connectivity. Removing the hub costs computation that grows with the number of agents, because each agent solves the system step itself.

### 6.4 E7: Resilience to link failures, dropout and lying agents

**Hypotheses.**  H3(i): link failures and dropout are absorbed (Proposition 2). H3(ii): a consistent liar is isolated on a robust graph and the others reach the optimum without it. H3(iii): W-MSR trimming does not preserve the optimum (Proposition 3).

**Protocol.**

- **Part A.** Simulated problems with eight agents on the complete graph, ring2 and the plain ring; the liar (agent 3) holds nothing, so the correct answer is the optimum without it.
- **Part B.** Real data with the eight agents of E6: 30% of links down; the largest agent (a carry variant) offline from 1 May to 31 August 2022; a momentum variant adding 0.01 to everything it sends, with the detector on.

Detector parameters were fixed on development problems before the rules were written.

**Table 6.3.** E7 Part A: outcomes on simulated problems.

| Test | Outcome |
|:--|:--|
| Link failures (10%, 30%) | **PASS**: error at most $5.5\times10^{-6}$; every run converged even with half the links down |
| Constant liar, detector on | **PASS**: 18 of 18 runs isolated only the liar; error at most $4.4\times10^{-6}$; no false alarm without a liar |
| Plain ring | **FAIL**, as predicted: in all nine liar runs honest agents were isolated (in one the liar was not), which disconnected the ring |
| Undefended liar ($d=0.01$) | error 5.5 to 5.9 typical positions after 1,000 iterations; no convergence |
| Noise liar, detector on | isolated in 1 of 6 runs; otherwise no convergence |
| Trimmed mixing, no attacker | no run converged; error 0.5 to 4.8 typical positions; **rejected** |

**Table 6.4.** E7 Part B: real data (daily, eight agents).

| Run | Sharpe | Final equity | Against the reference |
|:--|:--|:--|:--|
| Hub | 1.240 | 3.578 | -- |
| Complete, 30% of links down | 1.239 | 3.577 | within 0.001 of the hub |
| Ring, 30% of links down | 1.239 | 3.575 | within 0.001 of the hub |
| Hub, largest agent offline | 1.225 | 3.476 | the reference for dropout |
| Complete, largest agent offline | 1.225 | 3.476 | equals its reference |
| Complete, detector on, no liar | 1.239 | 3.577 | nobody isolated |
| Complete, liar, detector on | 1.182 | 3.391 | liar isolated at the first rebalance, nobody else ever |
| Hub without the liar | 1.182 | 3.392 | the reference for the liar |

**Table 6.5.** Median iterations under link failures (eight agents, simulated).

| Graph | $q_\ell=0$ | 0.1 | 0.3 | 0.5 |
|:--|:--|:--|:--|:--|
| Complete, $g=1$ | 187 | 215 | 262 | 288 |
| Ring2, $g=3$ | 193 | 214 | 235 | 265 |
| Ring, $g=3$ | 439 | 513 | 700 | 1,075 |

**Further observations.**  In all three offline runs the highest ex-ante volatility inside the window was 17.5%, against 20.9% outside it, so dropout did not raise risk. The undefended liar on real data was not completed: with the lie every solve ran to the iteration cap and the volatility search repeated it up to five times, so its cost is shown only on simulated problems.

**Interpretation.**

- (i) *Link failures and dropout are absorbed.* With weights recomputed on the surviving links, the optimiser reaches the same answer, on real data to within 0.001 Sharpe. The cost is communication (Table 6.5): on the ring, 30% failures raise iterations by about 60% on simulated problems, and by about 15% on real data. The money lost in a defended failure comes from what is missing, not from the coordination: four months without the largest agent, which held 38% of final wealth, cost 0.015 Sharpe against the full system, and leaving out the lying agent cost 0.058 Sharpe, mostly because its capital then sits idle.
- (ii) *The detector works on robust graphs.* A consistent liar was caught from 4% of a typical position upward, with no false alarm, and the result was exactly that of the system without it. On the plain ring honest agents were isolated too, as the robustness condition predicts. A plausible explanation, not tested, is that with only two neighbours a single deviating neighbour is already a majority.
- (iii) *Trimming fails as an averaging rule*, as Proposition 3 predicts.

A *stealthy liar* whose noise stays inside the honest range gets through, and the solver then fails to converge. This non-convergence is observable, which motivates the hold supervisor of E8.

### 6.5 E8: Safety monitoring and supervision

**Hypotheses.**  H4(i): the monitor shows the system's margin to its rules through stress periods. H4(ii): derisk reduces breaches of the drawdown rule. H4(iii): hold prevents trading on corrupted solutions without acting on honest ones. Both supervisors act through what the optimiser already has, the volatility target and the decision to trade: a shield that scales the finished portfolio re-trades the whole book (Section 1.3), and a drawdown constraint has no clean form inside the optimiser because a drawdown is a property of a path.

**Protocol.**

- **Part A.** The main system (carry plus momentum, centralised), with safety off and derisk on every bar size. Gate A1: with safety off, $\varphi_{\mathrm{solve}}$ always holds and $\varphi_{\mathrm{vol}}$ at at least 95% of rebalances. Gate A2: derisk has fewer bars violating $\varphi_{\mathrm{dd}}$ and a shallower worst drawdown.
- **Part B.** A stealthy liar: reversal adds normal noise (standard deviation 0.01) from May to July 2022 only, with and without hold. Gate B1: every unsafe solve is held and no honest one is.

The implementation was first checked in a smoke test on the first 900 days of daily data, in which derisk acted (target down to 0.32 of its value) and hold never triggered; no setting was changed afterwards, and the smoke test is not counted as a trial.

**Table 6.6.** Safety modes on the main system.

| Mode | Metric | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|:--|
| Off | Sharpe | 1.394 | 1.478 | 1.483 |
|  | CAGR | 31.2% | 29.8% | 29.2% |
|  | worst 365-day drawdown | $-23.7\%$ | $-24.4\%$ | $-25.9\%$ |
|  | bars with drawdown below $-15\%$ | 211 | 2,223 | 7,695 |
|  | rebalances with $\hat\sigma\le1.05\sigma^\ast$ | 97.8% | 97.6% | 94.3% |
|  | worst volatility margin | $-0.5\%$ | $-3.0\%$ | $-10.0\%$ |
|  | unsafe solves | 0 | 0 | 0 |
| Derisk | Sharpe | 1.277 | 1.275 | 1.462 |
|  | CAGR | 23.9% | 21.0% | 24.3% |
|  | worst 365-day drawdown | $-19.7\%$ | $-18.8\%$ | $-16.7\%$ |
|  | bars with drawdown below $-15\%$ | 229 | 2,159 | 5,135 |
|  | lowest volatility multiplier $\kappa$ | 0.2 | 0.2 | 0.2 |
| Hold | Sharpe; rebalances held | 1.394; 0 | -- | -- |

**Results, Part A.**

- **Gate A1 fails on hourly bars only.** $\varphi_{\mathrm{vol}}$ holds at 94.3% of rebalances, with breaches up to 10% over the limit, because the volatility-price search (at most five re-solves) lags a covariance that moves fast between hourly rebalances.
- **Gate A2 fails on daily bars and passes on the others.** Derisk always makes the worst drawdown shallower (by 4 to 9 points), but on daily bars it has more bars below $-15\%$ (229 against 211): smaller positions after a loss recover more slowly, so the account stays below the line longer, although it never falls as far.
- **Cost of derisk.** 0.12, 0.20 and 0.02 Sharpe and 7.3, 8.8 and 4.9 points of annual growth on daily, 4-hourly and hourly bars.
- **Stress windows.** The rules were tightest in the FTX collapse, not in May 2021 or Luna as we expected. In those two windows the system made money (7% to 16%, drawdown inside the window at most 8.5%) and derisk did not act. FTX is the only window in which $\varphi_{\mathrm{dd}}$ is violated (1 daily, 444 4-hourly and 1,741 hourly bars with safety off). There derisk acts: on 4-hourly bars the drawdown inside the window falls from 8.5% to 2.0% and the volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%); on hourly bars the drawdown falls from 12.6% to 2.8%.
- **Recovery rule.** $\varphi_{\mathrm{rvol}}$ is violated only on daily bars (34 bars with safety off, 28 with derisk) and never inside a stress window.

**Table 6.7.** E8 Part B: hold against a noise liar (daily; the window is May to July 2022).

| Run | Sharpe | Final equity | Return in window | Worst drawdown in window | Unsafe solves | Held |
|:--|:--|:--|:--|:--|:--|:--|
| (a) no liar | 1.257 | 3.56 | 11.7% | $-3.0\%$ | 8 (2025) | 0 |
| (c) liar, hold | 1.033 | 2.77 | 6.7% | $-5.8\%$ | 15 | 15 |
| (b) liar, no defence | diverges at the first attacked rebalance |  |  |  |  |  |

**Results, Part B.**  Without a supervisor the attacked solve diverges (Table 6.7): at the first attacked rebalance the relative residual is 1.32 against the limit $10^{-3}$, the iterates grow from 0.4 to 44 within 700 iterations, and one 3,000-iteration solve takes about 45 minutes, so a complete undefended run was not obtained.

Gate B1 *fails*: all six attacked rebalances were held (residuals 1.18 to 1.62), but so were nine honest rebalances in 2025, whose slow convergence gave residuals of 0.0013 to 0.0059; the clean run (a) has eight such slow solves and traded them. The fixed limit $10^{-3}$ cannot separate an attack (residuals above 1) from slow honest convergence (about 0.003); a better limit exists but was not tuned after seeing the result.

The false alarms cost more than the attack: frozen for most of May to October 2025, stale positions drifted to an ex-ante volatility of up to 31%, and the Sharpe ratio fell from 1.26 to 1.03.

**Interpretation.**  The monitor is informative: it showed where the system was in danger and found a window we had not predicted. Derisk works as designed and exposes a trade-off between the depth and the duration of drawdowns. Hold stops a stealthy liar but also freezes honest slow solves, so detection (consistent liars) and hold (noisy ones) are each incomplete alone.

### 6.6 Summary

The decentralised optimiser reproduces the hub on real data; network shape decides the communication, not the result; link failures, dropout and a consistent liar on a robust graph cost nothing in money; W-MSR trimming breaks the optimiser but the W-MSR test is a good detector; a stealthy liar gets through. The safety monitor is informative, derisk makes the worst losses shallower at a cost, and hold needs a better limit. Three pre-registered gates failed and are reported as failures. Table 6.8 collects the main numbers of the chapter. The next chapter puts all results in one comparison.

**Table 6.8.** Coordination, resilience and safety at a glance (real data, daily unless stated).

| Test | Result | Against the reference |
|:--|:--|:--|
| No central node (E5) | graphs 1.256 to 1.257 Sharpe | hub 1.258; within 0.002 |
| Network shape (E6) | 46k to 124k messages per rebalance | every uncapped graph within 0.002 Sharpe of the hub |
| 30% of links down (E7) | 1.239 Sharpe on the complete graph and the ring | hub 1.240; within 0.001 |
| Largest agent offline (E7) | 1.225 Sharpe | equals the hub without it |
| Consistent liar, detector on (E7) | liar isolated at the first rebalance, nobody else ever; 1.182 Sharpe | equals the hub without the liar |
| Derisk supervisor (E8) | worst drawdown $-16.7\%$ (hourly), $-19.7\%$ (daily) | $-25.9\%$ and $-23.7\%$ with safety off, at 0.02 to 0.20 Sharpe |
| Hold against a noise liar (E8) | all six attacked solves held, nine honest ones too; 1.033 Sharpe | 1.257 without the liar |

## 7. Final Evaluation and Multiple-Testing Verdict

### 7.1 Overview

This chapter answers three questions on one consistent footing: how much money each system makes after all costs, what each multi-agent feature costs and buys, and whether the main system's Sharpe ratio survives the correction for the 45 strategy trials behind it.

### 7.2 Evaluation protocol

No new simulation and no new setting: the saved runs of E4 to E8 and the trial log are read. The rules were written before the table was computed.

**Trial count.**  The strategy variants are carry in three belief designs, carry with the funding forecast, momentum before and after enforcing its coin set, the market of two with each, timed momentum with its market, reversal, the market of three, and the corrected re-runs of five runs (E4).

- Pre-registered count: 15 variants on 3 bar sizes, $L=45$.
- Trial register: 16 variants, $L=48$.
- Conservative count, adding 29 engineering variants: $L=74$.

Any of these counts leaves the verdict unchanged, because the deflated Sharpe ratio passes only for $L\le2$.

**Gates.**

- C1: every number shared with an earlier experiment reproduces to 0.001 Sharpe.
- C2: the deflated Sharpe ratio of the main system is at least 0.95 at $L=45$ on some bar size.

### 7.3 Performance after all costs

Gate C1 *passes*. Figure 7.1 and Table 7.1 give the net Sharpe ratios.

**Figure 7.1.** Net Sharpe ratio with 90% block-bootstrap interval. Dots are estimates, bars are intervals, the dark line is zero. Source: E9, table T1. (see the PDF report)

**Table 7.1.** Net Sharpe ratio with 90% interval (T1).

|   | Daily | 4-hourly | Hourly |
|:--|:--|:--|:--|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [$-0.03$, 1.44] |
| Reversal | $-0.66$ [$-1.29$, $-0.03$] | $-1.17$ [$-1.81$, $-0.48$] | $-0.99$ [$-1.63$, $-0.32$] |
| **Main system** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 mix | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

The main system (the market of carry and momentum) earns 31.2%, 29.8% and 29.2% a year at a volatility of 21%, 19% and 18%, with a worst drawdown of $-23.7\%$, $-24.4\%$ and $-25.9\%$. Reversal loses on every bar size, with its whole interval below zero. A fixed 50/50 mix does about as well as the main system: with good agents the market adds no return. Every interval is wide: five and a half years is not much data.

### 7.4 Cost and benefit of each multi-agent feature

Each figure in Table 7.2 comes from running the same system with and without the feature.

**Table 7.2.** The price and the benefit of each multi-agent feature.

| Feature | What it costs | What it buys |
|:--|:--|:--|
| No central node | messages vary up to 2.7 times with the network shape (line against ring) | no central computer that can fail; same portfolio within 0.002 Sharpe |
| Resilience | at most 0.001 Sharpe | the system keeps working through 30% link failures, an offline agent and a consistent liar |
| Derisk supervisor | 0.02 to 0.20 Sharpe | worst drawdown $-25.9\%\to-16.7\%$ (hourly), $-23.7\%\to-19.7\%$ (daily) |
| Market of agents | no significant cost | +0.86 / +0.88 Sharpe over a fixed mix on 4-hourly / hourly bars when one agent is bad |

In one line: decentralisation and resilience cost messages, safety costs return, and the market of agents buys protection against a bad agent.

### 7.5 Multiple-testing correction: the deflated Sharpe ratio

When only the best of many tries is shown, luck can look like skill: among 45 people flipping a coin ten times, someone will get eight or nine heads. The deflated Sharpe ratio asks whether the main system's Sharpe ratio is higher than what the best of 45 trials with no skill would show by chance (equations (4.2)--(4.3)).

**Table 7.3.** Deflated Sharpe ratio of the main system (gate C2: at least 0.95).

| Bar | Sharpe | $g_3$ | $g_4$ | DSR, $L=45$ | DSR, $L=74$ | C2 |
|:--|:--|:--|:--|:--|:--|:--|
| Daily | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 | **FAIL** |
| 4-hourly | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 | **FAIL** |
| Hourly | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 | **FAIL** |

**Figure 7.2.** Deflated Sharpe ratio of the main system against the number of trials. The same Sharpe ratio would pass at one or two trials and falls to 0.07--0.10 at our 45. Source: E9, table T5. (see the PDF report)

**Results.**  Gate C2 *fails on every bar size* (Table 7.3). With $V_{\mathrm{SR}}=0.82$ (the 15 corrected strategy runs, from $-1.17$ to $1.48$), the luck bar $\mathrm{SR}_0$ is about 2.0 in annual terms, above the main system's 1.39 to 1.48. The deflated Sharpe ratio is above 0.95 only for $L\le2$ and is 0.47 to 0.55 at $L=10$ (Figure 7.2).

**Why the correction is so large.**  Four things make the test strict here: many trials (45); widely spread results, because the roster deliberately contains a bad agent; a short history; and fat tails ($g_4$ between 11 and 29), which the denominator of (4.3) penalises.

**What it means.**  H6 is rejected. This is a statement about the evidence on the development period, not proof that the system has no edge: carry's interval is above zero on every bar size, and the sealed final year, never examined, is the independent test that the correction cannot replace. It does not affect the comparison of mechanisms, which is made on the same strategy on both sides.

### 7.6 Answers to the research questions

Table 7.4 brings the evidence of Chapters 5 to 7 together and answers the five research questions of Section 1.4, including the parts where a hypothesis or a pre-registered gate failed.

**Table 7.4.** Answers to the research questions.

|   | Answer | Evidence |
|:--|:--|:--|
| RQ1 | Yes. The neighbour-only optimiser matches the hub to 0.002 Sharpe, and every decentralised or resilient variant stays within 0.002 of its reference. A supervised variant does not (hold against a noise liar: 1.033 against 1.257). | E5, E9 |
| RQ2 | Network shape governs communication, not outcome. $\varsigma$ predicts iterations at 8 and 16 agents but not reliably at 4. A short budget costs about 3% of final equity. | E6 |
| RQ3 | Link failures and dropout are absorbed because the sum invariant survives them. Trimming breaks the invariant; the W-MSR test isolates a consistent liar on robust graphs, not on a plain ring and not against noise. | E7 |
| RQ4 | The monitor shows the margin and found an unexpected stress window; derisk makes the worst drawdown shallower at 0.02 to 0.20 Sharpe; three gates failed; hold needs a better limit. | E8 |
| RQ5 | Carry is a solid edge, momentum marginal, reversal loses. The market equals a fixed mix of good agents and beats it when one is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone. | E3, E4, E9 |

### 7.7 Demonstration dashboard

The final demonstration uses an interactive Streamlit dashboard with six tabs: a live consensus simulator, network shape and communication, performance and agents' wealth, the STL safety record, resilience, and the final comparison. The simulator runs the decentralised optimiser of Section 3.6 live on the simulated problems of E6 and E7; the user chooses the number of agents, the network, the gossip rounds, the share of links down, a misbehaving agent and whether the detector is on. The other tabs read saved results only and never touch the sealed data. The performance and safety tabs plot saved runs from a local folder that is not part of the repository, so they are not shown here; their numbers are those of Tables 6.6 to 7.3. Figures 7.3 to 7.5 show the dashboard. It is started with:

"` uv run --group dashboard streamlit run dashboard.py "`

**Figure 7.3.** Dashboard, consensus simulator: eight agents, complete graph, one gossip round, no liar. The error against the central optimum falls steadily and the agents agree throughout. (screenshot in the PDF report)

**Figure 7.4.** Dashboard, consensus simulator: the same problem with agent 3 adding a constant 0.01 to everything it sends, detector on. Agent 3 (grey) is isolated and the others converge to the optimum without it. (screenshot in the PDF report)

**Figure 7.5.** Dashboard, network shape and communication tab: median iterations to converge and messages per solve for eight agents, by network shape and gossip rounds (E6 Part A). (screenshot in the PDF report)

**Reading the simulator.**  The two runs show the two results of Section 3.6 and Section 3.7 at work. With no liar the disagreement between the agents stays at machine precision throughout, because the sum invariant holds at every iteration, and the error against the central optimum falls steadily.

With the liar the error stays near one typical position for the 50-iteration persistence window, because the lie spreads through the mixing; once a majority of its neighbours has flagged agent 3 it is isolated, the honest agents restart without it, their disagreement drops to zero at once and the error falls as in the clean run. The extra cost of the attack is communication: about twice the iterations and the messages.

**The other tabs.**  Table 7.5 lists what each tab shows and where its data come from. Only the simulator computes anything; the other five tabs display committed result tables or saved runs, so the dashboard cannot produce a number that is not in the project records.

**Table 7.5.** The six tabs of the dashboard and the data behind them.

| Tab | What it shows | Data |
|:--|:--|:--|
| Consensus simulator | the decentralised optimiser run live; error against the central optimum and disagreement between agents at each iteration; isolated agents in grey | simulated problems of E6 and E7, computed on the spot |
| Topology and communication | median iterations to converge and messages per solve by network shape and gossip rounds, for 4, 8 or 16 agents; the real-data run on each graph | committed tables of E6 (Parts A and B) |
| Performance and agents | equity curves and statistics of the chosen runs; each agent's wealth over time, stacked | saved runs (local folder) |
| STL safety | robustness of each of the four rules over time, stress windows shaded; derisk multiplier and solver residual per rebalance, held solves in red | saved runs; committed stress-window table of E8 |
| Resilience | link failures, an offline agent and a liar, on simulated problems and on real data, each against its reference; hold against the noise liar | committed tables of E7 and E8 |
| Final comparison | tables T1 to T5 of the final evaluation | committed tables of E9 |

### 7.8 Summary

The main system earns a Sharpe ratio of 1.4 to 1.5 after all costs, but a fixed mix of the same good agents does about as well, and after correcting for 45 trials the evidence for skill is weak (deflated Sharpe 0.07 to 0.10). The multi-agent machinery, in contrast, is verified: removing the hub and surviving failures cost messages, not money; safety costs some return; and the market protects against a bad agent. The next chapter interprets these results and states what we cannot explain.

## 8. Discussion

### 8.1 Overview

This chapter draws three general lessons from the results, lists the negative results, states plainly what we cannot explain, and discusses the threats to validity.

### 8.2 Interpretation

**Information bounds what coordination can achieve.**  The value of the system was limited by the information in its agents. Carry is the only agent whose profit survives costs and scale. Reversal has a stronger signal and loses, because heavy turnover meets a superlinear impact cost. Sizing each belief by its card was worth more than any combination scheme.

**One invariant organises the decentralised results.**  Every decentralisation result follows from Proposition 1: mixing that stays doubly stochastic (link failures, dropout) keeps the optimum (Proposition 2); a rule that does not (trimming) destroys it (Proposition 3). The same observation separates two roles of W-MSR: as an averaging rule it conflicts with optimisation; as a detector it needs only a robust graph. Our reconciliation is to separate detection from averaging.

**Prices coordinate without exposing beliefs, and capital selects without evaluating.**  Agents interact only through prices of exposure, capital and trading. Pricing the volatility limit removes the cross-subsidy of a uniform rescale; costing the net trade lets opposing agents cancel. The market does not add return over a fixed mix of good agents, because wealth moves slowly compared with noise, but it removes a failing agent quickly, limited by the floor that keeps a small stake in every agent.

### 8.3 Negative and null results

A funding forecast from the premium index does not improve carry (E2). Timing momentum by market state does not help (E3). Reversal does not pay after costs (E3). W-MSR trimming cannot be the optimiser's averaging rule (E7). A hold rule with a fixed residual limit freezes honest solves (E8). The main system fails the deflated Sharpe test (E9). Each followed a rule written in advance, and none was changed after the result.

### 8.4 Open questions and unexplained findings

Some findings we can describe but not explain with confidence. We report them as open rather than defend a guess.

- **The uneven cost of derisk.** Derisk costs 0.20 Sharpe on 4-hourly bars but only 0.02 on hourly bars, although it cuts the worst drawdown more on hourly bars. We have not identified why.
- **The market against a fixed mix of good agents.** The market leads the fixed blend by 0.14 and 0.29 on 4-hourly and hourly bars and trails it by 0.07 on daily bars. All intervals include zero, so we cannot say whether this pattern is real.
- **Reversal across liquidity.** Its signal is strongest in the middle third of coins by liquidity, not in the least liquid third as its mechanism predicts. We have no explanation.
- **Isolated honest agents on the plain ring.** The agents wrongly isolated were mostly two steps from the liar, not its neighbours. Our explanation (one deviating neighbour is already a majority) is plausible but untested.
- **The failed funding forecast.** Our explanation (a noisy one-hour state) is plausible but untested.

### 8.5 Threats to validity

**Internal.**  The system is complex and its volatility limit was first mis-specified (E4); all affected experiments were repeated, but other specification errors cannot be excluded. The first momentum run is a forking path; both runs count as trials. Some quantities (step sizes, the stopping test, the restart after an isolation) are computed centrally in the experiments.

**Construct.**  Momentum's information coefficient is an assumption chosen by a mechanical check. The impact coefficient, the one-million-dollar scale and the fee were fixed and not varied. A one-factor risk model underprices books that are not tightly neutral: reversal runs at 24% to 29% volatility against a 20% limit.

**External.**  Five and a half years of data, mostly one bull market, from one exchange; momentum's profit is concentrated in 2020 and 2021. Only three hypotheses were tested; four more (cross-sectional momentum, size and illiquidity, low volatility, a machine-learning trend model) were planned and not built, and two further carry steps (a crowding term from open interest, a tail cap from high and low prices) were not run.

**Statistical.**  Intervals are wide and the number of independent periods is limited. The block bootstrap handles autocorrelation but not regime change. The trial count involves judgement, though the conclusion is insensitive to it.

**Computational.**  The decentralised solver does work that grows with the number of agents, because each agent solves the system step itself (the sixteen-agent simulations were the most demanding), and some real-data solves stop at the iteration cap even for the hub (21 to 27 of about 135 rebalances), with a small effect on profit.

### 8.6 Connection to multi-agent systems concepts

Table 8.1 maps the multi-agent ideas the project uses to the part of the system that uses them and the experiment that tests them.

**Table 8.1.** Multi-agent concepts used in the project.

| Concept | How it is used here | Where |
|:--|:--|:--|
| Average consensus, Metropolis weights | agents mix their estimates and prices with neighbours only | 3.6, E5, E6 |
| Dynamic average consensus | each agent adds its own change before mixing, so the sum of the positions is kept exactly | 3.6 |
| Mixing rate of a graph | predicts how many iterations each network needs | 3.6, E6 |
| Distributed optimisation (ADMM) | one joint problem solved by agents that exchange prices, not beliefs | 3.5, E1, E5 |
| Resilient consensus (W-MSR), robust graphs | used as a liar detector, not as the averaging rule | 3.7, E7 |
| Markets of agents (Kelly bettors) | capital moves to the agents whose beliefs pay | 3.4, E1, E3 |
| Signal temporal logic | safety rules with a robustness margin, monitored and enforced | 3.8, E8 |

### 8.7 Reproducibility

The software, the pre-registered rules, the result tables and the trial log are in the project repository; the raw data come from the exchange's public archive [22]. Results are deterministic for fixed data and settings. The guide `docs/REPRODUCING.md` gives the exact commands; `scripts/experiments/` holds one script per experiment and `run_all.sh` runs them all; `docs/experiments/` holds the numbered write-ups and `docs/decisions/` the design decisions. The figures of this report are drawn from the committed result tables. Table B.2 in Appendix B maps each part of the system to its code.

### 8.8 Summary

The results support three lessons: information, not coordination, bounds the returns; one invariant explains every decentralisation result; and prices and capital coordinate and select without sharing beliefs. Six negative results and five open questions are reported as such. The main threats are the short, bull-market history and the complexity of the system. The final chapter draws the conclusions and sets out the next steps.

## 9. Conclusion and Future Work

### 9.1 Overview

This chapter states what the project showed and what should come next.

### 9.2 Conclusions

We designed and evaluated a multi-agent trading system in which hypothesis agents stake capital in a market, are coordinated by prices in a joint ADMM, can do so without a central node, tolerate link failures, dropout and a lying agent, and are monitored by formal safety rules. The decentralised system reproduces the centralised one on every network tested and under every defended failure, because one invariant (the sum of the agents' positions) is preserved by every admissible mixing and destroyed by trimming. Failures cost communication, not return; the market protects against a bad agent; and the monitor shows where the system was in danger. The return claim is weaker: carry is a real edge and the combined system earns a Sharpe ratio of 1.4 to 1.5 at its risk limit, but after correcting for the number of variants tried, the development data alone cannot establish it. Failed gates are reported as failures, and none was changed after the result was known.

### 9.3 Future work

1. Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged.
2. Re-argue the hold supervisor's limit, for example with a rule that separates a diverging solve from a slow one, and lengthen the volatility-price search on fast bar sizes.
3. Add an alt-coin risk factor to close the risk-model gap for books that are not neutral.
4. Test two colluding liars and further hypotheses, each with a card and rules written first.
5. Move towards deployment: pre-agreed step sizes, a max-consensus stopping test, flooded isolation notices and communication delays.

### 9.4 Summary

The multi-agent mechanisms are verified on real data; the profit is not yet proven to be skill. The sealed final year is the next and decisive test.

## References

1. S. Boyd, N. Parikh, E. Chu, B. Peleato, J. Eckstein. Distributed optimization and statistical learning via the alternating direction method of multipliers. *Foundations and Trends in Machine Learning*, 3(1), 2011.
2. R. Olfati-Saber, R. M. Murray. Consensus problems in networks of agents with switching topology and time-delays. *IEEE Transactions on Automatic Control*, 49(9), 2004.
3. L. Xiao, S. Boyd, S. Lall. A scheme for robust distributed sensor fusion based on average consensus. *IPSN*, 2005.
4. M. Zhu, S. Martínez. Discrete-time dynamic average consensus. *Automatica*, 46(2), 2010.
5. H. J. LeBlanc, H. Zhang, X. Koutsoukos, S. Sundaram. Resilient asymptotic consensus in robust networks. *IEEE Journal on Selected Areas in Communications*, 31(4), 2013.
6. T.-H. Chang, M. Hong, X. Wang. Multi-agent distributed optimization via inexact consensus ADMM. *IEEE Transactions on Signal Processing*, 63(2), 2015.
7. J. L. Kelly. A new interpretation of information rate. *Bell System Technical Journal*, 35(4), 1956.
8. A. Beygelzimer, J. Langford, D. Pennock. Learning performance of prediction markets with Kelly bettors. *AAMAS*, 2012 (arXiv:1201.6655).
9. L. Blume, D. Easley. Evolution and market behavior. *Journal of Economic Theory*, 58(1), 1992.
10. I. Evstigneev, T. Hens, K. R. Schenk-Hoppé. *Evolutionary Behavioral Finance*, 2016.
11. O. Maler, D. Nickovic. Monitoring temporal properties of continuous signals. *FORMATS*, 2004.
12. A. Donzé, O. Maler. Robust satisfaction of temporal logic over real-valued signals. *FORMATS*, 2010.
13. R. Grinold. The fundamental law of active management. *Journal of Portfolio Management*, 15(3), 1989.
14. R. Koijen, T. Moskowitz, L. H. Pedersen, E. Vrugt. Carry. *Journal of Financial Economics*, 127(2), 2018.
15. S. He, A. Manela, O. Ross, V. von Wachter. Fundamentals of perpetual futures. arXiv:2212.06888, 2022.
16. T. Moskowitz, Y. H. Ooi, L. H. Pedersen. Time series momentum. *Journal of Financial Economics*, 104(2), 2012.
17. N. Jegadeesh. Evidence of predictable behavior of security returns. *Journal of Finance*, 45(3), 1990.
18. Y. Liu, A. Tsyvinski. Risks and returns of cryptocurrency. *Review of Financial Studies*, 34(6), 2021.
19. B. T\'oth, Y. Lempérière, C. Deremble, J. de Lataillade, J. Kockelkoren, J.-P. Bouchaud. Anomalous price impact and the critical nature of liquidity in financial markets. *Physical Review X*, 1, 021006, 2011.
20. D. H. Bailey, M. L\'opez de Prado. The deflated Sharpe ratio. *Journal of Portfolio Management*, 40(5), 2014.
21. C. R. Harvey, Y. Liu, H. Zhu. ... and the cross-section of expected returns. *Review of Financial Studies*, 29(1), 2016.
22. Binance. Public market data archive. <https://data.binance.vision>.
23. H. R. Künsch. The jackknife and the bootstrap for general stationary observations. *Annals of Statistics*, 17(3), 1989.
24. V. Renganathan. AI3403 Multi-Agent Systems, lecture notes, IIT Hyderabad, 2026.

## Appendix A. Settings Used Throughout

### A.1 Overview

This appendix collects in one table every setting used in the experiments, all fixed before the runs.

**Table A.1.** Settings, all fixed in advance.

| Setting | Value |
|:--|:--|
| Development period | April 2020 to November 2025; final twelve months sealed; data snapshot ending 5 November 2026 |
| Universe | 243 coins, about 63 a day; top 50 by 90-day median dollar volume, kept while in the top 75 |
| Tradability | trailing median daily volume at least one million dollars; complete history window |
| Warm-up | 90 days before trading |
| Risk model | one market factor (Bitcoin); coin variances and betas over the trailing 60 days; median dollar volume over the trailing 30 days |
| Minimum cross-section | 8 tradable coins |
| Bars and rebalancing | daily (every 14 days), 4-hourly (5 days), hourly (48 hours) |
| Costs | fee 5 basis points; square-root impact, $c_{\mathrm{imp}}=1$; capital one million dollars; capacity 5% of daily volume |
| Kelly fraction $q$ | 0.5 |
| Margin; gross cap; beta band | $3V_i$; $3E$; $0.25E$ |
| Volatility target | 20% a year as a price on system variance; at most five re-solves; 2% band |
| Wealth floor $\omega$ | 2% of total wealth |
| Card information coefficients | carry 0.02; momentum 0.05; reversal 0.02 |
| Calibration check | slope floor 0.5; 52 rebalances; at least 1,500 observations; upper confidence bound |
| Belief sanity | within six robust standard deviations of the agent's own history |
| ADMM tolerance | $10^{-6}$ (real data); $10^{-8}$ (simulated experiments) |
| Bootstrap | 7-day blocks, 500 draws, 90% interval |
| Detector | extreme in at least 90% of coordinates for 50 iterations; isolation by a majority of neighbours |
| STL limits | Table 3.3; derisk multiplier (3.19) |

### A.2 Summary

No setting in Table A.1 was tuned on returns; each was fixed by the design, a written mandate or a mechanical check before the experiments.

## Appendix B. Correspondence with the Project Records

### B.1 Overview

The repository holds a numbered write-up for each experiment, with the exact command and the committed result tables. This appendix maps the experiments of the report to those records and each part of the system to its code, so that every number in this report can be traced to a numbered write-up and a committed result table.

**Table B.1.** Experiments of this report and the project's records.

| Experiment of this report | Project records |
|:--|:--|
| Earlier systems (Section 1.3) | experiments 001 to 010 |
| Data audit (Section 2.3) | 011 |
| E1 Simulated markets | 012 |
| E2 Single-agent baseline | 013, 014 |
| E3 Agent roster and market | 015, 016, 017 |
| E4 Specification sensitivity | 018 |
| E5 Decentralised equivalence | 019 |
| E6 Network shape and budget | 020 |
| E7 Resilience | 021 |
| E8 Safety | 022 |
| E9 Final evaluation | 023 |
| Dashboard | decision 0045 |

**Table B.2.** Parts of the system and their code (all paths in the repository).

| Part of the system | Code |
|:--|:--|
| Data pipeline and universe (Section 2.3) | `mas_trade/data.py`, `mas_trade/panel.py`, `download_data.py` |
| Hypothesis agents (Section 3.3) | `mas_trade/agents/` |
| Market of agents and cost sharing (Section 3.4) | `mas_trade/market.py`, `mas_trade/attribution.py` |
| Joint optimiser (Section 3.5) | `mas_trade/cells_admm.py`, `mas_trade/risk.py` |
| Decentralised optimiser and resilience (Sections 3.6, 3.7) | `mas_trade/graph_admm.py` |
| STL monitor and supervisors (Section 3.8) | `mas_trade/stl.py`, `mas_trade/supervisor.py` |
| Backtest engine and settings | `mas_trade/engine.py`, `mas_trade/config.py`, `run_benchmark.py` |
| Simulated markets (E1) | `mas_trade/simulate.py` |
| Statistics and deflated Sharpe ratio (Section 4.5) | `mas_trade/diagnostics.py`, `mas_trade/metrics.py`, `final_table.py` |
| Dashboard (Section 7.7) | `dashboard.py`, `mas_trade/dashboard_data.py` |
| Tests | `tests/` |
