# 0016. v2 books: rank-gauss scores, dollar- and beta-neutral, vol-targeted

Status: **Accepted**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `v2/agents.py`, `v2/books.py`

## Decision
New agent set: XS momentum, residual reversal, funding carry, size/liquidity (cross-sectional), and a BTC timing agent. Cross-sectional scores are rank-gauss transformed, projected to dollar- **and** BTC-beta-neutral, and vol-targeted (20% annual, gross cap 3) with a Ledoit-Wolf covariance. The timing book alone owns net exposure and trades BTC only. Information before t only.

## Rationale (inferred)
Neutral books isolate selection skill from market moves. Rank-gauss makes agents comparable.
