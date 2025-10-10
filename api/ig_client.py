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
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                snapshot = data.get('snapshot', {})
                bid = snapshot.get('bid')
                offer = snapshot.get('offer')
                mid = (bid + offer) / 2 if bid and offer else None
                
                return {
                    'bid': bid,
                    'offer': offer,
                    'mid': mid,
                    'market_status': snapshot.get('marketStatus')
                }
            else:
                return None
                
        except Exception as e:
            print(f"Price error: {str(e)}")
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