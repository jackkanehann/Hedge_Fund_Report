"""Risk/return and drawdown/return scatter plots.

Every point comes from ``series_registry.py``: the plots loop over the specs
flagged ``include_in_scatter``, resolve their values through ``data_loader`` and
label/colour them from the spec.  Adding a CSV series to the registry therefore
adds a point to both charts with no code change here.

Run:  python scatter_plots.py
Out:  scatter_volatility_returns.png, scatter_drawdown_returns.png
      (written next to this file, referenced by HF_ReportLab_4thstone.py)
"""

import logging
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from data_loader import PROJECT_ROOT, build_series_map
from series_registry import scatter_specs

OUTPUT_VOLATILITY = PROJECT_ROOT / "scatter_volatility_returns.png"
OUTPUT_DRAWDOWN = PROJECT_ROOT / "scatter_drawdown_returns.png"

# Colours come from each series' SeriesSpec in series_registry.py, so new
# series can be styled without editing this file.

FIG_SIZE = (8, 6)
DPI = 150

logger = logging.getLogger(__name__)


@dataclass
class ScatterPoint:
    """One plotted series: its position, label and styling."""

    label: str
    x: float
    y: float
    color: str
    size: int
    months: int = 0


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def annualized_return(series):
    """CAGR from monthly returns series."""
    cumulative = (1 + series).prod() - 1
    years = len(series) / 12.0
    return (1 + cumulative) ** (1 / years) - 1 if years > 0 else np.nan


def annualized_volatility(series):
    return series.std() * np.sqrt(12)


def max_drawdown(series):
    """Maximum peak-to-trough drawdown."""
    cumulative = (1 + series).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()  # most negative


METRICS = {
    "annual_vol": annualized_volatility,
    "max_dd": max_drawdown,
    "annual_return": annualized_return,
}


# ---------------------------------------------------------------------------
# Point collection
# ---------------------------------------------------------------------------
def collect_points(specs, series_map, metric_key):
    """Build ScatterPoints for every series, skipping ones without data.

    Each series is measured over its own full history, matching the behaviour
    of the original hand-written plots (which did not align the series first).
    """
    metric = METRICS[metric_key]
    points = []
    for spec in specs:
        series = series_map.get(spec.key)
        if series is None:
            logger.warning("series %r is not available - skipped", spec.key)
            continue

        series = series.dropna()
        if series.empty:
            logger.warning("series %r has no observations - skipped", spec.key)
            continue

        annual = annualized_return(series)
        x_value = metric(series)
        if np.isnan(annual) or np.isnan(x_value):
            logger.warning("series %r produced NaN metrics - skipped", spec.key)
            continue

        points.append(ScatterPoint(
            label=spec.label,
            x=float(x_value),
            y=float(annual),
            color=spec.color,
            size=spec.marker_size,
            months=int(len(series)),
        ))
    return points


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_scatter(points, x_label, y_label, title, output_path, invert_x=False):
    """Draw one scatter chart and save it as a PNG."""
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ax.scatter(
        [point.x for point in points],
        [point.y for point in points],
        s=[point.size for point in points],
        c=[point.color for point in points],
    )

    for point in points:
        ax.annotate(
            point.label,
            (point.x, point.y),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    # Legend intentionally omitted - points are annotated directly

    if invert_x:
        ax.invert_xaxis()

    # Add marginal whitespace on x-axis
    ax.margins(x=0.15)

    plt.tight_layout()
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)
    return output_path


def log_summary(points, metric_label):
    """Print what was plotted so the numbers can be sanity-checked."""
    print(f"{'Series':<28}{'Annual Return':>14}{metric_label:>16}{'Months':>8}")
    for point in points:
        print(f"{point.label:<28}{point.y:>13.2%}{point.x:>16.2%}{point.months:>8}")


def main():
    specs = scatter_specs()
    series_map = build_series_map(specs)

    volatility_points = collect_points(specs, series_map, "annual_vol")
    drawdown_points = collect_points(specs, series_map, "max_dd")

    render_scatter(
        volatility_points,
        "Annualized Volatility",
        "Annualized Returns",
        "Annualized Returns vs. Annualized Volatility",
        OUTPUT_VOLATILITY,
    )
    render_scatter(
        drawdown_points,
        "Maximum Drawdown",
        "Annualized Returns",
        "Annualized Returns vs. Maximum Drawdown",
        OUTPUT_DRAWDOWN,
        invert_x=True,
    )

    log_summary(volatility_points, "Annualized Vol")
    log_summary(drawdown_points, "Max Drawdown")
    print(
        f"\nScatter plots saved: {OUTPUT_VOLATILITY.name}, {OUTPUT_DRAWDOWN.name} "
        f"({len(volatility_points)} series)"
    )
    return volatility_points, drawdown_points


if __name__ == "__main__":
    main()

