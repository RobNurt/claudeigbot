"""
Ladder Trading Strategy
Implements ladder order placement with automatic retry on level errors
"""
import time

class LadderStrategy:
    """Ladder strategy for placing multiple stop orders"""
    
    def __init__(self, ig_client):
        self.ig_client = ig_client
    
    def place_ladder(self, epic, direction, start_offset, step_size, num_orders, 
                    order_size, retry_jump=10, max_retries=3, log_callback=None, 
                    limit_distance=0, stop_distance=0, guaranteed_stop=False):
        """
        Place a ladder of orders with configurable retry on level errors
        
        Args:
            epic: Market epic code
            direction: BUY or SELL
            start_offset: Initial offset from current price
            step_size: Distance between orders
            num_orders: Number of orders to place
            order_size: Size of each order
            retry_jump: Points to add on each retry
            max_retries: Maximum retry attempts
            log_callback: Function to call for logging (optional)
            limit_distance: Distance for limit orders (0 = no limits)
            stop_distance: Distance for stop loss (0 = no stop)
            guaranteed_stop: Whether to use guaranteed stops
        
        Returns:
            Tuple of (successful_count, total_orders)
        """
        def log(message):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        
        # Get current price
        price_data = self.ig_client.get_market_price(epic)
        if not price_data or not price_data['mid']:
            log("Could not get market price")
            return 0, num_orders
        
        current_price = price_data['mid']
        log(f"Current {epic} price: {current_price}")
        
        # Log stop loss configuration
        if stop_distance > 0:
            stop_type = "Guaranteed" if guaranteed_stop else "Regular"
            log(f"Using {stop_type} stops at {stop_distance} points distance")
        
        successful_orders = 0
        
        for i in range(num_orders):
            placed = False
            
            for retry_attempt in range(max_retries):
                # Calculate offset: start + (retry_attempt * retry_jump)
                current_offset = start_offset + (retry_attempt * retry_jump)
                
                if direction == "BUY":
                    order_level = current_price + current_offset + (i * step_size)
                else:
                    order_level = current_price - current_offset - (i * step_size)
                
                # Try to place the order WITH stop loss
                response = self.ig_client.place_order(
                    epic, direction, order_size, order_level, 
                    stop_distance=stop_distance, 
                    guaranteed_stop=guaranteed_stop
                )
                
                if response.status_code == 200:
                    deal_ref = response.json().get('dealReference')
                    if deal_ref:
                        deal_status = self.ig_client.check_deal_status(deal_ref)
                        
                        # Check if order was accepted
                        if deal_status.get('dealStatus') == 'ACCEPTED':
                            if retry_attempt > 0:
                                log(f"Order {i+1} placed at {order_level} (offset: {current_offset})")
                            else:
                                log(f"Order {i+1} placed at {order_level}")
                            successful_orders += 1
                            placed = True
                            
                            # Place limit order if requested
                            if limit_distance > 0:
                                if direction == "BUY":
                                    limit_level = order_level + limit_distance
                                    limit_direction = "SELL"
                                else:
                                    limit_level = order_level - limit_distance
                                    limit_direction = "BUY"
                                
                                limit_response = self.ig_client.place_limit_order(
                                    epic, limit_direction, order_size, limit_level
                                )
                                
                                if limit_response.status_code == 200:
                                    limit_ref = limit_response.json().get('dealReference')
                                    limit_status = self.ig_client.check_deal_status(limit_ref)
                                    if limit_status.get('dealStatus') == 'ACCEPTED':
                                        log(f"Limit order placed at {limit_level}")
                                    else:
                                        log(f"Limit order rejected: {limit_status.get('reason')}")
                                else:
                                    log(f"Limit order failed: {limit_response.text}")
                            
                            break  # Exit retry loop on success
                        
                        elif deal_status.get('reason') == 'ATTACHED_ORDER_LEVEL_ERROR':
                            if retry_attempt < max_retries - 1:
                                log(f"Order {i+1} too close at {order_level}. Retrying with larger offset...")
                            else:
                                log(f"Order {i+1} failed after {max_retries} retries - minimum distance too large")
                                break
                        else:
                            log(f"Order {i+1} rejected: {deal_status.get('reason')}")
                            break
                else:
                    log(f"Order {i+1} failed: {response.text}")
                    break
                
                time.sleep(0.3)  # Short delay between retries
            
            if not placed:
                log(f"Order {i+1} could not be placed")
            
            time.sleep(0.5)  # Rate limiting between orders
        
        log(f"Ladder complete: {successful_orders}/{num_orders} orders placed successfully")
        return successful_orders, num_orders