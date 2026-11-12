import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Import data series from the analysis script
# These should be available after running or importing Monthly_Return_Analysis_Fourthstone
from Monthly_Return_Analysis_Fourthstone import (
    Fourthstone_net_return,
    benchmark_SPY,
    benchmark_AGG,
    benchmark_SOFR,
    benchmark_bankIndex,
    benchmark_KRX,
    benchmark_BKX,
    benchmark_SOFR500,  # we will exclude this
)

# Report colour scheme (matches HF_ReportLab_4thstone.py)
PRIMARY_COLOR = '#350B4D'
TEXT_MUTED = '#5A1F78'
LINE_COLOR = '#E5A93B'  # gold
GOLD_COLOR = LINE_COLOR

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def annualized_return(series):
    """CAGR from monthly returns series."""
    cum = (1 + series).prod() - 1
    n_months = len(series)
    years = n_months / 12.0
    return (1 + cum) ** (1 / years) - 1 if years > 0 else np.nan


def annualized_volatility(series):
    return series.std() * np.sqrt(12)


def max_drawdown(series):
    """Maximum peak-to-trough drawdown."""
    cum = (1 + series).cumprod()
    running_max = cum.cummax()
    drawdown = (cum - running_max) / running_max
    return drawdown.min()  # most negative


# ---------------------------------------------------------------------------
# Build lists of series and names, excluding SOFR500
# ---------------------------------------------------------------------------
benchmarks = {
    "S&P 500": benchmark_SPY,
    "Global AGG": benchmark_AGG,
    "SOFR": benchmark_SOFR,
    "bank Index": benchmark_bankIndex,
    "KRX Index": benchmark_KRX,
    "Bank Idx": benchmark_BKX,
    # "SOFR + 500bps": benchmark_SOFR500  # excluded per request
}

# Compute metrics for Fourthstone net returns and each benchmark
metrics = {}
metrics["Fourthstone Net Return"] = {
    "annual_return": annualized_return(Fourthstone_net_return),
    "annual_vol": annualized_volatility(Fourthstone_net_return),
    "max_dd": max_drawdown(Fourthstone_net_return),
}

for name, series in benchmarks.items():
    metrics[name] = {
        "annual_return": annualized_return(series),
        "annual_vol": annualized_volatility(series),
        "max_dd": max_drawdown(series),
    }

# ---------------------------------------------------------------------------
# Helper: build colored point lists for a given metric key
# ---------------------------------------------------------------------------
def build_point_lists(metrics, key):
    """Return xs, ys, colors lists ordered by metric keys.
    Fourthstone Net Return gets GOLD_COLOR, all benchmarks get 'black'."""
    xs = []
    ys = []
    colors = []
    for name, m in metrics.items():
        xs.append(m[key])
        ys.append(m["annual_return"])
        if name == "Fourthstone Net Return":
            colors.append(GOLD_COLOR)
        else:
            colors.append("black")
    return xs, ys, colors


# ---------------------------------------------------------------------------
# Scatter plot 1: Annualized Returns vs Annualized Volatility
# ---------------------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(8, 6))

xs1, ys1, colors1 = build_point_lists(metrics, "annual_vol")
ax1.scatter(xs1, ys1, s=80, c=colors1)

# Annotate points with names
for i, name in enumerate(metrics.keys()):
    ax1.annotate(name, (xs1[i], ys1[i]), textcoords="offset points", xytext=(5, 5), fontsize=8)

ax1.set_xlabel("Annualized Volatility")
ax1.set_ylabel("Annualized Returns")
ax1.set_title("Annualized Returns vs. Annualized Volatility")
ax1.grid(True, alpha=0.3)
# Legend removed per request

# Add marginal whitespace on x‑axis
ax1.margins(x=0.15)

# tight layout
plt.tight_layout()
fig1.savefig(r"C:\GithubLocalDirectory\Hedge_Fund_Report\scatter_volatility_returns.png", dpi=150)
plt.close(fig1)

# ---------------------------------------------------------------------------
# Scatter plot 2: Annualized Returns vs Maximum Drawdown
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(8, 6))

xs2, ys2, colors2 = build_point_lists(metrics, "max_dd")
ax2.scatter(xs2, ys2, s=80, c=colors2)

for i, name in enumerate(metrics.keys()):
    ax2.annotate(name, (xs2[i], ys2[i]), textcoords="offset points", xytext=(5, 5), fontsize=8)

ax2.set_xlabel("Maximum Drawdown")
ax2.set_ylabel("Annualized Returns")
ax2.set_title("Annualized Returns vs. Maximum Drawdown")
ax2.grid(True, alpha=0.3)
# Legend removed per request

# Reverse the x‑axis as requested
ax2.invert_xaxis()

# Add marginal whitespace on x‑axis
ax2.margins(x=0.15)

# tight layout
plt.tight_layout()
fig2.savefig(r"C:\GithubLocalDirectory\Hedge_Fund_Report\scatter_drawdown_returns.png", dpi=150)
plt.close(fig2)

print("Scatter plots saved: scatter_volatility_returns.png, scatter_drawdown_returns.png")