# 0026. Safety limits

Status: **Accepted** (2026-11-05, approved by the user)   Flags: `Config.safety_*`

## Context
Every spec has a limit. Results, and how often the shield acts, depend strongly on the limits, and choosing them by looking at performance is a form of overfitting. So each limit is justified by a risk-mandate argument, not by a backtest.

## Limits and the mandate behind each (stocks)
| Setting | Value | Mandate argument |
|---|---|---|
| `safety_max_vol` / `safety_vol_window` | 20% annual, over 21 bars | The system should be **no riskier than the equity market it trades**. SPY's vol over the sample is about 18.5%; 20% rounds that up. A one-month window is the horizon a risk desk would check. |
| `safety_max_dd` / `safety_dd_window` | 15% over 252 bars | Lose at most **about half of what the equity market lost in its worst stretch** (SPY -34% in 2020) within any one year. One-year window, so the limit resets and a drawdown can recover. |
| `safety_recover` | 10 bars | A vol breach lasting more than **two trading weeks** means the vol control has failed, not just lagged. |
| `safety_max_weight` | 20% | **No single stock decides the outcome**: with 20 stocks, at most 4x the equal weight (5%). |
| `safety_buffer` / `safety_min_scale` | 0.5 / 0.2 | Start de-risking with **half the drawdown budget left**, and never go below 20% exposure, so the system keeps a track record to recover with. |
| `safety_max_disagreement` | 0.35 | Monitor only (W-MSR mode): agents should not end a rebalance further apart than they usually do (95th percentile 0.30). |

## Crypto (`Config.for_tier`)
| Setting | Value | Mandate argument |
|---|---|---|
| `safety_max_vol` | 40% | **Well below BTC's own vol** (typically 60–80% annual); a diversified long-short book should not carry single-asset crypto risk. |
| `safety_dd_window`, `safety_vol_window`, `safety_recover` | 365, 30, 14 days (in bars) | Same horizons as stocks, in calendar time for a 24/7 market. |
| others | as stocks | |

## Honesty note
The provisional values (set earlier on 2026-11-05) were picked by looking at the unshielded system's **risk levels** (vol, drawdown, concentration, disagreement) over the full stock sample, not its performance. They were then accepted unchanged with the arguments above. No threshold sweep has been run. **Changing a limit needs a new decision record**, and limits must never be chosen by comparing Sharpe ratios across values.

## Rollback
Each is a Config field.
