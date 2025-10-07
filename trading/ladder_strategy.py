"""
Ladder Trading Strategy
Implements ladder order placement with automatic retry on level errors
"""
import time


class LadderStrategy:
    """Ladder strategy for placing multiple stop orders"""

    def __init__(self, ig_client):
        self.ig_client = ig_client
        self.placed_orders = []  # Track placed orders
        self.trailing_active = False
        self.cancel_requested = False

    def place_ladder(self, epic, direction, start_offset, step_size, num_orders,
                    order_size, retry_jump=10, max_retries=3, log_callback=None,
                    limit_distance=0, stop_distance=0, guaranteed_stop=False):
        """
        Place a ladder of orders with configurable retry on level errors
        """
        def log(message):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        
        # Clear previous orders tracking
        self.placed_orders = []
        
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
            # Check for cancellation
            if self.cancel_requested:
                log("Ladder placement cancelled by user")
                self.cancel_requested = False
                return successful_orders, num_orders
            
            placed = False
            
            for retry_attempt in range(max_retries):
                # Calculate offset
                current_offset = start_offset + (retry_attempt * retry_jump)
                
                # Calculate order level - MUST BE INSIDE RETRY LOOP
                if direction == "BUY":
                    order_level = current_price + current_offset + (i * step_size)
                else:
                    order_level = current_price - current_offset - (i * step_size)
                
                # Try to place the order
                response = self.ig_client.place_order(
                    epic, direction, order_size, order_level,
                    stop_distance=stop_distance,
                    guaranteed_stop=guaranteed_stop,
                    limit_distance=limit_distance
                )
                
                if response.status_code == 200:
                    deal_ref = response.json().get('dealReference')
                    if deal_ref:
                        deal_status = self.ig_client.check_deal_status(deal_ref)
                        
                        if deal_status.get('dealStatus') == 'ACCEPTED':
                            if retry_attempt > 0:
                                log(f"Order {i+1} placed at {order_level} (offset: {current_offset})")
                            else:
                                log(f"Order {i+1} placed at {order_level}")
                            
                            if limit_distance > 0:
                                log(f"  with limit at {limit_distance} points")
                            
                            successful_orders += 1
                            placed = True
                            
                            self.placed_orders.append({
                                'level': order_level,
                                'direction': direction,
                                'epic': epic,
                                'size': order_size
                            })
                            
                            break
                        
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
                
                time.sleep(0.3)
            
            if not placed:
                log(f"Order {i+1} could not be placed")
            
            time.sleep(0.5)
        
        log(f"Ladder complete: {successful_orders}/{num_orders} orders placed successfully")
        return successful_orders, num_orders

    def toggle_limits(self, enable, distance, log):
        """Toggle limits on all placed orders"""
        if not self.placed_orders:
            log("No orders to modify")
            return

        for order in self.placed_orders:
            # Basic implementation - just logs for now
            action = "Adding" if enable else "Removing"
            log(f"{action} limit on order at {order['level']:.2f}")
            time.sleep(0.2)

        log(f"Limit toggle complete on {len(self.placed_orders)} orders")

    def start_trailing(self, log):
        """Start trailing stops - monitor ALL working orders and adjust based on current price"""
        import threading
        import time
        
        self.trailing_active = True
        log("Trailing started - monitoring all working orders")
        print("DEBUG: Trailing thread starting")
        
        def trail_orders():
            """Background thread to monitor and adjust ALL orders"""
            trailing_distance = 5
            min_move = 0.1  # Very sensitive for testing
            check_interval = 3
            
            print("DEBUG: Trail thread running")
            
            while self.trailing_active:
                try:
                    print("DEBUG: Checking for orders to trail...")
                    
                    # Get ALL current working orders from IG
                    working_orders = self.ig_client.get_working_orders()
                    print(f"DEBUG: Found {len(working_orders)} working orders")
                    
                    if not working_orders:
                        time.sleep(check_interval)
                        continue
                    
                    # Process each order
                    for order in working_orders:
                        try:
                            order_data = order.get('workingOrderData', {})
                            market_data = order.get('marketData', {})

                            print(f"DEBUG: order_data keys: {order_data.keys()}")
                            print(f"DEBUG: Full order_data: {order_data}")
                            
                            epic = market_data.get('epic')
                            current_level = order_data.get('level')
                            direction = order_data.get('direction')
                            deal_id = order_data.get('dealId')
                            
                            print(f"DEBUG: Order - {epic} {direction} @ {current_level}")
                            
                            if not all([epic, current_level, direction, deal_id]):
                                print("DEBUG: Missing data, skipping")
                                continue
                            
                            # Get current price for this instrument
                            price_data = self.ig_client.get_market_price(epic)
                            print(f"DEBUG: price_data response: {price_data}")
                            if not price_data or not price_data['mid']:
                                print(f"DEBUG: Could not get price for {epic}")
                                continue
                            
                            current_price = price_data['mid']
                            print(f"DEBUG: Current price for {epic}: {current_price}")
                            
                            # Calculate where order SHOULD be
                            if direction == "BUY":
                                ideal_level = current_price + trailing_distance
                                print(f"DEBUG: BUY - ideal={ideal_level}, current={current_level}, diff={current_level - ideal_level}")
                                
                                # Only move DOWN (better entry for buys)
                                if ideal_level < current_level - min_move:
                                    new_level = ideal_level
                                    print(f"DEBUG: Will trail from {current_level} to {new_level}")
                                    
                                    success, message = self.ig_client.update_working_order(deal_id, new_level)
                                    
                                    if success:
                                        log(f"{epic}: Order trailed {current_level:.2f} → {new_level:.2f}")
                                    else:
                                        log(f"{epic}: Trail failed - {message}")
                                        print(f"DEBUG: Trail failed - {message}")
                                else:
                                    print(f"DEBUG: Not trailing - improvement too small")
                            
                            else:  # SELL
                                ideal_level = current_price - trailing_distance
                                print(f"DEBUG: SELL - ideal={ideal_level}, current={current_level}, diff={ideal_level - current_level}")
                                
                                # Only move UP (better entry for sells)
                                if ideal_level > current_level + min_move:
                                    new_level = ideal_level
                                    print(f"DEBUG: Will trail from {current_level} to {new_level}")
                                    
                                    success, message = self.ig_client.update_working_order(deal_id, new_level)
                                    
                                    if success:
                                        log(f"{epic}: Order trailed {current_level:.2f} → {new_level:.2f}")
                                    else:
                                        log(f"{epic}: Trail failed - {message}")
                                        print(f"DEBUG: Trail failed - {message}")
                                else:
                                    print(f"DEBUG: Not trailing - improvement too small")
                        
                        except Exception as e:
                            print(f"DEBUG: Error processing order: {str(e)}")
                            log(f"Error processing order: {str(e)}")
                            continue
                    
                except Exception as e:
                    print(f"DEBUG: Trailing error: {str(e)}")
                    log(f"Trailing error: {str(e)}")
                
                time.sleep(check_interval)
            
            log("Trailing stopped")
            print("DEBUG: Trailing thread stopped")
        
        # Start the trailing thread
        trail_thread = threading.Thread(target=trail_orders, daemon=True)
        trail_thread.start()

    def stop_trailing(self):
        """Stop trailing stops"""
        self.trailing_active = False
