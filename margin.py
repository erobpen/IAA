
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import traceback
import analyzer
import dividend_module
import database
from plotting import save_plot_to_buffer

def get_merged_data():
    """
    Fetches and aligns data from:
    1. Strategy Data (Price, Regime) from analyzer
    2. Interest Rate Data from dividend_module
    3. Inflation Data from inflation (database)
    """
    strat_data = analyzer.get_strategy_data()
    if strat_data.empty:
        return pd.DataFrame()

    # Interest Rate Data (Monthly)
    div_data = dividend_module.get_dividend_data()
    
    # Inflation Data (Monthly)
    inf_data = database.get_all_inflation_data()
    
    # --- Merge/Align Data ---
    df = strat_data[['Close', 'Regime', 'Total_Return_Daily']].copy()
    
    # Ensure indices are datetime
    div_data.index = pd.to_datetime(div_data.index)
    inf_data.index = pd.to_datetime(inf_data.index)
    
    # Reindex Interest Rate to Daily and FFill
    ir_daily = div_data['Long Interest Rate'].reindex(df.index, method='ffill')
    df['Long_Yield'] = ir_daily
    
    # Join CPI for Inflation Calculation
    cpi_daily = inf_data['CPI'].reindex(df.index, method='ffill')
    df['CPI'] = cpi_daily
    
    # Fill any remaining NaNs
    df = df.ffill()
    df = df.bfill()
    
    return df

def calculate_margin_strategy(df):
    """
    Simulates the margin strategy:
    - Initial Margin Limit: $2000
    - Margin Limit Adjusts annually by Inflation
    - Criteria (Regime = 1): Invest using Cash + Margin Debt.
    - Criteria (Regime = 0): Sell, Repay Debt.
    - Interest: Accumulated daily, deducted annually.
    """
    if df.empty:
        return df
        
    # Parameters
    base_limit = 2000.0
    margin_add = 0.015 # +1.5% spread
    
    # Simulation State
    cash = 0.0
    debt = 0.0
    invested_value = 0.0
    
    margin_limit = base_limit
    
    current_year = df.index[0].year
    
    last_year_cpi = df['CPI'].iloc[0]
    
    accrued_interest_cumulative = 0.0
    
    # 3x Leverage Daily Return
    leveraged_daily_ret = (df['Total_Return_Daily'] * 3).clip(lower=-1.0)
    
    # Extract numpy arrays for speed
    dates = df.index
    regimes = df['Regime'].values
    yields = df['Long_Yield'].values
    cpis = df['CPI'].values
    lev_returns = leveraged_daily_ret.values
    
    # Result arrays
    equity_curve = np.zeros(len(df))
    debt_curve = np.zeros(len(df))
    cash_curve = np.zeros(len(df))
    invested_curve = np.zeros(len(df))
    
    year_start_cpi = cpis[0]
    
    # State flags
    in_market = False
    
    for i in range(len(df)):
        date = dates[i]
        year = date.year
        
        # 1. Year Change Handling (Inflation & Interest)
        if year != current_year:
            year_end_cpi = cpis[i-1]
            if year_start_cpi > 0:
                inflation_rate = (year_end_cpi / year_start_cpi) - 1
            else:
                inflation_rate = 0
                
            # Update Limit
            margin_limit = margin_limit * (1 + inflation_rate)
            
            # Deduct Interest
            cash -= accrued_interest_cumulative
            accrued_interest_cumulative = 0.0
            
            # Reset counters
            current_year = year
            year_start_cpi = cpis[i-1]
            
        # 2. Daily Interest Accrual
        daily_rate_annual = (yields[i] + (margin_add*100)) / 100.0
        daily_interest_cost = debt * (daily_rate_annual / 365.0)
        accrued_interest_cumulative += daily_interest_cost
        
        # 3. Strategy Logic
        signal = regimes[i]
        
        if signal == 1:
            # BUY / HOLD Signal
            if not in_market:
                # ENTER Market
                debt = margin_limit
                investment_amt = cash + debt
                
                if investment_amt < 0:
                    invested_value = 0
                    pass 
                else:
                    invested_value = investment_amt
                    cash = 0
                
                in_market = True
            else:
                # ALREADY IN Market — apply daily return
                pct_change = lev_returns[i]
                invested_value = invested_value * (1 + pct_change)
                
        else:
            # CASH Signal (Sell/Stay Out)
            if in_market:
                # EXIT Market
                proceeds = invested_value
                invested_value = 0
                
                if proceeds >= debt:
                    cash = proceeds - debt
                    debt = 0
                else:
                    repay_amount = proceeds
                    debt = debt - repay_amount
                    cash = 0
                    
                in_market = False
        
        # Calculate Daily Equity
        current_equity = (cash + invested_value) - debt
        
        equity_curve[i] = current_equity
        debt_curve[i] = debt
        cash_curve[i] = cash
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
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df.index, df['Margin_Equity'], label='3x Strategy Margin Equity ($0 Start)', color='purple', linewidth=1)
        
        ax.set_yscale('symlog')
        
        ax.set_title('Margin Strategy Cumulative Yield')
        ax.set_xlabel('Date')
        ax.set_ylabel('Net Liquidation Value ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        img = save_plot_to_buffer(fig)
        
        # Prepare Table Data (vectorized)
        df_latest = df.sort_index(ascending=False)
        
        table_data = []
        dates = df_latest.index.strftime('%Y-%m-%d')
        equity_vals = df_latest['Margin_Equity'].values
        cash_vals = df_latest['Margin_Cash'].values
        invested_vals = df_latest['Margin_Invested'].values
        debt_vals = df_latest['Margin_Debt'].values
        regime_vals = df_latest['Regime'].values
        yield_vals = df_latest['Long_Yield'].values
        
        for i in range(len(df_latest)):
            rate_str = f"{yield_vals[i]:.2f}%" if pd.notna(yield_vals[i]) else "-"
            table_data.append({
                'date': dates[i],
                'equity': f"${equity_vals[i]:,.2f}",
                'cash': f"${cash_vals[i]:,.2f}",
                'invested': f"${invested_vals[i]:,.2f}",
                'debt': f"${debt_vals[i]:,.2f}",
                'regime': int(regime_vals[i]),
                'rate': rate_str
            })
            
        return img, table_data
        
    except Exception as e:
        print(f"Error in analyze_margin: {e}")
        traceback.print_exc()
        return None, []

if __name__ == "__main__":
    analyze_margin()
