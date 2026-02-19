"""
Debug script: Verify 3x Buy & Hold ($10k) column from Leverage tab.

Formula (analyzer.py lines 173-179):
    Strategy_3x_BH_Daily = 3 * Total_Return_Daily - Financing_Rate_Daily - ETF_EXPENSE_RATIO_DAILY
    Lev_3x_BH_Growth = 10000 * cumprod(1 + Strategy_3x_BH_Daily)

Where:
    Total_Return_Daily = Simple_Ref (pct_change of Close) + 0 (no dividend)
    Financing_Rate_Daily = 2 * (Fed_Funds_Rate / 100) / 252
    ETF_EXPENSE_RATIO_DAILY = 0.01 / 252  (1% annual)
"""
import database
import analyzer
import pandas as pd
import numpy as np

database.init_db()
data = analyzer.get_strategy_data()

lines = []
lines.append("=" * 90)
lines.append("VERIFICATION: 3x Buy & Hold ($10k) Column")
lines.append("=" * 90)
lines.append("")

# Show the formula
lines.append("FORMULA:")
lines.append("  3x_BH_daily = 3 * price_return - 2*(FedFunds/100/252) - (0.01/252)")
lines.append("  3x_BH_growth = 10000 * cumprod(1 + 3x_BH_daily)")
lines.append("")

ETF_EXPENSE_DAILY = 0.01 / 252

# ---- Step-by-step for last 12 rows ----
lines.append("=== Last 12 rows: Step-by-step breakdown ===")
hdr = "{:<12} {:>10} {:>10} {:>10} {:>10} {:>10} {:>14}".format(
    "Date", "Close", "PriceRet", "FedFunds%", "FinCost", "3xBH_Ret", "3xBH_Growth")
lines.append(hdr)
lines.append("-" * 90)

df = data.tail(12)
for idx, row in df.iterrows():
    dt = idx.strftime('%Y-%m-%d')
    close = row['Close']
    price_ret = row['Simple_Ref']
    ff_rate = row['Fed_Funds_Rate']
    fin_cost = row['Financing_Rate_Daily']
    strat_daily = row['Strategy_3x_BH_Daily']
    growth = row['Lev_3x_BH_Growth']
    
    # Manual recalculation
    manual_daily = 3 * price_ret - fin_cost - ETF_EXPENSE_DAILY
    manual_daily_clipped = max(manual_daily, -1.0)
    
    lines.append("{:<12} {:>10.2f} {:>10.6f} {:>10.2f} {:>10.8f} {:>10.6f} {:>14,.2f}".format(
        dt, close, price_ret, ff_rate, fin_cost, strat_daily, growth))

lines.append("")

# ---- Detailed verification for specific date ----
lines.append("=== Detailed: 2026-02-17 ===")
mask = data.index.strftime('%Y-%m-%d') == '2026-02-17'
if mask.any():
    row = data.loc[mask].iloc[0]
    prev_mask = data.index.strftime('%Y-%m-%d') == '2026-02-13'
    prev_row = data.loc[prev_mask].iloc[0] if prev_mask.any() else None
    
    close = row['Close']
    price_ret = row['Simple_Ref']
    ff = row['Fed_Funds_Rate']
    fin = row['Financing_Rate_Daily']
    strat = row['Strategy_3x_BH_Daily']
    growth = row['Lev_3x_BH_Growth']
    
    lines.append("  Close today     = {:.2f}".format(close))
    if prev_row is not None:
        lines.append("  Close prev      = {:.2f}".format(prev_row['Close']))
        manual_ret = (close - prev_row['Close']) / prev_row['Close']
        lines.append("  Price Return    = ({:.2f} - {:.2f}) / {:.2f} = {:.6f}".format(
            close, prev_row['Close'], prev_row['Close'], manual_ret))
    lines.append("  Simple_Ref      = {:.6f}".format(price_ret))
    lines.append("  Fed Funds Rate  = {:.2f}%".format(ff))
    lines.append("  Financing Cost  = 2 * ({:.2f}/100/252) = {:.8f}".format(ff, fin))
    lines.append("  ETF Expense     = 0.01/252 = {:.8f}".format(ETF_EXPENSE_DAILY))
    lines.append("")
    manual_3x = 3 * price_ret - fin - ETF_EXPENSE_DAILY
    lines.append("  3x BH Daily     = 3 * {:.6f} - {:.8f} - {:.8f} = {:.6f}".format(
        price_ret, fin, ETF_EXPENSE_DAILY, manual_3x))
    lines.append("  Stored value    = {:.6f}".format(strat))
    lines.append("  Match?          = {}".format(abs(manual_3x - strat) < 1e-10))
    lines.append("")
    lines.append("  3x BH Growth    = {:,.2f}".format(growth))
    if prev_row is not None:
        prev_growth = prev_row['Lev_3x_BH_Growth']
        expected_growth = prev_growth * (1 + strat)
        lines.append("  Prev Growth     = {:,.2f}".format(prev_growth))
        lines.append("  Expected Growth = {:,.2f} * (1 + {:.6f}) = {:,.2f}".format(
            prev_growth, strat, expected_growth))
        lines.append("  Match?          = {}".format(abs(expected_growth - growth) < 0.01))

lines.append("")

# ---- Check overall: the $3,683 value seems very low vs $3.8M Buy&Hold ----
lines.append("=== Context: Why 3x BH is so much lower than 1x BH ===")
last = data.iloc[-1]
lines.append("  Latest 1x BH Growth  = {:,.2f}".format(last['Buy_Hold_Growth']))
lines.append("  Latest 3x BH Growth  = {:,.2f}".format(last['Lev_3x_BH_Growth']))
lines.append("  Ratio (1x / 3x BH)   = {:.2f}x".format(
    last['Buy_Hold_Growth'] / last['Lev_3x_BH_Growth']))
lines.append("")

# Count how many days have negative 3x daily returns
neg_days = (data['Strategy_3x_BH_Daily'] < 0).sum()
total_days = len(data)
lines.append("  Days with negative 3x BH return: {} / {} ({:.1f}%)".format(
    neg_days, total_days, neg_days/total_days*100))

# Average daily return comparison
avg_1x = data['Simple_Ref'].mean()
avg_3x = data['Strategy_3x_BH_Daily'].mean()
lines.append("  Avg daily 1x return: {:.6f} ({:.4f}% annualized)".format(avg_1x, avg_1x*252*100))
lines.append("  Avg daily 3x BH return: {:.6f} ({:.4f}% annualized)".format(avg_3x, avg_3x*252*100))
lines.append("")

# Check some historically bad periods
lines.append("=== Worst 5 daily 3x BH returns ===")
worst = data['Strategy_3x_BH_Daily'].nsmallest(5)
for idx, val in worst.items():
    dt = idx.strftime('%Y-%m-%d')
    close = data.loc[idx, 'Close']
    price_ret = data.loc[idx, 'Simple_Ref']
    lines.append("  {}: 3x_ret={:>10.6f}  price_ret={:>10.6f}  close={:.2f}".format(
        dt, val, price_ret, close))

lines.append("")
lines.append("=== Financing cost impact over entire period ===")
# Total cumulative financing drag
total_fin = data['Financing_Rate_Daily'].sum()
total_expense = ETF_EXPENSE_DAILY * len(data)
lines.append("  Total financing cost (summed daily): {:.4f} ({:.2f}% total drag)".format(
    total_fin, total_fin * 100))
lines.append("  Total expense ratio (summed daily):  {:.4f} ({:.2f}% total drag)".format(
    total_expense, total_expense * 100))
lines.append("  Combined annual avg drag: {:.2f}%".format(
    (total_fin + total_expense) / len(data) * 252 * 100))

output = "\n".join(lines)
print(output)
with open('check_3x_bh.txt', 'w') as f:
    f.write(output)
