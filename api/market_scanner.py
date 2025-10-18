"""
Market Scanner with Historical Data Caching
Caches historical high/low data for 24 hours
Only fetches current prices on subsequent scans
"""
import time
import json
import os
from datetime import datetime, timedelta

MARKET_PRIORITIES = {
    # Indices (most popular first)
    'US 500': 1,
    'FTSE 100': 2,
    'Germany 40': 3,
    'Wall Street': 4,
    'US Tech 100': 5,
    'Russell 2000': 6,
    'Japan 225': 7,
    'Hong Kong HS50': 8,
    'Australia 200': 9,
    'France 40': 10,
    
    # Commodities (most popular first)
    'Spot Gold': 101,
    'Spot Silver': 102,
    'Oil - US Crude': 103,
    'Oil - Brent Crude': 104,
    'Natural Gas': 105,
    'Copper': 106,
    'Platinum': 107,
    'Palladium': 108,
}

def get_market_priority(market_name):
    """Get priority for a market (lower = higher priority)"""
    for key, priority in MARKET_PRIORITIES.items():
        if key.lower() in market_name.lower():
            return priority
    return 999  # Unknown markets go last

class CachedMarketScanner:
    """Market scanner with intelligent caching to avoid rate limits"""
    
    # EXPANDED: All spot commodities and top 20 indices
    PRIORITY_COMMODITIES = [
        'CS.D.USCGC.TODAY.IP',  # Gold Spot
        'CS.D.CFSILVER.TODAY.IP',  # Silver Spot
        'CC.D.CL.USS.IP',  # US Crude Oil
        'CC.D.LCO.USS.IP',  # Brent Crude Oil
        'CS.D.CFDXC.CFD.IP',  # Copper
        'CC.D.NG.USS.IP',  # Natural Gas
        'CS.D.PLATINUM.TODAY.IP',  # Platinum
        'CS.D.PALLADIUM.TODAY.IP',  # Palladium
        'CC.D.CC.USS.IP',  # Cocoa
        'CC.D.SB.USS.IP',  # Sugar
        'CC.D.CT.USS.IP',  # Cotton
        'CC.D.KC.USS.IP',  # Coffee
        'CC.D.W.USS.IP',  # Wheat
        'CC.D.C.USS.IP',  # Corn
    ]
    
    PRIORITY_INDICES = [
        'IX.D.SPTRD.DAILY.IP',  # S&P 500 (US)
        'IX.D.DOW.DAILY.IP',  # Dow Jones (US)
        'IX.D.NASDAQ.DAILY.IP',  # Nasdaq (US)
        'IX.D.RUSSELL.DAILY.IP',  # Russell 2000 (US)
        'IX.D.FTSE.DAILY.IP',  # FTSE 100 (UK)
        'IX.D.DAX.DAILY.IP',  # DAX (Germany)
        'IX.D.CAC.DAILY.IP',  # CAC 40 (France)
        'IX.D.IBEX.DAILY.IP',  # IBEX 35 (Spain)
        'IX.D.MIB.DAILY.IP',  # FTSE MIB (Italy)
        'IX.D.AEX.DAILY.IP',  # AEX (Netherlands)
        'IX.D.NIKKEI.DAILY.IP',  # Nikkei 225 (Japan)
        'IX.D.HANGSENG.CASH.IP',  # Hang Seng (Hong Kong)
        'IX.D.ASX.IFE.IP',  # ASX 200 (Australia)
        'IX.D.INDIA.DAILY.IP',  # Nifty 50 (India)
        'IX.D.SWISSMI.IFE.IP',  # SMI (Switzerland)
        'IX.D.KOSPI.DAILY.IP',  # KOSPI (South Korea)
        'IX.D.SINGAPORE.CASH.IP',  # STI (Singapore)
        'IX.D.BRAZIL.CASH.IP',  # Bovespa (Brazil)
        'IX.D.MEXICO.CASH.IP',  # IPC (Mexico)
        'IX.D.SPASX.DAILY.IP',  # S&P/ASX 200 (Australia)
    ]
    
    def __init__(self, ig_client):
        self.ig_client = ig_client
        self.cache_file = "market_scanner_cache.json"
        self.cache_duration_hours = 24
        self.historical_cache = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cached historical data from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.historical_cache = json.load(f)
                print(f"Loaded {len(self.historical_cache)} cached markets")
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.historical_cache = {}
    
    def save_cache(self):
        """Save historical data cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.historical_cache, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def is_cache_valid(self, epic):
        """Check if cached data for this epic is still valid"""
        if epic not in self.historical_cache:
            return False
        
        cached_time = datetime.fromisoformat(self.historical_cache[epic]['timestamp'])
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        
        return age_hours < self.cache_duration_hours
    
    def prioritize_markets(self, markets_list):
        """Sort markets by priority - popular ones first"""
        priority_epics = set(self.PRIORITY_COMMODITIES + self.PRIORITY_INDICES)
        
        # Split into priority and non-priority
        priority_markets = [m for m in markets_list if m.get('epic') in priority_epics]
        other_markets = [m for m in markets_list if m.get('epic') not in priority_epics]
        
        # Return priority first
        return priority_markets + other_markets
    
    def get_historical_data(self, epic, name, timeframe, log_func):
        """Get historical data - Yahoo Finance first, then IG API, then cache"""
        
        # Check cache first
        if self.is_cache_valid(epic):
            cached = self.historical_cache[epic]
            age_hours = cached.get('age_hours', 0)
            source = cached.get('source', 'unknown')
            log_func(f"  ✓ Using cached data for {name} ({age_hours:.1f}h old, source: {source})")
            return {
                'high': cached['high'],
                'low': cached['low'],
                'from_cache': True
            }
        
        # Try Yahoo Finance first (FREE! No API quota!)
        from api.yahoo_finance_helper import get_yahoo_ticker, get_historical_range, get_timeframe_period
        
        yahoo_ticker = get_yahoo_ticker(epic)
        if yahoo_ticker:
            log_func(f"  📊 Fetching from Yahoo Finance: {yahoo_ticker}")
            
            period = get_timeframe_period(timeframe)
            yahoo_data = get_historical_range(yahoo_ticker, period)
            
            if yahoo_data:
                # Cache it
                self.historical_cache[epic] = {
                    'epic': epic,
                    'name': name,
                    'high': yahoo_data['high'],
                    'low': yahoo_data['low'],
                    'source': 'yahoo',
                    'num_candles': yahoo_data['num_candles'],
                    'timestamp': datetime.now().isoformat(),
                    'age_hours': 0
                }
                self.save_cache()
                
                log_func(f"  ✓ Yahoo data: High={yahoo_data['high']:.2f}, Low={yahoo_data['low']:.2f}")
                
                return {
                    'high': yahoo_data['high'],
                    'low': yahoo_data['low'],
                    'from_cache': False
                }
            else:
                log_func(f"  ⚠️ Yahoo Finance failed for {yahoo_ticker}, trying IG API...")
        else:
            log_func(f"  ⚠️ No Yahoo ticker for {epic}, using IG API...")
        
        # Fallback to IG API (uses quota)
        # ... existing IG API code would go here if needed ...
        
        return None
    
    def get_yahoo_current_price(self, epic, log_func):
        """Get current price from Yahoo Finance (latest close)"""
        from api.yahoo_finance_helper import get_yahoo_ticker, get_current_price
        
        yahoo_ticker = get_yahoo_ticker(epic)
        if not yahoo_ticker:
            return None
        
        try:
            current_price = get_current_price(yahoo_ticker)
            return current_price
        except Exception as e:
            log_func(f"  ⚠️ Yahoo price error: {str(e)}")
            return None

    def scan_markets(self, filter_type, timeframe, include_closed, max_markets, log_func, data_source="IG + Yahoo"):
        """
        Scan markets with intelligent caching and configurable data source
        
        Args:
            filter_type: "Commodities", "Indices", or "All"
            timeframe: "Daily", "Annual", etc.
            include_closed: Include closed markets
            max_markets: Maximum number of markets to scan (None = unlimited)
            log_func: Logging function
            data_source: "Yahoo Only", "IG + Yahoo", or "IG Only"
        
        Returns: (scan_results, stats)
        """
        
        # === MODE 1: YAHOO ONLY (ZERO IG API CALLS) ===
        if data_source == "Yahoo Only":
            return self.scan_markets_yahoo_only(filter_type, timeframe, include_closed, max_markets, log_func)
        
        # === MODE 2 & 3: IG + Yahoo or IG Only ===
        from api.market_list import get_popular_markets

        markets_list = get_popular_markets(filter_type)
        log_func(f"Using hardcoded list of {len(markets_list)} popular markets")
        
        # Prioritize popular markets
        markets_list = self.prioritize_markets(markets_list)
        
        # Limit if specified
        if max_markets and max_markets > 0:
            markets_list = markets_list[:max_markets]
            log_func(f"Limiting to top {max_markets} markets")
        
        log_func(f"Scanning {len(markets_list)} markets with {data_source}...")
        
        # Stats
        stats = {
            'total': len(markets_list),
            'cached': 0,
            'fetched': 0,
            'failed': 0,
            'skipped': 0,
            'rate_limited': 0
        }
        
        scan_results = []
        
        for idx, market in enumerate(markets_list, 1):
            try:
                epic = market.get('epic')
                name = market.get('instrumentName', 'Unknown')
                
                # === STEP 1: Get current price ===
                time.sleep(0.5)  # Rate limit protection
                price_data = self.ig_client.get_market_price(epic)
                
                # Check for rate limit
                if price_data is None:
                    log_func(f"  ⚠️ Rate limited at {name} - stopping scan")
                    stats['rate_limited'] += 1
                    break
                
                if not price_data.get('mid'):
                    log_func(f"  ✗ Skipping {name} (no price data)")
                    stats['skipped'] += 1
                    continue
                
                current_price = price_data['mid']
                market_status = price_data.get('market_status', 'UNKNOWN')
                is_closed = market_status not in ['TRADEABLE', 'EDITS_ONLY']
                
                if is_closed and not include_closed:
                    stats['skipped'] += 1
                    continue
                
                # === STEP 2: Get historical data ===
                if data_source == "IG Only":
                    # Use IG API for historical (not implemented - would need IG historical endpoint)
                    log_func(f"  ⚠️ IG Only mode not fully implemented, using cache")
                    historical = self.get_historical_data(epic, name, timeframe, log_func)
                else:
                    # Default: IG + Yahoo (Yahoo for historical)
                    historical = self.get_historical_data(epic, name, timeframe, log_func)

                if not historical:
                    log_func(f"  ✗ No historical data for {name}")
                    stats['failed'] += 1
                    continue
                
                # Update stats
                if historical['from_cache']:
                    stats['cached'] += 1
                else:
                    stats['fetched'] += 1
                    time.sleep(1.5)  # Extra delay after fetching
                
                # Calculate position in range
                period_low = historical['low']
                period_high = historical['high']
                price_range = period_high - period_low
                position_pct = ((current_price - period_low) / price_range) * 100 if price_range > 0 else 50
                
                scan_results.append({
                    'name': name,
                    'epic': epic,
                    'price': current_price,
                    'low': period_low,
                    'high': period_high,
                    'position_pct': position_pct,
                    'status': market_status,
                    'is_closed': is_closed,
                    'cached': historical['from_cache']
                })
                
                cache_status = "(cached)" if historical['from_cache'] else "(fresh)"
                log_func(f"  [{idx}/{stats['total']}] ✓ {name}: {position_pct:.1f}% {cache_status}")
                
            except Exception as e:
                log_func(f"  Error scanning {name}: {str(e)}")
                stats['failed'] += 1
                continue
        
        return scan_results, stats
    
    def scan_markets_yahoo_only(self, filter_type, timeframe, include_closed, market_limit, log_func):
        """
        Scan using ONLY Yahoo Finance - ZERO IG API calls!
        Uses Yahoo for both historical ranges AND current prices
        """
        from api.market_list import get_popular_markets
        from api.yahoo_finance_helper import get_yahoo_ticker, get_historical_range, get_timeframe_period, get_current_price
        
        markets_list = get_popular_markets(filter_type)
        
        # Sort by priority
        markets_list = sorted(markets_list, 
                            key=lambda m: get_market_priority(m.get('instrumentName', '')))
        
        # Apply limit
        if market_limit and market_limit > 0:
            markets_list = markets_list[:market_limit]
            log_func(f"Limiting to {market_limit} markets")
        
        log_func(f"🌟 Yahoo Only Mode: Scanning {len(markets_list)} markets (ZERO IG quota used)")
        
        scan_results = []
        stats = {'total': len(markets_list), 'success': 0, 'failed': 0, 'cached': 0}
        
        period = get_timeframe_period(timeframe)
        
        for idx, market in enumerate(markets_list, 1):
            epic = market.get('epic')
            name = market.get('instrumentName', 'Unknown')
            
            yahoo_ticker = get_yahoo_ticker(epic)
            if not yahoo_ticker:
                log_func(f"  [{idx}/{len(markets_list)}] ⚠️ {name}: No Yahoo ticker")
                stats['failed'] += 1
                continue
            
            try:
                # Check cache first
                if self.is_cache_valid(epic):
                    cached = self.historical_cache[epic]
                    period_high = cached['high']
                    period_low = cached['low']
                    log_func(f"  [{idx}/{len(markets_list)}] 💾 {name}: Using cache")
                    stats['cached'] += 1
                else:
                    # Fetch historical from Yahoo
                    yahoo_data = get_historical_range(yahoo_ticker, period)
                    
                    if not yahoo_data:
                        log_func(f"  [{idx}/{len(markets_list)}] ✗ {name}: Yahoo historical failed")
                        stats['failed'] += 1
                        continue
                    
                    period_high = yahoo_data['high']
                    period_low = yahoo_data['low']
                    
                    # Cache it
                    self.historical_cache[epic] = {
                        'epic': epic,
                        'name': name,
                        'high': period_high,
                        'low': period_low,
                        'source': 'yahoo',
                        'timestamp': datetime.now().isoformat(),
                        'age_hours': 0
                    }
                    self.save_cache()
                
                # Get current price from Yahoo
                current_price = get_current_price(yahoo_ticker)
                
                if current_price is None:
                    log_func(f"  [{idx}/{len(markets_list)}] ✗ {name}: No current price")
                    stats['failed'] += 1
                    continue
                
                # Calculate position
                price_range = period_high - period_low
                position_pct = ((current_price - period_low) / price_range) * 100 if price_range > 0 else 50
                
                scan_results.append({
                    'name': name,
                    'epic': epic,
                    'price': current_price,
                    'low': period_low,
                    'high': period_high,
                    'position_pct': position_pct,
                    'status': 'YAHOO',
                    'is_closed': False,  # Yahoo doesn't provide market status
                    'has_price': True
                })
                
                stats['success'] += 1
                log_func(f"  [{idx}/{len(markets_list)}] ✓ {name}: {position_pct:.1f}%")
                
            except Exception as e:
                log_func(f"  [{idx}/{len(markets_list)}] ✗ {name}: {str(e)}")
                stats['failed'] += 1
                continue
        
        log_func(f"✓ Yahoo scan complete: {stats['success']} success, {stats['failed']} failed, {stats['cached']} cached")
        return scan_results, stats
    
    def get_cache_summary(self):
        """Get summary of cached data"""
        if not self.historical_cache:
            return "No cached data"
        
        now = datetime.now()
        valid_count = 0
        expired_count = 0
        
        for epic, data in self.historical_cache.items():
            cached_time = datetime.fromisoformat(data['timestamp'])
            age_hours = (now - cached_time).total_seconds() / 3600
            
            # Update age in cache
            data['age_hours'] = age_hours
            
            if age_hours < self.cache_duration_hours:
                valid_count += 1
            else:
                expired_count += 1
        
        return f"{valid_count} valid, {expired_count} expired (of {len(self.historical_cache)} total)"
    
    def clear_expired_cache(self):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired = []
        
        for epic, data in self.historical_cache.items():
            cached_time = datetime.fromisoformat(data['timestamp'])
            age_hours = (now - cached_time).total_seconds() / 3600
            
            if age_hours >= self.cache_duration_hours:
                expired.append(epic)
        
        for epic in expired:
            del self.historical_cache[epic]
        
        if expired:
            self.save_cache()
        
        return len(expired)
    
    def clear_all_cache(self):
        """Clear all cached data"""
        self.historical_cache = {}
        self.save_cache()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)