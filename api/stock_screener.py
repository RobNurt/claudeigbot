"""
Stock Screener for ISA Investments
Uses Yahoo Finance to screen UK stocks by fundamental and technical criteria

Place this file in your api/ folder: api/stock_screener.py
"""
import yfinance as yf
from datetime import datetime, timedelta

# FTSE constituent lists - YOU NEED TO UPDATE THESE with actual constituents
# For now, these are just examples to get you started
# Get full lists from: https://www.londonstockexchange.com/indices/

FTSE_100_TICKERS = [
    # Top 20 by market cap (EXAMPLES - update with full list)
    'SHEL.L',   # Shell
    'AZN.L',    # AstraZeneca  
    'HSBA.L',   # HSBC
    'ULVR.L',   # Unilever
    'DGE.L',    # Diageo
    'BP.L',     # BP
    'GSK.L',    # GSK
    'RIO.L',    # Rio Tinto
    'NG.L',     # National Grid
    'LSEG.L',   # London Stock Exchange Group
    'REL.L',    # RELX
    'AAL.L',    # Anglo American
    'BARC.L',   # Barclays
    'VOD.L',    # Vodafone
    'LLOY.L',   # Lloyds Banking Group
    'GLEN.L',   # Glencore
    'BA.L',     # BAE Systems
    'PRU.L',    # Prudential
    'CPG.L',    # Compass Group
    'BATS.L',   # British American Tobacco
    # ... ADD THE REST OF THE FTSE 100 HERE ...
]

FTSE_250_TICKERS = [
    # Top 20 (EXAMPLES - update with full list)
    'WIZZ.L',   # Wizz Air
    'FRES.L',   # Fresnillo
    'IMB.L',    # Imperial Brands
    'SPX.L',    # Spirax-Sarco
    'SMDS.L',   # DS Smith
    'JD.L',     # JD Sports
    'AUTO.L',   # Auto Trader
    'DCC.L',    # DCC
    'RTO.L',    # Rentokil
    'MNG.L',    # M&G
    # ... ADD THE REST OF THE FTSE 250 HERE ...
]

def get_uk_stock_universe(indices):
    """
    Get list of tickers to screen based on selected indices
    
    Args:
        indices: List of index names ["FTSE 100", "FTSE 250", "Small Cap", "AIM"]
    
    Returns:
        List of ticker symbols with .L suffix
    """
    universe = []
    
    if not indices:
        # If no indices selected, scan both FTSE 100 and 250
        universe = FTSE_100_TICKERS + FTSE_250_TICKERS
    else:
        if "FTSE 100" in indices:
            universe.extend(FTSE_100_TICKERS)
        if "FTSE 250" in indices:
            universe.extend(FTSE_250_TICKERS)
        # Small Cap and AIM would need separate lists
        # For now, we'll skip them
    
    # Remove duplicates
    universe = list(set(universe))
    
    return universe


def get_stock_fundamentals(ticker):
    """
    Get fundamental and technical data for a single stock from Yahoo Finance
    
    Returns dict with all the data needed for screening, or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get historical data for technical indicators
        hist = stock.history(period='6mo')
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        
        # Calculate moving averages
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
        ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
        
        # Calculate 3-month price change
        if len(hist) >= 60:  # ~3 months of trading days
            price_3m_ago = hist['Close'].iloc[-60]
            price_change_3m = ((current_price - price_3m_ago) / price_3m_ago) * 100
        else:
            price_change_3m = None
        
        # Get fundamental data
        fundamentals = {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'debt_to_equity': info.get('debtToEquity'),
            'profit_margin': info.get('profitMargins') * 100 if info.get('profitMargins') else None,
            'dividend_yield': info.get('dividendYield') * 100 if info.get('dividendYield') else None,
            'price': current_price,
            'ma_50': ma_50,
            'ma_200': ma_200,
            'price_change_3m': price_change_3m,
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
        }
        
        return fundamentals
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def screen_stocks(filters, log_func=None):
    """
    Screen stocks based on fundamental and technical filters
    
    Args:
        filters: Dict containing filter criteria
        log_func: Optional function to log progress messages
    
    Returns:
        List of stocks that pass all filters
    """
    
    def log(msg):
        if log_func:
            log_func(msg)
        else:
            print(msg)
    
    # Get universe of stocks to scan
    universe = get_uk_stock_universe(filters.get('indices', []))
    
    log(f"Scanning {len(universe)} stocks...")
    log("This may take a few minutes on first run...\n")
    
    results = []
    processed = 0
    
    for ticker in universe:
        processed += 1
        
        # Log progress every 10 stocks
        if processed % 10 == 0:
            log(f"Progress: {processed}/{len(universe)} stocks scanned...")
        
        stock_data = get_stock_fundamentals(ticker)
        
        if not stock_data:
            continue
        
        # Apply fundamental filters
        passes_filters = True
        
        # Market cap filter
        if filters.get('market_cap_min') and stock_data['market_cap']:
            if stock_data['market_cap'] < filters['market_cap_min']:
                passes_filters = False
                continue
        
        if filters.get('market_cap_max') and stock_data['market_cap']:
            if stock_data['market_cap'] > filters['market_cap_max']:
                passes_filters = False
                continue
        
        # P/E ratio filter
        if filters.get('pe_min') and stock_data['pe_ratio']:
            if stock_data['pe_ratio'] < filters['pe_min']:
                passes_filters = False
                continue
        
        if filters.get('pe_max') and stock_data['pe_ratio']:
            if stock_data['pe_ratio'] > filters['pe_max']:
                passes_filters = False
                continue
        
        # Debt/Equity filter
        if filters.get('debt_to_equity_max') and stock_data['debt_to_equity']:
            if stock_data['debt_to_equity'] > filters['debt_to_equity_max']:
                passes_filters = False
                continue
        
        # Profit margin filter
        if filters.get('profit_margin_min') and stock_data['profit_margin']:
            if stock_data['profit_margin'] < filters['profit_margin_min']:
                passes_filters = False
                continue
        
        # Dividend yield filter
        if filters.get('dividend_yield_min') and stock_data['dividend_yield']:
            if stock_data['dividend_yield'] < filters['dividend_yield_min']:
                passes_filters = False
                continue
        
        # Technical filters
        if filters.get('above_ma_50') and stock_data['ma_50']:
            if stock_data['price'] < stock_data['ma_50']:
                passes_filters = False
                continue
        
        if filters.get('above_ma_200') and stock_data['ma_200']:
            if stock_data['price'] < stock_data['ma_200']:
                passes_filters = False
                continue
        
        if filters.get('price_up_3m') and stock_data['price_change_3m']:
            if stock_data['price_change_3m'] < 0:
                passes_filters = False
                continue
        
        # Stock passed all filters!
        if passes_filters:
            results.append(stock_data)
    
    log(f"\nScan complete: Found {len(results)} matching stocks out of {len(universe)} scanned")
    
    # Sort by market cap (largest first)
    results.sort(key=lambda x: x['market_cap'] if x['market_cap'] else 0, reverse=True)
    
    return results


# For testing
if __name__ == "__main__":
    print("Testing stock screener...")
    
    # Test with relaxed filters
    test_filters = {
        'market_cap_min': 100_000_000,  # £100M
        'market_cap_max': 5_000_000_000,  # £5B
        'pe_min': 5,
        'pe_max': 30,
        'debt_to_equity_max': 100,
        'profit_margin_min': 5,
        'above_ma_50': False,
        'above_ma_200': False,
        'price_up_3m': False,
        'indices': ['FTSE 100']  # Just test with FTSE 100 examples
    }
    
    results = screen_stocks(test_filters)
    
    print(f"\nFound {len(results)} stocks:")
    for stock in results[:5]:  # Show top 5
        print(f"- {stock['ticker']}: {stock['name']}, Market Cap: £{stock['market_cap']/1_000_000_000:.1f}B, P/E: {stock['pe_ratio']:.1f if stock['pe_ratio'] else 'N/A'}")