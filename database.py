import os
from sqlalchemy import create_engine, Column, Date, String, Float, Integer, BigInteger, inspect, select, text
from sqlalchemy.orm import declarative_base, sessionmaker
import pandas as pd

# Database Connection URL (matches docker-compose environment variables)
# host='db' comes from the service name in docker-compose
db_host = os.getenv('DB_HOST', 'db')
DATABASE_URL = f"postgresql://user:password@{db_host}:5432/investing"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StockPrice(Base):
    __tablename__ = "stock_prices"

    date = Column(Date, primary_key=True, index=True)
    ticker = Column(String, primary_key=True, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(BigInteger)

def init_db():
    """Create tables if they don't exist."""
    print("Initializing database...")
    try:
        # iterate over all tables and create them if they don't exist
        Base.metadata.create_all(bind=engine)
        print("Tables initialized.")
    except Exception as e:
        print(f"Error initializing DB: {e}")

def get_latest_date(ticker):
    """Returns the latest date available for a given ticker."""
    db = SessionLocal()
    try:
        stmt = select(StockPrice.date).where(StockPrice.ticker == ticker).order_by(StockPrice.date.desc()).limit(1)
        result = db.execute(stmt).scalar_one_or_none()
        return result
    except Exception as e:
        print(f"Error getting latest date: {e}")
        return None
    finally:
        db.close()

def save_stock_data(df, ticker):
    """Saves a Pandas DataFrame (from yfinance) to the database."""
    if df.empty:
        return

    # Standardize DataFrame
    # yfinance returns Date as index. Reset it to make it a column.
    df = df.reset_index()
    
    # Rename columns to match model if necessary, or just map them
    # Expected yfinance cols: Date, Open, High, Low, Close, Adj Close, Volume
    
    records = []
    for _, row in df.iterrows():
        record = StockPrice(
            date=row['Date'].date() if hasattr(row['Date'], 'date') else pd.to_datetime(row['Date']).date(),
            ticker=ticker,
            open=row.get('Open', 0.0),
            high=row.get('High', 0.0),
            low=row.get('Low', 0.0),
            close=row.get('Close', 0.0),
            adj_close=row.get('Adj Close', 0.0),
            volume=int(row.get('Volume', 0))
        )
        records.append(record)

    db = SessionLocal()
    try:
        # Use merge to handle potential duplicates (slower but safer)
        for record in records:
            db.merge(record)
            
        db.commit()
        print(f"Saved {len(records)} records for {ticker}.")
    except Exception as e:
        print(f"Error saving data: {e}")
        db.rollback()
    finally:
        db.close()

def get_all_stock_data(ticker):
    """Reads all data for a ticker from DB into a Pandas DataFrame."""
    query = text("SELECT * FROM stock_prices WHERE ticker = :ticker ORDER BY date ASC")
    try:
        df = pd.read_sql(query, engine, params={"ticker": ticker})
        if not df.empty:
            df['Date'] = pd.to_datetime(df['date'])
            df.set_index('Date', inplace=True)
            # Normalize column names to match yfinance expected output
            df = df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 
                'close': 'Close', 'adj_close': 'Adj Close', 'volume': 'Volume'
            })
        return df
    except Exception as e:
        print(f"Error reading data: {e}")
        return pd.DataFrame()

# --- Inflation Data Support ---

class InflationData(Base):
    __tablename__ = 'inflation_data'
    
    date = Column(Date, primary_key=True)
    cpi = Column(Float) # CPIAUCNS value

def get_latest_inflation_date():
    """Get the latest date we have inflation data for."""
    session = SessionLocal()
    try:
        last_entry = session.query(InflationData).order_by(InflationData.date.desc()).first()
        return last_entry.date if last_entry else None
    except Exception as e:
        print(f"Error getting latest inflation date: {e}")
        return None
    finally:
        session.close()

def save_inflation_data(df):
    """Save inflation dataframe to DB."""
    session = SessionLocal()
    try:
        # Expecting DataFrame with DateTime index and 'CPIAUCNS' column (or similar)
        # We will iterate and merge
        for date, row in df.iterrows():
            # Check if exists
            exists = session.query(InflationData).filter_by(date=date.date()).first()
            if not exists:
                # Value might be in 'CPIAUCNS' or just the first column
                val = row.iloc[0] 
                record = InflationData(date=date.date(), cpi=float(val))
                session.add(record)
        
        session.commit()
        print("Inflation data saved successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error saving inflation data: {e}")
    finally:
        session.close()

def get_all_inflation_data():
    """Get all inflation data from DB as DataFrame."""
    session = SessionLocal()
    try:
        data = session.query(InflationData).order_by(InflationData.date).all()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame([{'Date': d.date, 'CPI': d.cpi} for d in data])
        
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
    except Exception as e:
        print(f"Error getting inflation data: {e}")
        return pd.DataFrame()
    finally:
        session.close()

# --- Market Statistics Data Support (Shiller) ---

class MarketStats(Base):
    __tablename__ = 'market_stats'
    
    date = Column(Date, primary_key=True)
    sp500 = Column(Float)
    dividend = Column(Float)
    earnings = Column(Float)
    cpi = Column(Float)
    long_interest_rate = Column(Float)
    real_price = Column(Float)
    real_dividend = Column(Float)
    real_earnings = Column(Float)
    pe_ratio = Column(Float)

def get_latest_market_stats_date():
    """Get the latest date we have market stats for."""
    session = SessionLocal()
    try:
        last_entry = session.query(MarketStats).order_by(MarketStats.date.desc()).first()
        return last_entry.date if last_entry else None
    except Exception as e:
        print(f"Error getting latest market stats date: {e}")
        return None
    finally:
        session.close()

def save_market_stats(df):
    """Save market stats dataframe to DB."""
    session = SessionLocal()
    # Helper to clean numpy/pandas types
    def safe_float(val):
        if pd.isna(val) or val is None:
            return None
        return float(val)

    try:
        # Expecting DataFrame with DateTime index and specific columns
        # We will iterate and merge
        for date, row in df.iterrows():
            # Check if exists
            exists = session.query(MarketStats).filter_by(date=date.date()).first()
            if not exists:
                record = MarketStats(
                    date=date.date(),
                    sp500=safe_float(row.get('SP500')),
                    dividend=safe_float(row.get('Dividend')),
                    earnings=safe_float(row.get('Earnings')),
                    cpi=safe_float(row.get('CPI')),
                    long_interest_rate=safe_float(row.get('Long Interest Rate')),
                    real_price=safe_float(row.get('Real Price')),
                    real_dividend=safe_float(row.get('Real Dividend')),
                    real_earnings=safe_float(row.get('Real Earnings')),
                    pe_ratio=safe_float(row.get('PE10'))
                )
                session.add(record)
        
        session.commit()
        print("Market stats saved successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error saving market stats: {e}")
    finally:
        session.close()

def get_all_market_stats():
    """Get all market stats from DB as DataFrame."""
    session = SessionLocal()
    try:
        data = session.query(MarketStats).order_by(MarketStats.date).all()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame([{
            'Date': d.date,
            'SP500': d.sp500,
            'Dividend': d.dividend,
            'Earnings': d.earnings,
            'CPI': d.cpi,
            'Long Interest Rate': d.long_interest_rate,
            'Real Price': d.real_price,
            'Real Dividend': d.real_dividend,
            'Real Earnings': d.real_earnings,
            'PE10': d.pe_ratio
        } for d in data])
        
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
    except Exception as e:
        print(f"Error getting market stats: {e}")
        return pd.DataFrame()
    finally:
        session.close()

# --- Fed Funds Rate Data Support (FRED: DFF) ---
# Used to calculate the financing cost (cost of carry) for 3x leveraged ETFs.
# Leveraged ETFs use swaps to achieve 3x exposure; the swap counterparty charges
# a financing rate tied to short-term rates (SOFR/Fed Funds).
# The daily cost of leverage = 2 × (fed_funds_rate / 252) for the 2x borrowed portion.

class FedFundsRate(Base):
    __tablename__ = 'fed_funds_rate'
    
    date = Column(Date, primary_key=True)
    rate = Column(Float)  # Daily effective rate (annualized %)

def get_latest_fed_funds_date():
    """Get the latest date we have Fed Funds Rate data for."""
    session = SessionLocal()
    try:
        last_entry = session.query(FedFundsRate).order_by(FedFundsRate.date.desc()).first()
        return last_entry.date if last_entry else None
    except Exception as e:
        print(f"Error getting latest fed funds date: {e}")
        return None
    finally:
        session.close()

def save_fed_funds_data(df):
    """Save Fed Funds Rate dataframe to DB.
    Expects DataFrame with DateTime index and 'DFF' column (from FRED)."""
    session = SessionLocal()
    try:
        for date, row in df.iterrows():
            exists = session.query(FedFundsRate).filter_by(date=date.date()).first()
            if not exists:
                val = row.iloc[0] if pd.notna(row.iloc[0]) else None
                if val is not None:
                    record = FedFundsRate(date=date.date(), rate=float(val))
                    session.add(record)
        
        session.commit()
        print(f"Fed Funds Rate data saved successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error saving fed funds data: {e}")
    finally:
        session.close()

def get_all_fed_funds_data():
    """Get all Fed Funds Rate data from DB as DataFrame.
    Returns DataFrame with Date index and 'Rate' column (annualized %)."""
    session = SessionLocal()
    try:
        data = session.query(FedFundsRate).order_by(FedFundsRate.date).all()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame([{'Date': d.date, 'Rate': d.rate} for d in data])
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
    except Exception as e:
        print(f"Error getting fed funds data: {e}")
        return pd.DataFrame()
    finally:
        session.close()

