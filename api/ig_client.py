"""
IG API Client
Handles all communication with IG Markets REST API
"""
import requests
import time

class IGClient:
    """Client for interacting with IG Markets API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = ""
        self.logged_in = False
        self.emergency_stop = False
    
    def trigger_emergency_stop(self):
        """Trigger emergency stop - halts all trading operations"""
        self.emergency_stop = True
    
    def reset_emergency_stop(self):
        """Reset emergency stop flag"""
        self.emergency_stop = False
    
    def connect(self, username, password, api_key, base_url):
        """Connect to IG API and create session"""
        try:
            self.base_url = base_url
            
            login_data = {
                "identifier": username,
                "password": password
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-IG-API-KEY": api_key,
                "Version": "2"
            }
            
            response = self.session.post(f"{self.base_url}/session",
                                       json=login_data, headers=headers)
            
            if response.status_code == 200:
                self.session.headers.update({
                    "CST": response.headers.get("CST"),
                    "X-SECURITY-TOKEN": response.headers.get("X-SECURITY-TOKEN"),
                    "X-IG-API-KEY": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
                
                self.logged_in = True
                return True, "Connected successfully"
            else:
                return False, f"Login failed: {response.text}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def disconnect(self):
        """Disconnect from IG API"""
        self.logged_in = False
        self.session = requests.Session()
        self.base_url = ""

    def update_working_order(self, deal_id, new_level, stop_distance=None, guaranteed_stop=False):
            """Update the level of a working order, preserving stop loss if provided"""
            try:
                url = f"{self.base_url}/workingorders/otc/{deal_id}"
                
                update_data = {
                    "level": str(new_level),
                    "type": "STOP",
                    "timeInForce": "GOOD_TILL_CANCELLED"
                }
                
                # Preserve stop loss if specified
                if stop_distance is not None and stop_distance > 0:
                    update_data["stopDistance"] = str(stop_distance)
                    update_data["guaranteedStop"] = "true" if guaranteed_stop else "false"
                
                headers = self.session.headers.copy()
                headers["version"] = "2"
                headers["_method"] = "PUT"
                
                response = self.session.post(url, json=update_data, headers=headers)
                
                if response.status_code == 200:
                    deal_ref = response.json().get('dealReference')
                    if deal_ref:
                        deal_status = self.check_deal_status(deal_ref)
                        if deal_status.get('dealStatus') == 'ACCEPTED':
                            return True, "Order updated"
                        else:
                            return False, deal_status.get('reason')
                else:
                    return False, response.text
                    
            except Exception as e:
                return False, str(e)
            
    def get_market_price(self, epic):
        """Get current market price for an epic"""
        try:
            url = f"{self.base_url}/markets/{epic}"
            
            # Add proper headers with version
            headers = self.session.headers.copy()
            headers['Version'] = '3'
            
            print(f"DEBUG get_market_price: Fetching {url}")
            print(f"DEBUG get_market_price: Headers = {headers}")
            
            response = self.session.get(url, headers=headers)
            
            print(f"DEBUG get_market_price: Status = {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG get_market_price: Response keys = {data.keys()}")
                
                snapshot = data.get('snapshot', {})
                bid = snapshot.get('bid')
                offer = snapshot.get('offer')
                mid = (bid + offer) / 2 if bid and offer else None
                
                result = {
                    'bid': bid,
                    'offer': offer,
                    'mid': mid,
                    'market_status': snapshot.get('marketStatus')
                }
                
                print(f"DEBUG get_market_price: Result = {result}")
                return result
            else:
                print(f"DEBUG get_market_price: Error - {response.status_code}: {response.text}")
                return None
            
        except Exception as e:
            print(f"DEBUG get_market_price: Exception - {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
        
    def place_order(self, epic, direction, size, level, order_type="STOP", stop_distance=0, guaranteed_stop=False, limit_distance=0):
        """Place a single working order with optional stop loss and limit"""
        url = f"{self.base_url}/workingorders/otc"
        
        # Determine expiry based on epic
        if epic.startswith("IX.D") or epic == "CS.D.USCGC.TODAY.IP":
            expiry = "DFB"
        else:
            expiry = "-"
        
        order_data = {
            "epic": epic,
            "expiry": expiry,
            "direction": direction,
            "size": str(size),
            "level": str(level),
            "type": order_type,
            "timeInForce": "GOOD_TILL_CANCELLED",
            "goodTillDate": None,
            "guaranteedStop": "true" if guaranteed_stop else "false",
            "currencyCode": "GBP"
        }
        
        # Add stop loss if specified
        if stop_distance > 0:
            order_data["stopDistance"] = str(stop_distance)
        
        # Add limit if specified
        if limit_distance > 0:
            order_data["limitDistance"] = str(limit_distance)
            print(f"DEBUG: Adding limitDistance={limit_distance} to order")  # ADD THIS
        
        print(f"DEBUG: Order data being sent: {order_data}")  # ADD THIS
        
        headers = self.session.headers.copy()
        headers["version"] = "2"
        
        response = self.session.post(url, json=order_data, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")  # ADD THIS
        print(f"DEBUG: Response body: {response.text}")  # ADD THIS
        return response
    
    def check_deal_status(self, deal_reference):
        """Check the status of a placed deal"""
        try:
            url = f"{self.base_url}/confirms/{deal_reference}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status check failed: {response.text}"}
                
        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}
    
    def update_position_stop(self, deal_id, stop_level):
        """Update stop level on an open position"""
        try:
            url = f"{self.base_url}/positions/otc/{deal_id}"
            
            update_data = {
                "stopLevel": str(stop_level)
            }
            
            headers = self.session.headers.copy()
            headers["version"] = "2"
            headers["_method"] = "PUT"
            
            response = self.session.post(url, json=update_data, headers=headers)
            
            if response.status_code == 200:
                deal_ref = response.json().get('dealReference')
                if deal_ref:
                    deal_status = self.check_deal_status(deal_ref)
                    if deal_status.get('dealStatus') == 'ACCEPTED':
                        return True, f"Stop updated to {stop_level}"
                    else:
                        return False, f"Update rejected: {deal_status.get('reason')}"
            else:
                return False, f"Update failed: {response.text}"
                
        except Exception as e:
            return False, f"Update error: {str(e)}"
        
    def update_position_stops(self, deal_id, stop_level=None, stop_distance=None, 
        trailing_stop=False, trailing_distance=None, trailing_step=None,
        limit_level=None, limit_distance=None):
        """
        Update stops/limits on an open position
        
        Args:
            deal_id: Position deal ID
            stop_level: Absolute stop level (use either this OR stop_distance)
            stop_distance: Stop distance from current price
            trailing_stop: Enable trailing stop (requires trailing_distance and trailing_step)
            trailing_distance: Distance for trailing stop
            trailing_step: Step distance for trailing stop
            limit_level: Absolute limit level
            limit_distance: Limit distance from current price
        
        Returns:
            (success, message)
        """
        try:
            url = f"{self.base_url}/positions/otc/{deal_id}"
            
            print(f"DEBUG update_position_stops: deal_id={deal_id}")
            print(f"DEBUG: stop_level={stop_level}, stop_distance={stop_distance}")
            print(f"DEBUG: trailing_stop={trailing_stop}, trailing_distance={trailing_distance}, trailing_step={trailing_step}")
            
            update_data = {}
            
            # Stop configuration
            if stop_level is not None:
                update_data["stopLevel"] = str(stop_level)
            elif stop_distance is not None:
                update_data["stopDistance"] = str(stop_distance)
            
            # Trailing stop configuration
            if trailing_stop and trailing_distance is not None and trailing_step is not None:
                update_data["trailingStop"] = True
                update_data["trailingStopDistance"] = str(trailing_distance)
                update_data["trailingStopIncrement"] = str(trailing_step)
            else:
                update_data["trailingStop"] = False
            
            # Limit configuration
            if limit_level is not None:
                update_data["limitLevel"] = str(limit_level)
            elif limit_distance is not None:
                update_data["limitDistance"] = str(limit_distance)
            
            print(f"DEBUG update_position_stops: Sending data = {update_data}")
            
            headers = self.session.headers.copy()
            headers["_method"] = "PUT"
            headers["version"] = "2"  # V2 required for trailing stops
            
            response = self.session.put(url, json=update_data, headers=headers)
            
            print(f"DEBUG update_position_stops: Status = {response.status_code}")
            print(f"DEBUG update_position_stops: Response = {response.text}")
            
            if response.status_code == 200:
                deal_ref = response.json().get('dealReference')
                print(f"DEBUG update_position_stops: dealReference = {deal_ref}")
                
                if deal_ref:
                    deal_status = self.check_deal_status(deal_ref)
                    print(f"DEBUG update_position_stops: Deal status = {deal_status}")
                    
                    if deal_status.get('dealStatus') == 'ACCEPTED':
                        trailing_info = ""
                        if trailing_stop:
                            trailing_info = f" with trailing stop ({trailing_distance}/{trailing_step})"
                        return True, f"Position updated{trailing_info}"
                    else:
                        reason = deal_status.get('reason', 'Unknown reason')
                        print(f"DEBUG update_position_stops: REJECTED - {reason}")
                        return False, f"Update rejected: {reason}"
                else:
                    print(f"DEBUG update_position_stops: No dealReference in response")
                    return False, "No deal reference returned"
            else:
                print(f"DEBUG update_position_stops: HTTP error {response.status_code}")
                return False, f"Update failed: {response.text}"
                
        except Exception as e:
            print(f"DEBUG update_position_stops: EXCEPTION - {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Update error: {str(e)}"

    def check_trailing_stops_enabled(self):
        """Check if account has trailing stops enabled"""
        # This is set during login from the session response
        return getattr(self, 'trailing_stops_enabled', False)
    
    def get_working_orders(self):
        """Get list of working orders"""
        try:
            url = f"{self.base_url}/workingorders"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json().get('workingOrders', [])
            else:
                return []
                
        except Exception as e:
            print(f"Orders error: {str(e)}")
            return []
    
    def cancel_order(self, deal_id):
        """Cancel a working order"""
        try:
            url = f"{self.base_url}/workingorders/otc/{deal_id}"
            headers = self.session.headers.copy()
            headers["_method"] = "DELETE"
            headers["version"] = "2"
            
            response = self.session.post(url, headers=headers)
            
            if response.status_code == 200:
                return True, f"Order {deal_id} cancelled"
            else:
                return False, f"Cancel failed: {response.text}"
                
        except Exception as e:
            return False, f"Cancel error: {str(e)}"
    
    def get_open_positions(self):
        """Get list of open positions"""
        try:
            url = f"{self.base_url}/positions"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json().get('positions', [])
            else:
                return []
                
        except Exception as e:
            print(f"Positions error: {str(e)}")
            return []
    
    def close_position(self, deal_id, direction, size):
        """Close an open position"""
        try:
            url = f"{self.base_url}/positions/otc"
            
            # Close in opposite direction
            close_direction = "SELL" if direction == "BUY" else "BUY"
            
            close_data = {
                "dealId": deal_id,
                "direction": close_direction,
                "size": str(size),
                "orderType": "MARKET"
            }
            
            headers = self.session.headers.copy()
            headers["_method"] = "DELETE"
            headers["version"] = "1"
            
            response = self.session.post(url, json=close_data, headers=headers)
            
            if response.status_code == 200:
                deal_ref = response.json().get('dealReference')
                if deal_ref:
                    deal_status = self.check_deal_status(deal_ref)
                    if deal_status.get('dealStatus') == 'ACCEPTED':
                        return True, f"Position {deal_id} closed"
                    else:
                        return False, f"Close rejected: {deal_status.get('reason')}"
            else:
                return False, f"Close failed: {response.text}"
                
        except Exception as e:
            return False, f"Close error: {str(e)}"
    def place_limit_order(self, epic, direction, size, level):
        """Place a limit order"""
        url = f"{self.base_url}/workingorders/otc"
    
        # Determine expiry based on epic
        if epic.startswith("IX.D") or epic == "CS.D.USCGC.TODAY.IP":
            expiry = "DFB"
        else:
            expiry = "-"
    
        order_data = {
            "epic": epic,
            "expiry": expiry,
            "direction": direction,
            "size": str(size),
            "level": str(level),
            "type": "LIMIT",  # Changed from STOP
            "timeInForce": "GOOD_TILL_CANCELLED",
            "goodTillDate": None,
            "guaranteedStop": "false",
            "currencyCode": "GBP"
        }
    
        headers = self.session.headers.copy()
        headers["version"] = "2"
    
        return self.session.post(url, json=order_data, headers=headers)

    def place_limit_order(self, epic, direction, size, level):
        """Place a limit order"""
        url = f"{self.base_url}/workingorders/otc"
        
        # Determine expiry based on epic
        if epic.startswith("IX.D") or epic == "CS.D.USCGC.TODAY.IP":
            expiry = "DFB"
        else:
            expiry = "-"
        
        order_data = {
            "epic": epic,
            "expiry": expiry,
            "direction": direction,
            "size": str(size),
            "level": str(level),
            "type": "LIMIT",
            "timeInForce": "GOOD_TILL_CANCELLED",
            "goodTillDate": None,
            "guaranteedStop": "false",
            "currencyCode": "GBP"
        }
        
        headers = self.session.headers.copy()
        headers["version"] = "2"
        
        return self.session.post(url, json=order_data, headers=headers)
        
    def search_markets(self, search_term):
        """Search for markets by name"""
        try:
            url = f"{self.base_url}/markets"
            params = {"searchTerm": search_term}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json().get('markets', [])
            else:
                return []
        
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def get_market_details(self, epic):
        """Get detailed market information including min/max deal sizes"""
        if not self.logged_in:
            return None
        
        try:
            url = f"{self.base_url}/markets/{epic}"
            
            print(f"DEBUG market_details: Fetching {url}")
            print(f"DEBUG market_details: Headers = {self.session.headers}")
            
            response = self.session.get(url, headers=self.session.headers)
            
            print(f"DEBUG market_details: Status = {response.status_code}")
            
            if response.status_code == 200:
                print(f"DEBUG market_details: Full Response = {response.text}")
                data = response.json()
                
                # Extract dealing rules
                dealing_rules = data.get('dealingRules', {})
                market_data = data.get('instrument', {})
                
                return {
                    'epic': epic,
                    'name': market_data.get('name', 'Unknown'),
                    'type': market_data.get('type', 'Unknown'),
                    'min_deal_size': float(dealing_rules.get('minDealSize', {}).get('value', 0)),
                    'max_deal_size': float(dealing_rules.get('maxDealSize', {}).get('value', 0)),  # ✅ CORRECT!
                    'deal_size_unit': dealing_rules.get('minDealSize', {}).get('unit', 'AMOUNT'),
                    'min_stop_distance': float(dealing_rules.get('minNormalStopOrLimitDistance', {}).get('value', 0)),
                    'min_gslo_distance': float(dealing_rules.get('minControlledRiskStopDistance', {}).get('value', 0)),
                }
            else:
                print(f"DEBUG market_details: Error = {response.text}")
                print(f"Failed to get market details: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting market details: {str(e)}")
            return None
            
    def get_historical_prices(self, epic, resolution='DAY', num_points=365):
        """
        Get historical price data for an epic
        
        resolution: 'MINUTE', 'MINUTE_5', 'MINUTE_15', 'MINUTE_30', 
                    'HOUR', 'HOUR_4', 'DAY', 'WEEK', 'MONTH'
        num_points: Number of data points to retrieve
        """
        if not self.logged_in:
            print(f"DEBUG historical: Not logged in")
            return None
        
        try:
            url = f"{self.base_url}/prices/{epic}"
            
            params = {
                'resolution': resolution,
                'max': num_points
            }
            
            headers = self.session.headers.copy()
            headers['Version'] = '3'
            
            print(f"DEBUG historical: Fetching {url}")
            print(f"DEBUG historical: Params = resolution:{resolution}, max:{num_points}")
            print(f"DEBUG historical: Headers = {headers}")
            
            response = self.session.get(url, params=params, headers=headers)
            
            print(f"DEBUG historical: Status = {response.status_code}")
            
            if response.status_code != 200:
                print(f"DEBUG historical: Error response = {response.text}")
                print(f"Historical data error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            print(f"DEBUG historical: Response keys = {data.keys()}")
            
            prices = data.get('prices', [])
            print(f"DEBUG historical: Got {len(prices)} candles")
            
            if not prices:
                print(f"DEBUG historical: prices array is empty")
                return None
            
            # Extract high/low from candles
            all_highs = []
            all_lows = []
            
            for idx, price in enumerate(prices):
                snapshot = price.get('snapshot', {})
                high = snapshot.get('high')
                low = snapshot.get('low')
                
                if idx < 3:  # Print first 3 candles for debugging
                    print(f"DEBUG historical: Candle {idx}: high={high}, low={low}")
                
                if high is not None:
                    all_highs.append(high)
                if low is not None:
                    all_lows.append(low)
            
            print(f"DEBUG historical: Collected {len(all_highs)} highs, {len(all_lows)} lows")
            
            if all_highs and all_lows:
                result = {
                    'high': max(all_highs),
                    'low': min(all_lows),
                    'num_candles': len(prices)
                }
                print(f"DEBUG historical: Success! High={result['high']}, Low={result['low']}, Candles={result['num_candles']}")
                return result
            else:
                print(f"DEBUG historical: No high/low data found in candles")
                return None
                
        except Exception as e:
            print(f"DEBUG historical: Exception = {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    
# ===== UPDATE in ig_client.py - get_all_markets_by_type method =====

    def get_all_markets_by_type(self, market_type):
        """
        Get all SPOT markets of a specific type (filters out futures)
        market_type: 'COMMODITIES', 'INDICES', etc.
        """
        if not self.logged_in:
            return []
        
        try:
            all_markets = []
            
            # For commodities, search common terms
            if market_type == "COMMODITIES":
                search_terms = ["gold", "silver", "oil", "copper", "gas", "platinum", 
                            "palladium", "wheat", "corn", "sugar", "coffee", "cotton",
                            "cocoa", "soybean", "lumber", "crude", "brent", "natural gas"]
            # For indices, search common terms
            elif market_type == "INDICES":
                search_terms = ["index", "dow", "nasdaq", "s&p", "ftse", "dax", "nikkei",
                            "cac", "asx", "hang seng", "russell", "stoxx", "ibex"]
            else:
                search_terms = [""]
            
            seen_epics = set()
            
            for term in search_terms:
                try:
                    url = f"{self.base_url}/markets"
                    params = {"searchTerm": term}
                    response = self.session.get(url, params=params)
                    
                    if response.status_code == 200:
                        markets = response.json().get('markets', [])
                        
                        # Filter by type and remove duplicates
                        for market in markets:
                            epic = market.get('epic')
                            instrument_type = market.get('instrumentType', '')
                            instrument_name = market.get('instrumentName', '')
                            expiry = market.get('expiry', '')
                            
                            # Skip if wrong type or duplicate
                            if epic in seen_epics or instrument_type != market_type:
                                continue
                            
                            # ===== SPOT FILTER - Only include DFB or - expiry =====
                            if expiry not in ['DFB', '-']:
                                continue  # Skip futures/monthly contracts
                            
                            # Skip mini/micro contracts and weekly/monthly options
                            skip_terms = ['mini', 'micro', 'weekly', 'monthly', 'month1', 'month2', 'month3']
                            if any(skip in instrument_name.lower() for skip in skip_terms):
                                continue
                            
                            all_markets.append(market)
                            seen_epics.add(epic)
                    
                    time.sleep(0.2)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error searching term '{term}': {str(e)}")
                    continue
            
            return all_markets
            
        except Exception as e:
            print(f"Error getting markets by type: {str(e)}")
            return []
        
        # ===== ADD TO ig_client.py =====

    def get_historical_prices(self, epic, resolution='DAY', num_points=365):
        """
        Get historical price data for an epic
        
        resolution: 'MINUTE', 'MINUTE_5', 'MINUTE_15', 'MINUTE_30', 
                    'HOUR', 'HOUR_4', 'DAY', 'WEEK', 'MONTH'
        num_points: Number of data points to retrieve (max depends on resolution)
        """
        if not self.logged_in:
            return None
        
        try:
            url = f"{self.base_url}/prices/{epic}"
            
            params = {
                'resolution': resolution,
                'max': num_points
            }
            
            headers = self.session.headers.copy()
            headers['Version'] = '3'
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                
                if not prices:
                    return None
                
                # Extract high/low from candles
                all_highs = []
                all_lows = []
                
                for price in prices:
                    snapshot = price.get('snapshot', {})
                    high = snapshot.get('high')
                    low = snapshot.get('low')
                    
                    if high is not None:
                        all_highs.append(high)
                    if low is not None:
                        all_lows.append(low)
                
                if all_highs and all_lows:
                    return {
                        'high': max(all_highs),
                        'low': min(all_lows),
                        'num_candles': len(prices)
                    }
                else:
                    return None
            else:
                print(f"Historical data error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting historical prices: {str(e)}")
            return None


    # ===== HELPER FUNCTION =====

def get_timeframe_params(timeframe):
    """
    Get resolution and num_points for different timeframes
    
    timeframe: 'Daily', 'Weekly', 'Monthly', 'Annual', 'All-Time'
    Returns: dict with 'resolution' and 'num_points'
    """
    params = {
        'Daily': {'resolution': 'HOUR', 'num_points': 24},
        'Weekly': {'resolution': 'HOUR_4', 'num_points': 42},
        'Monthly': {'resolution': 'DAY', 'num_points': 30},
        'Quarterly': {'resolution': 'DAY', 'num_points': 90},
        '6-Month': {'resolution': 'DAY', 'num_points': 180},
        'Annual': {'resolution': 'DAY', 'num_points': 365},
        '2-Year': {'resolution': 'WEEK', 'num_points': 104},
        '5-Year': {'resolution': 'WEEK', 'num_points': 260},
        'All-Time': {'resolution': 'MONTH', 'num_points': 1200},
    }
    
    return params.get(timeframe, params['Annual'])