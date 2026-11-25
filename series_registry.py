"""Single source of truth for every return series in the project.

Any series used by the analysis, the scatter plots or the report is declared
here exactly once.  Downstream code (``data_loader``, ``scatter_plots``, the
analysis module) reads this registry instead of hardcoding its own lists, so a
new series becomes a one-entry change.

Adding a new CSV series
-----------------------
1. Drop the CSV in the project folder (it is picked up relative to this file).
2. Append a ``SeriesSpec`` to ``EXTERNAL_SERIES_SPECS`` below.
3. Re-run ``python scatter_plots.py`` (and the report) - nothing else changes.

The CSV needs a date column and one or more numeric return columns, e.g.::

    Date,My Fund,MSCI World
    2020-01-31,1.25%,-0.80%
    2020-02-28,-2.10%,-8.40%

Percent signs, thousands separators and currency symbols are stripped
automatically; ``value_scale`` controls whether figures are read as percent or
as decimals (see ``data_loader.load_csv_returns``).
"""

from dataclasses import dataclass

# --- Workbook (primary data source) ------------------------------------------
WORKBOOK_FILENAME = "Fourthstone_Cleaned_Data.xlsx"
WORKBOOK_RETURNS_SHEET = "Mthly_returns"
WORKBOOK_ATTRIBUTION_SHEET = "LS_attribution"

# --- Styling defaults --------------------------------------------------------
FUND_COLOR = "#E5A93B"          # gold, matches the report accent
BENCHMARK_COLOR = "#000000"     # black, as used by the existing scatters
# Distinct colours handed out to CSV series so they stay identifiable.
EXTERNAL_COLORS = ("#1F6F8B", "#B85C38", "#2E7D32", "#6A1B9A", "#C2185B", "#00838F")


@dataclass(frozen=True)
class SeriesSpec:
    """Declaration of one monthly return series and how to display it."""

    key: str                    # variable/key name, e.g. "benchmark_SPY"
    label: str                  # display label used in charts and legends
    column: str                 # column name in the source
    source: str = "workbook"    # "workbook" | "csv"
    role: str = "benchmark"     # "fund" | "benchmark" | "external"
    color: str = BENCHMARK_COLOR
    marker_size: int = 80
    include_in_scatter: bool = True
    bold_label: bool = False
    # CSV-only settings (ignored for workbook series)
    csv_path: str = ""                  # relative to the project folder
    date_column: str = ""               # "" = auto-detect
    value_scale: str = "auto"           # "auto" | "percent" | "decimal"

    @property
    def is_csv(self) -> bool:
        return self.source == "csv"


# ---------------------------------------------------------------------------
# Workbook series.  Keys are the historical module-level names exported by
# Monthly_Return_Analysis_Fourthstone, so existing imports keep working.
# ---------------------------------------------------------------------------
WORKBOOK_SERIES_SPECS = [
    # Fund returns (net is the headline series plotted in the scatters)
    SeriesSpec("Fourthstone_net_return", "Fourthstone Net Return",
               "Net Monthly Composite Return %", role="fund",
               color=FUND_COLOR, marker_size=80),
    SeriesSpec("Fourthstone_gross_return", "Fourthstone Gross Return",
               "Gross Monthly Composite Return %", role="fund",
               color=FUND_COLOR, marker_size=80, include_in_scatter=False),
    SeriesSpec("Fourthstone_long_return", "Fourthstone Long Book",
               "Long Return %", role="fund",
               color=FUND_COLOR, marker_size=80, include_in_scatter=False),
    SeriesSpec("Fourthstone_short_return", "Fourthstone Short Book",
               "Short Return %", role="fund",
               color=FUND_COLOR, marker_size=80, include_in_scatter=False),

    # Benchmarks
    SeriesSpec("benchmark_SPY", "S&P 500", "SPX INDEX"),
    SeriesSpec("benchmark_AGG", "Global AGG", "LBUSTRUU INDEX"),
    SeriesSpec("benchmark_SOFR", "SOFR", "BTSISOFR INDEX"),
    SeriesSpec("benchmark_bankIndex", "bank Index", "NASDAQ Bank Index Monthly Return %"),
    SeriesSpec("benchmark_KRX", "KRX Index", "KRX INDEX"),
    SeriesSpec("benchmark_BKX", "Bank Idx", "BKX INDEX"),
    # Maintained for the tear sheets but deliberately excluded from the scatter
    # plots (it is a rate hurdle, not a comparable investment).
    SeriesSpec("benchmark_SOFR500", "SOFR + 500bps", "SOFR + 500bps",
               include_in_scatter=False),
]


# ---------------------------------------------------------------------------
# CSV series.  Append entries here to bring new return streams into the scatter
# plots.  `column` must match the CSV header exactly; `csv_path` is relative to
# this project folder.
#
# Example (uncomment and edit):
#
# EXTERNAL_SERIES_SPECS = [
#     SeriesSpec(
#         key="external_my_fund",
#         label="My Fund",
#         source="csv",
#         csv_path="my_fund_returns.csv",
#         column="My Fund",
#         role="external",
#         color=EXTERNAL_COLORS[0],
#         marker_size=60,
#     ),
# ]
# ---------------------------------------------------------------------------
EXTERNAL_SERIES_SPECS: list = []


def all_specs():
    """Every registered series spec, in declaration order.

    Computed on each call so specs added at runtime are included.
    """
    return WORKBOOK_SERIES_SPECS + EXTERNAL_SERIES_SPECS


def scatter_specs(specs=None):
    """Series that belong on the scatter plots, in declaration order."""
    specs = all_specs() if specs is None else specs
    return [spec for spec in specs if spec.include_in_scatter]


def spec_by_key(key, specs=None):
    """Look up one spec by key; raises KeyError listing what is available."""
    specs = all_specs() if specs is None else specs
    for spec in specs:
        if spec.key == key:
            return spec
    raise KeyError(f"Unknown series key {key!r}. Known keys: {[s.key for s in specs]}")


def workbook_specs(specs=None):
    """Series that come from the Fourthstone workbook (all available keys)."""
    specs = all_specs() if specs is None else specs
    return [spec for spec in specs if not spec.is_csv]
