"""
Market List - Hardcoded popular markets to avoid IG API calls
"""

# All Spot Commodities
COMMODITIES = [
    {
        'epic': 'CS.D.USCGC.TODAY.IP',
        'instrumentName': 'Spot Gold',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CS.D.CFSILVER.TODAY.IP',
        'instrumentName': 'Spot Silver',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.CL.USS.IP',
        'instrumentName': 'Oil - US Crude',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.LCO.USS.IP',
        'instrumentName': 'Oil - Brent Crude',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CS.D.CFDXC.CFD.IP',
        'instrumentName': 'Copper',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.NG.USS.IP',
        'instrumentName': 'Natural Gas',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CS.D.PLATINUM.TODAY.IP',
        'instrumentName': 'Platinum',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CS.D.PALLADIUM.TODAY.IP',
        'instrumentName': 'Palladium',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.CC.USS.IP',
        'instrumentName': 'Cocoa',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.SB.USS.IP',
        'instrumentName': 'Sugar',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.CT.USS.IP',
        'instrumentName': 'Cotton',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.KC.USS.IP',
        'instrumentName': 'Coffee',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.W.USS.IP',
        'instrumentName': 'Wheat',
        'instrumentType': 'COMMODITIES'
    },
    {
        'epic': 'CC.D.C.USS.IP',
        'instrumentName': 'Corn',
        'instrumentType': 'COMMODITIES'
    },
]

# Top 20 Indices
INDICES = [
    {
        'epic': 'IX.D.SPTRD.DAILY.IP',
        'instrumentName': 'US 500',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.DOW.DAILY.IP',
        'instrumentName': 'Wall Street',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.NASDAQ.DAILY.IP',
        'instrumentName': 'US Tech 100',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.RUSSELL.DAILY.IP',
        'instrumentName': 'Russell 2000',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.FTSE.DAILY.IP',
        'instrumentName': 'FTSE 100',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.DAX.DAILY.IP',
        'instrumentName': 'Germany 40',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.CAC.DAILY.IP',
        'instrumentName': 'France 40',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.IBEX.DAILY.IP',
        'instrumentName': 'Spain 35',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.MIB.DAILY.IP',
        'instrumentName': 'Italy 40',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.AEX.DAILY.IP',
        'instrumentName': 'Netherlands 25',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.NIKKEI.DAILY.IP',
        'instrumentName': 'Japan 225',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.HANGSENG.CASH.IP',
        'instrumentName': 'Hong Kong HS50',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.ASX.IFE.IP',
        'instrumentName': 'Australia 200',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.INDIA.DAILY.IP',
        'instrumentName': 'India 50',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.SWISSMI.IFE.IP',
        'instrumentName': 'Switzerland 20',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.KOSPI.DAILY.IP',
        'instrumentName': 'Korea 200',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.SINGAPORE.CASH.IP',
        'instrumentName': 'Singapore',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.BRAZIL.CASH.IP',
        'instrumentName': 'Brazil',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.MEXICO.CASH.IP',
        'instrumentName': 'Mexico',
        'instrumentType': 'INDICES'
    },
    {
        'epic': 'IX.D.SPASX.DAILY.IP',
        'instrumentName': 'S&P/ASX 200',
        'instrumentType': 'INDICES'
    },
]

def get_popular_markets(filter_type="All"):
    """
    Get hardcoded list of popular markets
    
    Args:
        filter_type: "All", "Commodities", or "Indices"
    
    Returns:
        List of market dicts with 'epic', 'instrumentName', 'instrumentType'
    """
    if filter_type == "Commodities":
        return COMMODITIES.copy()
    elif filter_type == "Indices":
        return INDICES.copy()
    else:  # "All"
        return COMMODITIES + INDICES

def get_all_epics():
    """Get list of all epic codes"""
    return [m['epic'] for m in get_popular_markets("All")]

def get_market_name(epic):
    """Get instrument name for an epic"""
    for market in get_popular_markets("All"):
        if market['epic'] == epic:
            return market['instrumentName']
    return None

# Test function
if __name__ == "__main__":
    print("=== ALL MARKETS ===")
    all_markets = get_popular_markets("All")
    print(f"Total: {len(all_markets)}")
    
    print("\n=== COMMODITIES ===")
    commodities = get_popular_markets("Commodities")
    print(f"Total: {len(commodities)}")
    for m in commodities:
        print(f"  - {m['instrumentName']} ({m['epic']})")
    
    print("\n=== INDICES ===")
    indices = get_popular_markets("Indices")
    print(f"Total: {len(indices)}")
    for m in indices:
        print(f"  - {m['instrumentName']} ({m['epic']})")