/**
 * Column header tooltip definitions for all Data subtabs.
 *
 * Each key is a unique tooltip identifier used in  data-tooltip="key"  on <th> elements.
 * The rendering logic at the bottom turns these into hover popups using the
 * existing .tooltip-wrap / .tooltip-box CSS already in dashboard.html.
 */
const TOOLTIPS = {

    /* ─── LEVERAGE TAB ──────────────────────────────────────────────── */

    sp500_10k: {
        title: "Buy & Hold Growth",
        formula: "$10k × cumprod(1 + daily_return)",
        terms: [
            "<b>daily_return</b> — S&P 500 daily price change",
            "Cumulative product from the first trading day"
        ]
    },
    sma_200: {
        title: "200-Day Moving Average (rescaled)",
        formula: "Buy_Hold × (SMA₂₀₀ / Close)",
        terms: [
            "<b>SMA₂₀₀</b> — 200-day simple moving average of S&P 500 Close",
            "Rescaled into $10k portfolio space for visual comparison",
            "Portfolio above this line → <b>Risk On</b> (Regime=1)"
        ]
    },
    "3x_bh": {
        title: "Daily Return Formula",
        formula: "3 × daily_total_return − financing − expense",
        terms: [
            "<b>financing</b> — (SOFR + 0.5%) / 252 on 2× borrowed notional",
            "<b>expense</b> — 1% annual ETF fee / 252",
            "<b>daily_total_return</b> — price return + dividend yield"
        ]
    },
    "3x_strategy": {
        title: "3x Leveraged with SMA Filter",
        formulas: [
            "Regime=1: 3×return − financing − expense",
            "Regime=0: 0% (cash)"
        ],
        terms: [
            "<b>Regime=1</b> (Close > SMA₂₀₀) → same as 3x Buy & Hold",
            "<b>Regime=0</b> (Close ≤ SMA₂₀₀) → move to cash, no return",
            "Regime shifted 1 day to avoid look-ahead bias"
        ]
    },

    /* ─── INFLATION TAB ─────────────────────────────────────────────── */

    inf_year: {
        title: "Calendar Year",
        terms: [
            "CPI data sourced from FRED (series CPIAUCNS)",
            "Annual data: last CPI reading of each year"
        ]
    },
    inflation_pct: {
        title: "Year-over-Year CPI Change",
        formula: "(CPI_end / CPI_start − 1) × 100",
        terms: [
            "Percentage change in Consumer Price Index vs previous year",
            "Values > 5% highlighted in red"
        ]
    },
    cumulative_factor: {
        title: "Total Price Level Increase",
        formula: "CPI_current / CPI_base",
        terms: [
            "How many times prices have multiplied since the first year in the dataset",
            "Example: 15.0x means prices are 15× higher"
        ]
    },
    purchasing_power: {
        title: "Real Value of $10,000",
        formula: "$10,000 / Cumulative_Factor",
        terms: [
            "What $10k from the base year buys today in real terms",
            "Decreases as inflation erodes purchasing power"
        ]
    },

    /* ─── DIVIDEND TAB ──────────────────────────────────────────────── */

    div_sp500: {
        title: "S&P 500 Price Level",
        terms: [
            "Nominal S&P 500 index price from Robert Shiller's historical dataset",
            "Monthly data point"
        ]
    },
    div_dividend: {
        title: "Annual Dividend per Share",
        terms: [
            "Annualized S&P 500 dividend from Shiller dataset",
            "Trailing 12-month dividends summed across index components"
        ]
    },
    div_yield: {
        title: "S&P 500 Dividend Yield",
        formula: "(Dividend / Price) × 100",
        terms: [
            "Annual dividend as a percentage of the current price"
        ]
    },
    pe_ratio: {
        title: "Shiller CAPE / PE10",
        terms: [
            "Cyclically Adjusted Price-to-Earnings ratio",
            "Price divided by 10-year average real earnings",
            "Smooths out business cycle fluctuations"
        ]
    },

    /* ─── LDA TAB ───────────────────────────────────────────────────── */

    lda_year: {
        title: "Calendar Year",
        terms: [
            "Annual data combining daily strategy returns with Shiller dividend data"
        ]
    },
    total_sp500: {
        title: "Total Return (Price + Dividends)",
        formula: "prev × (1 + price_change + div_yield)",
        terms: [
            "Buy & Hold growth with annual dividends reinvested",
            "Starting from $10k"
        ]
    },
    total_3x: {
        title: "3x MA Strategy + Dividends",
        formula: "prev × (1 + lev_change + div_yield)",
        terms: [
            "3x leveraged ETF earns ~1× dividend (not 3×)",
            "Swap-based leverage doesn't pay dividends on borrowed portion",
            "Financing cost + expense ratio already embedded in lev_change"
        ]
    },
    lda_div_yield: {
        title: "Average Annual Dividend Yield",
        formula: "mean(Dividend / SP500) per year",
        terms: [
            "Average of monthly dividend yields from Shiller data"
        ]
    },
    price_sp500: {
        title: "Price-Only Growth (no dividends)",
        terms: [
            "Same as Buy_Hold_Growth from Leverage tab",
            "Shows how much return comes from price vs dividends"
        ]
    },
    price_3x: {
        title: "3x Price-Only Growth (no dividends)",
        terms: [
            "Same as Lev_3x_Growth from Leverage tab",
            "3x MA strategy return without dividend reinvestment"
        ]
    },

    /* ─── SMALL CAP TAB ─────────────────────────────────────────────── */

    sc_monthly_yield: {
        title: "Small Cap Value Monthly Return",
        terms: [
            "Monthly return of the Small HiBM (High Book-to-Market) portfolio",
            "From Fama-French 6 Portfolios (2×3)"
        ]
    },
    sc_index: {
        title: "Cumulative Growth Index",
        formula: "cumprod(1 + monthly_return) × 100",
        terms: [
            "Base = 100 at start of dataset (1926)",
            "Shows cumulative compounded growth over time"
        ]
    },

    /* ─── LSC TAB ───────────────────────────────────────────────────── */

    lsc_regime: {
        title: "SMA 200 Market Regime",
        terms: [
            "<b>Risk On</b> (Close > SMA₂₀₀) → hold 3× leveraged S&P 500",
            "<b>Risk Off</b> (Close ≤ SMA₂₀₀) → hold Small Cap Value"
        ]
    },
    lsc_cash: {
        title: "Baseline 3x Strategy (Cash in Risk Off)",
        terms: [
            "<b>Risk On</b> → 3× leveraged S&P 500 return",
            "<b>Risk Off</b> → 0% return (cash)",
            "Same as 3x Strategy from Leverage tab"
        ]
    },
    lsc_sc: {
        title: "3x Strategy with Small Cap in Risk Off",
        formula: "$10k × cumprod(1 + daily)",
        terms: [
            "<b>Risk On</b> → 3× leveraged S&P 500 return",
            "<b>Risk Off</b> → Small Cap Value daily return",
            "Replaces idle cash with productive small-cap allocation"
        ]
    },
    sc_daily_yield: {
        title: "Estimated Daily Small Cap Return",
        formula: "(1 + monthly_ret)^(1/days) − 1",
        terms: [
            "Monthly Fama-French return converted to daily",
            "Spread evenly across trading days in each month"
        ]
    },

    /* ─── LSCDA TAB ─────────────────────────────────────────────────── */

    lscda_regime: {
        title: "SMA 200 Market Regime",
        terms: [
            "<b>Risk On</b> (Close > SMA₂₀₀) → 3× leveraged ETF + dividends",
            "<b>Risk Off</b> (Close ≤ SMA₂₀₀) → Small Cap + dividends"
        ]
    },
    lscda_sc_div: {
        title: "3x Strategy + Small Cap + Dividends",
        formula: "$10k × cumprod(1 + daily)",
        terms: [
            "<b>Risk On</b> → 3× leveraged + daily dividend",
            "<b>Risk Off</b> → Small Cap Value + daily dividend"
        ]
    },
    lscda_cash_div: {
        title: "3x Strategy + Cash + Dividends",
        formula: "$10k × cumprod(1 + daily)",
        terms: [
            "<b>Risk On</b> → 3× leveraged + daily dividend",
            "<b>Risk Off</b> → cash (0%) + daily dividend"
        ]
    },
    daily_div_yield: {
        title: "Estimated Daily Dividend",
        formula: "annual_yield / 100 / 252",
        terms: [
            "Annual dividend yield from Shiller data divided by trading days"
        ]
    },

    /* ─── INTEREST RATE TAB ─────────────────────────────────────────── */

    ir_10y: {
        title: "10-Year Treasury Yield",
        terms: [
            "Long-term interest rate from Shiller's dataset",
            "Based on US 10-Year Treasury bond yield"
        ]
    },
    ir_margin_rate: {
        title: "Estimated Broker Margin Rate",
        formula: "10Y_yield + 1.5%",
        terms: [
            "Low-cost broker margin rate estimate",
            "Spread of 1.5% above the 10-Year Treasury"
        ]
    },

    /* ─── MARGIN TAB ────────────────────────────────────────────────── */

    margin_cash: {
        title: "Uninvested Cash Balance",
        terms: [
            "Proceeds from selling minus accrued interest deductions",
            "Interest deducted annually from cash balance"
        ]
    },
    margin_invested: {
        title: "Current Market Value of Position",
        formula: "invested × (1 + 3× daily_return)",
        terms: [
            "3× leveraged daily returns applied to invested amount",
            "Only non-zero when Regime=1 (invested)"
        ]
    },
    margin_debt: {
        title: "Outstanding Margin Loan",
        terms: [
            "Initial: $2,000 (adjusted annually for inflation via CPI)",
            "Borrowed when entering market (Regime=1)",
            "Repaid from proceeds when exiting (Regime=0)"
        ]
    },
    margin_equity: {
        title: "Net Liquidation Value",
        formula: "Cash + Invested − Debt",
        terms: [
            "Starting capital = $0 (fully margin-funded)",
            "Represents your true net worth in this strategy"
        ]
    },
    margin_signals: {
        title: "Market Regime Signal",
        terms: [
            "<b>Invested</b> (Regime=1) → enter market with margin loan",
            "<b>Cash</b> (Regime=0) → sell position, repay debt",
            "Based on SMA 200 filter (same as Leverage tab)"
        ]
    },
    margin_rate: {
        title: "10-Year Treasury Yield",
        formula: "daily_interest = (10Y + 1.5%) / 365 × debt",
        terms: [
            "Used to calculate margin interest cost",
            "Interest accrues daily, deducted from cash annually"
        ]
    }
};


/* ─── RENDERING ─────────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-tooltip]").forEach(el => {
        const key = el.getAttribute("data-tooltip");
        const tip = TOOLTIPS[key];
        if (!tip) return;

        // Mark the element as a tooltip trigger (for CSS hover styles)
        el.classList.add("tooltip-wrap");

        // Build the popup
        const box = document.createElement("span");
        box.className = "tooltip-box";

        let html = `<div class="tt-title">${tip.title}</div>`;

        // Support single formula or multiple formulas
        if (tip.formula) {
            html += `<code>${tip.formula}</code>`;
        }
        if (tip.formulas) {
            tip.formulas.forEach(f => { html += `<code>${f}</code>`; });
        }

        if (tip.terms) {
            tip.terms.forEach(t => {
                html += `<div class="tt-term">${t}</div>`;
            });
        }

        box.innerHTML = html;
        el.appendChild(box);
    });
});
