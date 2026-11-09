# Resilient Decentralised Portfolio Consensus

*A multi-agent system for trading Binance perpetual futures: design, mathematics and evidence*

AI3403 Multi-Agent Systems, project report. Evidence: development period April 2020 to November 2025. The final twelve months of data were sealed before the work began and have not been examined. Nothing was traded live. Experiments are numbered 011 to 023 and decisions 0032 to 0045 in the project repository, which holds the exact commands and result tables behind every number below.

## Abstract

We build and evaluate a multi-agent system that manages one portfolio of cryptocurrency perpetual futures. The agents are trading hypotheses with different beliefs. They coordinate through two mechanisms. First, a market in which each agent stakes capital on its own belief and its wealth follows its own results. Second, a joint convex optimisation, solved by the alternating direction method of multipliers (ADMM), that turns all stakes into one portfolio, with shared limits and the cost of the net trade handled as prices. We remove the central node of that optimisation by dynamic average consensus on a communication graph and prove that this keeps the quantity ADMM needs, the sum of the agents' positions, exactly correct. We add link failures, agent dropout, a detect-and-isolate defence built on the W-MSR test, and a signal-temporal-logic (STL) monitor with two supervisors. We evaluate everything against the centralised optimiser, on simulated markets and on five and a half years of real data, using pre-registered pass or fail rules.

The decentralised system matches the centralised one to within 0.002 Sharpe on every network shape, under 30% link failures, with the largest agent offline for four months, and with a lying agent isolated. Network shape changes the number of messages, not the result. W-MSR trimming cannot replace the averaging inside the optimiser, but its test detects a consistent liar on a robust graph. The capital market equals a fixed mix of good agents and beats a fixed mix by about 0.9 Sharpe when one agent is bad. The main system earns a net Sharpe ratio of about 1.4 to 1.5, but after correcting for the 45 strategy variants tried its deflated Sharpe ratio is about 0.1 (threshold 0.95), so the return result is not conclusive on the development data alone. Several pre-registered gates failed and are reported as failures.

## 1. Introduction

**1.1 Setting.** A portfolio is managed by several analysts. Each holds a belief about what drives returns. They share one pool of capital, one risk budget and one market that charges them to trade. A single optimiser that collects all forecasts is simple, but it is a single point of failure, it hides the disagreement between beliefs, and it cannot be studied with the tools of distributed computation. We treat the problem as a multi-agent system and ask how far the central node can be removed without changing the answer or the safety of the result.

**1.2 Starting point.** The project began as a consensus system (W-MSR averaging, trust weights) on US stocks and on crypto. Its experiments (001 to 010) found that only one idea, funding carry, earned a positive return after costs, and that its "multi-agent" layer was a distributed solver of a problem a central optimiser solves identically. We rebuilt the system around agents that make genuinely different bets and around a coordination mechanism with a clear economic meaning, prices.

**1.3 Research questions.**

| | Question |
|---|---|
| RQ1 | Does a neighbour-only optimiser reproduce the centralised portfolio on real data? |
| RQ2 | How does the communication topology affect convergence, communication cost and the result? |
| RQ3 | Does the decentralised consensus stay correct under link failures, agent dropout and a lying agent, and does W-MSR protect it? |
| RQ4 | Does an STL monitor with a supervisor keep the system inside its safety specifications in stress periods, and at what cost? |
| RQ5 | What do the agents and the market of agents contribute in money and risk, and does the result survive correction for the number of variants tried? |

**1.4 Contributions.**
1. A two-level architecture: a capital-staked market above a joint ADMM over (agent, coin) cells, with shared limits and the cost of the net trade as prices (Sections 3.2 to 3.4).
2. A neighbour-only version of that ADMM with a proof that it keeps the sum of positions exact, and an empirical study of convergence against graph mixing rate (Sections 3.5, 5.5, 5.6).
3. A resilience study with a negative result: W-MSR trimming breaks the optimiser, while the W-MSR test works as a detector (Sections 3.6, 5.7).
4. An STL monitor with two supervisors whose limits come from a written mandate (Sections 3.7, 5.8).
5. A pre-registered evaluation that reports failures, including a bug found in the risk limit, with every earlier result re-run after the correction (Sections 4, 5.2, 6.2).

**1.5 Organisation.** Section 2 fixes the setting and notation. Section 3 gives the method. Section 4 gives the experimental protocol. Section 5 gives the results. Section 6 discusses them. Section 7 concludes.

## 2. Setting and notation

**2.1 Market and data.** The market is Binance USD-M perpetual futures: contracts on coins that never expire. A long position pays, and a short receives, a funding payment (every eight hours, sometimes at shorter intervals) that ties the contract to the spot price. We use open, high, low and close prices, volume, taker volume, funding events, the premium over the index, spot prices and open interest, in bars of one day, four hours and one hour.

*Universe.* Point-in-time and free of survivorship bias. A coin enters when its rank by the 90-day median daily dollar volume (computed strictly before the day) is within the top 50, stays while within the top 75, and is re-ranked every 30 days. Delisted coins are included. In total 243 coins appear. A coin is tradable at a rebalance only if its trailing median daily dollar volume is at least one million dollars and its history window is complete. Stablecoin pairs, index contracts and non-crypto perpetuals are excluded.

*Rebalancing.* The system trades every 14 days on daily bars, every 5 days on four-hourly bars and every 48 hours on hourly bars. Anything computed for a rebalance at time $t$ uses only information strictly before $t$.

**2.2 Notation.** Index $i \in \{1,\dots,M\}$ is an agent, $a \in \{1,\dots,N\}$ a tradable coin. All positions are notional amounts in units of initial equity.

| Symbol | Meaning |
|---|---|
| $\mu_i \in \mathbb{R}^N$ | belief of agent $i$: expected net return of a unit position in each coin over one holding period |
| $x_i \in \mathbb{R}^N$ | position of agent $i$; $X = \sum_i x_i$ is the net position, $h$ the net position currently held |
| $\Sigma = \operatorname{diag}(d) + F\,\beta\beta^\top$ | return covariance over one holding period: idiosyncratic variances $d$, one market factor with variance $F$ and betas $\beta$ |
| $W_i$, $E = \sum_i W_i$ | wealth of agent $i$ and total equity |
| $f = 0.5$, $\gamma_i = 1/(f W_i)$ | Kelly fraction and the resulting risk aversion of agent $i$ |
| $C(\cdot)$ | trading cost, charged on the net trade $X - h$ |
| $\lambda \ge 0$ | price on system variance (the volatility limit) |
| $G=(V,\mathcal{E})$, $W$ | communication graph on the agents and its doubly stochastic mixing matrix |
| $r$ | gossip rounds per iteration |
| $\rho_\varphi(t)$ | STL robustness of specification $\varphi$ at time $t$ |

**2.3 Costs.** Trading $d_a$ in coin $a$ costs
$$C_a(d_a) = c_f\,\lvert d_a\rvert + \kappa_a\,\lvert d_a\rvert^{3/2},\qquad \kappa_a = \frac{k\,\sigma_a}{\sqrt{\mathrm{ADV}_a}},$$
with taker fee $c_f = 5$ basis points, daily volatility $\sigma_a$, average daily dollar volume $\mathrm{ADV}_a$ and impact coefficient $k = 1$ (an assumption). The second term is the usual square-root impact: slippage per dollar is $k\sigma_a\sqrt{\lvert d_a\rvert/\mathrm{ADV}_a}$. $C(d) = \sum_a C_a(d_a)$ is convex. Funding is paid and received exactly as incurred. Assets under management are one million dollars and a position may be at most 5% of a coin's daily volume.

**2.4 Evaluation criterion.** The annualised net Sharpe ratio $\mathrm{SR} = \sqrt{P}\,\bar r / s_r$, where $P$ is the number of bars per year and $\bar r$, $s_r$ the mean and standard deviation of net bar returns, against zero. The benchmark for any mechanism is the same agents solved by the centralised optimiser.

## 3. Method

### 3.1 Agents and beliefs

An agent is a trading hypothesis. Each is written on a **card** before any test: the claim, the mechanism, the allowed coin set $\mathcal{U}_i$, the predicted sign $s_i$ and size $\mathrm{IC}_i$ of its edge, and a switch-off rule.

*Belief.* Let $z_{ia}$ be a standardised score of the hypothesis for coin $a$, with unit variance across coins, and let $\mathrm{IC}_i$ be the expected rank correlation between score and next return. If the score is the only information, the conditional mean return is $\mathrm{IC}_i\,\sigma_{H,a}\,z_{ia}$, where $\sigma_{H,a}$ is the volatility of coin $a$ over one holding period (Grinold's fundamental law). The belief is
$$\mu_{ia} = s_i\;\mathrm{IC}_i\;\sigma_{H,a}\;z_{ia}.$$
**The size $\mathrm{IC}_i$ is fixed by the card and not estimated.** A trailing estimate is too noisy to size a bet: in our data it changed sign about half the time, and an early version of the carry agent that used it earned less than half the Sharpe of the fixed version. Evidence acts only through a kill rule. Let $\overline{\mathrm{IC}}_n$ and $s_n$ be the mean and standard deviation of the agent's realised per-period skill over $n$ periods and $t_n = \overline{\mathrm{IC}}_n/(s_n/\sqrt n)$. If $n \ge 20$ and $s_i t_n < -2$ the belief is set to zero. The agent never bets the opposite.

*The three agents.*

| Agent | Score $z_{ia}$ | Coins | Neutral | $\mathrm{IC}_i$ |
|---|---|---|---|---|
| **Funding carry** | rank-Gaussian of $-\overline{\text{funding}}_{14\text{d}}(a)$: long low funding, short high funding | all tradable | yes | 0.02 |
| **Momentum** | $\operatorname{clip}\!\big(\sum_{\tau\in 30\text{d}} r_{a\tau} \big/ (\operatorname{sd}(r_a)\sqrt{L}),\,-2,\,2\big)$ | BTC, ETH only | no, owns net exposure | 0.05 (assumed) |
| **Residual reversal** | rank-Gaussian of $-\sum_{\tau\in 7\text{d}} e_{a\tau}\big/(\operatorname{sd}(e_a)\sqrt n)$, where $e_{a\tau} = r_{a\tau} - \hat\beta_a r_{\mathrm{BTC},\tau}$ | all tradable | yes | 0.02 |

The rank-Gaussian transform is $z_a = \Phi^{-1}\big((\operatorname{rank}_a - 0.5)/N\big)$. The mechanism of carry is that funding is a transfer from the crowded side, so expected return is carry plus expected price change. Momentum rests on slow diffusion of information, and reversal on temporary price pressure from demand for immediacy.

### 3.2 Level 1: the capital-staked market

Each agent bets Kelly on its own belief. For a single asset with expected return $\mu$ and variance $\sigma^2$, the log-growth of wealth when investing a fraction $f$ is approximately $g(f) = f\mu - \tfrac12 f^2\sigma^2$. It is maximised at $f^\star = \mu/\sigma^2$ and falls to zero at $2f^\star$, so over-confident agents are punished by the mathematics itself. We use half the Kelly size. Minimising $-\mu x + \tfrac{\gamma}{2}\sigma^2 x^2$ gives $x = \mu/(\gamma\sigma^2)$, so a bet of $f W \mu/\sigma^2$ corresponds to $\gamma = 1/(fW)$, the risk aversion of Section 2.2.

*Wealth dynamics.* The system trades the sum of the agents' positions. Each agent has an account that earns the profit and loss of its own positions less its allocated share of cost and funding, so the accounts sum exactly to the real result. Wealth compounds with the account return $r_i(t)$:
$$W_i(t+1) = \max\!\Big(W_i(t)\,\big(1 + r_i(t)\big),\;\omega\,\textstyle\sum_j W_j(t)\Big),\qquad \omega = 0.02.$$
The floor $\omega$ keeps a failed agent alive so the market can still reallocate. Beliefs are never averaged across agents. They influence the portfolio only through the wealth that backs them.

### 3.3 Level 2: the joint portfolio problem

At each rebalance the system solves one convex problem over all positions:
$$\min_{x_1,\dots,x_M}\;\sum_{i=1}^{M}\Big[-\mu_i^\top x_i + \tfrac{\gamma_i}{2}\,x_i^\top\Sigma\,x_i\Big] \;+\; C\big(X-h\big) \;+\; \tfrac{\lambda}{2}\,X^\top\Sigma X \tag{P}$$
$$\text{subject to}\quad x_i\in\mathcal{X}_i\ \ (i=1,\dots,M),\qquad X=\sum_i x_i\in\mathcal{G}.$$
The agent sets $\mathcal{X}_i$ contain the constraints that belong to one agent:
- allowed coins: $x_{ia}=0$ for $a\notin\mathcal{U}_i$;
- capacity: $\lvert x_{ia}\rvert \le u_a$, where $u_a$ is 5% of the coin's daily volume;
- margin: $\lVert x_i\rVert_1 \le 3\,W_i$;
- neutrality, for agents whose hypothesis is market-neutral: $\mathbf{1}^\top x_i = 0$ and $\beta^\top x_i = 0$.

The system set $\mathcal{G}$ contains the constraints that belong to the whole system:
- gross cap: $\lVert X\rVert_1 \le 3E$;
- beta band: $\lvert\beta^\top X\rvert \le 0.25\,E$.

Three features are central.

*Cost on the net trade.* $C$ acts on $X-h$, not on each $x_i$. Two agents trading opposite ways in the same coin cancel and pay only for the difference.

*A volatility limit as a price.* The last term in (P) is a price $\lambda$ on system variance. After each solve the ex-ante annual volatility of the net position, $\sqrt{P\,X^\top\Sigma X/H}$ with $H$ bars per holding period, is compared with the 20% target. If it is above, $\lambda$ is raised and (P) is solved again, up to five times, until the volatility is within 2% of the target. The agent that adds risk then pays for it. In a test at equal total volatility, this priced limit left the market-neutral agent 97% of its unconstrained position, where a uniform shrink of all positions left it 45%.

*Prices are the coordination signal.* Problem (P) is convex, so it has multipliers. The multipliers of the neutrality, beta, margin, gross, capacity and net-trade terms are prices of exposure, scarce capital, scarce gross exposure and trading. Each agent reacts to them. No agent needs to know another agent's belief.

### 3.4 Solving (P): sharing ADMM

Write $f_i(x_i) = -\mu_i^\top x_i + \tfrac{\gamma_i}{2}x_i^\top\Sigma x_i + \iota_{\mathcal{X}_i}(x_i)$ and $g(X) = C(X-h) + \tfrac\lambda2 X^\top\Sigma X + \iota_{\mathcal{G}}(X)$, with $\iota$ the indicator of a set. Then (P) is the sharing problem $\min \sum_i f_i(x_i) + g\big(\sum_i x_i\big)$. With $\bar x = \tfrac1M\sum_i x_i$, penalty $\rho>0$ and scaled dual (price) $u$, ADMM iterates:
$$x_i^{k+1} = \arg\min_{x_i}\; f_i(x_i) + \tfrac{\rho}{2}\,\big\lVert x_i - x_i^{k} + \bar x^{k} - z^{k} + u^{k}\big\rVert^2 \qquad\text{(each agent, in parallel)}$$
$$z^{k+1} = \arg\min_{z}\; g(Mz) + \tfrac{M\rho}{2}\,\big\lVert z - \bar x^{k+1} - u^{k}\big\rVert^2 \qquad\text{(system step)}$$
$$u^{k+1} = u^{k} + \bar x^{k+1} - z^{k+1}\qquad\text{(price update)}$$
This is the sharing form of Boyd et al. (2011, Section 7.3), run by a central node (the "hub"). It converges because (P) is convex. The scaled dual $u$ is, up to the factor $\rho$, the price of the net position per coin.

*Implementation notes.* The cost step has a closed form, the cost with a shifted point being a one-dimensional problem with a closed-form minimiser. The agent step includes a nested bracketed root search for the multipliers of the margin, gross and beta constraints, and an exact projection onto an $\ell_1$-box. Termination uses primal and dual residuals relative to the size of the positions (tolerance $10^{-6}$), with over-relaxation 1.7. These choices decide speed and not the optimum. A previous absolute stopping rule stopped real problems after about ten iterations; the relative rule fixed it.

### 3.5 Removing the hub: dynamic average consensus

In Section 3.4 three quantities are global: the average position $\bar x$, the system step $z$ and the price $u$. In the decentralised version agent $i$ holds its own copies $s_i$ (estimate of the group average), $z_i$ and $u_i$. The system data (cost parameters, limits) are public. Let $W\in\mathbb{R}^{M\times M}$ be the **Metropolis** mixing matrix of the graph,
$$W_{ij} = \frac{1}{1+\max(\deg i,\deg j)}\ \text{ for } \{i,j\}\in\mathcal{E},\qquad W_{ii} = 1-\sum_{j\ne i}W_{ij},$$
which is symmetric with rows summing to one, hence doubly stochastic. Per iteration:

> **Algorithm 1 (decentralised ADMM, one iteration).**
> 1. Each agent $i$ solves its local step against its own price $u_i$, giving $x_i^{\text{new}}$.
> 2. Tracking: $\;s \leftarrow W^{r}\big(s + x^{\text{new}} - x^{\text{old}}\big)$, mixing the stacked estimates over $r$ gossip rounds.
> 3. Each agent solves the system step from its own estimate $s_i$, giving $z_i$.
> 4. Price: $\;u \leftarrow W^{r}\big(u + s - z\big)$.

Initialise $s_i = x_i^{0}$.

> **Proposition 1 (sum invariant).** For every iteration $k$, $\sum_i s_i^{k} = \sum_i x_i^{k}$.
>
> *Proof.* Let $\mathbf 1$ be the all-ones vector. Because $W$ is doubly stochastic, $\mathbf 1^\top W^{r} = \mathbf 1^\top$. Then $\mathbf 1^\top s^{k+1} = \mathbf 1^\top\big(s^{k} + x^{k+1} - x^{k}\big) = \mathbf 1^\top s^{k} + \mathbf 1^\top x^{k+1} - \mathbf 1^\top x^{k}$. By induction, with $s^0 = x^0$, the claim holds. $\square$

**Corollary.** If the iteration reaches a fixed point, then $x^{k+1}=x^{k}$, mixing drives $s_i$ to the common value $\bar s = \tfrac1M\sum_i s_i = \bar x$ (by Proposition 1), and the prices agree for the same reason. The fixed point satisfies the optimality conditions of Section 3.4, so it is the optimum of (P). On the complete graph with exact mixing the algorithm coincides with the hub algorithm.

*Convergence and communication.* With no new input, mixing shrinks the disagreement $s - \mathbf 1\bar s^\top$ by the factor $\lvert\lambda_2(W)\rvert^{r}$ per iteration, where $\lambda_2$ is the second-largest eigenvalue modulus of $W$ (the mixing rate). A smaller value means faster agreement. Messages per rebalance equal $(\text{iterations})\times r\times 2\,\lvert\mathcal{E}\rvert$. The stopping test also requires agreement between the agents' estimates and prices, since a run once stopped as converged while agents still disagreed by about 10%.

*What remains central in our experiments.* The step sizes use the mean risk aversion, a number the agents could agree on once before trading. The stopping test is evaluated by the simulator, where a deployment would run a max-consensus over the graph's diameter.

### 3.6 Resilience

Three faults are considered.

*Link failures.* In every gossip round each edge is down independently with probability $q$. The weights are recomputed by the Metropolis rule on the edges that are up. The recomputed matrix is again symmetric with unit row sums, hence doubly stochastic, so Proposition 1 still holds and the optimum is still reached. Failures cost iterations, not correctness.

*Agent dropout.* The agent's positions are closed and the remaining agents solve (P) without it, on the graph without its node. The same invariant applies to the smaller system.

*Misbehaving agent.* A liar $\ell$ sends values that differ from what its algorithm would send. We use **detect and isolate**. At iteration $k$, agent $i$ looks at the values $v_j$ (the estimate $s_j$ and the price $u_j$) of its neighbours and itself. For neighbour $j$ and coordinate $c$ let $e_{ijc}=1$ if $v_{jc}$ is the largest value above $v_{ic}$ or the smallest below it, that is, the value W-MSR would discard first. Define the share $\pi_{ij}=\tfrac1{n}\sum_c e_{ijc}$. Agent $i$ flags $j$ when $\pi_{ij}\ge 0.9$ for both the estimates and the prices for 50 consecutive iterations. Agent $j$ is isolated when more than half of its neighbours flag it, and the others restart without it. Plain averaging is used otherwise. The parameters (0.9, 50, majority) were fixed on development problems before the evaluation.

*Why W-MSR is used as a detector and not as the averaging rule.* In W-MSR each agent drops up to $F$ larger and $F$ smaller neighbour values and averages the rest. The resulting weight matrix depends on the data and is not doubly stochastic in general, so $\mathbf 1^\top s$ is no longer preserved and Proposition 1 fails. The agents then agree on a value that is not the average of the positions. Experiment 021 confirmed this: with no attacker at all, the trimmed version did not converge (Section 5.7). For $F=1$, W-MSR also requires the graph to be $(2,2)$-robust. A ring is connected but not $(2,2)$-robust. A ring with each agent linked to its two nearest neighbours on each side ("ring2") is sparse but robust.

### 3.7 Safety: STL monitor and supervisors

For a real-valued signal $y$ and a threshold $c$, the atomic predicate $y \ge c$ has robustness $\rho(t)=y(t)-c$: positive means satisfied by that margin, negative means violated by that much. The operators are $\rho(\mathbf{G}_{[a,b]}\varphi,t) = \min_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (always) and $\rho(\mathbf{F}_{[a,b]}\varphi,t)=\max_{t'\in[t+a,t+b]}\rho(\varphi,t')$ (eventually). The system specifications, with limits fixed from a written mandate before any run, are:

| Spec | Statement | Limit |
|---|---|---|
| $\varphi_{\mathrm{vol}}$ | $\mathbf{G}\;\big(\hat\sigma_t \le 1.05\,\sigma^\ast_t\big)$, ex-ante volatility within the target in force | 5% tolerance on the target $\sigma^\ast$ |
| $\varphi_{\mathrm{dd}}$ | $\mathbf{G}\;\big(\mathrm{DD}_t \ge -0.15\big)$, with $\mathrm{DD}_t = E_t/\max_{s\in[t-365\mathrm{d},t]}E_s - 1$ | 15% over 365 days |
| $\varphi_{\mathrm{rvol}}$ | $\mathbf{G}\big(\sigma^{\mathrm{real}}_t > 0.4 \Rightarrow \mathbf{F}_{[0,14\mathrm{d}]}\,\sigma^{\mathrm{real}}_t \le 0.4\big)$, 30-day realised volatility breaches recover | 40%, 14 days |
| $\varphi_{\mathrm{solve}}$ | $\mathbf{G}\;\big(\text{relative residual}\le 10^{-3}\big)$ | $10^{-3}$ |

The **monitor** records $\rho_\varphi(t)$ for every bar and summarises it over three stress windows (May to July 2021, the May 2022 Luna collapse, and the November 2022 to January 2023 FTX collapse). Two **supervisors** act on the robustness, and both are off by default.

*Derisk.* Let $m_t = (\mathrm{DD}_t+0.15)/0.15\in[0,1]$ be the share of the drawdown budget that is left. The volatility target is multiplied by
$$\kappa(m_t)=\begin{cases}1 & m_t\ge 0.5,\\ 0.2+1.6\,m_t & 0\le m_t<0.5,\end{cases}$$
so the system starts de-risking with half the budget left and never goes below 20% of its target. This acts through the volatility price of Section 3.3, so (P) is re-solved with the tighter target, costs included. It is not a post-hoc rescale of the finished portfolio.

*Hold.* If the solve is unsafe (it did not converge and its relative residual exceeds $10^{-3}$) the system trades nothing and keeps its positions. This is the fail-safe against a corrupted solve.

## 4. Experimental protocol

**4.1 Reference and data discipline.** Every decentralised or resilience result is compared with the centralised optimiser with the same agents, data and costs, or with the reference that is right for the failure (for example the central system without the agent that is offline). No lookahead is allowed, and this is a tested invariant. The development period ends in November 2025. The last twelve months are sealed and will be opened once, after the design is frozen.

**4.2 Pre-registration.** For each experiment the pass or fail rules, with thresholds, were written and committed before its runs. Amendments carry a date and say whether any result had been seen. Rejected code is deleted and the commit that holds it is recorded.

**4.3 Statistics.**
- *Intervals.* A 90% moving-block bootstrap: resample blocks of 7 days with replacement ($B=500$ draws) and take the 5th and 95th percentiles of the statistic. Differences between two strategies use the same resampled blocks for both (a paired difference).
- *Alpha.* For an agent with net return $r_t$ we regress $r_t=\alpha+\beta\,r^{\mathrm{BTC}}_t+\epsilon_t$, and also on the carry agent's return, and report $\alpha$ annualised with a block-bootstrap interval.
- *Skill.* The rank information coefficient is the Spearman correlation between the score and the next return, averaged over rebalances with its $t$-statistic.
- *Deflated Sharpe ratio* (Bailey and López de Prado, 2014). Let $\widehat{\mathrm{SR}}$ be the per-period Sharpe ratio of the best strategy over $T$ periods with skewness $\hat\gamma_3$ and kurtosis $\hat\gamma_4$ (3 for a normal distribution), $V$ the variance of Sharpe ratios across the $N$ trials, and $\gamma_{\mathrm{E}}\approx0.5772$ Euler's constant. Then
$$\mathrm{SR}_0=\sqrt{V}\Big[(1-\gamma_{\mathrm{E}})\,\Phi^{-1}\!\big(1-\tfrac1N\big)+\gamma_{\mathrm{E}}\,\Phi^{-1}\!\big(1-\tfrac{1}{Ne}\big)\Big],\qquad
\mathrm{DSR}=\Phi\!\left(\frac{(\widehat{\mathrm{SR}}-\mathrm{SR}_0)\sqrt{T-1}}{\sqrt{1-\hat\gamma_3\widehat{\mathrm{SR}}+\tfrac{\hat\gamma_4-1}{4}\widehat{\mathrm{SR}}^{2}}}\right).$$
$\mathrm{SR}_0$ is the Sharpe ratio the best of $N$ strategies with no skill would show by chance, and DSR is the probability that the observed Sharpe ratio exceeds it. We require $\mathrm{DSR}\ge0.95$.

**4.4 Trial accounting.** Every variant evaluated is written to an append-only log. A strategy trial is one pair (strategy variant, bar size). Exact repeats count once. Engineering variants (consensus, topology, resilience, safety) are counted separately as a more conservative total. The variance $V$ is that of the annualised Sharpe ratios of the 15 strategy runs of experiment 018, divided by the number of periods per year.

**4.5 Metrics.** Financial: net Sharpe, compound annual growth rate (CAGR), volatility, maximum drawdown, turnover, cost. Multi-agent: iterations to convergence, rebalances that reach the iteration cap, messages per rebalance, agreement between agents, error against the central optimum, who was isolated. Safety: robustness per specification, violating bars, held rebalances.

## 5. Results

All returns are net of fees, price impact and funding. Intervals are 90%. Columns are daily, four-hourly and hourly bars unless stated.

### 5.1 The experimental programme

| Experiment | Question | Outcome |
|---|---|---|
| 011 | Is the data store sound; is funding computed as assumed? | Verified (funding rule checked; data extended to all columns, premium index, spot, open interest) |
| 012 | Do the mechanisms behave on simulated markets where the truth is known? | Mostly pass; two failures that shaped the design (Section 5.2) |
| 013 | Does carry in the new engine reproduce the earlier result? | Pass |
| 014 | Does forecasting funding improve carry? | No; dropped |
| 015 | Admit momentum? Does the market beat carry alone? | Initial run broke the agent's own card (bug); after correction, market beats carry, but equals a fixed mix |
| 016 | Does timing momentum with bull and panic states help? | No (slightly worse); rejected, code deleted |
| 017 | Admit reversal? Does a market of three beat two? | Reversal not admitted; market of three worse than two |
| 018 | Do conclusions survive a corrected risk limit? | Numbers changed; momentum's admission flipped to a narrow fail |
| 019 | Does the neighbour-only optimiser equal the hub on real data? | Pass |
| 020 | How do topology and communication budget matter? | Shape sets communication, not the outcome; one gate failed |
| 021 | Resilience to link failures, dropout and a lying agent; role of W-MSR | Mostly pass; W-MSR trimming rejected |
| 022 | Does an STL monitor with supervisors keep the system safe? | Partly; three gates failed |
| 023 | One comparison table and the deflated Sharpe | Mechanisms match the reference; the return result fails the deflated Sharpe |

### 5.2 Validation on simulated markets (experiment 012)

*Protocol.* Random problems with 3 to 4 agents and 6 to 10 coins (5 seeds per configuration) for the optimiser, and simulated coins with planted skill for the market. Criteria were fixed before implementation.

| Mechanism | Criterion | Result |
|---|---|---|
| Joint optimiser | matches an exact one-node solver on every coupling (35 random problems) | pass; typical error $10^{-7}$; hardest case about 1,100 iterations |
| Prices | non-negative, zero when slack, equal to the marginal value of the limit within 5% | pass |
| Netting | opposite views on a coin are charged on the net trade, which is cheaper than the sum | pass |
| Capital follows its price | a tighter margin moves capital to the best-edge coin | pass |
| Market selects skill | a skilled agent's share exceeds 0.5 at the computed horizon in at least 90% of seeds | pass at 160 periods |
| Market drops decayed skill | share falls after skill vanishes | pass |
| Accounting | account profits, cells and wealth sum to the real values | pass to $10^{-9}$ |
| Over-confidence punished | an over-confident agent ends with less wealth | **fail** with the 2% floor (6 of 20 seeds); pass without a floor (18 of 20) |
| Guard against a corrupt member | fused belief changes by less than 10% | restated after a failed run; the guard equals the honest average exactly |
| Timing on planted regime skill | timed beats untimed; costs little with no dependence | pass |

Two findings shaped the design. *The floor blunts selection:* it re-seeds a ruined agent, so it acts as a rebalancing rule. *An unlimited over-confident agent can ruin the whole system:* 2 to 5 of 20 seeds were wiped out at an effective Kelly fraction of 2, and wealth dynamics are too slow to prevent it. Hence the priced margin and gross limits and an agent-level calibration check are always on, Kelly fractions stay at or below 0.5, and the floor is a liveness device, not a selector.

### 5.3 The agents on real data (experiment 018)

| Agent | Daily | 4-hourly | Hourly | Volatility | Verdict |
|---|---|---|---|---|---|
| Carry | 1.14 | 1.12 | 0.94 | 19% to 23% | works; rank IC about 0.02 to 0.035 |
| Momentum (BTC, ETH) | 0.96 | 0.80 | 0.76 | 13% to 15% | earns about 9% a year above what Bitcoin explains, but its pre-registered admission rule (alpha lower bound above zero on at least two of three bar sizes) narrowly fails; kept as a *provisional* agent without a claim of stand-alone edge |
| Reversal | −0.66 | −1.17 | −0.99 | 24% to 29% | the signal is real (rank IC 0.025, 0.042, 0.046; $t$ = 1.5, 4.4, 7.3) but cost is 5.9% to 9.5% a year at 45 to 91 times equity turnover; not admitted |

Daily 90% intervals: carry $[0.36, 1.90]$, momentum $[0.24, 1.61]$, reversal $[-1.29, -0.03]$. Momentum's alpha against Bitcoin has interval $[+0.2\%, +17.7\%]$ on daily bars, $[-0.9\%, +18.5\%]$ on four-hourly and $[-2.7\%, +19.7\%]$ on hourly bars. Two other hypotheses were rejected: a funding-forecast improvement to carry did not help (014), and timing momentum with an estimated bull and panic state gave Sharpe 1.03, 0.90 and 0.86 against 1.06, 0.95 and 0.90 for the plain agent (016, under the earlier risk limit). Their code was deleted.

### 5.4 What the market of agents adds (experiments 015, 018)

| Paired Sharpe difference | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Market of carry and momentum minus carry alone | +0.26 | +0.36 | +0.55 |
| Same market minus a fixed blend of the two stand-alone runs | −0.07 | +0.14 | +0.29 |
| Market of three (with reversal) minus market of two | −0.14 | −0.14 | −0.15 |
| Market of three minus a fixed inverse-volatility blend of its three stand-alone runs | +0.35 | +0.86 | +0.88 |

The intervals of the first row are all above zero. The second row has no interval that excludes zero. In the fourth row the intervals are $[-0.17, 0.84]$, $[0.31, 1.35]$ and $[0.34, 1.39]$.

With good agents the market is indistinguishable from a fixed mix, so its gain over carry alone is diversification. With a failing agent present it beats a fixed mix, because capital moves. Reversal's final wealth share was 1.9%, 1.8% and 2.0%, the floor, while the fixed blend kept paying for its losses. This is the clearest real-data evidence for the capital market: protection against a bad agent, not extra return. (The fixed blend used full-sample volatilities for its weights.)

### 5.5 RQ1: the neighbour-only optimiser equals the hub (experiment 019)

*Protocol.* Three agents, daily bars, same data and settings. Rule fixed in advance: Sharpe within 0.01 and final equity within 1% of the hub.

| Run | Net Sharpe | Final equity | Rebalances at the iteration cap |
|---|---|---|---|
| Centralised hub | 1.258 | 3.564 | 21 of about 137 |
| Graph, complete | 1.257 | 3.560 | 22 |
| Graph, line, 1 gossip round | 1.256 | 3.554 | 43 |
| Graph, line, 3 gossip rounds | 1.257 | 3.559 | 24 |

**Pass.** The largest differences are 0.002 in Sharpe and 0.3% in equity, and every agent's account is the same to three decimals. The price of a poor topology shows in the cap counts: the line with one round reaches the cap twice as often.

### 5.6 RQ2: topology and communication budget (experiment 020)

*Part A, simulated problems.* All limits binding, tolerance $10^{-8}$, iteration cap 4,000, three gossip rounds. Median iterations to converge, with $\lvert\lambda_2(W)\rvert$ in brackets:

| Agents | Complete | Ring | Random | Star | Line |
|---|---|---|---|---|---|
| 4 | 151 (0) | 165 (0.33) | 228 (0.75) | 264 (0.75) | 389 (0.80) |
| 8 | 386 (0) | 499 (0.80) | 883 (0.68) | 1,183 (0.88) | not converged (0.95) |
| 16 | 1,000 (0) | 3,709 (0.95), 2 of 3 converged | 1,000 (0.79) | not converged (0.94) | not converged (0.99) |

- **Gate A1** required a Spearman correlation of at least 0.7 between $\lvert\lambda_2\rvert$ and iterations at each size. Results: 0.60 at 4 agents (**fail**), 0.90 at 8 and 0.78 at 16. At four agents the difficulty of the individual problem dominates: one problem needed about 830 iterations on every topology, including the complete graph. Within each problem the ordering matches the prediction (mean correlation 0.79, 0.96, 0.82). We report the failure as pre-registered.
- **Gate A2:** the complete graph takes exactly the hub's iterations (pass), since it is the hub algorithm.
- The star has higher algebraic connectivity than the ring (1.0 against 0.59 at 8 agents) but is slower (1,183 against 499 iterations). The mixing rate $\lvert\lambda_2(W)\rvert$ predicts better, because with Metropolis weights the centre of a star is a bottleneck.
- The fewest messages occur with one gossip round on the complete graph and (at 4 agents) the ring, and with three rounds elsewhere.
- After a fixed budget the error is almost the same on every topology early on (about 0.40 at 25 iterations and 0.16 at 100 with eight agents). Topology decides how long the last, precise part takes.

*Part B, real data, eight agents.* Carry with 7, 14 and 30-day windows, momentum with 15, 30 and 60-day lookbacks and reversal with 3 and 7-day lookbacks, used only as parameter variants to study coordination.

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

**Gate B1** (every uncapped graph run within 0.02 Sharpe and 2% equity of the hub): pass, with differences of at most 0.002 and 0.23%. Network shape sets the communication, not the outcome. A short budget costs about 0.025 Sharpe and 3% of final equity. By the pre-registered rule the default for later experiments is the complete graph with one gossip round. Because link failures on a complete graph are a weak test, the resilience experiments also used a sparse graph.

### 5.7 RQ3: resilience (experiment 021)

*Part A, simulated problems.* Eight agents, on fresh problems not used to set any parameter.

| Gate | Result |
|---|---|
| **A1.** Each link down with probability 0.1 or 0.3: every run on the complete graph, ring2 and ring converges with error at most $10^{-4}$ | **pass**; error at most $5.4\times10^{-6}$; converged even at 0.5; the ring needs 60% more iterations at $q=0.3$ |
| **A2.** On complete and ring2, a constant liar of size 0.001 to 1.0 (from 4% of a typical position) is isolated, only the liar, and the error against the optimum without it is at most $10^{-4}$; with no liar nobody is isolated | **pass**; 18 of 18 runs; error at most $4.4\times10^{-6}$ |
| **A3** (predicted to fail). The same on the plain ring | **fail**, as predicted: in all 9 liar runs an honest agent was isolated too and the graph fell apart (the ring is not $(2,2)$-robust) |
| **A4** (reported). Undefended constant liar; noise liar with the detector | undefended: error 5.5 to 5.9 typical positions, no convergence; noise liar isolated in 1 of 6 runs, otherwise no convergence and error 12.5 to 14.8 typical positions |
| **A5** (decides the code). W-MSR trimmed mixing, no attacker | no run converged; error 0.50 to 4.8 typical positions; **rejected and deleted** (Section 3.6 explains why) |

*Part B, real data, daily, eight agents.*

| Run | Net Sharpe | Final equity | Against the reference |
|---|---|---|---|
| Hub | 1.240 | 3.578 | |
| Complete, 30% of links down each round | 1.239 | 3.577 | within 0.001 of the hub (B1: pass) |
| Ring, 3 rounds, 30% of links down | 1.239 | 3.575 | mean iterations 1,870 to 2,155; capped rebalances 43 to 56 |
| Largest agent (a carry variant with 38% of final wealth) offline May to August 2022; hub, complete, ring | 1.225, 1.225, 1.225 | 3.476, 3.476, 3.474 | graph equals the hub with that agent offline (B2: pass); highest ex-ante volatility in the window 17.5% against 20.9% outside it |
| A momentum variant lies (adds 0.01 to everything it sends), detector on | 1.182 | 3.391 | equals the hub without that agent, 1.182 (B3: pass); isolated at the first rebalance, nobody else ever |

Dropping the largest agent for four months costs 0.015 Sharpe and 2.8% of final equity, and leaving out the lying agent costs 0.058 Sharpe and 5.2%, both relative to the full hub. The cost comes from what is missing (its capital sits idle), not from the coordination. The undefended liar on real data was not completed because its solves diverge and each would need hours (recorded in an amendment).

**Conclusions.** Link failures and dropped agents are absorbed at the price of extra communication. W-MSR trimming cannot be placed inside the optimiser, but its test works as a detector. Whether a defence works depends on the robustness of the graph and not only on its connectivity. A liar that stays inside the honest range is not caught.

### 5.8 RQ4: the STL monitor and supervisors (experiment 022)

*Part A, the main system (carry and momentum, centralised).*

| Mode | Metric | Daily | 4-hourly | Hourly |
|---|---|---|---|---|
| Off | Sharpe | 1.394 | 1.478 | 1.483 |
| | CAGR | 31.2% | 29.8% | 29.2% |
| | worst 365-day drawdown | −23.7% | −24.4% | −25.9% |
| | rebalances with ex-ante volatility within $1.05\times$ target | 97.8% | 97.6% | 94.3% |
| Derisk | Sharpe | 1.277 | 1.275 | 1.462 |
| | CAGR | 23.9% | 21.0% | 24.3% |
| | worst 365-day drawdown | −19.7% | −18.8% | −16.7% |

- **Gate A1** (solver health at every rebalance; the volatility specification at at least 95% of rebalances): solver health always holds. The volatility specification **fails on hourly bars** (94.3%): the volatility price search is limited to five re-solves and a 2% band, and on hourly data the covariance moves faster than the warm-started price follows. This is a limit of the search, not a bug.
- **Gate A2** (derisk has fewer bars violating the drawdown specification and a shallower worst drawdown): the worst drawdown is shallower on all three bar sizes, and the violating bars fall on four-hourly (2,159 against 2,223) and hourly (5,135 against 7,695), but they **rise on daily** (229 against 211) because smaller positions after a loss recover more slowly. **Fail on daily.**
- Cost of derisk: Sharpe $-0.12$, $-0.20$, $-0.02$ and CAGR $-7.3$, $-8.8$, $-4.9$ points. Limits are never chosen by Sharpe, so this is the price, not a criterion.
- **Stress windows.** The tightest was not May 2021 or Luna (the system made money in both; window drawdown at most $-8.5\%$) but the **FTX collapse (November 2022 to January 2023)**, the only window in which the drawdown specification was violated (1 daily bar, 444 four-hourly, 1,741 hourly). There derisk acts: on four-hourly bars the window drawdown falls from $-8.5\%$ to $-2.0\%$ and volatility from 20.8% to 6.7%, at a lower window return (8.2% to 3.7%).

*Part B, a stealthy liar on real data.* Carry, momentum and reversal on daily bars, complete graph. Reversal sends random noise from May to July 2022.

| Run | Sharpe | Final equity | Return in window | Unsafe solves | Held |
|---|---|---|---|---|---|
| No liar | 1.257 | 3.56 | 11.7% | 8 (all in 2025) | 0 |
| Liar, hold | 1.033 | 2.77 | 6.7% | 15 | 15 |
| Liar, no defence | stopped: the corrupted solve diverges (the largest iterate grows from 0.4 to 44 in 700 iterations; one solve takes about 45 minutes) | | | | |

**Gate B1** (every unsafe solve held, all inside the liar's window, none outside) **fails**. All six rebalances in the window were held (relative residual 1.18 to 1.62), but nine honest, slowly converging solves in 2025 (residuals 0.0013 to 0.0059) were held too. The frozen positions drifted to as much as 31% volatility and the whole-period Sharpe fell from 1.26 to 1.03. The residuals of the attack and of slow honest convergence differ by a factor of about 300, so a better limit exists. That is a follow-up and was not changed after seeing the result. Decision: the monitor is on in every run, derisk is usable, and hold stays off until its limit is re-argued.

### 5.9 RQ5: final comparison and the deflated Sharpe (experiment 023)

This experiment adds no new run. It is a consistency table over experiments 018 to 022, and every shared figure reproduces to 0.001 (gate C1: pass).

| Net Sharpe [90% interval] | Daily | 4-hourly | Hourly |
|---|---|---|---|
| Carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| Momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [−0.03, 1.44] |
| Reversal | −0.66 [−1.29, −0.03] | −1.17 [−1.81, −0.48] | −0.99 [−1.63, −0.32] |
| **Main system: carry + momentum market** | **1.39** [0.61, 2.09] | **1.48** [0.79, 2.15] | **1.48** [0.76, 2.22] |
| Market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| Fixed 50/50 blend, carry + momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2%, 29.8%, 29.2%; volatility 21%, 19%, 18%; maximum drawdown $-23.7\%$, $-24.4\%$, $-25.9\%$.

*Deflated Sharpe (gate C2: at least 0.95).* With $N=45$ strategy trials (15 variants on each of three bar sizes; annual variance of the trial Sharpe ratios $V=0.82$):

| Bar | Sharpe | Skewness | Kurtosis | DSR at $N=45$ | DSR at $N=74$ | Gate C2 |
|---|---|---|---|---|---|---|
| Daily | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 | fail |
| 4-hourly | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 | fail |
| Hourly | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 | fail |

$N=74$ also counts the 29 engineering variants. The deflated Sharpe stays above 0.95 only for $N\le 2$ and is about 0.5 at $N=10$. A best Sharpe of 1.4 to 1.5 among 45 trials of widely spread quality (from $-1.2$ to $1.5$) is what chance would produce with probability about 90%. This does not say there is no edge: carry's interval is above zero on every bar size. The sealed final year is the independent test.

*Mechanism summary.* The neighbour-only optimiser, every topology, link failures, an offline agent and an isolated liar all reproduce the centralised portfolio to within 0.002 Sharpe. Their price is up to 2.7 times the messages and 4.5 times the capped rebalances (on a line).

## 6. Discussion

### 6.1 Answers to the research questions

- **RQ1.** Yes. On real data the neighbour-only optimiser matches the hub to 0.002 Sharpe and 0.3% of final equity (019, 020).
- **RQ2.** Topology governs communication, not the outcome. The mixing rate $\lvert\lambda_2(W)\rvert$ predicts the iterations needed at 8 and 16 agents but not reliably at 4, and predicts better than algebraic connectivity. With a short budget sparse graphs leave agents in disagreement and cost about 3% of final equity.
- **RQ3.** Link failures and dropout are absorbed with extra communication, because the sum invariant survives them (Proposition 1). W-MSR trimming fails inside the optimiser because it breaks that invariant. As a detector it isolates a consistent liar exactly and without false alarms on robust graphs, but not on a non-robust ring and not against random noise.
- **RQ4.** The monitor shows the safety margin bar by bar and found a stress window we had not predicted. Derisk shortens drawdowns at a Sharpe cost. Two gates failed (drawdown count on daily bars, volatility specification on hourly bars) and the hold supervisor needs a better-argued limit.
- **RQ5.** Carry is a solid edge, momentum is marginal and concentrated in 2020 and 2021, and reversal does not pay after costs. The market equals a fixed mix of good agents and beats it when one agent is bad. The headline Sharpe does not survive multiple-testing correction on the development data alone.

### 6.2 Mistakes found and corrected

These are part of the result. Each is documented with the commit that fixed it.
1. **An agent held positions its card forbids.** Momentum's first run held hedge positions in other coins, because the optimiser cancelled market exposure with an alt-coin basket. It gave 39% volatility and a Sharpe of $-0.45$ on daily bars. The system now enforces each agent's coin set. Both runs count as trials, and the correction came after seeing the failure, which is a forking path that we disclose.
2. **The volatility limit used starting equity, not current equity.** As the system grew its effective limit fell (about 8% by 2025 on daily bars), and a losing agent's limit grew large relative to its remaining equity. After the correction every system runs at 18% to 21% in every year. Sharpe ratios fell by 0.03 to 0.2, returns rose, momentum's admission flipped from pass to a narrow fail, and the worry that the risk model underestimates risk proved to be mostly this bug. Every earlier experiment was re-run.
3. **A monitoring bug.** On a held rebalance the monitor logged the volatility of the rejected solve instead of that of the held positions. Fixed, with a test that fails on the old code.
4. **A gate that was too blunt.** The fixed residual limit of the hold supervisor cannot tell an attack from slow honest convergence. It is reported as failed and was not tuned away.

### 6.3 Limitations

- **Short sample, one regime.** Five and a half years, mostly one bull market, with momentum's profit concentrated in 2020 and 2021. The sealed year has not been seen. Nothing was traded live.
- **Multiple testing.** The deflated Sharpe is below its threshold at 45 strategy trials, and what counts as one trial needs judgement.
- **Assumptions not varied.** The impact coefficient, the information coefficients on the cards (momentum's 0.05 is an assumption), the one-million-dollar scale and the taker fee were fixed and not stress-tested.
- **Provisional momentum.** The agent covers two coins and failed its own admission rule narrowly. It was kept to study coordination and not to claim an edge.
- **Risk-model gap.** Reversal still runs at 24% to 29% volatility against the 20% limit. A one-factor beta model underprices books that are not tightly neutral.
- **Cost of decentralisation.** Each agent solves the system step itself, so work grows with the number of agents (the sixteen-agent study took about three hours). Some real-data rebalances reach the iteration cap (21 to 27 of about 135, even for the hub) with a small effect on profit.
- **Central pieces in simulation.** The step sizes, the stopping test and the simultaneous restart after an isolation are evaluated centrally. A deployment would use a pre-agreed constant, a max-consensus over the graph's diameter and a flooded isolation notice.
- **Earlier experiments not re-run.** The carry improvement (014) and timing (016) were not re-run after the volatility fix, because their code had been deleted when they were rejected.

### 6.4 Links to the theory

- *Prices as coordination.* Agents never see each other's beliefs. They see prices for margin, net trade, neutrality, beta and variance. Enforcing the system volatility limit as a price removed the cross-subsidy that a uniform rescale creates.
- *Consensus and optimisation interact.* Proposition 1 is what lets an optimiser run on a graph. A mixing rule that breaks it, such as trimming, breaks the optimiser.
- *Robustness is structural.* Whether a defence works depends on a property of the graph, as resilient-consensus theory states, and we observed it directly (ring against ring2).
- *Capital as a learning signal.* The market learns whom to trust without any agent evaluating another. Its practical benefit here was protection from failure, not return.

## 7. Conclusion and future work

We built and evaluated a multi-agent trading system in which heterogeneous agents stake capital in a market, are coordinated by prices in a joint ADMM, do so without a central node, tolerate link failures, dropout and a lying agent, and are monitored by formal safety specifications. The claim that survives scrutiny concerns mechanisms: the decentralised system reproduces the centralised one, and what it costs is communication and computation, not return. The return claim is weaker. Carry is a real edge and the combined system earns a Sharpe ratio of about 1.4 to 1.5 at its risk limit, but after correcting for the number of variants tried the development data alone cannot establish it. We report the failed gates as failed.

**Future work.**
1. Open the sealed final twelve months once, with the design frozen and momentum's admission rule applied unchanged.
2. Re-argue the hold supervisor's limit (the residuals of an attack and of slow honest convergence differ by about 300 times) and lengthen the volatility-price search for fast bar sizes.
3. Add a second, alt-coin-market risk factor to close the risk-model gap.
4. Test further established hypotheses one at a time, each with a card and rules written first: low volatility, a machine-learning trend model, and carry variants that use open interest or high and low prices.
5. Move towards deployment: pre-agreed step sizes, a max-consensus stopping test, flooded isolation notices and a communication model with delays.

## References

*Prepared from memory of the primary sources. Verify details before submission.*

1. Boyd, S., Parikh, N., Chu, E., Peleato, B., Eckstein, J. (2011). Distributed optimization and statistical learning via the alternating direction method of multipliers. *Foundations and Trends in Machine Learning* 3(1).
2. Olfati-Saber, R., Murray, R. M. (2004). Consensus problems in networks of agents with switching topology and time-delays. *IEEE Transactions on Automatic Control* 49(9).
3. Xiao, L., Boyd, S., Lall, S. (2005). A scheme for robust distributed sensor fusion based on average consensus. *IPSN* (Metropolis weights).
4. Zhu, M., Martínez, S. (2010). Discrete-time dynamic average consensus. *Automatica* 46(2).
5. LeBlanc, H. J., Zhang, H., Koutsoukos, X., Sundaram, S. (2013). Resilient asymptotic consensus in robust networks. *IEEE Journal on Selected Areas in Communications* 31(4).
6. Kelly, J. L. (1956). A new interpretation of information rate. *Bell System Technical Journal* 35(4).
7. Beygelzimer, A., Langford, J., Pennock, D. (2012). Learning performance of prediction markets with Kelly bettors. *AAMAS* (arXiv:1201.6655).
8. Maler, O., Nickovic, D. (2004). Monitoring temporal properties of continuous signals. *FORMATS*. Donzé, A., Maler, O. (2010). Robust satisfaction of temporal logic over real-valued signals. *FORMATS*.
9. Grinold, R. (1989). The fundamental law of active management. *Journal of Portfolio Management* 15(3).
10. Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
11. Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). Carry. *Journal of Financial Economics* 127(2). He, S., Manela, A., Ross, O., von Wachter, V. (2022). Fundamentals of perpetual futures, arXiv:2212.06888.
12. Moskowitz, T., Ooi, Y. H., Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics* 104(2).
13. Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of Finance* 45(3).
14. Course lecture notes (AI3403): Consensus Theory, ADMM, Distributed Learning, Resilient Consensus, Temporal Logics. Epistemic logic and infection models were part of the course and are not used here.

## Appendix A. Glossary

| Term | Meaning |
|---|---|
| Agent | an autonomous trading hypothesis with its own belief, capital and positions |
| Card | the written hypothesis of an agent: claim, mechanism, coins, expected edge, switch-off rule |
| Cell | an (agent, coin) pair |
| Hub | the central node of the centralised optimiser |
| Gossip round | one exchange of values between neighbours |
| Mixing rate | $\lvert\lambda_2(W)\rvert$; smaller means faster agreement |
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

## Appendix B. Where the evidence is

The experiment write-ups (011 to 023) and decision records (0032 to 0045) in the project repository give, for each result, the exact command, the pre-registered rule and the committed result tables. Section 5.2 is experiment 012. Section 5.3 is 013 to 018. Section 5.4 is 015 and 018. Section 5.5 is 019. Section 5.6 is 020. Section 5.7 is 021. Section 5.8 is 022. Section 5.9 is 023.
