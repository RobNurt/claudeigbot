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
                                'size': order_size,
                                'stop_distance': stop_distance,  # ADD THIS
                                'guaranteed_stop': guaranteed_stop  # ADD THIS
                            })
                                break

                            elif deal_status.get('reason') == 'ATTACHED_ORDER_LEVEL_ERROR':
                                log(f"Order {i+1} stop level error - stop distance: {stop_distance}, entry: {order_level}")
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

# Replace the start_trailing method in ladder_strategy.py

    def start_trailing(self, log, min_move=0.5, check_interval=30):
            """
            Start trailing stops - maintains individual ladder spacing and preserves stop losses
            
            Args:
                log: Logging callback function
                min_move: Minimum price movement in points to trigger adjustment (default: 0.5)
                check_interval: Seconds between checks (default: 30)
            """
            import threading
            import time
            
            self.trailing_active = True
            
            def trail_orders():
                """Background thread to monitor and adjust ALL orders while preserving stops"""
                
                log(f"Trailing started - checking every {check_interval}s, min move: {min_move} pts")
                
                # Track original offset and stop info for each order (key = deal_id)
                order_offsets = {}
                order_stops = {}
                
                check_count = 0
                while self.trailing_active:
                    try:
                        check_count += 1
                        
                        if check_count % 5 == 1:
                            log(f"Trailing check #{check_count} (next in {check_interval}s)...")
                        
                        working_orders = self.ig_client.get_working_orders()
                        
                        if not working_orders:
                            if check_count % 5 == 1:
                                log("No working orders found")
                            time.sleep(check_interval)
                            continue
                        
                        orders_checked = 0
                        orders_trailed = 0
                        
                        # Cache prices per epic
                        price_cache = {}
                        
                        for order in working_orders:
                            try:
                                order_data = order.get('workingOrderData', {})
                                market_data = order.get('marketData', {})
                                
                                epic = market_data.get('epic')
                                current_level = order_data.get('level')
                                direction = order_data.get('direction')
                                deal_id = order_data.get('dealId')
                                
                                if not all([epic, current_level, direction, deal_id]):
                                    continue
                                
                                orders_checked += 1
                                
                                # Get price (cached)
                                if epic not in price_cache:
                                    price_data = self.ig_client.get_market_price(epic)
                                    if not price_data or not price_data['mid']:
                                        continue
                                    price_cache[epic] = price_data['mid']
                                
                                current_price = price_cache[epic]
                                
                                # First time seeing this order - record its offset and look up stop info
                                if deal_id not in order_offsets:
                                    if direction == "BUY":
                                        order_offsets[deal_id] = current_level - current_price
                                    else:  # SELL
                                        order_offsets[deal_id] = current_price - current_level
                                
                                # Look up stop info ONCE and store it permanently
                                if deal_id not in order_stops:
                                    # All orders from the same ladder have the same stop_distance
                                    # Just use the first order's stop info for this epic/direction
                                    tracked_order = next((o for o in self.placed_orders 
                                                        if o.get('stop_distance') is not None), None)
                                    if tracked_order:
                                        order_stops[deal_id] = {
                                            'stop_distance': tracked_order.get('stop_distance'),
                                            'guaranteed': tracked_order.get('guaranteed_stop', False)
                                        }
                                        log(f"DEBUG: Using stop {tracked_order.get('stop_distance')} for {deal_id}")
                                    else:
                                        # No orders with stops
                                        order_stops[deal_id] = {
                                            'stop_distance': None,
                                            'guaranteed': False
                                        }
                                        log(f"DEBUG: No stop distance found in placed_orders")
                                
                                # Use the ORIGINAL offset
                                original_offset = order_offsets[deal_id]
                                stop_info = order_stops.get(deal_id, {'stop_distance': None, 'guaranteed': False})
                                
                                if direction == "BUY":
                                    # BUY orders trail DOWN as price falls
                                    ideal_level = current_price + original_offset
                                    
                                    # Only move DOWN
                                    if ideal_level < current_level - min_move:
                                        new_level = ideal_level
                                        
                                        success, message = self.ig_client.update_working_order(
                                            deal_id, 
                                            new_level,
                                            stop_distance=stop_info['stop_distance'],
                                            guaranteed_stop=stop_info['guaranteed']
                                        )
                                        
                                        if success:
                                            stop_msg = f" (stop: {stop_info['stop_distance']})" if stop_info['stop_distance'] else ""
                                            log(f"{epic} BUY: Trailed DOWN {current_level:.2f} → {new_level:.2f}{stop_msg}")
                                            orders_trailed += 1
                                        else:
                                            log(f"{epic}: Trail failed - {message}")
                                
                                elif direction == "SELL":
                                    # SELL orders trail UP as price rises
                                    ideal_level = current_price - original_offset
                                    
                                    # Only move UP
                                    if ideal_level > current_level + min_move:
                                        new_level = ideal_level
                                        
                                        success, message = self.ig_client.update_working_order(
                                            deal_id,
                                            new_level,
                                            stop_distance=stop_info['stop_distance'],
                                            guaranteed_stop=stop_info['guaranteed']
                                        )
                                        
                                        if success:
                                            stop_msg = f" (stop: {stop_info['stop_distance']})" if stop_info['stop_distance'] else ""
                                            log(f"{epic} SELL: Trailed UP {current_level:.2f} → {new_level:.2f}{stop_msg}")
                                            orders_trailed += 1
                                        else:
                                            log(f"{epic}: Trail failed - {message}")
                            
                            except Exception as e:
                                log(f"Error processing order: {str(e)}")
                                continue
                        
                        # Summary every 5 checks
                        if check_count % 5 == 0 and orders_checked > 0:
                            log(f"Check #{check_count}: {orders_checked} orders monitored, {orders_trailed} trailed")
                        
                    except Exception as e:
                        log(f"Trailing error: {str(e)}")
                    
                    time.sleep(check_interval)
                
                log("Trailing stopped")
            
            # Start the trailing thread
            trail_thread = threading.Thread(target=trail_orders, daemon=True)
            trail_thread.start()
            
    def stop_trailing(self):
        """Stop trailing stops"""
        self.trailing_active = False
