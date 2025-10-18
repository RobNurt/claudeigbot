"""
Yahoo Finance Helper
Maps IG epics to Yahoo tickers and fetches historical data
"""
import yfinance as yf
from datetime import datetime, timedelta

# Mapping of IG epics to Yahoo Finance tickers
EPIC_TO_YAHOO = {
    # Commodities
    'CS.D.USCGC.TODAY.IP': 'GC=F',  # Gold Futures
    'CS.D.CFSILVER.TODAY.IP': 'SI=F',  # Silver Futures
    'CC.D.CL.USS.IP': 'CL=F',  # Crude Oil WTI Futures
    'CC.D.LCO.USS.IP': 'BZ=F',  # Brent Crude Futures
    'CS.D.CFDXC.CFD.IP': 'HG=F',  # Copper Futures
    'CC.D.NG.USS.IP': 'NG=F',  # Natural Gas Futures
    'CS.D.PLATINUM.TODAY.IP': 'PL=F',  # Platinum Futures
    'CS.D.PALLADIUM.TODAY.IP': 'PA=F',  # Palladium Futures
    
    # More commodities
    'CC.D.CC.USS.IP': 'CC=F',  # Cocoa Futures
    'CC.D.SB.USS.IP': 'SB=F',  # Sugar Futures
    'CC.D.CT.USS.IP': 'CT=F',  # Cotton Futures
    'CC.D.KC.USS.IP': 'KC=F',  # Coffee Futures
    'CC.D.W.USS.IP': 'ZW=F',  # Wheat Futures
    'CC.D.C.USS.IP': 'ZC=F',  # Corn Futures
    
    # Major Indices
    'IX.D.SPTRD.DAILY.IP': '^GSPC',  # S&P 500
    'IX.D.DOW.DAILY.IP': '^DJI',  # Dow Jones
    'IX.D.NASDAQ.DAILY.IP': '^IXIC',  # Nasdaq Composite
    'IX.D.RUSSELL.DAILY.IP': '^RUT',  # Russell 2000
    'IX.D.FTSE.DAILY.IP': '^FTSE',  # FTSE 100
    'IX.D.DAX.DAILY.IP': '^GDAXI',  # DAX
    'IX.D.CAC.DAILY.IP': '^FCHI',  # CAC 40
    'IX.D.NIKKEI.DAILY.IP': '^N225',  # Nikkei 225
    'IX.D.HANGSENG.CASH.IP': '^HSI',  # Hang Seng
    'IX.D.ASX.IFE.IP': '^AXJO',  # ASX 200
    
    # More indices
    'IX.D.IBEX.DAILY.IP': '^IBEX',  # IBEX 35
    'IX.D.MIB.DAILY.IP': 'FTSEMIB.MI',  # FTSE MIB
    'IX.D.AEX.DAILY.IP': '^AEX',  # AEX
    'IX.D.SWISSMI.IFE.IP': '^SSMI',  # Swiss Market Index
    'IX.D.KOSPI.DAILY.IP': '^KS11',  # KOSPI
    'IX.D.SINGAPORE.CASH.IP': '^STI',  # Straits Times Index
    'IX.D.BRAZIL.CASH.IP': '^BVSP',  # Bovespa
    'IX.D.MEXICO.CASH.IP': '^MXX',  # IPC Mexico
}

def get_yahoo_ticker(epic):
    """Convert IG epic to Yahoo Finance ticker"""
    return EPIC_TO_YAHOO.get(epic)

def get_timeframe_period(timeframe):
    """Convert timeframe string to yfinance period"""
    period_map = {
        "Daily": "1d",
        "Weekly": "5d",
        "Monthly": "1mo",
        "Quarterly": "3mo",
        "6-Month": "6mo",
        "Annual": "1y",
        "2-Year": "2y",
        "5-Year": "5y",
        "All-Time": "max"
    }
    return period_map.get(timeframe, "1y")

def get_historical_range(ticker, period="1y"):
    """
    Get high and low for a period from Yahoo Finance
    
    Args:
        ticker: Yahoo Finance ticker symbol
        period: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
    
    Returns:
        dict with 'high', 'low', 'num_candles' or None
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            print(f"No data for {ticker} (period: {period})")
            return None
        
        return {
            'high': float(hist['High'].max()),
            'low': float(hist['Low'].min()),
            'num_candles': len(hist)
        }
    except Exception as e:
        print(f"Yahoo Finance error for {ticker}: {str(e)}")
        return None

def get_current_price(ticker):
    """
    Get current/latest price from Yahoo Finance
    
    Args:
        ticker: Yahoo Finance ticker symbol
    
    Returns:
        float: Current price or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Try to get real-time price first
        info = stock.info
        
        # Try different price fields (Yahoo API varies)
        price = (info.get('regularMarketPrice') or 
                info.get('currentPrice') or 
                info.get('previousClose'))
        
        if price:
            return float(price)
        
        # Fallback: get latest close from history
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        
        return None
        
    except Exception as e:
        print(f"Yahoo current price error for {ticker}: {str(e)}")
        return None

def test_yahoo_data(epic):
    """Test function to verify Yahoo data for an epic"""
    ticker = get_yahoo_ticker(epic)
    if not ticker:
        print(f"No Yahoo ticker for {epic}")
        return
    
    print(f"\nTesting {epic} -> {ticker}")
    
    # Get historical
    data = get_historical_range(ticker, "1y")
    if data:
        print(f"✓ Annual High: {data['high']:.2f}")
        print(f"✓ Annual Low: {data['low']:.2f}")
        print(f"✓ Candles: {data['num_candles']}")
    else:
        print("✗ No historical data")
    
    # Get current
    current = get_current_price(ticker)
    if current:
        print(f"✓ Current Price: {current:.2f}")
    else:
        print("✗ No current price")

if __name__ == "__main__":
    # Test with gold
    test_yahoo_data('CS.D.USCGC.TODAY.IP')
    test_yahoo_data('IX.D.SPTRD.DAILY.IP')
    test_yahoo_data('IX.D.RUSSELL.DAILY.IP')