import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
import io
import traceback
from datetime import timedelta, datetime
import pandas_datareader.data as web
import database
import data_cache
from plotting import save_plot_to_buffer

def _fetch_fed_funds_rate():
    """
    Fetches the Daily Effective Federal Funds Rate (DFF) from FRED.
    Stores in DB for caching. Returns DataFrame with Date index and 'Rate' column.
    
    This rate represents the cost of leverage financing for 3x leveraged ETFs.
    Leveraged ETFs use total return swaps; the swap counterparty charges a
    financing rate tied to short-term rates (SOFR/Fed Funds).
    DFF data starts from 1954-07-01.
    """
    cached = data_cache.get('fed_funds_data')
    if cached is not None:
        return cached
    
    # Check DB for latest data
    last_date = database.get_latest_fed_funds_date()
    current_date = datetime.now()
    
    start_date = None
    if last_date:
        days_diff = (current_date.date() - last_date).days
        if days_diff > 5:
            start_date = last_date + timedelta(days=1)
            print(f"Updating Fed Funds Rate data from {start_date}...")
        else:
            print("Fed Funds Rate data is up to date.")
    else:
        print("No Fed Funds Rate data. Fetching full history...")
        start_date = datetime(1954, 7, 1)
    
    if start_date:
        try:
            new_data = web.DataReader('DFF', 'fred', start_date, current_date)
            if not new_data.empty:
                print(f"Downloaded {len(new_data)} Fed Funds Rate records.")
                database.save_fed_funds_data(new_data)
        except Exception as e:
            print(f"Error fetching DFF from FRED: {e}")
    
    ff_data = database.get_all_fed_funds_data()
    data_cache.set('fed_funds_data', ff_data)
    return ff_data

def get_strategy_data():
    """
    Fetches data and performs all strategy calculations.
    Returns the prepared DataFrame. Uses caching to avoid redundant work.
    
    3x leveraged ETF daily return model:
        3x_ETF_return = 3 × price_return − 2 × financing_rate − expense_ratio
        
    Where:
    - price_return: daily S&P 500 price change
    - financing_rate: Fed Funds Rate (DFF from FRED) — cost of swap-based leverage
    - expense_ratio: ~1% annual for 3x ETFs like SPXL (index ETF ~0.06% disregarded)
    
    The financing rate is included in the DataFrame as 'Financing_Rate_Daily' so
    downstream modules (lsc, lscda) can access it for their own 3x calculations.
    """
    cached = data_cache.get('strategy_data')
    if cached is not None:
        return cached

    print("Getting strategy data...")
    
    ticker = "^GSPC"
    
    # 1. Check what we have in DB
    last_date = database.get_latest_date(ticker)
    
    today = pd.Timestamp.today().date()
    
    # 2. Determine download range
    if last_date:
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        start_date = "1928-01-01"
        
    end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
    
    # 3. Download only if start_date < today
    start_date_obj = pd.to_datetime(start_date).date()
    
    if start_date_obj <= today:
        try:
            new_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if not new_data.empty:
                # Handle MultiIndex if present
                if isinstance(new_data.columns, pd.MultiIndex):
                    try:
                        if ticker in new_data.columns.levels[1]:
                             new_data = new_data.xs(ticker, level=1, axis=1)
                    except:
                         new_data.columns = new_data.columns.get_level_values(0)

                database.save_stock_data(new_data, ticker)
        except Exception as e:
            print(f"Error downloading data: {e}")
    
    # 4. Load ALL data from DB for analysis
    data = database.get_all_stock_data(ticker)
    
    if data.empty:
         return pd.DataFrame()

    # Calculate 200-day Simple Moving Average
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    data['Regime'] = np.where(data['Close'] > data['SMA_200'], 1, 0)
    # Shift regime by 1 day to avoid look-ahead bias
    data['Regime'] = data['Regime'].shift(1)
    
    # Calculate daily simple returns (Price Return)
    data['Simple_Ref'] = data['Close'].pct_change()
    data['Simple_Ref'] = data['Simple_Ref'].fillna(0)
    
    # Simulated Total Return (Adding Dividends) -> 0 as per user request
    daily_dividend = 0
    data['Total_Return_Daily'] = data['Simple_Ref'] + daily_dividend
    
    # --- Financing Cost (Cost of Carry) ---
    # Fetch Fed Funds Rate (DFF) from FRED — represents the cost of swap-based leverage.
    # For pre-1954 data (before DFF series exists), assume 1% rate as approximation.
    # A 3x leveraged ETF borrows 2x its capital via swaps, paying this rate on the 2x portion.
    PRE_1954_RATE_ASSUMPTION = 1.0  # 1% annual — Fed Funds was very low in 1930s-1950s
    
    ff_data = _fetch_fed_funds_rate()
    
    if not ff_data.empty:
        # Reindex to daily trading dates, forward-fill to cover weekends/holidays
        ff_reindexed = ff_data['Rate'].reindex(data.index, method='ffill')
        # Back-fill any NaN at the start (dates before first DFF record)
        ff_reindexed = ff_reindexed.fillna(PRE_1954_RATE_ASSUMPTION)
        data['Fed_Funds_Rate'] = ff_reindexed
    else:
        # If no data available, use assumption
        data['Fed_Funds_Rate'] = PRE_1954_RATE_ASSUMPTION
    
    # Convert annual rate (%) to daily cost for the 2x borrowed portion
    # financing_cost_daily = 2 × (annual_rate / 100) / 252
    data['Financing_Rate_Daily'] = 2 * (data['Fed_Funds_Rate'] / 100) / 252
    
    # --- ETF Expense Ratio ---
    # 3x leveraged ETFs (e.g., SPXL) charge ~1% annual expense ratio.
    # Index ETFs (e.g., SPY/VOO) have ~0.06% fee which is disregarded.
    ETF_EXPENSE_RATIO_ANNUAL = 0.01  # 1% annual
    ETF_EXPENSE_RATIO_DAILY = ETF_EXPENSE_RATIO_ANNUAL / 252
    
    # Initial Capital
    initial_capital = 10000
    
    # 1. Buy & Hold (1x) — no expense ratio (index ETF fee negligible)
    data['Strategy_1x_Daily'] = data['Total_Return_Daily']
    data['Buy_Hold_Growth'] = initial_capital * (1 + data['Strategy_1x_Daily']).cumprod()
    
    # 2. 3x Buy & Hold — full cost model:
    #    3 × price_return − 2 × financing_rate − expense_ratio
    data['Strategy_3x_BH_Daily'] = (
        3 * data['Total_Return_Daily']
        - data['Financing_Rate_Daily']
        - ETF_EXPENSE_RATIO_DAILY
    )
    data['Strategy_3x_BH_Daily'] = data['Strategy_3x_BH_Daily'].clip(lower=-1.0)
    data['Lev_3x_BH_Growth'] = initial_capital * (1 + data['Strategy_3x_BH_Daily']).cumprod()
    
    # 3. 3x Strategy (MA Filter) — costs only when holding the ETF (Regime=1)
    data['Strategy_3x_Daily'] = np.where(
        data['Regime'] == 1,
        3 * data['Total_Return_Daily'] - data['Financing_Rate_Daily'] - ETF_EXPENSE_RATIO_DAILY,
        0
    )
    data['Strategy_3x_Daily'] = data['Strategy_3x_Daily'].clip(lower=-1.0)
    data['Lev_3x_Growth'] = initial_capital * (1 + data['Strategy_3x_Daily']).cumprod()
    
    data_cache.set('strategy_data', data)
    return data

def analyze_strategy():
    try:
        data = get_strategy_data()
        
        if data.empty:
             raise Exception("No data available!")
             
        print("Plotting results...")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data.index, data['Buy_Hold_Growth'], label='Buy & Hold (1x Total Return)', linewidth=1)
        ax.plot(data.index, data['Lev_3x_BH_Growth'], label='3x Buy & Hold', linewidth=1, color='orange')
        ax.plot(data.index, data['Lev_3x_Growth'], label='3x Strategy (MA)', linewidth=1, color='purple')
        
        ax.set_yscale('log')
        ax.set_title('Leverage for the Long Run: Portfolio Value ($10k Initial)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, which="both", ls="-", alpha=0.2)
        
        output = save_plot_to_buffer(fig)
        print("Analysis complete. Returning image buffer.")
        
        # Prepare Data for Table — vectorized approach
        full_data = data.reset_index()
        
        # Pre-compute scaled SMA
        valid_sma = pd.notna(full_data['SMA_200']) & (full_data['Close'] != 0)
        full_data['scaled_sma'] = np.where(
            valid_sma,
            full_data['Buy_Hold_Growth'] * (full_data['SMA_200'] / full_data['Close']),
            np.nan
        )
        
        # Build table data vectorized
        table_data = []
        dates = full_data['Date'].dt.strftime('%Y-%m-%d').values
        sp500_vals = full_data['Buy_Hold_Growth'].values
        sma_vals = full_data['scaled_sma'].values
        bh_3x_vals = full_data['Lev_3x_BH_Growth'].values
        strat_3x_vals = full_data['Lev_3x_Growth'].values
        regime_vals = full_data['Regime'].values
        
        for i in range(len(full_data)):
            sma_str = f"{sma_vals[i]:,.2f}" if not np.isnan(sma_vals[i]) else "-"
            table_data.append({
                'date': dates[i],
                'sp500_val': f"{sp500_vals[i]:,.2f}",
                'sma_val': sma_str,
                'strategy_3x_bh_val': f"{bh_3x_vals[i]:,.2f}",
                'strategy_3x_val': f"{strat_3x_vals[i]:,.2f}",
                'regime': int(regime_vals[i]) if not np.isnan(regime_vals[i]) else 0
            })
            
        # Reverse list to show newest first
        table_data.reverse()
        
        return output, table_data
    except Exception as e:
        print("Error during analysis:")
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    analyze_strategy()


def analyze_strategy_filtered(start_date, end_date):
    """
    Re-run the leverage strategy simulation for a specific date range.
    Uses the same daily return series but re-compounds from $10k
    starting at start_date through end_date.
    
    Returns a BytesIO plot image.
    """
    data = get_strategy_data()
    if data.empty:
        return None

    # Slice to requested date range
    mask = (data.index >= pd.Timestamp(start_date)) & (data.index <= pd.Timestamp(end_date))
    window = data.loc[mask].copy()

    if window.empty or len(window) < 2:
        return None

    initial_capital = 10000

    # Re-compound from $10k over just this window
    window['BH_Filtered'] = initial_capital * (1 + window['Strategy_1x_Daily']).cumprod()
    window['BH_3x_Filtered'] = initial_capital * (1 + window['Strategy_3x_BH_Daily']).cumprod()
    window['Strat_3x_Filtered'] = initial_capital * (1 + window['Strategy_3x_Daily']).cumprod()

    # Recalculate SMA in portfolio space
    window['SMA_200_Filtered'] = np.where(
        pd.notna(window['SMA_200']) & (window['Close'] != 0),
        window['BH_Filtered'] * (window['SMA_200'] / window['Close']),
        np.nan
    )

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(window.index, window['BH_Filtered'], label='Buy & Hold (1x)', linewidth=1)
    ax.plot(window.index, window['BH_3x_Filtered'], label='3x Buy & Hold', linewidth=1, color='orange')
    ax.plot(window.index, window['Strat_3x_Filtered'], label='3x Strategy (MA)', linewidth=1, color='purple')

    ax.set_yscale('log')
    start_yr = window.index[0].strftime('%Y')
    end_yr = window.index[-1].strftime('%Y')
    ax.set_title(f'Leverage for the Long Run: {start_yr}–{end_yr} ($10k Initial)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Portfolio Value ($)')
    ax.legend()
    ax.grid(True, which="both", ls="-", alpha=0.2)

    return save_plot_to_buffer(fig)

