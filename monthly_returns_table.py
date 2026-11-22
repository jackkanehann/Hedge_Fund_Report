"""Monthly return matrix page.

Builds one page of monthly net returns for:
    * Fourthstone Opportunity Fund (net of fees)
    * Nasdaq Bank Index
    * S&P 500 Index

Layout is a 14-column grid:  Year | Jan ... Dec | Annual
Each calendar year from 2026 back to 2014 occupies three rows (one per series),
newest year first, and the year label is vertically spanned across those rows.
The rightmost column compounds the months displayed, so an unfinished year
shows a year-to-date figure.

`build_monthly_returns_table()` is designed to be dropped straight into
HF_ReportLab_4thstone.py; running this file builds a one-page preview so the
layout can be reviewed before it is inserted into the report.

Run:  python monthly_returns_table.py
Out:  monthly_returns_preview.pdf
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
)

from Monthly_Return_Analysis_Fourthstone import (
    Fourthstone_net_return,
    benchmark_bankIndex,
    benchmark_SPY,
)

PREVIEW_FILENAME = "monthly_returns_preview.pdf"

# --- Report colour scheme (matches HF_ReportLab_4thstone.py) ------------------
PRIMARY_COLOR = colors.HexColor("#350B4D")     # dark purple - titles, Year column
TEXT_MUTED = colors.HexColor("#5A1F78")        # muted purple - secondary text
LINE_COLOR = colors.HexColor("#E5A93B")        # gold - accents
HEADING_COLOR = colors.HexColor("#1A365D")     # report section headings
BODY_COLOR = colors.HexColor("#2D3748")        # report body text
DARK_TEXT = colors.HexColor("#1A202C")         # figures
NEGATIVE_COLOR = colors.HexColor("#9B2C2C")    # losses (report's crimson)
GRID_COLOR = colors.HexColor("#B4B4C4")
RULE_DARK = colors.HexColor("#1A202C")

# Row tints make the three series readable across fourteen columns without
# resorting to coloured numerals at 7pt.
FOURTHSTONE_TINT = colors.HexColor("#FBEFD6")  # warm sand
BANK_INDEX_TINT = colors.HexColor("#E7DDF5")   # lilac
SP500_TINT = colors.HexColor("#FFFFFF")        # white
YEAR_COLUMN_TINT = colors.HexColor("#EDE9F4")

MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# (display label, series, row tint, bold, legend swatch colour)
SERIES_ROWS = [
    ("Fourthstone Net Return", Fourthstone_net_return, FOURTHSTONE_TINT, True, PRIMARY_COLOR),
    ("Nasdaq Bank Index", benchmark_bankIndex, BANK_INDEX_TINT, False, TEXT_MUTED),
    ("S&P 500 Index", benchmark_SPY, SP500_TINT, False, colors.HexColor("#4A5568")),
]

ROWS_PER_YEAR = len(SERIES_ROWS)


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------
def _to_decimal_series(series):
    """Index a return series by (year, month) as floats, skipping gaps."""
    values = {}
    for timestamp, value in series.items():
        if value != value:  # NaN guard
            continue
        values[(timestamp.year, timestamp.month)] = float(value)
    return values


def _compounded(month_values):
    """Compound a list of monthly decimals; None if there is nothing to show."""
    growth = 1.0
    for value in month_values:
        growth *= 1.0 + value
    return growth - 1.0 if month_values else None


def build_monthly_returns_data(newest_first=True):
    """Return {year: [(label, [12 month values or None], annual), ...]}.

    Blocks are keyed in display order: newest year first by default, so the
    table reads from the current year back to inception.
    """
    matrices = [(label, _to_decimal_series(series)) for label, series, *_ in SERIES_ROWS]

    years_present = {
        year
        for _label, matrix in matrices
        for (year, _month) in matrix.keys()
    }
    years = sorted(years_present, reverse=newest_first)

    blocks = {}
    for year in years:
        rows = []
        for label, matrix in matrices:
            months = [matrix.get((year, month)) for month in range(1, 13)]
            observed = [value for value in months if value is not None]
            rows.append((label, months, _compounded(observed)))
        blocks[year] = rows
    return blocks


def _format_return(value):
    return "" if value is None else f"{value * 100:.2f}%"


# ---------------------------------------------------------------------------
# Table construction
# ---------------------------------------------------------------------------
# 15 columns inside a 504pt text frame, matching the report's 54pt margins.
YEAR_COL_WIDTH = 30
ANNUAL_COL_WIDTH = 45
MONTH_COL_WIDTH = (504 - YEAR_COL_WIDTH - ANNUAL_COL_WIDTH) / 12.0


def build_monthly_returns_table(
    cell_font_size=7.2,
    header_font_size=7.5,
    row_height=13.0,
    header_row_height=13.0,
    row_padding=0.5,
):
    """Return a ReportLab Table of monthly returns by year.

    Column 0 is the (spanned) year, columns 1-12 are Jan..Dec and the final
    column compounds the displayed months for that calendar year.

    Row heights are set explicitly: ReportLab otherwise sizes string cells from
    the default 10pt leading and ignores the FONTSIZE style command, which
    leaves the table too tall for a single portrait page.
    """
    blocks = build_monthly_returns_data()

    header = ["Year"] + MONTH_LABELS + ["Annual"]
    table_rows = [header]

    fund_rows = []          # (row index, tint colour) for every series row
    year_spans = []         # (first row, last row) of each year block
    negative_cells = []     # (column, row) of every negative figure

    for year, series_rows in blocks.items():
        first_row = len(table_rows)
        for offset, (_label, months, annual) in enumerate(series_rows):
            row = [str(year)] + [_format_return(value) for value in months]
            row.append(_format_return(annual))
            table_rows.append(row)
            fund_rows.append((len(table_rows) - 1, SERIES_ROWS[offset][2]))
            for column_index, value in enumerate(months, start=1):
                if value is not None and value < 0:
                    negative_cells.append((column_index, len(table_rows) - 1))
            if annual is not None and annual < 0:
                negative_cells.append((len(header) - 1, len(table_rows) - 1))
        year_spans.append((first_row, len(table_rows) - 1))

    table = Table(
        table_rows,
        colWidths=[YEAR_COL_WIDTH] + [MONTH_COL_WIDTH] * 12 + [ANNUAL_COL_WIDTH],
        rowHeights=[header_row_height] + [row_height] * (len(table_rows) - 1),
        repeatRows=1,
    )

    style = [
        # Header band
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, RULE_DARK),

        # Body defaults
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), cell_font_size),
        ("TEXTCOLOR", (1, 1), (-1, -1), DARK_TEXT),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),

        # Year column
        ("BACKGROUND", (0, 1), (0, -1), YEAR_COLUMN_TINT),
        ("TEXTCOLOR", (0, 1), (0, -1), PRIMARY_COLOR),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (0, -1), cell_font_size + 1.0),

        # Grid
        ("GRID", (0, 0), (-1, -1), 0.35, GRID_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), row_padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), row_padding),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
    ]

    # Series row tints (label the three rows without colouring the numerals)
    for row_index, tint in fund_rows:
        style.append(("BACKGROUND", (1, row_index), (-1, row_index), tint))

    for year_index, (first_row, last_row) in enumerate(year_spans):
        style.append(("SPAN", (0, first_row), (0, last_row)))
        style.append(("LINEBELOW", (0, last_row), (-1, last_row), 0.9, RULE_DARK))
        # The fund itself is the emphasis row of each three-row block
        if SERIES_ROWS[0][3]:
            style.append(("FONTNAME", (1, first_row), (-1, first_row), "Helvetica-Bold"))
        if SERIES_ROWS[1][3]:
            style.append(("FONTNAME", (1, first_row + 1), (-1, first_row + 1), "Helvetica-Bold"))
        if SERIES_ROWS[2][3]:
            style.append(("FONTNAME", (1, first_row + 2), (-1, first_row + 2), "Helvetica-Bold"))

    # Annual column emphasis: bold figures behind a gold rule, so the fund row
    # tints still read across the full width.
    annual_col = len(header) - 1
    style.append(("FONTNAME", (annual_col, 1), (annual_col, -1), "Helvetica-Bold"))
    style.append(("LINEBEFORE", (annual_col, 0), (annual_col, -1), 0.9, LINE_COLOR))

    # Losses in crimson
    for column, row in negative_cells:
        style.append(("TEXTCOLOR", (column, row), (column, row), NEGATIVE_COLOR))

    table.setStyle(TableStyle(style))
    return table


def build_monthly_returns_legend(legend_style, legend_bold_style=None):
    """Row-key for the table: one filled, labelled chip per series.

    Each chip is a table cell filled with the same tint used on that series'
    rows and edged in its accent colour, so the pale tints read clearly at
    small size.  Plain strings are used rather than Paragraphs: a Paragraph
    given a cell exactly as wide as its text can wrap and clip a glyph.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    font_size = legend_style.fontSize
    chip_padding = 5
    gap = 12

    cells = []
    widths = []
    chip_columns = []
    for index, (label, _series, tint, bold, swatch_color) in enumerate(SERIES_ROWS):
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        widths.append(stringWidth(label, font_name, font_size) + 2 * chip_padding + 2)
        cells.append(label)
        chip_columns.append((len(cells) - 1, tint, swatch_color, font_name))
        if index < len(SERIES_ROWS) - 1:
            cells.append("")
            widths.append(gap)

    legend = Table([cells], colWidths=widths)
    style_commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), BODY_COLOR),
    ]
    for column, tint, accent, font_name in chip_columns:
        style_commands.append(("BACKGROUND", (column, 0), (column, 0), tint))
        style_commands.append(("BOX", (column, 0), (column, 0), 0.7, accent))
        style_commands.append(("FONTNAME", (column, 0), (column, 0), font_name))

    # The fund's chip carries its accent colour, tying it to the bold rows.
    style_commands.append(("TEXTCOLOR", (0, 0), (0, 0), PRIMARY_COLOR))

    legend.setStyle(TableStyle(style_commands))
    return legend


def build_page_styles():
    """Styles for this page, sized to keep the whole table on one portrait page.

    Defaults reproduce the approved preview build; pass explicit styles to
    override when embedding in the report.
    """
    styles = getSampleStyleSheet()
    page_title_style = ParagraphStyle(
        'MonthlyReturnsTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=HEADING_COLOR,
        spaceBefore=0,
        spaceAfter=4,
        keepWithNext=True,
    )
    caption_style = ParagraphStyle(
        'MonthlyReturnsCaption',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#4A5568"),
    )
    legend_style = ParagraphStyle(
        'MonthlyReturnsLegend',
        parent=caption_style,
        fontSize=7.8,
        leading=10,
        textColor=BODY_COLOR,
    )
    legend_bold_style = ParagraphStyle(
        'MonthlyReturnsLegendBold',
        parent=legend_style,
        fontName='Helvetica-Bold',
        textColor=PRIMARY_COLOR,
    )
    return page_title_style, caption_style, legend_style, legend_bold_style


def build_monthly_returns_page_story(page_title_style=None, caption_style=None,
                                     legend_style=None, legend_bold_style=None):
    """Page contents: heading, table, legend and caption.

    Returns a list of flowables, so it can be spliced straight into the
    report's story wherever this page belongs.  Unsupplied styles fall back to
    the validated defaults, so a bare ``build_monthly_returns_page_story()``
    is a complete page.
    """
    default_title, default_caption, default_legend, default_legend_bold = build_page_styles()
    page_title_style = page_title_style or default_title
    caption_style = caption_style or default_caption
    legend_style = legend_style or default_legend
    legend_bold_style = legend_bold_style or default_legend_bold

    story = [
        Paragraph("Monthly Returns", page_title_style),
        Paragraph(
            "Fourthstone Opportunity Fund (net of fees) vs. Nasdaq Bank Index and S&amp;P 500 Index "
            "| January 2014 &ndash; July 2026",
            caption_style,
        ),
        Spacer(1, 8),
        build_monthly_returns_table(),
        Spacer(1, 7),
        build_monthly_returns_legend(legend_style, legend_bold_style),
        Spacer(1, 5),
        Paragraph(
            "Monthly net returns in percent. The Annual column compounds the monthly figures shown, "
            "so 2026 is year-to-date through 31 July 2026. Blank cells are months not yet reported. "
            "Source: Fourthstone monthly composite data; Nasdaq Bank and S&amp;P 500 index returns.",
            caption_style,
        ),
    ]
    return story


def _build_preview(output_filename=PREVIEW_FILENAME):
    """Render the page on its own so the layout can be reviewed before insertion."""
    # Imported lazily to keep this module free of a circular dependency with
    # the report script once it is embedded there.
    from HF_ReportLab_4thstone import NumberedCanvas

    page_size = letter
    doc = BaseDocTemplate(
        output_filename,
        pagesize=page_size,
        title="Monthly Returns (preview)",
        author="Jack Kanehann, CFA",
    )
    frame = Frame(
        54, 72,
        page_size[0] - 108,
        page_size[1] - 144,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id='PortraitFrame',
    )
    doc.addPageTemplates([PageTemplate(id='Portrait', pagesize=page_size, frames=[frame])])

    story = build_monthly_returns_page_story()
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Preview written to {output_filename}")


if __name__ == "__main__":
    _build_preview()

