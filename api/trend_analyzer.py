"""
Trend Analyzer
Multi-timeframe trend analysis with rally detection for catching breakouts
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time


class TrendAnalyzer:
    """Analyzes market trends across multiple timeframes"""
    
    def __init__(self, cache_duration=300):
        """
        Initialize trend analyzer
        
        Args:
            cache_duration: Cache duration in seconds (default 5 minutes)
        """
        self.cache = {}
        self.cache_duration = cache_duration
        self.cache_timestamps = {}
        
    def analyze_instrument(self, epic, timeframe='1h'):
        """
        Analyze a single instrument on a specific timeframe
        
        Args:
            epic: IG epic code (e.g., 'CS.D.USCGC.TODAY.IP')
            timeframe: '3m', '1h', '4h', or '1d' (Daily)
            
        Returns:
            dict with trend analysis or None if failed
        """
        try:
            # Convert IG epic to Yahoo symbol
            yahoo_symbol = self._epic_to_yahoo(epic)
            if not yahoo_symbol:
                return None
            
            # Get historical data
            data = self._get_cached_data(yahoo_symbol, timeframe)
            if data is None or len(data) < 50:  # Need at least 50 bars for MA50
                return None
            
            # Calculate current price and changes
            current_price = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2] if len(data) >= 2 else current_price
            
            # Calculate percentage changes
            change_1_bar = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # Get price from various periods ago
            price_5_ago = data['Close'].iloc[-6] if len(data) >= 6 else current_price
            price_10_ago = data['Close'].iloc[-11] if len(data) >= 11 else current_price
            price_20_ago = data['Close'].iloc[-21] if len(data) >= 21 else current_price
            
            change_5_bars = ((current_price - price_5_ago) / price_5_ago * 100) if price_5_ago > 0 else 0
            change_10_bars = ((current_price - price_10_ago) / price_10_ago * 100) if price_10_ago > 0 else 0
            change_20_bars = ((current_price - price_20_ago) / price_20_ago * 100) if price_20_ago > 0 else 0
            
            # Calculate indicators
            rsi = self._calculate_rsi(data['Close'])
            macd_line, signal_line, histogram = self._calculate_macd(data['Close'])
            ma20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else None
            ma50 = data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else None
            
            # Volume analysis
            avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else None
            current_volume = data['Volume'].iloc[-1]
            volume_ratio = (current_volume / avg_volume) if avg_volume and avg_volume > 0 else 1.0
            
            # Trend detection
            trend = self._detect_trend(current_price, ma20, ma50)
            
            # Rally detection (for 3m timeframe mainly)
            is_rally = self._detect_rally(
                change_1_bar, 
                change_5_bars, 
                rsi, 
                volume_ratio,
                timeframe
            )
            
            # Momentum score (0-100)
            momentum_score = self._calculate_momentum_score(
                change_1_bar,
                change_5_bars,
                change_10_bars,
                rsi,
                histogram,
                trend,
                volume_ratio
            )
            
            return {
                'epic': epic,
                'yahoo_symbol': yahoo_symbol,
                'timeframe': timeframe,
                'current_price': round(current_price, 2),
                'change_1_bar': round(change_1_bar, 2),
                'change_5_bars': round(change_5_bars, 2),
                'change_10_bars': round(change_10_bars, 2),
                'change_20_bars': round(change_20_bars, 2),
                'rsi': round(rsi, 1) if rsi else None,
                'macd': round(macd_line, 2) if macd_line else None,
                'macd_signal': round(signal_line, 2) if signal_line else None,
                'macd_histogram': round(histogram, 2) if histogram else None,
                'ma20': round(ma20, 2) if ma20 else None,
                'ma50': round(ma50, 2) if ma50 else None,
                'volume_ratio': round(volume_ratio, 2) if volume_ratio else None,
                'trend': trend,
                'is_rally': is_rally,
                'momentum_score': round(momentum_score, 1),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error analyzing {epic}: {e}")
            return None
    
    def _get_cached_data(self, yahoo_symbol, timeframe):
        """Get historical data with caching"""
        cache_key = f"{yahoo_symbol}_{timeframe}"
        
        # Check cache
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.cache_duration:
                return self.cache[cache_key]
        
        # Fetch new data
        try:
            # Map timeframe to yfinance parameters
            interval_map = {
                '5m': ('5m', '5d'),    # 5-minute bars, last 5 days (3m not supported!)
                '1h': ('1h', '1mo'),   # 1-hour bars, last month
                '4h': ('1h', '3mo'),   # Use 1h and resample to 4h, last 3 months
                '1d': ('1d', '1y')     # Daily bars, last year
            }
            
            interval, period = interval_map.get(timeframe, ('1h', '1mo'))
            
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period, interval=interval)
            
            # Resample 1h to 4h if needed
            if timeframe == '4h':
                data = data.resample('4H').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            
            if data is not None and len(data) > 0:
                # Cache it
                self.cache[cache_key] = data
                self.cache_timestamps[cache_key] = time.time()
                return data
            
            return None
            
        except Exception as e:
            print(f"Error fetching data for {yahoo_symbol}: {e}")
            return None
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return None
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
        except:
            return None
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD indicator"""
        try:
            if len(prices) < slow + signal:
                return None, None, None
            
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
        except:
            return None, None, None
    
    def _detect_trend(self, current_price, ma20, ma50):
        """Detect current trend based on moving averages"""
        if ma20 is None or ma50 is None:
            return "UNKNOWN"
        
        if current_price > ma20 > ma50:
            return "STRONG_UPTREND"
        elif current_price > ma20:
            return "UPTREND"
        elif current_price < ma20 < ma50:
            return "STRONG_DOWNTREND"
        elif current_price < ma20:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    
    def _detect_rally(self, change_1_bar, change_5_bars, rsi, volume_ratio, timeframe):
        """
        Detect if there's a rally happening
        
        Rally criteria:
        - For 5m: >0.5% move in last bar OR >1% in last 5 bars
        - Volume spike (>1.5x average)
        - RSI momentum (either oversold bounce or strong momentum)
        """
        if timeframe == '5m':
            # Quick rally detection for 5-minute charts
            strong_move = change_1_bar > 0.5 or change_5_bars > 1.0
            volume_spike = volume_ratio and volume_ratio > 1.5
            
            # RSI conditions
            oversold_bounce = rsi and rsi < 35  # Bouncing from oversold
            strong_momentum = rsi and rsi > 65  # Strong upward momentum
            
            return strong_move and (volume_spike or oversold_bounce or strong_momentum)
        
        else:
            # For longer timeframes, need stronger confirmation
            strong_move = change_5_bars > 2.0
            volume_spike = volume_ratio and volume_ratio > 1.5
            
            return strong_move and volume_spike
    
    def _calculate_momentum_score(self, change_1, change_5, change_10, rsi, macd_hist, trend, volume_ratio):
        """
        Calculate overall momentum score (0-100)
        
        Components:
        - Price momentum (40 points)
        - RSI (20 points)
        - MACD (20 points)
        - Trend alignment (10 points)
        - Volume (10 points)
        """
        score = 0
        
        # Price momentum (40 points max)
        # Weight recent changes more heavily
        price_score = 0
        price_score += min(abs(change_1) * 4, 15)   # Up to 15 points
        price_score += min(abs(change_5) * 2, 15)   # Up to 15 points
        price_score += min(abs(change_10) * 1, 10)  # Up to 10 points
        
        # If price is negative, reduce score
        if change_1 < 0 or change_5 < 0:
            price_score *= 0.5
        
        score += price_score
        
        # RSI (20 points max)
        if rsi:
            if rsi > 70:
                score += 20  # Overbought - strong momentum
            elif rsi > 60:
                score += 15  # Strong
            elif rsi > 50:
                score += 10  # Moderate
            elif rsi > 40:
                score += 5   # Weak
            elif rsi < 30:
                score += 15  # Oversold - potential bounce
        
        # MACD (20 points max)
        if macd_hist:
            if macd_hist > 0:
                score += min(abs(macd_hist) * 10, 20)
            else:
                score -= min(abs(macd_hist) * 5, 10)
        
        # Trend alignment (10 points max)
        if trend == "STRONG_UPTREND":
            score += 10
        elif trend == "UPTREND":
            score += 7
        elif trend == "SIDEWAYS":
            score += 5
        elif trend == "DOWNTREND":
            score += 3
        elif trend == "STRONG_DOWNTREND":
            score += 0
        
        # Volume (10 points max)
        if volume_ratio:
            if volume_ratio > 2.0:
                score += 10
            elif volume_ratio > 1.5:
                score += 7
            elif volume_ratio > 1.0:
                score += 5
            else:
                score += 2
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _epic_to_yahoo(self, epic):
        """
        Convert IG epic to Yahoo Finance symbol
        
        Common conversions:
        - Gold: CS.D.USCGC.TODAY.IP -> GC=F
        - Russell 2000: IX.D.RUSSELL.DAILY.IP -> ^RUT
        - FTSE 100: IX.D.FTSE.DAILY.IP -> ^FTSE
        - S&P 500: IX.D.SPTRD.DAILY.IP -> ^GSPC
        """
        # Map of known IG epics to Yahoo symbols
        epic_map = {
            'CS.D.USCGC.TODAY.IP': 'GC=F',          # Gold
            'CS.D.USCGC.DAILY.IP': 'GC=F',          # Gold Daily
            'IX.D.RUSSELL.DAILY.IP': '^RUT',        # Russell 2000
            'IX.D.FTSE.DAILY.IP': '^FTSE',          # FTSE 100
            'IX.D.SPTRD.DAILY.IP': '^GSPC',         # S&P 500
            'IX.D.DOW.DAILY.IP': '^DJI',            # Dow Jones
            'IX.D.NASDAQ.DAILY.IP': '^IXIC',        # NASDAQ
            'IX.D.DAX.DAILY.IP': '^GDAXI',          # DAX
            'IX.D.NIKKEI.DAILY.IP': '^N225',        # Nikkei
            'CS.D.USCRD.TODAY.IP': 'CL=F',          # Crude Oil
            'CS.D.USSLV.TODAY.IP': 'SI=F',          # Silver
            'CS.D.NGCUSD.TODAY.IP': 'NG=F',         # Natural Gas
        }
        
        # Try direct lookup first
        if epic in epic_map:
            return epic_map[epic]
        
        # If not found, return None (caller will handle)
        return None
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        self.cache_timestamps = {}