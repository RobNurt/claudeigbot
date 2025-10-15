"""
Yahoo Finance Helper
Fetches historical data from Yahoo Finance to avoid IG API quota
"""
import yfinance as yf
from datetime import datetime

# Map IG instruments to Yahoo tickers
IG_TO_YAHOO_TICKER = {
    # ===== COMMODITIES =====
    # Gold & Precious Metals
    'CS.D.USCGC.TODAY.IP': 'GC=F',        # Gold Spot
    'CS.D.USISC.TODAY.IP': 'SI=F',        # Silver Spot
    'CC.D.PL.USS.IP': 'PL=F',             # Platinum
    'CC.D.PA.USS.IP': 'PA=F',             # Palladium
    
    # Oil & Energy
    'CC.D.CL.USS.IP': 'CL=F',             # Oil - US Crude (WTI)
    'CC.D.LCO.USS.IP': 'BZ=F',            # Oil - Brent Crude
    'CC.D.NG.USS.IP': 'NG=F',             # Natural Gas
    'CC.D.HO.USS.IP': 'HO=F',             # Heating Oil
    'CC.D.RB.USS.IP': 'RB=F',             # Gasoline
    
    # Base Metals
    'CC.D.HG.USS.IP': 'HG=F',             # Copper (High Grade)
    
    # Agriculture
    'CC.D.ZW.USS.IP': 'ZW=F',             # Wheat
    'CC.D.ZC.USS.IP': 'ZC=F',             # Corn
    'CC.D.ZS.USS.IP': 'ZS=F',             # Soybeans
    'CC.D.SB.USS.IP': 'SB=F',             # Sugar
    'CC.D.KC.USS.IP': 'KC=F',             # Coffee
    'CC.D.CT.USS.IP': 'CT=F',             # Cotton
    'CC.D.CC.USS.IP': 'CC=F',             # Cocoa
    
    # ===== US INDICES =====
    'IX.D.SPTRD.DAILY.IP': '^GSPC',       # S&P 500
    'IX.D.DOW.DAILY.IP': '^DJI',          # Dow Jones
    'IX.D.NASDAQ.CASH.IP': '^IXIC',       # NASDAQ
    'IX.D.NASDAQ.IFE.IP': '^IXIC',        # NASDAQ (alternative epic)
    'IX.D.RUSSELL.DAILY.IP': '^RUT',      # Russell 2000
    'IX.D.SPMIB.DAILY.IP': '^VIX',        # VIX (if this is VIX)
    
    # ===== UK INDICES =====
    'IX.D.FTSE.DAILY.IP': '^FTSE',        # FTSE 100
    'IX.D.FTSE.CASH.IP': '^FTSE',         # FTSE 100 (cash)
    'IX.D.FTSE.MONTH1.IP': '^FTSE',       # FTSE 100 (futures)
    
    # ===== EUROPE INDICES =====
    'IX.D.DAX.DAILY.IP': '^GDAXI',        # Germany 40 (DAX)
    'IX.D.DAX.CASH.IP': '^GDAXI',         # DAX (cash)
    'IX.D.CAC.DAILY.IP': '^FCHI',         # France 40 (CAC)
    'IX.D.STXE.CASH.IP': '^STOXX50E',     # Euro Stoxx 50
    'IX.D.IBEX.DAILY.IP': '^IBEX',        # Spain 35 (IBEX)
    'IX.D.AEX.DAILY.IP': '^AEX',          # Netherlands 25 (AEX)
    'IX.D.SMI.DAILY.IP': '^SSMI',         # Switzerland 20 (SMI)
    
    # ===== ASIA INDICES =====
    'IX.D.NIKKEI.DAILY.IP': '^N225',      # Japan 225 (Nikkei)
    'IX.D.HANGSENG.DAILY.IP': '^HSI',     # Hong Kong (Hang Seng)
    'IX.D.ASX.DAILY.IP': '^AXJO',         # Australia 200
    'IX.D.XINHUA.DFB.IP': '000001.SS',    # China A50
    'IX.D.KOSPI.DAILY.IP': '^KS11',       # South Korea (KOSPI)
    
    # ===== BONDS (via bond ETFs - Yahoo doesn't have futures for all) =====
    # Note: These are ETF approximations, not exact
    'IX.D.TREASURY.2YR.IP': '^IRX',       # US 2-Year (via 13-week T-bill)
    'IX.D.TREASURY.10YR.IP': '^TNX',      # US 10-Year Treasury
    'IX.D.TREASURY.30YR.IP': '^TYX',      # US 30-Year Treasury
}

def get_yahoo_ticker(ig_epic):
    """
    Convert IG epic to Yahoo Finance ticker
    
    Args:
        ig_epic: IG instrument epic code
        
    Returns:
        Yahoo Finance ticker string or None if not mapped
    """
    return IG_TO_YAHOO_TICKER.get(ig_epic)

def get_historical_range(ticker, period='1y'):
    """
    Get high/low range from Yahoo Finance
    
    Args:
        ticker: Yahoo Finance ticker (e.g., 'GC=F' for Gold)
        period: Time period - '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
        
    Returns:
        dict with 'high', 'low', 'num_candles' or None if failed
    """
    try:
        print(f"DEBUG Yahoo: Fetching {ticker} for period {period}")
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            print(f"DEBUG Yahoo: No data returned for {ticker}")
            return None
        
        high = hist['High'].max()
        low = hist['Low'].min()
        num_candles = len(hist)
        
        print(f"DEBUG Yahoo: {ticker} - High={high:.2f}, Low={low:.2f}, Candles={num_candles}")
        
        return {
            'high': float(high),
            'low': float(low),
            'num_candles': num_candles
        }
        
    except Exception as e:
        print(f"DEBUG Yahoo: Error fetching {ticker}: {e}")
        return None

def get_timeframe_period(timeframe):
    """
    Convert scanner timeframe to Yahoo Finance period
    
    Args:
        timeframe: Scanner timeframe string
        
    Returns:
        Yahoo period string
    """
    mapping = {
        'Daily': '1d',
        'Weekly': '5d',
        'Monthly': '1mo',
        'Quarterly': '3mo',
        '6-Month': '6mo',
        'Annual': '1y',
        '2-Year': '2y',
        '5-Year': '5y',
        'All-Time': 'max'
    }
    return mapping.get(timeframe, '1y')

def test_ticker(ig_epic):
    """Test if we can fetch data for an IG epic via Yahoo"""
    ticker = get_yahoo_ticker(ig_epic)
    if not ticker:
        print(f"No Yahoo ticker mapping for {ig_epic}")
        return False
    
    print(f"Testing {ig_epic} -> {ticker}")
    data = get_historical_range(ticker, '1mo')
    
    if data:
        print(f"  ✓ Success! High={data['high']:.2f}, Low={data['low']:.2f}")
        return True
    else:
        print(f"  ✗ Failed to fetch data")
        return False

# Test when run directly
if __name__ == "__main__":
    print("Testing Yahoo Finance integration...\n")
    
    test_instruments = [
        ('CS.D.USCGC.TODAY.IP', 'Gold Spot'),
        ('IX.D.RUSSELL.DAILY.IP', 'Russell 2000'),
        ('CC.D.CL.USS.IP', 'Oil - US Crude'),
        ('IX.D.SPTRD.DAILY.IP', 'S&P 500'),
    ]
    
    for epic, name in test_instruments:
        print(f"\n{name}:")
        test_ticker(epic)