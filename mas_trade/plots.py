import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def equity_curves(returns, path, title="Growth of $1"):
    fig, ax = plt.subplots(figsize=(11, 6))
    for col in returns:
        lw, z = (2.6, 5) if col == "MAS" else (1.0, 2)
        ax.plot((1 + returns[col]).cumprod(), label=col, lw=lw, zorder=z)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.legend(ncol=3, fontsize=8)
    ax.grid(alpha=0.3)
    _save(fig, path)


def capital_area(capital, path):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(capital.index, capital.values.T / 1e3, labels=capital.columns)
    ax.set_title("Capital controlled by each agent ($k) - total changes only through P&L")
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    _save(fig, path)


def heatmap(df, path, title, center_zero=False, xlabel_every=6):
    """df: rows = dates, columns = labels."""
    fig, ax = plt.subplots(figsize=(11, 0.35 * df.shape[1] + 2.5))
    v = np.abs(df.values).max() if center_zero else None
    im = ax.imshow(df.values.T, aspect="auto", cmap="RdBu_r" if center_zero else "viridis",
                   vmin=-v if center_zero else None, vmax=v)
    ax.set_yticks(range(df.shape[1]), df.columns, fontsize=8)
    ticks = range(0, len(df), xlabel_every)
    ax.set_xticks(list(ticks), [df.index[i].strftime("%Y-%m") for i in ticks], rotation=45, fontsize=7)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _save(fig, path)


def consensus_convergence(dis, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.semilogy(np.arange(dis.shape[1]), np.maximum(dis.mean(0), 1e-16), marker="o")
    ax.set_xlabel("consensus round k")
    ax.set_ylabel("mean disagreement  x^T L x")
    ax.set_title("Consensus convergence (avg over rebalances)")
    ax.grid(alpha=0.3)
    _save(fig, path)


def matrix_snapshot(W, names, path, title):
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(W, cmap="viridis")
    ax.set_xticks(range(len(names)), names, rotation=45, fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{W[i, j]:.2f}", ha="center", va="center", color="w", fontsize=7)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _save(fig, path)


def sub_capital_heatmap(G, strategies, tickers, path, title):
    """Each strategy's budget shares over its asset subagents (rows sum to 1)."""
    share = G / G.sum(1, keepdims=True)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    im = ax.imshow(share, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(tickers)), tickers, rotation=45, fontsize=8)
    ax.set_yticks(range(len(strategies)), strategies, fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _save(fig, path)


def sub_capital_area(sub_capital, tickers, strategy_idx, strategy, path):
    """One strategy's budget per asset subagent over the rebalances ($k)."""
    dates = list(sub_capital)
    data = np.array([sub_capital[d][strategy_idx] for d in dates]) / 1e3
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(dates, data.T, labels=tickers)
    ax.set_title(f"{strategy}: capital run by each asset subagent ($k)")
    ax.legend(loc="upper left", fontsize=6, ncol=5)
    _save(fig, path)
