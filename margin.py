
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import traceback
import analyzer
import dividend_module
import inflation
import database
from datetime import timedelta

def get_merged_data():
    """
    Fetches and aligns data from:
    1. Strategy Data (Price, Regime) from analyzer
    2. Interest Rate Data from dividend_module
    3. Inflation Data from inflation (database)
    """
    # 1. Strategy Data (Daily)
    # analyzer.get_strategy_data already returns a DataFrame with 'Close', 'Regime', 'Date' (index)
    # calculated up to today.
    # Note: process might verify if we need to call database functions directly 
    # if we want to avoid re-calculating everything in analyzer, 
    # but analyzer.get_strategy_data() is the source of truth for "Regime".
    
    strat_data = analyzer.get_strategy_data()
    if strat_data.empty:
        return pd.DataFrame()

    # 2. Interest Rate Data (Monthly)
    # dividend_module.get_dividend_data() returns Shiller data
    # Columns: 'Long Interest Rate'
    div_data = dividend_module.get_dividend_data()
    
    # 3. Inflation Data (Monthly)
    # database.get_all_inflation_data() returns CPI
    inf_data = database.get_all_inflation_data()
    
    # --- Merge/Align Data ---
    # We want a daily DataFrame based on strat_data.index
    df = strat_data[['Close', 'Regime', 'Total_Return_Daily']].copy()
    
    # Join Interest Rates
    # Resample monthly interest data to daily (ffill)
    # First ensure indices are datetime
    div_data.index = pd.to_datetime(div_data.index)
    inf_data.index = pd.to_datetime(inf_data.index)
    
    # Reindex Interest Rate to Daily and FFill
    # We use 'Long Interest Rate'
    # Rate is in %, e.g., 4.5
    # We need to handle the date alignment carefully. Shiller dates are usually 1st of month.
    # We ffill effectively applying that rate for the subsequent days until next month.
    
    # We can join by reindexing
    ir_daily = div_data['Long Interest Rate'].reindex(df.index, method='ffill')
    df['Long_Yield'] = ir_daily
    
    # Join CPI for Inflation Calculation
    cpi_daily = inf_data['CPI'].reindex(df.index, method='ffill')
    df['CPI'] = cpi_daily
    
    # Fill any remaining NaNs (e.g. if stock data starts before IR/CPI data)
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True) # Fallback to bfill for start
    
    return df

def calculate_margin_strategy(df):
    """
    Simulates the margin strategy:
    - Initial Margin Limit: $2000
    - Margin Limit Adjusts annually by Inflation
    - Criteria (Regime = 1): Invest using Cash + Margin Debt.
      - "total of 2k margin is taken" -> Debt becomes Margin Limit.
    - Criteria (Regime = 0): Sell, Repay Debt.
    - Interest: Accumulated daily, deducted annually.
    - Start Date: 1928-01-01 (or earliest common data)
    """
    if df.empty:
        return df
        
    # Parameters
    base_limit = 2000.0
    margin_add = 0.015 # +1.5% spread
    
    # Simulation State
    cash = 0.0
    debt = 0.0
    invested_value = 0.0 # Value of 3x Position
    
    margin_limit = base_limit
    
    # We need to track year change to adjust margin limit and deduct interest
    current_year = df.index[0].year
    
    # Use CPI to calculate annual inflation for margin limit adjustment
    # Rule: "limit is increase by annual inflation"
    # We'll calculate inflation at year end and update limit for NEXT year? 
    # Or update continuously? "calculated for each year by that rule". 
    # Let's update at start of each year based on previous year's CPI change.
    last_year_cpi = df['CPI'].iloc[0]
    
    # Trackers for history
    history_equity = []
    history_debt = []
    
    accrued_interest_cumulative = 0.0 # Interest to be deducted at year end
    
    # 3x Leverage Daily Return
    # Using 'Total_Return_Daily' * 3 (clipped at -100%)
    # Note: Total_Return_Daily is (Price_Change + Div) / Price. 
    # 3x Strategy specific return:
    leveraged_daily_ret = (df['Total_Return_Daily'] * 3).clip(lower=-1.0)
    
    # Convert columns to numpy for speed if needed, but iteration is clearer for logic
    # Iterating row by row is slow but safer for complex state machines like this.
    
    dates = df.index
    regimes = df['Regime'].values
    yields = df['Long_Yield'].values
    cpis = df['CPI'].values
    lev_returns = leveraged_daily_ret.values
    
    # Result arrays
    equity_curve = np.zeros(len(df))
    debt_curve = np.zeros(len(df))
    cash_curve = np.zeros(len(df)) # Debug
    invested_curve = np.zeros(len(df))
    
    # Previous day's CPI for continuous check or just use year bounds
    year_start_cpi = cpis[0]
    
    # State flags
    in_market = False
    
    for i in range(len(df)):
        date = dates[i]
        year = date.year
        
        # 1. Year Change Handling (Inflation & Interest)
        if year != current_year:
            # Update Margin Limit based on Inflation
            # Inflation = (Current CPI / Year Start CPI) - 1 ??
            # Text: "increase by annual inflation... 2000 + 10% of 2000".
            # This implies cumulative inflation adjustment? 
            # Or Year-over-Year adjustment of the limit?
            # "Limit is calculate for each year by that rule."
            # Base Limit = 2000.
            # Limit_Year_N = Limit_Year_N-1 * (1 + Inflation_N-1)
            
            # Helper: Get CPI at end of year (last val of i-1)
            year_end_cpi = cpis[i-1]
            if year_start_cpi > 0:
                inflation_rate = (year_end_cpi / year_start_cpi) - 1
            else:
                inflation_rate = 0
                
            # Update Limit
            margin_limit = margin_limit * (1 + inflation_rate)
            
            # Deduct Interest
            # "Cost that need to be subtructed annually"
            # Deduct from Cash
            cash -= accrued_interest_cumulative
            accrued_interest_cumulative = 0.0
            
            # Reset counters
            current_year = year
            # Set start cpi to the end of the previous year (Dec 31) to capture full Year-Over-Year change
            year_start_cpi = cpis[i-1]
            
        # 2. Daily Interest Accrual
        # Rate = (Long Yield + 1.5%) / 100
        # Daily Rate = Rate / 365
        daily_rate_annual = (yields[i] + (margin_add*100)) / 100.0
        daily_interest_cost = debt * (daily_rate_annual / 365.0)
        accrued_interest_cumulative += daily_interest_cost
        
        # 3. Strategy Logic
        signal = regimes[i]
        
        if signal == 1:
            # BUY / HOLD Signal
            if not in_market:
                # ENTER Market
                # "2k$ is taken on top of extra cash from previous cycle and all is invested"
                # "total of 2k margin is taken" -> Debt = margin_limit
                
                # Check if we have negative cash (from interest payments while out of market?)
                # "margin is reduced my availabe money"
                # If cash is negative (we owe money), we use borrowed funds to fix cash?
                # Or does debt just increase?
                # Let's assume standard account:
                # Buying Power = Cash. We want to borrow `margin_limit`.
                # Total Investment = Cash + margin_limit.
                
                # Scenario: Cash = -100 (Interest debt). Limit = 2000.
                # Invest = -100 + 2000 = 1900? 
                # Debt = 2000? 
                # Net Account Value = 1900 Asset - 2000 Debt = -100. Matches.
                
                debt = margin_limit
                investment_amt = cash + debt
                
                # Cannot invest negative amount
                if investment_amt < 0:
                    invested_value = 0
                    # We obtain debt, but it just covers the negative cash hole?
                    # Effectively we are short cash. 
                    # If Cash is -3000, Debt 2000 -> Still -1000 Cash. 0 Invested.
                    cash = cash + debt # Cash becomes -1000? No, Debt is a liability.
                    # Accounting:
                    # Assets: Invested_Value, Cash (if +)
                    # Liabilities: Debt, Cash (if -)
                    # Let's stick to: Net_Liq = Invested + Cash - Debt.
                    pass 
                else:
                    invested_value = investment_amt
                    cash = 0 # All deployed
                
                in_market = True
            else:
                # ALREADY IN Market
                # Apply Daily Return to Invested Value
                pct_change = lev_returns[i]
                invested_value = invested_value * (1 + pct_change)
                
                # Rebalance? 
                # User says: "strategy alternated between two states... If criteria is meet... invested... if not all is in cash"
                # Does not explicitly mention daily rebalancing of leverage ratio. 
                # Usually "3x Strategy" implies daily rebalancing of the INDEX (which we handled in data preparation), 
                # but does the portfolio rebalance debt daily?
                # User says: "once criteria is met to invest... total of 2k margin is taken".
                # Implies we define the debt amount AT ENTRY. 
                # We do NOT drift the debt amount? 
                # Or do we Maintain 2k debt? 
                # "If there is enough money to close margin, we remain in cash... criteria is again met... 2k$ is taken".
                # This suggests Debt is fixed at Entry (or adjusted only at entry?).
                # I will assume Debt stays constant until we Exit.
                pass
                
        else:
            # CASH Signal (Sell/Stay Out)
            if in_market:
                # EXIT Market
                # Sell 3x Position
                proceeds = invested_value
                invested_value = 0
                
                # Repay Debt
                # "Two possible scenarios... do not have enough money... or enough money"
                if proceeds >= debt:
                    # Case 1: Enough money
                    cash = proceeds - debt
                    debt = 0
                else:
                    # Case 2: Not enough money
                    # "margin is reduced my availabe money"
                    # We pay what we can.
                    repay_amount = proceeds
                    debt = debt - repay_amount
                    cash = 0
                    # "calculation of margin is continued" -> means we still owe interest on remaining debt
                    
                in_market = False
            else:
                # ALREADY OUT
                # Just sitting in cash (or debt if we couldn't pay it off)
                pass
        
        # Calculate Daily Equity
        # Equity = (Cash + Invested) - Debt
        current_equity = (cash + invested_value) - debt
        
        equity_curve[i] = current_equity
        debt_curve[i] = debt
        cash_curve[i] = cash # Debug
        invested_curve[i] = invested_value
        
    df['Margin_Equity'] = equity_curve
    df['Margin_Debt'] = debt_curve
    df['Margin_Cash'] = cash_curve
    df['Margin_Invested'] = invested_curve
    
    return df

def analyze_margin():
    try:
        print("Calculating Margin Strategy...")
        df = get_merged_data()
        
        if df.empty:
            return None, []
            
        df = calculate_margin_strategy(df)
        
        # Plotting
        plt.figure(figsize=(12, 6))
        
        # Plot Equity
        # Filter where equity is not just flat 0 at start if needed, but 1928 start is fine.
        plt.plot(df.index, df['Margin_Equity'], label='3x Strategy Margin Equity ($0 Start)', color='purple', linewidth=1)
        
        # Optional: Plot Debt on secondary axis?
        # Or just show Equity
        
        plt.title('Margin Strategy Cumulative Yield')
        plt.xlabel('Date')
        plt.ylabel('Net Liquidation Value ($)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Save plot
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        
        # Prepare Table Data
        # Columns: Date, Equity, Margin Debt, Invested?, Regime, Interest Rate, Margin Limit (need to calc/infer?)
        # Let's return Date, Equity, Margin Debt
        
        df_latest = df.sort_index(ascending=False)
        table_data = []
        
        for date, row in df_latest.iterrows():
            # Format
            table_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'equity': f"${row['Margin_Equity']:,.2f}",
                'cash': f"${row['Margin_Cash']:,.2f}",
                'invested': f"${row['Margin_Invested']:,.2f}",
                'debt': f"${row['Margin_Debt']:,.2f}",
                'regime': int(row['Regime']),
                'rate': f"{row['Long_Yield']:.2f}%" if pd.notna(row['Long_Yield']) else "-"
            })
            
        return img, table_data
        
    except Exception as e:
        print(f"Error in analyze_margin: {e}")
        traceback.print_exc()
        return None, []

if __name__ == "__main__":
    analyze_margin()
