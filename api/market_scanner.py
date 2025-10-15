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
    
    # Popular markets prioritized for scanning
    PRIORITY_COMMODITIES = [
        'CS.D.USCGC.TODAY.IP',  # Gold
        'CS.D.CFSILVER.TODAY.IP',  # Silver
        'CC.D.CL.USS.IP',  # US Crude Oil
        'CC.D.LCO.USS.IP',  # Brent Crude
        'CS.D.CFDXC.CFD.IP',  # Copper
        'CC.D.NG.USS.IP',  # Natural Gas
        'CS.D.PLATINUM.TODAY.IP',  # Platinum
        'CS.D.PALLADIUM.TODAY.IP',  # Palladium
    ]
    
    PRIORITY_INDICES = [
        'IX.D.SPTRD.DAILY.IP',  # S&P 500
        'IX.D.DOW.DAILY.IP',  # Dow Jones
        'IX.D.NASDAQ.DAILY.IP',  # Nasdaq
        'IX.D.FTSE.DAILY.IP',  # FTSE 100
        'IX.D.DAX.DAILY.IP',  # DAX
        'IX.D.CAC.DAILY.IP',  # CAC 40
        'IX.D.ASX.IFE.IP',  # ASX 200
        'IX.D.HANGSENG.CASH.IP',  # Hang Seng
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
        
        if historical:
            # Store in cache
            self.historical_cache[epic] = {
                'epic': epic,
                'name': name,
                'high': historical['high'],
                'low': historical['low'],
                'source': 'ig_api',
                'resolution': resolution,
                'num_points': num_points,
                'timestamp': datetime.now().isoformat(),
                'age_hours': 0
            }
            self.save_cache()
            
            return {
                'high': historical['high'],
                'low': historical['low'],
                'from_cache': False
            }
        
        return None
    
    def scan_markets_yahoo_only(self, filter_type, timeframe, include_closed, market_limit, log_func):
        """
        Scan using ONLY Yahoo Finance - zero IG API calls!
        Returns markets with historical ranges but no current prices
        """
        from api.market_list import get_popular_markets
        from api.yahoo_finance_helper import get_yahoo_ticker, get_historical_range, get_timeframe_period
        
        markets_list = get_popular_markets(filter_type)
        
        # Sort by priority
        markets_list = sorted(markets_list, 
                            key=lambda m: get_market_priority(m.get('instrumentName', '')))
        
        # Apply limit
        if market_limit and market_limit > 0:
            markets_list = markets_list[:market_limit]
        
        log_func(f"Scanning {len(markets_list)} markets (Yahoo only - zero IG quota)")
        
        scan_results = []
        stats = {'total': len(markets_list), 'yahoo_success': 0, 'yahoo_failed': 0}
        
        period = get_timeframe_period(timeframe)
        
        for idx, market in enumerate(markets_list, 1):
            epic = market.get('epic')
            name = market.get('instrumentName', 'Unknown')
            
            yahoo_ticker = get_yahoo_ticker(epic)
            if not yahoo_ticker:
                log_func(f"  [{idx}/{len(markets_list)}] ⚠️ {name}: No Yahoo ticker")
                stats['yahoo_failed'] += 1
                continue
            
            log_func(f"  [{idx}/{len(markets_list)}] 📊 {name}: {yahoo_ticker}")
            
            yahoo_data = get_historical_range(yahoo_ticker, period)
            
            if yahoo_data:
                scan_results.append({
                    'name': name,
                    'epic': epic,
                    'price': None,  # No current price yet
                    'low': yahoo_data['low'],
                    'high': yahoo_data['high'],
                    'position_pct': None,  # Can't calculate without current price
                    'status': 'UNKNOWN',
                    'is_closed': False,
                    'has_price': False
                })
                stats['yahoo_success'] += 1
            else:
                log_func(f"  ✗ Yahoo failed for {name}")
                stats['yahoo_failed'] += 1
        
        return scan_results, stats

    def update_current_prices(self, scan_results, log_func):
        """
        Update scan results with current prices from IG
        Pass in the scan_results from yahoo_only scan
        """
        updated = 0
        failed = 0
        
        for result in scan_results:
            epic = result['epic']
            name = result['name']
            
            log_func(f"  Getting current price for {name}...")
            
            price_data = self.ig_client.get_market_price(epic)
            
            if price_data and price_data.get('mid'):
                result['price'] = price_data['mid']
                result['status'] = price_data.get('market_status', 'UNKNOWN')
                result['has_price'] = True
                
                # Calculate position
                low = result['low']
                high = result['high']
                price_range = high - low
                
                if price_range > 0:
                    result['position_pct'] = ((result['price'] - low) / price_range) * 100
                else:
                    result['position_pct'] = 50
                
                updated += 1
                log_func(f"  ✓ {name}: {result['price']:.2f} ({result['position_pct']:.1f}%)")
            else:
                failed += 1
                log_func(f"  ✗ Failed to get price for {name}")
            
            time.sleep(0.5)  # Rate limit protection
        
        return updated, failed

    def scan_markets(self, filter_type, timeframe, include_closed, max_markets, log_func):
        """
        Scan markets with intelligent caching
        
        Args:
            filter_type: "Commodities", "Indices", or "All"
            timeframe: "Daily", "Annual", etc.
            include_closed: Include closed markets
            max_markets: Maximum number of markets to scan (None = unlimited)
            log_func: Logging function
        
        Returns: (scan_results, stats)
        stats contains: total, cached, fetched, failed, skipped
        """
        # Get market list - USE HARDCODED LIST (no IG API calls!)
        from api.market_list import get_popular_markets

        markets_list = get_popular_markets(filter_type)
        log_func(f"Using hardcoded list of {len(markets_list)} popular markets (zero IG quota used)")
        
        # Prioritize popular markets
        markets_list = self.prioritize_markets(markets_list)
        
        # Limit if specified
        if max_markets and max_markets > 0:
            markets_list = markets_list[:max_markets]
            log_func(f"Limiting to top {max_markets} markets (by popularity)")
        
        log_func(f"Scanning {len(markets_list)} markets...")
        log_func(f"Scanning with timeframe: {timeframe}")
        
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
                
                # === STEP 1: Get current price (always fetch) ===
                time.sleep(0.5)  # Rate limit protection
                price_data = self.ig_client.get_market_price(epic)
                
                # Check for rate limit
                if price_data is None:
                    log_func(f"  ⚠️ Rate limited at {name} - stopping scan")
                    stats['rate_limited'] += 1
                    break  # Stop entirely if rate limited
                
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
                
                # === STEP 2: Get historical data (cached or fresh) ===
                historical = self.get_historical_data(
                epic, name, resolution, num_points, log_func
                )
                
                if not historical:
                    log_func(f"  ✗ No historical data for {name}")
                    stats['failed'] += 1
                    continue
                
                # Update stats
                if historical['from_cache']:
                    stats['cached'] += 1
                else:
                    stats['fetched'] += 1
                    time.sleep(1.5)  # Extra delay after fetching historical
                
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