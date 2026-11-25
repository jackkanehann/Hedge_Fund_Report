"""Data access layer for the project.

Everything that turns a file on disk into a clean monthly return series lives
here, so the analysis module and the scatter plots share one implementation.

Conventions enforced for every series, whatever the source:

* index  : tz-aware month-end timestamps in ``PROJECT_TZ`` (see below)
* values : decimal returns (0.0123 == 1.23%), NaN where a month is missing
* name   : the registry key, so alignment by column name always works

The workbook already stores month-end dates localised to ``America/New_York``;
that convention is preserved so existing output is unchanged, and CSV data is
normalised onto the same index.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

import series_registry
from series_registry import (
    WORKBOOK_ATTRIBUTION_SHEET,
    WORKBOOK_FILENAME,
    WORKBOOK_RETURNS_SHEET,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_TZ = "America/New_York"
DEFAULT_WORKBOOK_PATH = PROJECT_ROOT / WORKBOOK_FILENAME

DATE_COLUMN_HINTS = ("date", "month", "period", "as of", "asof")


# ---------------------------------------------------------------------------
# Numeric cleaning (shared with the analysis module, which re-exports it)
# ---------------------------------------------------------------------------
def clean_numeric_column(df, column_name):
    """
    Cleans a dataframe column containing numbers stored as strings.
    Handles percentages, currency symbols, and commas.
    """
    # 1. Copy the column as strings and remove whitespace
    s = df[column_name].astype(str).str.strip()

    # 2. Check if the column represents percentages
    is_percent = s.str.endswith('%').any()

    # 3. Remove common non-numeric characters (%, $, commas)
    s = s.str.replace('%', '', regex=False)
    s = s.str.replace('$', '', regex=False)
    s = s.str.replace(',', '', regex=False)

    # 4. Convert to numeric, forcing errors to NaN (missing values)
    numeric_col = pd.to_numeric(s, errors='coerce')

    # 5. Convert percentage values to decimals
    if is_percent:
        numeric_col = numeric_col / 100.0

    return numeric_col


# ---------------------------------------------------------------------------
# Index / path helpers
# ---------------------------------------------------------------------------
def month_end_index(dates):
    """Return a tz-aware month-end DatetimeIndex in the project timezone."""
    index = pd.DatetimeIndex(pd.to_datetime(dates))
    if index.tz is not None:
        index = index.tz_convert(PROJECT_TZ).tz_localize(None)
    return index.to_period("M").to_timestamp("M").tz_localize(PROJECT_TZ)


def resolve_path(path):
    """Resolve a path relative to the project folder (absolute paths pass through)."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate



# ---------------------------------------------------------------------------
# Workbook
# ---------------------------------------------------------------------------
def _prepare_frame(frame, source_name):
    """Index by month end, drop bookkeeping columns, coerce everything numeric."""
    indexed = frame.set_index(month_end_index(frame["Date"]))
    for redundant in ("Month",):
        if redundant in indexed.columns:
            indexed = indexed.drop(columns=[redundant])
    for column in indexed.columns:
        if column != "Date":
            indexed[column] = clean_numeric_column(indexed, column)
    logger.debug("%s: %d rows, %d columns", source_name, len(indexed), len(indexed.columns))
    return indexed


@lru_cache(maxsize=4)
def _load_workbook_sheets(path_str):
    raw = pd.read_excel(path_str, sheet_name=None)
    # Preserve the historical behaviour: rows with any blank cell are dropped
    # (this is what removes the empty 2013-12-31 placeholder row).
    return {key: frame.dropna(how='any') for key, frame in raw.items()}


def load_workbook_returns(path=None):
    """The 'Mthly_returns' sheet as a cleaned, month-end indexed DataFrame."""
    path = resolve_path(path or DEFAULT_WORKBOOK_PATH)
    sheets = _load_workbook_sheets(str(path))
    return _prepare_frame(sheets[WORKBOOK_RETURNS_SHEET], WORKBOOK_RETURNS_SHEET)


def load_workbook_attribution(path=None):
    """The 'LS_attribution' sheet (exposure columns, not returns)."""
    path = resolve_path(path or DEFAULT_WORKBOOK_PATH)
    sheets = _load_workbook_sheets(str(path))
    return _prepare_frame(sheets[WORKBOOK_ATTRIBUTION_SHEET], WORKBOOK_ATTRIBUTION_SHEET)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def _read_csv(path):
    """Read a CSV, tolerating encoding and delimiter surprises."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return pd.read_csv(path, encoding="utf-8-sig")


def detect_date_column(frame):
    """Find the date column: by name first, then by parseability."""
    for column in frame.columns:
        if str(column).strip().lower() in DATE_COLUMN_HINTS:
            return column

    for column in frame.columns:
        parsed = pd.to_datetime(frame[column], errors="coerce", format="mixed")
        if parsed.notna().mean() > 0.9:
            return column

    raise ValueError(
        "Could not find a date column in the CSV. Columns present: "
        f"{list(frame.columns)}. Pass date_column=... to name it explicitly."
    )


def _coerce_returns(column_values, value_scale):
    """Return (decimal returns, description of the scaling that was applied)."""
    text = column_values.astype(str).str.strip()
    has_percent_symbol = text.str.endswith("%").any()

    stripped = (
        text.str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
    )
    values = pd.to_numeric(stripped, errors="coerce")

    if has_percent_symbol:
        return values / 100.0, "percent (detected '%' in values)"

    if value_scale == "percent":
        return values / 100.0, "percent (configured)"

    if value_scale == "decimal":
        return values, "decimal (configured)"

    if value_scale != "auto":
        raise ValueError(
            f"value_scale must be 'auto', 'percent' or 'decimal', got {value_scale!r}"
        )

    peak = values.abs().max()
    # A monthly decimal return above 1.0 (>100% in one month) is implausible, so
    # treat such a column as percent.  Override with value_scale='percent' or
    # 'decimal' when the data is genuinely ambiguous (e.g. 0.50 meaning 50bps).
    if pd.notna(peak) and peak > 1.0:
        return values / 100.0, f"percent (auto: max abs {peak:.2f} > 1)"
    return values, "decimal (auto)"


@lru_cache(maxsize=8)
def load_csv_returns(path, date_column=None, value_scale="auto"):
    """Load a CSV of monthly returns into a month-end indexed DataFrame.

    Columns that cannot be parsed as numbers are dropped; the remainder are
    returned as decimal returns named after their CSV headers.
    """
    resolved = resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Return series CSV not found: {resolved}\n"
            "Add the file to the project folder and reference it by filename in series_registry.py."
        )

    raw = _read_csv(resolved)
    if raw.empty:
        raise ValueError(f"{resolved.name} contains no rows.")

    date_column = date_column or detect_date_column(raw)
    index = month_end_index(raw[date_column])

    series = {}
    for column in raw.columns:
        if column == date_column:
            continue
        values, scaling = _coerce_returns(raw[column], value_scale)
        values = pd.Series(values.to_numpy(), index=index, name=column)
        if values.notna().sum() == 0:
            logger.warning("%s: column %r has no numeric data - skipped", resolved.name, column)
            continue
        logger.info("%s: column %r read as %s", resolved.name, column, scaling)
        series[column] = values

    if not series:
        raise ValueError(
            f"{resolved.name}: no numeric return columns found. Columns present: {list(raw.columns)}"
        )

    frame = pd.DataFrame(series)
    # Guard against duplicate month-end rows (e.g. two rows for the same month)
    frame = frame[~frame.index.duplicated(keep="last")]
    # Newest-first, matching the workbook convention: the tear sheets rely on
    # index[0] being the latest month and index[-1] the earliest.
    return frame.sort_index(ascending=False)


# ---------------------------------------------------------------------------
# Registry -> series
# ---------------------------------------------------------------------------
def series_for_spec(spec, workbook_returns=None, csv_frames=None):
    """Resolve one SeriesSpec into a named Series indexed by month end."""
    if spec.is_csv:
        cache = {} if csv_frames is None else csv_frames
        if spec.csv_path not in cache:
            cache[spec.csv_path] = load_csv_returns(
                spec.csv_path, spec.date_column or None, spec.value_scale
            )
        frame = cache[spec.csv_path]
        if spec.column not in frame.columns:
            raise KeyError(
                f"{spec.csv_path}: column {spec.column!r} not found for series {spec.key!r}. "
                f"Available columns: {list(frame.columns)}"
            )
        return frame[spec.column].rename(spec.key)

    frame = load_workbook_returns() if workbook_returns is None else workbook_returns
    if spec.column not in frame.columns:
        raise KeyError(
            f"{WORKBOOK_FILENAME}: column {spec.column!r} not found for series {spec.key!r}. "
            f"Available columns: {list(frame.columns)}"
        )
    return frame[spec.column].rename(spec.key)


def build_series_map(specs=None):
    """Return {key: Series} for the given specs (all registered specs by default)."""
    # Read the registry live so runtime additions to
    # series_registry.EXTERNAL_SERIES_SPECS are picked up too.
    specs = series_registry.all_specs() if specs is None else specs
    workbook_returns = None
    csv_frames = {}
    if any(not spec.is_csv for spec in specs):
        workbook_returns = load_workbook_returns()

    resolved = {}
    for spec in specs:
        try:
            resolved[spec.key] = series_for_spec(spec, workbook_returns, csv_frames)
        except (KeyError, FileNotFoundError, ValueError) as error:
            # One bad CSV entry must not take the whole report down.
            logger.error("series %r could not be loaded: %s", spec.key, error)
    return resolved


@lru_cache(maxsize=1)
def load_project_series():
    """Cached {key: Series} map for every registered series."""
    return build_series_map()


def clear_caches():
    """Drop cached files - useful after adding a CSV or editing the registry."""
    _load_workbook_sheets.cache_clear()
    load_csv_returns.cache_clear()
    load_project_series.cache_clear()

