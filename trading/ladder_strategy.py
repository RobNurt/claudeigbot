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

        # DEBUG
        print(
            f"DEBUG place_ladder: limit_distance received = {limit_distance}")

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

successful_orders = 0

        for i in range(num_orders):
            # Check for cancellation
            if self.cancel_requested:
                log("Ladder placement cancelled by user")
                self.cancel_requested = False  # Reset flag
                return successful_orders, num_orders
            
            placed = False
            
                for retry_attempt in range(max_retries):

                if direction == "BUY":
                    order_level = current_price + \
                        current_offset + (i * step_size)
                else:
                    order_level = current_price - \
                        current_offset - (i * step_size)

                # Try to place the order WITH stop loss AND limit
                response = self.ig_client.place_order(
                    epic, direction, order_size, order_level,
                    stop_distance=stop_distance,
                    guaranteed_stop=guaranteed_stop,
                    limit_distance=limit_distance  # ADDED
                )

                if response.status_code == 200:
                    deal_ref = response.json().get('dealReference')
                    if deal_ref:
                        deal_status = self.ig_client.check_deal_status(
                            deal_ref)

                        # Check if order was accepted
                        if deal_status.get('dealStatus') == 'ACCEPTED':
                            if retry_attempt > 0:
                                log(f"Order {i+1} placed at {order_level} (offset: {current_offset})")
                            else:
                                log(f"Order {i+1} placed at {order_level}")

                            if limit_distance > 0:
                                log(f"  with limit at {limit_distance} points")

                            successful_orders += 1
                            placed = True

                            # Track the order
                            self.placed_orders.append({
                                'level': order_level,
                                'direction': direction,
                                'epic': epic,
                                'size': order_size
                            })

                            break  # Exit retry loop on success
                        elif deal_status.get('reason') == 'ATTACHED_ORDER_LEVEL_ERROR':
                            if retry_attempt < max_retries - 1:
                                log(
                                    f"Order {i+1} too close at {order_level}. Retrying with larger offset...")
                            else:
                                log(
                                    f"Order {i+1} failed after {max_retries} retries - minimum distance too large")
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
        """Start trailing stops - monitor price and adjust orders"""
        import threading
        
        self.trailing_active = True
        log("Trailing started - orders will follow price movement")
        
        def trail_orders():
            """Background thread to monitor and adjust orders"""
            import time
            
            trailing_distance = 5  # Points behind current price
            check_interval = 5  # Seconds between checks
            
            while self.trailing_active:
                try:
                    if not self.placed_orders:
                        time.sleep(check_interval)
                        continue
                    
                    # Get current price for the epic
                    epic = self.placed_orders[0]['epic']
                    price_data = self.ig_client.get_market_price(epic)
                    
                    if not price_data or not price_data['mid']:
                        time.sleep(check_interval)
                        continue
                    
                    current_price = price_data['mid']
                    direction = self.placed_orders[0]['direction']
                    
                    # Get current working orders from API
                    working_orders = self.ig_client.get_working_orders()
                    
                    # Match our tracked orders with actual working orders
                    for tracked_order in self.placed_orders:
                        old_level = tracked_order['level']
                        
                        # Calculate new level based on trailing distance
                        if direction == "BUY":
                            # For buys, trail down as price drops
                            new_level = current_price + trailing_distance
                            
                            # Only move if new level is lower (better entry)
                            if new_level < old_level - 2:  # At least 2 points improvement
                                # Find the actual order in working orders
                                for wo in working_orders:
                                    wo_data = wo.get('workingOrderData', {})
                                    wo_level = wo_data.get('orderLevel')
                                    
                                    # Match by level (approximate)
                                    if wo_level and abs(wo_level - old_level) < 1:
                                        deal_id = wo_data.get('dealId')
                                        
                                        # Update the order
                                        success, message = self.ig_client.update_working_order(
                                            deal_id, new_level
                                        )
                                        
                                        if success:
                                            log(f"Order trailed: {old_level:.2f} → {new_level:.2f}")
                                            tracked_order['level'] = new_level
                                        else:
                                            log(f"Trail failed: {message}")
                                        
                                        break
                        
                        else:  # SELL
                            # For sells, trail up as price rises
                            new_level = current_price - trailing_distance
                            
                            # Only move if new level is higher (better entry)
                            if new_level > old_level + 2:
                                # Find and update order (same logic as above)
                                for wo in working_orders:
                                    wo_data = wo.get('workingOrderData', {})
                                    wo_level = wo_data.get('orderLevel')
                                    
                                    if wo_level and abs(wo_level - old_level) < 1:
                                        deal_id = wo_data.get('dealId')
                                        
                                        success, message = self.ig_client.update_working_order(
                                            deal_id, new_level
                                        )
                                        
                                        if success:
                                            log(f"Order trailed: {old_level:.2f} → {new_level:.2f}")
                                            tracked_order['level'] = new_level
                                        else:
                                            log(f"Trail failed: {message}")
                                        
                                        break
                    
                except Exception as e:
                    log(f"Trailing error: {str(e)}")
                
                time.sleep(check_interval)
        
        # Start the trailing thread
        trail_thread = threading.Thread(target=trail_orders, daemon=True)
        trail_thread.start()

    def stop_trailing(self):
        """Stop trailing stops"""
        self.trailing_active = False
