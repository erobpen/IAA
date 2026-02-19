"""
Debug script: Check the SMA 200 ($10k) calculation from the Leverage tab Data view.
"""
import database
import analyzer
import pandas as pd
import numpy as np

database.init_db()
data = analyzer.get_strategy_data()

lines = []
lines.append("Shape: {}".format(data.shape))
lines.append("")

# Last 12 rows to match screenshot
df = data[['Close','SMA_200','Regime','Simple_Ref','Buy_Hold_Growth']].tail(12)
lines.append("=== Verification: SMA 200 ($10k) Column ===")
lines.append("{:<12} {:>10} {:>10} {:>16} {:>16} {:>6}".format(
    "Date", "Close", "SMA200", "BuyHold", "SMA($10k)", "Regime"))
lines.append("-" * 72)

for idx, row in df.iterrows():
    dt = idx.strftime('%Y-%m-%d')
    c = row['Close']
    sma = row['SMA_200']
    bh = row['Buy_Hold_Growth']
    r = int(row['Regime']) if pd.notna(row['Regime']) else -1
    if pd.notna(sma) and c != 0:
        scaled = bh * (sma / c)
    else:
        scaled = float('nan')
    lines.append("{:<12} {:>10.2f} {:>10.2f} {:>16,.2f} {:>16,.2f} {:>6}".format(
        dt, c, sma, bh, scaled, r))

lines.append("")
lines.append("=== Manual Verification for 2026-02-17 ===")
mask = data.index.strftime('%Y-%m-%d') == '2026-02-17'
if mask.any():
    row = data.loc[mask].iloc[0]
    c = row['Close']
    sma = row['SMA_200']
    bh = row['Buy_Hold_Growth']
    scaled = bh * (sma / c) if pd.notna(sma) and c != 0 else float('nan')
    lines.append("Close          = {:.2f}".format(c))
    lines.append("SMA_200        = {:.2f}".format(sma))
    lines.append("Buy_Hold ($10k)= {:,.2f}".format(bh))
    lines.append("SMA ($10k)     = BH * (SMA/Close) = {:,.2f} * ({:.2f}/{:.2f}) = {:,.2f}".format(
        bh, sma, c, scaled))
    lines.append("Regime         = {}".format(int(row['Regime']) if pd.notna(row['Regime']) else 'NaN'))
    lines.append("Close > SMA?   = {} (should mean Regime=1)".format(c > sma))
else:
    lines.append("2026-02-17 not found in data")

lines.append("")
lines.append("=== Also check 3x calculations ===")
cols_3x = ['Strategy_3x_BH_Daily','Strategy_3x_Daily','Lev_3x_BH_Growth','Lev_3x_Growth']
df2 = data[cols_3x].tail(5)
for idx, row in df2.iterrows():
    dt = idx.strftime('%Y-%m-%d')
    lines.append("{}: 3xBH_Daily={:.6f} 3xStrat_Daily={:.6f} 3xBH_Growth={:,.2f} 3xStrat_Growth={:,.2f}".format(
        dt, row['Strategy_3x_BH_Daily'], row['Strategy_3x_Daily'],
        row['Lev_3x_BH_Growth'], row['Lev_3x_Growth']))

output = "\n".join(lines)
print(output)
with open('sma_check.txt', 'w') as f:
    f.write(output)
