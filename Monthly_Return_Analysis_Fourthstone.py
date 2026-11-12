import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from xml.sax.saxutils import escape
import io

r_f = 0.025

# --- Report color scheme (matches HF_ReportLab_4thstone.py) ------------------
PRIMARY_COLOR = '#350B4D'    # dark purple - titles, axis labels, Fourthstone
TEXT_MUTED = '#5A1F78'       # muted purple - benchmarks, secondary text
LINE_COLOR = '#E5A93B'       # gold - optimal portfolio curve, accents

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

def create_monthly_tear_sheet_text(returns, benchmark, port_name='Strategy', risk_free_rate=r_f):
    #Generates an advanced monthly metrics table
    
    # --- 1. Align Data & Validate Timezones ---
    df_combined = pd.concat([returns.rename(port_name), benchmark.rename('Benchmark')], axis=1).dropna()
    
    strat_rets = df_combined.iloc[:, 0] #df.iloc[:, 0] 
    #print("Strat rets variable", strat_rets)
    bench_rets = df_combined.iloc[:, 1]
    #print('bench rets, ', bench_rets)
    
    # --- 2. Baseline Horizon Calculations ---
    n_months = len(strat_rets)
    years = n_months / 12.0

    first_month = bench_rets.index[-1].date()
    last_month = bench_rets.index[0].date()
    
    # Cumulative & Annualized Returns (CAGR)
    cum_strat = (1 + strat_rets).prod() - 1
    cum_bench = (1 + bench_rets).prod() - 1
    cagr_strat = (1 + cum_strat) ** (1 / years) - 1
    cagr_bench = (1 + cum_bench) ** (1 / years) - 1
    
    # Annualized Volatility
    vol_strat = strat_rets.std() * np.sqrt(12)
    vol_bench = bench_rets.std() * np.sqrt(12)
    
    # Global Beta and Alpha (Annualized)
    covariance_matrix = np.cov(strat_rets, bench_rets)
    covariance = covariance_matrix[0, 1] if covariance_matrix.ndim > 1 else 0
    variance_bench = bench_rets.var()
    beta_global = covariance / variance_bench if variance_bench != 0 else np.nan
    alpha = cagr_strat - (risk_free_rate + beta_global * (cagr_bench - risk_free_rate))

    # --- 3. Advanced Monthly Risk & Performance Metrics ---
    excess_rets = strat_rets - (risk_free_rate / 12)
    
    # Sharpe & Sortino (Annualized)
    sharpe_strat = (excess_rets.mean() / strat_rets.std()) * np.sqrt(12) if strat_rets.std() != 0 else np.nan
    downside_rets = strat_rets[strat_rets < 0]
    sortino_strat = (excess_rets.mean() / downside_rets.std()) * np.sqrt(12) if len(downside_rets) > 0 else np.nan
    
    # Maximum Drawdown
    cum_wealth = (1 + strat_rets).cumprod()
    peaks = np.maximum.accumulate(cum_wealth)
    drawdowns = (cum_wealth - peaks) / peaks
    max_dd = drawdowns.min()
    
    # Calmar & Treynor
    calmar_strat = (cagr_strat / abs(max_dd)) if max_dd != 0 else np.nan
    annual_excess_return = cagr_strat - risk_free_rate
    treynor_strat = (annual_excess_return / beta_global) if (beta_global and beta_global != 0) else np.nan
    
    # Active Returns & Tracking Error
    active_rets = strat_rets - bench_rets
    tracking_error = active_rets.std() * np.sqrt(12)
    information_ratio = ((active_rets.mean() * 12) / tracking_error) if tracking_error != 0 else np.nan
    
    # Value at Risk (Monthly Historical VaR)
    var_90 = -np.percentile(strat_rets, 10)
    var_99 = -np.percentile(strat_rets, 1)

    #Up and Down Months
    up_months = 0
    down_months = 0
    for item in strat_rets:
        if item > 0:
            up_months += 1
        else:
            down_months += 1

    up_months_bench = 0
    down_months_bench = 0
    for item in bench_rets:
        if item > 0:
            up_months_bench += 1
        else:
            down_months_bench += 1
    

    # --- 4. Format and Output Metrics Table ---
    stats_data = {
        "Metric": [
            "Total Months","First Month End", "Last Month End","Up Months", "Down Months", "Cumulative Return", "Annualized Return (CAGR)", 
            "Annualized Volatility", "Sharpe Ratio", "Sortino Ratio", 
            "Max Drawdown", "Calmar Ratio", "Alpha (Annualized)", 
            "Beta vs Benchmark", "Treynor Ratio", "Tracking Error (Ann.)", 
            "Information Ratio", "Monthly VaR (90% Conf.)", "Monthly VaR (99% Conf.)"
        ],
        port_name: [
            f"{n_months}", f"{first_month}", f"{last_month}",f"{up_months}",f"{down_months}", f"{cum_strat:.2%}", f"{cagr_strat:.2%}", 
            f"{vol_strat:.2%}", f"{sharpe_strat:.2f}", f"{sortino_strat:.2f}", 
            f"{max_dd:.2%}", f"{calmar_strat:.2f}", f"{alpha:.2%}", 
            f"{beta_global:.2f}", f"{treynor_strat:.2f}", f"{tracking_error:.2%}", 
            f"{information_ratio:.2f}", f"{var_90:.2%}", f"{var_99:.2%}"
        ],
        "Benchmark": [
            f"{n_months}", f"{first_month}", f"{last_month}",f"{up_months_bench}",f"{down_months_bench}", f"{cum_bench:.2%}", f"{cagr_bench:.2%}", 
            f"{vol_bench:.2%}", "-", "-", "-", "-", "-", 
            "-", "-", "-", "-", "-", "-"
        ]
    }
    
    stats_df = pd.DataFrame(stats_data).set_index("Metric")

    return stats_df[port_name]

def create_monthly_tear_sheet_graphs(returns, benchmark, port_name='Strategy', risk_free_rate=r_f):
    
    #Generates an advanced monthly metrics table and a custom plotting grid.
    #Plot 1: Trailing 24 monthly returns vs benchmark.
    #Plot 2: Annual returns vs benchmark (bars) with a portfolio Beta line overlay (secondary axis).
    
    # --- 1. Align Data & Validate Timezones ---
    df_combined = pd.concat([returns.rename(port_name), benchmark.rename('Benchmark')], axis=1).dropna()
    
    strat_rets = df_combined[port_name]
    bench_rets = df_combined['Benchmark']
    
    # --- 2. Baseline Horizon Calculations ---
    n_months = len(strat_rets)
    years = n_months / 12.0
    
    # Cumulative & Annualized Returns (CAGR)
    cum_strat = (1 + strat_rets).prod() - 1
    cum_bench = (1 + bench_rets).prod() - 1
    cagr_strat = (1 + cum_strat) ** (1 / years) - 1
    cagr_bench = (1 + cum_bench) ** (1 / years) - 1
    
    # Annualized Volatility
    vol_strat = strat_rets.std() * np.sqrt(12)
    vol_bench = bench_rets.std() * np.sqrt(12)
    
    # Global Beta and Alpha (Annualized)
    covariance_matrix = np.cov(strat_rets, bench_rets)
    covariance = covariance_matrix[0, 1] if covariance_matrix.ndim > 1 else 0
    variance_bench = bench_rets.var()
    beta_global = covariance / variance_bench if variance_bench != 0 else np.nan
    alpha = cagr_strat - (risk_free_rate + beta_global * (cagr_bench - risk_free_rate))

    # --- 3. Advanced Monthly Risk & Performance Metrics ---
    excess_rets = strat_rets - (risk_free_rate / 12)
    
    # Sharpe & Sortino (Annualized)
    sharpe_strat = (excess_rets.mean() / strat_rets.std()) * np.sqrt(12) if strat_rets.std() != 0 else np.nan
    downside_rets = strat_rets[strat_rets < 0]
    sortino_strat = (excess_rets.mean() / downside_rets.std()) * np.sqrt(12) if len(downside_rets) > 0 else np.nan
    
    # Maximum Drawdown
    cum_wealth = (1 + strat_rets).cumprod()
    peaks = np.maximum.accumulate(cum_wealth)
    drawdowns = (cum_wealth - peaks) / peaks
    max_dd = drawdowns.min()
    
    # Calmar & Treynor
    calmar_strat = (cagr_strat / abs(max_dd)) if max_dd != 0 else np.nan
    annual_excess_return = cagr_strat - risk_free_rate
    treynor_strat = (annual_excess_return / beta_global) if (beta_global and beta_global != 0) else np.nan
    
    # Active Returns & Tracking Error
    active_rets = strat_rets - bench_rets
    tracking_error = active_rets.std() * np.sqrt(12)
    information_ratio = ((active_rets.mean() * 12) / tracking_error) if tracking_error != 0 else np.nan
    
    # Value at Risk (Monthly Historical VaR)
    var_90 = -np.percentile(strat_rets, 10)
    var_99 = -np.percentile(strat_rets, 1)

    # --- 5. Render each chart separately so ReportLab can preserve its aspect ratio ---
    recent_24 = df_combined.tail(24).copy()
    recent_24.index = recent_24.index.strftime('%Y-%m')
    monthly_fig, monthly_ax = plt.subplots(figsize=(12, 4.1))
    recent_24.plot(
        kind='bar',
        ax=monthly_ax,
        width=0.8,
        color=['#1f77b4', '#aec7e8']
    )
    monthly_ax.set_title(
        f"Trailing 24 Monthly Returns: {port_name} vs. Benchmark",
        fontsize=16,
        fontweight='bold',
        pad=12
    )
    monthly_ax.set_xlabel("")
    monthly_ax.set_ylabel("Monthly Return (%)", fontsize=12)
    monthly_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    monthly_ax.tick_params(axis='x', labelsize=10, rotation=45)
    monthly_ax.tick_params(axis='y', labelsize=10)
    for label in monthly_ax.get_xticklabels():
        label.set_horizontalalignment('right')
    monthly_ax.grid(axis='y', linestyle='--', alpha=0.5)
    monthly_ax.legend(loc='best', fontsize=11)
    monthly_fig.tight_layout(pad=1.4)

    # Step A: Group by calendar year to get annual compounded returns
    annual_df = df_combined.groupby(df_combined.index.year).apply(lambda x: (1 + x).prod() - 1)
    
    # Step B: Calculate the explicit portfolio beta inside each individual calendar year
    annual_betas = {}
    for year, group in df_combined.groupby(df_combined.index.year):
        if len(group) > 1 and group['Benchmark'].var() != 0:
            cov = np.cov(group[port_name], group['Benchmark'])[0, 1]
            var_b = group['Benchmark'].var()
            annual_betas[year] = cov / var_b
        else:
            annual_betas[year] = np.nan
    annual_df['Beta'] = pd.Series(annual_betas)
    
    # Step C: Plot the side-by-side annual returns on the main axis
    annual_fig, annual_ax = plt.subplots(figsize=(12, 4.1))
    annual_df[[port_name, 'Benchmark']].plot(
        kind='bar',
        ax=annual_ax,
        width=0.6,
        color=['#2ca02c', '#98df8a'],
        position=1
    )
    annual_ax.set_title(
        "Annual Returns vs. Benchmark with Overlaid Portfolio Beta",
        fontsize=16,
        fontweight='bold',
        pad=12
    )
    annual_ax.set_xlabel("")
    annual_ax.set_ylabel("Annual Return (%)", fontsize=12)
    annual_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    annual_ax.tick_params(axis='x', labelsize=10, rotation=0)
    annual_ax.tick_params(axis='y', labelsize=10)
    annual_ax.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Step D: Create a secondary Y-axis layout natively for the tracking line
    ax3_secondary = annual_ax.twinx()
    ax3_secondary.plot(
        np.arange(len(annual_df)),
        annual_df['Beta'],
        color='#d62728',
        marker='o',
        linewidth=2.5,
        label='Portfolio Beta'
    )
    ax3_secondary.set_ylabel("Portfolio Beta Value", color='#d62728', fontsize=12)
    ax3_secondary.tick_params(axis='y', labelcolor='#d62728', labelsize=10)
    
    # Step E: Clean up overlapping legends
    lines, labels = ax3_secondary.get_legend_handles_labels()
    bars, bar_labels = annual_ax.get_legend_handles_labels()
    annual_ax.legend(bars + lines, bar_labels + labels, loc='upper left', fontsize=11)
    annual_fig.tight_layout(pad=1.4)

    chart_streams = []
    for fig in (monthly_fig, annual_fig):
        img_stream = io.BytesIO()
        fig.savefig(img_stream, format='png', bbox_inches='tight', dpi=220)
        plt.close(fig)
        img_stream.seek(0)
        chart_streams.append(img_stream)

    return chart_streams

def create_monthly_attribution_graphs(attribution_df, gross_returns, short_returns, long_returns, bench_returns):
    #rolling 24/36-month alpha vs beta and vs net exposure
    #long and short book contribution via stacked bar chart compared to gross return and benchmark returns
    #underwater drawdown plot vs index 
    #up/down market scatterplot w/ fund returns on y axis and benchmark return on x axis
    #gross vs net exposure over time
    return

def up_down_performance(returns, benchmark, port_name = 'Strat'):
    #Ensure returns are in order and equal observation periods
    #clone df sorted by benchmark returns negative, again for positive
    #create tearsheet

    # --- 1. Align Data & Validate Timezones ---
    df_combined = pd.concat([returns.rename(port_name), benchmark.rename('Benchmark')], axis=1).dropna()

    # 1. Create the boolean condition where Column 2 is negative
    negative_col2_mask = df_combined['Benchmark'] < 0
    pos_col2_mask = df_combined['Benchmark'] >= 0

    # 2. Slice Column 1 based on that mask
    down_returns = df_combined.loc[negative_col2_mask, port_name]
    down_returns_bench = df_combined.loc[negative_col2_mask, 'Benchmark']
    up_returns = df_combined.loc[pos_col2_mask, port_name]
    up_returns_bench = df_combined.loc[pos_col2_mask, 'Benchmark']

    data_table_export = {
    "Metric": [
            "Total Months","First Month End", "Last Month End","Up Months", "Down Months", "Cumulative Return", "Annualized Return (CAGR)", 
            "Annualized Volatility", "Sharpe Ratio", "Sortino Ratio", 
            "Max Drawdown", "Calmar Ratio", "Alpha (Annualized)", 
            "Beta vs Benchmark", "Treynor Ratio", "Tracking Error (Ann.)", 
            "Information Ratio", "Monthly VaR (90% Conf.)", "Monthly VaR (99% Conf.)"]
    }

    data_df_export = pd.DataFrame(data_table_export).set_index("Metric")
    up_table = data_df_export
    down_table = data_df_export

    data = create_monthly_tear_sheet_text(down_returns, down_returns_bench, port_name)
    down_table = pd.concat([down_table, data], axis=1)
    data = create_monthly_tear_sheet_text(down_returns_bench, down_returns_bench, 'Benchmark')
    down_table = pd.concat([down_table, data], axis=1)
    
    data = create_monthly_tear_sheet_text(up_returns, up_returns_bench, port_name)
    up_table = pd.concat([up_table, data], axis=1)
    data = create_monthly_tear_sheet_text(up_returns_bench, up_returns_bench, "Benchmark")
    up_table = pd.concat([up_table, data], axis=1)


    return up_table[port_name], down_table[port_name]


#upload_path = "C:/GithubLocalDirectory/Fourthstone_Cleaned_Data.xlsx"
upload_path = "C:/GithubLocalDirectory/Hedge_Fund_Report/Fourthstone_Cleaned_Data.xlsx"
#Tabs = 'LS_attribution' w/ cols 'Month', 'Long %', 'Short %', 'Gross %', 'Net %', 'Date'
#Tab = 'Mthly_returns' w/ cols Month, Long Return %,	Short Return %,	Gross Monthly Composite Return %,	Net Monthly Composite Return %,	NASDAQ Bank Index Monthly Return %,
# ,	Date,	SPX INDEX,	LBUSTRUU INDEX,	RTY INDEX,	BTSISOFR INDEX,	SOFR + 500bps,	KRX INDEX,	BKX INDEX

all_sheets_raw = pd.read_excel(upload_path, sheet_name=None)
all_sheets = {key: df.dropna(how='any') for key, df in all_sheets_raw.items()}
df_attribution = all_sheets['LS_attribution']
df_returns = all_sheets['Mthly_returns']

# 1. Convert to datetime, localize to ET ('America/New_York'), and set as index
df_attribution = df_attribution.set_index(pd.to_datetime(df_attribution['Date']).dt.tz_localize('America/New_York'))
df_returns = df_returns.set_index(pd.to_datetime(df_returns['Date']).dt.tz_localize('America/New_York'))

df_attribution = df_attribution.drop(columns=['Month'])
df_returns = df_returns.drop(columns=['Month'])

for col in df_attribution:
    if col != 'Date':
        df_attribution[col] = clean_numeric_column(df_attribution, col)

for col in df_returns:
    if col != 'Date':
        df_returns[col] = clean_numeric_column(df_returns, col)

Fourthstone_net_return = df_returns['Net Monthly Composite Return %']
Fourthstone_gross_return = df_returns['Gross Monthly Composite Return %']
Fourthstone_long_return = df_returns['Long Return %']
Fourthstone_short_return = df_returns['Short Return %']

long_exposure = df_attribution['Long %']
short_exposure = df_attribution['Short %']
gross_exposure = df_attribution['Gross %']
net_exposure = df_attribution['Net %']

benchmark_SPY = df_returns['SPX INDEX']
benchmark_bankIndex = df_returns['NASDAQ Bank Index Monthly Return %']
benchmark_AGG = df_returns['LBUSTRUU INDEX']
benchmark_SOFR = df_returns['BTSISOFR INDEX']
benchmark_SOFR500 = df_returns['SOFR + 500bps']
benchmark_KRX = df_returns['KRX INDEX']
benchmark_BKX = df_returns['BKX INDEX']


def _generate_10pct_weight_combinations(n_assets):
    """Generate all portfolio weight vectors in 10% increments summing to 1.0."""
    from itertools import combinations_with_replacement

    portfolios = []
    for combo in combinations_with_replacement(range(n_assets), 10):
        weights = np.zeros(n_assets)
        for idx in combo:
            weights[idx] += 0.1  # each pick is one 10% slice
        portfolios.append(weights)
    return portfolios


def _compute_portfolio_metrics(weights, returns_matrix, n_months):
    """Return (annualized_return, annualized_vol, max_drawdown) for a portfolio."""
    port_rets = returns_matrix @ weights
    cum = (1 + port_rets).prod() - 1
    ann_ret = (1 + cum) ** (12 / n_months) - 1 if n_months > 0 else np.nan
    ann_vol = port_rets.std() * np.sqrt(12)
    cum_wealth = (1 + port_rets).cumprod()
    peaks = np.maximum.accumulate(cum_wealth)
    dd = (cum_wealth - peaks) / peaks
    max_dd = dd.min()
    return ann_ret, ann_vol, max_dd


def _efficient_frontier(x_vals, y_vals):
    """Return the upper envelope (max y for each x) sorted ascending by x."""
    x_vals = np.asarray(x_vals, dtype=float)
    y_vals = np.asarray(y_vals, dtype=float)
    order = np.argsort(x_vals)
    x_sorted = x_vals[order]
    y_sorted = y_vals[order]
    running_max = np.maximum.accumulate(y_sorted)
    return x_sorted, running_max


def create_risk_return_scatter_image(risk_free_rate=r_f, width=450, height=300):
    """
    Generates a risk/return scatter plot (annualized return vs. annualized volatility)
    for Fourthstone net return and key benchmarks. Each series is plotted as a single
    point, with Fourthstone Net Return highlighted in red. An optimal portfolio
    curve (efficient frontier from 10% weight-increment portfolios) shows the
    maximum return possible for each level of volatility.

    Returns a reportlab.platypus.Image flowable ready to append to the report story.
    """
    series_dict = {
        'Fourthstone_net_return': Fourthstone_net_return,
        'benchmark_SPY': benchmark_SPY,
        'benchmark_bankIndex': benchmark_bankIndex,
        'benchmark_AGG': benchmark_AGG,
        'benchmark_SOFR': benchmark_SOFR,
        'benchmark_KRX': benchmark_KRX,
        'benchmark_BKX': benchmark_BKX,
    }

    # --- Align all series to a common calendar index -----------------------
    aligned = pd.concat(
        [s.rename(name) for name, s in series_dict.items() if s is not None],
        axis=1,
    ).dropna()

    names = aligned.columns.tolist()
    returns_matrix = aligned.values  # (n_months, n_assets)
    n_months = len(aligned)

    def ann_metrics(rets):
        """Return (annualized_return, annualized_vol, max_drawdown)."""
        cum = (1 + rets).prod() - 1
        ann_ret = (1 + cum) ** (12 / n_months) - 1 if n_months > 0 else np.nan
        ann_vol = rets.std() * np.sqrt(12)
        cum_wealth = (1 + rets).cumprod()
        peaks = np.maximum.accumulate(cum_wealth)
        dd = (cum_wealth - peaks) / peaks
        max_dd = dd.min()
        return ann_ret, ann_vol, max_dd

    # --- Individual asset points ------------------------------------------
    x_ind, y_ind, labels_ind, colors_ind, sizes_ind = [], [], [], [], []

    for name in names:
        rets = aligned[name]
        ar, av, md = ann_metrics(rets)
        if np.isnan([ar, av, md]).any():
            continue
        x_ind.append(av)
        y_ind.append(ar)
        labels_ind.append(name)
        if name == 'Fourthstone_net_return':
            colors_ind.append('#d62728')   # red - special indicator
            sizes_ind.append(80)            # smaller marker
        else:
            colors_ind.append('#333333')   # dark gray - benchmarks
            sizes_ind.append(40)            # smaller marker

    # --- Optimal portfolio curve (10% weight increments) -------------------
    weight_combos = _generate_10pct_weight_combinations(len(names))
    x_port, y_port = [], []
    for w in weight_combos:
        ar, av, md = _compute_portfolio_metrics(w, returns_matrix, n_months)
        if np.isnan([ar, av, md]).any():
            continue
        x_port.append(av)
        y_port.append(ar)

    # --- Build the 2D figure ----------------------------------------------
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=150)

    # Plot efficient frontier curve
    if len(x_port) > 1:
        x_frontier, y_frontier = _efficient_frontier(x_port, y_port)
        ax.plot(x_frontier, y_frontier, color='#000000', linewidth=1.5,
                alpha=0.9, label='Optimal Portfolio Curve', zorder=2)

    # Individual assets as scatter points
    ax.scatter(x_ind, y_ind, s=sizes_ind, c=colors_ind, alpha=0.9,
               edgecolors='black', linewidth=0.5, zorder=3)

    # Annotate each point
    for i, label in enumerate(labels_ind):
        if label == 'Fourthstone_net_return':
            display_label = 'Fourthstone Net'
            ax.annotate(display_label, (x_ind[i], y_ind[i]),
                       xytext=(6, 6), textcoords='offset points',
                       fontsize=7, fontweight='bold', color='#000000',
                       zorder=4)
        else:
            short = label.replace('benchmark_', '')
            ax.annotate(short, (x_ind[i], y_ind[i]),
                       xytext=(6, 6), textcoords='offset points',
                       fontsize=6, color='#000000', zorder=4)

    ax.set_xlabel('Annualized Volatility', fontsize=8, fontweight='bold',
                  color='#000000')
    ax.set_ylabel('Annualized Return', fontsize=8, fontweight='bold',
                  color='#000000')
    ax.set_title('Annualized Return vs. Volatility', fontsize=10,
                 fontweight='bold', pad=8, color='#000000')
    ax.grid(True, linestyle='--', alpha=0.4, color='#000000', zorder=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1%}'))

    # Style spines and ticks to plain black
    for spine in ax.spines.values():
        spine.set_color('#000000')
        spine.set_linewidth(0.8)
    ax.tick_params(colors='#000000', labelsize=7)
    ax.set_facecolor('white')

    # No individual legend - shared legend is created separately

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150,
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)

    img = Image(buf, width=width, height=height)
    return img


def create_drawdown_return_scatter_image(width=450, height=300):
    """
    Generates a 2D scatter plot (annualized return vs. maximum drawdown)
    for Fourthstone net return and key benchmarks. The x-axis shows maximum
    drawdown magnitude (absolute value). Each series is plotted as a single
    point, with Fourthstone Net Return highlighted in red. An optimal
    portfolio curve shows the maximum return possible for each level of
    drawdown risk.

    Returns a reportlab.platypus.Image flowable ready to append to the report story.
    """

    series_dict = {
        'Fourthstone_net_return': Fourthstone_net_return,
        'benchmark_SPY': benchmark_SPY,
        'benchmark_bankIndex': benchmark_bankIndex,
        'benchmark_AGG': benchmark_AGG,
        'benchmark_SOFR': benchmark_SOFR,
        'benchmark_KRX': benchmark_KRX,
        'benchmark_BKX': benchmark_BKX,
    }

    # --- Align all series to a common calendar index -----------------------
    aligned = pd.concat(
        [s.rename(name) for name, s in series_dict.items() if s is not None],
        axis=1,
    ).dropna()

    names = aligned.columns.tolist()
    returns_matrix = aligned.values  # (n_months, n_assets)
    n_months = len(aligned)

    def ann_metrics(rets):
        """Return (annualized_return, max_drawdown)."""
        cum = (1 + rets).prod() - 1
        ann_ret = (1 + cum) ** (12 / n_months) - 1 if n_months > 0 else np.nan
        cum_wealth = (1 + rets).cumprod()
        peaks = np.maximum.accumulate(cum_wealth)
        dd = (cum_wealth - peaks) / peaks
        max_dd = dd.min()  # negative value
        return ann_ret, max_dd

    # --- Individual asset points ------------------------------------------
    x_ind, y_ind, labels_ind, colors_ind, sizes_ind = [], [], [], [], []

    for name in names:
        rets = aligned[name]
        ar, md = ann_metrics(rets)
        if np.isnan([ar, md]).any():
            continue
        x_ind.append(abs(md))  # drawdown magnitude on x-axis
        y_ind.append(ar)
        labels_ind.append(name)
        if name == 'Fourthstone_net_return':
            colors_ind.append('#d62728')   # red - special indicator
            sizes_ind.append(80)            # smaller marker
        else:
            colors_ind.append('#333333')   # dark gray - benchmarks
            sizes_ind.append(40)            # smaller marker

    # --- Optimal portfolio curve (10% weight increments) -------------------
    weight_combos = _generate_10pct_weight_combinations(len(names))
    x_port, y_port = [], []
    for w in weight_combos:
        ar, av, md = _compute_portfolio_metrics(w, returns_matrix, n_months)
        if np.isnan([ar, av, md]).any():
            continue
        x_port.append(abs(md))  # drawdown magnitude
        y_port.append(ar)

    # --- Build the 2D figure ----------------------------------------------
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=150)

    # Plot efficient frontier curve
    if len(x_port) > 1:
        x_frontier, y_frontier = _efficient_frontier(x_port, y_port)
        ax.plot(x_frontier, y_frontier, color='#000000', linewidth=1.5,
                alpha=0.9, label='Optimal Portfolio Curve', zorder=2)

    # Individual assets as scatter points
    ax.scatter(x_ind, y_ind, s=sizes_ind, c=colors_ind, alpha=0.9,
               edgecolors='black', linewidth=0.5, zorder=3)

    # Annotate each point
    for i, label in enumerate(labels_ind):
        if label == 'Fourthstone_net_return':
            display_label = 'Fourthstone Net'
            ax.annotate(display_label, (x_ind[i], y_ind[i]),
                       xytext=(6, 6), textcoords='offset points',
                       fontsize=7, fontweight='bold', color='#000000',
                       zorder=4)
        else:
            short = label.replace('benchmark_', '')
            ax.annotate(short, (x_ind[i], y_ind[i]),
                       xytext=(6, 6), textcoords='offset points',
                       fontsize=6, color='#000000', zorder=4)

    ax.set_xlabel('Maximum Drawdown', fontsize=8, fontweight='bold',
                  color='#000000')
    ax.set_ylabel('Annualized Return', fontsize=8, fontweight='bold',
                  color='#000000')
    ax.set_title('Annualized Return vs. Max Drawdown', fontsize=10,
                 fontweight='bold', pad=8, color='#000000')
    ax.grid(True, linestyle='--', alpha=0.4, color='#000000', zorder=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1%}'))

    # Style spines and ticks to plain black
    for spine in ax.spines.values():
        spine.set_color('#000000')
        spine.set_linewidth(0.8)
    ax.tick_params(colors='#000000', labelsize=7)
    ax.set_facecolor('white')

    # No individual legend - shared legend is created separately

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150,
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)

    img = Image(buf, width=width, height=height)
    return img


def create_shared_legend_image(width=450, height=60):
    """
    Creates a standalone shared legend image for both scatter plots.

    Shows: Fourthstone Net Return, Benchmarks, Optimal Portfolio Curve
    Uses the report's color scheme (PRIMARY_COLOR, TEXT_MUTED, LINE_COLOR).

    Returns a reportlab.platypus.Image flowable.
    """
    from matplotlib.lines import Line2D
    import matplotlib

    # Use a non-interactive backend
    matplotlib.use('Agg')

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=150)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Fourthstone Net Return',
               markerfacecolor='#d62728', markersize=8, markeredgecolor='black'),
        Line2D([0], [0], marker='o', color='w', label='Benchmarks',
               markerfacecolor='#333333', markersize=6, markeredgecolor='black'),
        Line2D([0], [0], color='#000000', lw=1.5, label='Optimal Portfolio Curve',
               alpha=0.9),
    ]

    ax.legend(handles=legend_elements, loc='center', ncol=3, fontsize=7,
              frameon=False, handletextpad=0.5, columnspacing=1.5,
              labelcolor='#000000')

    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150,
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)

    img = Image(buf, width=width, height=height)
    return img


def period_returns(start_date, end_date):
    #Cumulative and annualized return between two dates (inclusive) for each Fourthstone_ and benchmark_ series
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.tzinfo is None:
        start = start.tz_localize('America/New_York')
    if end.tzinfo is None:
        end = end.tz_localize('America/New_York')

    series_dict = {
        'Fourthstone_net_return': Fourthstone_net_return,
        'Fourthstone_gross_return': Fourthstone_gross_return,
        'Fourthstone_long_return': Fourthstone_long_return,
        'Fourthstone_short_return': Fourthstone_short_return,
        'benchmark_SPY': benchmark_SPY,
        'benchmark_bankIndex': benchmark_bankIndex,
        'benchmark_AGG': benchmark_AGG,
        'benchmark_SOFR': benchmark_SOFR,
        'benchmark_SOFR500': benchmark_SOFR500,
        'benchmark_KRX': benchmark_KRX,
        'benchmark_BKX': benchmark_BKX,
    }

    results = {}
    for name, series in series_dict.items():
        window = series.sort_index().loc[start:end].dropna()
        n_months = len(window)
        if n_months == 0:
            results[name] = [0, np.nan, np.nan]
            continue
        cum = (1 + window).prod() - 1
        cagr = (1 + cum) ** (12 / n_months) - 1
        results[name] = [n_months, cum, cagr]

    results_df = pd.DataFrame.from_dict(
        results, orient='index',
        columns=['Months', 'Cumulative Return', 'Annualized Return'])
    print(f"Period returns {start.date()} to {end.date()}")
    print(results_df.to_string(formatters={
        'Cumulative Return': '{:.2%}'.format,
        'Annualized Return': '{:.2%}'.format}))
    return results_df

benchmark_list = [benchmark_SPY, benchmark_AGG, benchmark_SOFR, benchmark_bankIndex, benchmark_SOFR500, benchmark_KRX, benchmark_BKX]
Port_Name_list = ['S&P 500', 'Global AGG', 'SOFR', 'SOFR + 500', 'Nasdaq Bank Index','Regional Banks', 'National Banks']

data_table_export = {
    "Metric": [
            "Total Months","First Month End", "Last Month End","Up Months", "Down Months", "Cumulative Return", "Annualized Return (CAGR)", 
            "Annualized Volatility", "Sharpe Ratio", "Sortino Ratio", 
            "Max Drawdown", "Calmar Ratio", "Alpha (Annualized)", 
            "Beta vs Benchmark", "Treynor Ratio", "Tracking Error (Ann.)", 
            "Information Ratio", "Monthly VaR (90% Conf.)", "Monthly VaR (99% Conf.)"]

}
data_df_export = pd.DataFrame(data_table_export).set_index("Metric")
up_data_export = pd.DataFrame(data_table_export).set_index("Metric")
down_data_export = pd.DataFrame(data_table_export).set_index("Metric")

data = create_monthly_tear_sheet_text(Fourthstone_net_return, benchmark_bankIndex, 'NET')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(Fourthstone_gross_return, benchmark_bankIndex, 'GROSS')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(Fourthstone_long_return, benchmark_bankIndex, 'LONG BOOK')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(Fourthstone_short_return, benchmark_bankIndex, 'SHORT BOOK')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(benchmark_KRX, benchmark_bankIndex, 'Reg Bank Idx')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(benchmark_BKX, benchmark_bankIndex, 'Bank Idx')
data_df_export = pd.concat([data_df_export, data], axis=1)

data = create_monthly_tear_sheet_text(benchmark_bankIndex, benchmark_bankIndex, 'Ndq Bank Index')
data_df_export = pd.concat([data_df_export, data], axis=1)

up_data, down_data = up_down_performance(Fourthstone_net_return, benchmark_bankIndex, 'NET')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(Fourthstone_gross_return, benchmark_bankIndex, 'GROSS')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(Fourthstone_long_return, benchmark_bankIndex, 'LONG BOOK')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(Fourthstone_short_return, benchmark_bankIndex, 'SHORT BOOK')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(benchmark_KRX, benchmark_bankIndex, 'Reg Bank Index')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(benchmark_BKX, benchmark_bankIndex, 'Bank Idx')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

up_data, down_data = up_down_performance(benchmark_bankIndex, benchmark_bankIndex, 'Ndq Bank Index')
up_data_export = pd.concat([up_data_export, up_data], axis=1)
down_data_export = pd.concat([down_data_export, down_data], axis=1)

def get_tearsheet_data():
    export_df = data_df_export.reset_index()
    list_of_lists = [export_df.columns.tolist()] + export_df.to_numpy().tolist()
    return list_of_lists

def get_att_data():
    list_of_lists = [df_attribution.columns.tolist()] + df_attribution.to_numpy().tolist()
    return list_of_lists

def get_updown_data():
    up_export_df = up_data_export.reset_index()
    down_export_df = down_data_export.reset_index()
    list_of_lists_up = [up_export_df.columns.tolist()] + up_export_df.to_numpy().tolist()
    list_of_lists_down = [down_export_df.columns.tolist()] + down_export_df.to_numpy().tolist()
    return list_of_lists_up, list_of_lists_down

#period_returns('2018-06-1', '2020-3-31')
#period_returns('2018-06-1', '2021-2-28')
#period_returns('2022-01-1', '2023-5-31')
period_returns('2019-1-1', '2019-12-31')