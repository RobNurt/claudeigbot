"""
Hardcoded list of popular markets to avoid IG API search quota
"""

POPULAR_MARKETS = {
    'COMMODITIES': [
        {'epic': 'CS.D.USCGC.TODAY.IP', 'instrumentName': 'Spot Gold', 'instrumentType': 'COMMODITIES', 'expiry': 'DFB'},
        {'epic': 'CS.D.USISC.TODAY.IP', 'instrumentName': 'Spot Silver', 'instrumentType': 'COMMODITIES', 'expiry': 'DFB'},
        {'epic': 'CC.D.CL.USS.IP', 'instrumentName': 'Oil - US Crude', 'instrumentType': 'COMMODITIES', 'expiry': '-'},
        {'epic': 'CC.D.LCO.USS.IP', 'instrumentName': 'Oil - Brent Crude', 'instrumentType': 'COMMODITIES', 'expiry': '-'},
        {'epic': 'CC.D.NG.USS.IP', 'instrumentName': 'Natural Gas', 'instrumentType': 'COMMODITIES', 'expiry': '-'},
        {'epic': 'CC.D.HG.USS.IP', 'instrumentName': 'High Grade Copper', 'instrumentType': 'COMMODITIES', 'expiry': '-'},
        {'epic': 'CC.D.PL.USS.IP', 'instrumentName': 'Platinum', 'instrumentType': 'COMMODITIES', 'expiry': '-'},
    ],
    
    'INDICES': [
        {'epic': 'IX.D.SPTRD.DAILY.IP', 'instrumentName': 'US 500', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.RUSSELL.DAILY.IP', 'instrumentName': 'Russell 2000', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.DOW.DAILY.IP', 'instrumentName': 'Wall Street', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.NASDAQ.CASH.IP', 'instrumentName': 'US Tech 100', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.FTSE.DAILY.IP', 'instrumentName': 'FTSE 100', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.DAX.DAILY.IP', 'instrumentName': 'Germany 40', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.CAC.DAILY.IP', 'instrumentName': 'France 40', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
        {'epic': 'IX.D.NIKKEI.DAILY.IP', 'instrumentName': 'Japan 225', 'instrumentType': 'INDICES', 'expiry': 'DFB'},
    ]
}

def get_popular_markets(market_type):
    """Get hardcoded popular markets without hitting IG API"""
    if market_type == 'COMMODITIES':
        return POPULAR_MARKETS['COMMODITIES']
    elif market_type == 'INDICES':
        return POPULAR_MARKETS['INDICES']
    else:  # 'All'
        return POPULAR_MARKETS['COMMODITIES'] + POPULAR_MARKETS['INDICES']