import os
from sqlalchemy import create_engine, Column, Date, String, Float, Integer, BigInteger, inspect, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
        db.rollback()
    finally:
        db.close()

def get_all_stock_data(ticker):
    """Reads all data for a ticker from DB into a Pandas DataFrame."""
    query = f"SELECT * FROM stock_prices WHERE ticker = '{ticker}' ORDER BY date ASC"
    try:
        df = pd.read_sql(query, engine)
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
    try:
        session = SessionLocal()
        last_entry = session.query(InflationData).order_by(InflationData.date.desc()).first()
        session.close()
        return last_entry.date if last_entry else None
    except Exception as e:
        print(f"Error getting latest inflation date: {e}")
        return None

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
    try:
        session = SessionLocal()
        data = session.query(InflationData).order_by(InflationData.date).all()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame([{'Date': d.date, 'CPI': d.cpi} for d in data])
        
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        session.close()
        return df
    except Exception as e:
        print(f"Error getting inflation data: {e}")
        return pd.DataFrame()

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
    try:
        session = SessionLocal()
        last_entry = session.query(MarketStats).order_by(MarketStats.date.desc()).first()
        session.close()
        return last_entry.date if last_entry else None
    except Exception as e:
        print(f"Error getting latest market stats date: {e}")
        return None

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
    try:
        session = SessionLocal()
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
        
        session.close()
        return df
    except Exception as e:
        print(f"Error getting market stats: {e}")
        return pd.DataFrame()
