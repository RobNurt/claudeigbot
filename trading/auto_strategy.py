"""
Auto Trading Strategy
Manages automatic ladder adjustment and trailing stop management
"""
import time
import threading

class AutoStrategy:
    """Automated ladder management with trailing stops"""
    
    def __init__(self, ig_client, ladder_strategy):
        self.ig_client = ig_client
        self.ladder_strategy = ladder_strategy
        self.running = False
        self.monitor_thread = None
        
        # Configuration
        self.check_interval = 30
        self.adjustment_threshold = 10
        self.trailing_stop_distance = 20
        self.max_spread = 5
        
        # State tracking
        self.last_price = None
        self.current_ladder_base = None
        self.log_callback = None
        
    def start(self, epic, direction, start_offset, step_size, num_orders, 
             order_size, retry_jump, max_retries, log_callback):
        """Start the auto strategy"""
        if self.running:
            log_callback("Auto strategy already running")
            return
        
        self.running = True
        self.epic = epic
        self.direction = direction
        self.start_offset = start_offset
        self.step_size = step_size
        self.num_orders = num_orders
        self.order_size = order_size
        self.retry_jump = retry_jump
        self.max_retries = max_retries
        self.log_callback = log_callback
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        log_callback(f"Auto strategy started - monitoring every {self.check_interval}s")
    
    def stop(self):
        """Stop the auto strategy"""
        self.running = False
        if self.log_callback:
            self.log_callback("Auto strategy stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - checks orders and adjusts as needed"""
        while self.running:
            try:
                # Get current price
                price_data = self.ig_client.get_market_price(self.epic)
                if not price_data or not price_data.get('mid'):
                    time.sleep(self.check_interval)
                    continue
                
                current_price = price_data['mid']
                
                # Get working orders
                orders = self.ig_client.get_working_orders()
                
                # Filter orders for this epic
                our_orders = [
                    o for o in orders 
                    if o.get('marketData', {}).get('epic') == self.epic
                ]
                
                if not our_orders:
                    if self.log_callback:
                        self.log_callback("Auto-strategy: No orders found")
                    time.sleep(self.check_interval)
                    continue
                
                # Check if adjustment needed
                needs_adjustment = self._check_if_adjustment_needed(our_orders, current_price)
                
                if needs_adjustment:
                    if self.log_callback:
                        self.log_callback("Auto-strategy: Adjusting ladder...")
                    self._adjust_ladder(our_orders, current_price)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Auto-strategy error: {e}")
                time.sleep(self.check_interval)
    
    def _check_if_adjustment_needed(self, orders, current_price):
        """Check if ladder needs adjustment"""
        if not orders:
            return False
        
        # Find closest order to current price
        closest_distance = float('inf')
        
        for order in orders:
            order_data = order.get('workingOrderData', {})
            order_level = order_data.get('orderLevel')
            
            if order_level:
                distance = abs(current_price - order_level)
                closest_distance = min(closest_distance, distance)
        
        # If closest order is beyond threshold, need adjustment
        return closest_distance > self.adjustment_threshold
    
    def _adjust_ladder(self, orders, current_price):
        """Adjust ladder positions"""
        try:
            # For each order, calculate new level
            for order in orders:
                order_data = order.get('workingOrderData', {})
                deal_id = order_data.get('dealId')
                direction = order_data.get('direction')
                old_level = order_data.get('orderLevel')
                stop_level = order_data.get('stopLevel')
                guaranteed_stop = order_data.get('guaranteedStop', False)
                
                if not deal_id or not old_level:
                    continue
                
                # Calculate offset from current price
                if direction == "BUY":
                    offset = old_level - current_price
                    new_level = current_price + offset
                else:  # SELL
                    offset = current_price - old_level
                    new_level = current_price - offset
                
                # Calculate new stop level if stop exists
                new_stop_distance = None
                if stop_level:
                    stop_distance = abs(old_level - stop_level)
                    # Preserve the same stop distance with the new level
                    new_stop_distance = stop_distance
                
                # Update the order - FIX: Use correct parameter names
                success, message = self.ig_client.update_working_order(
                    deal_id,  # positional arg
                    new_level,  # positional arg - new order level
                    stop_distance=new_stop_distance,  # preserve stop
                    guaranteed_stop=guaranteed_stop
                )
                
                if success:
                    if self.log_callback:
                        self.log_callback(f"Adjusted order {deal_id}: {old_level:.2f} → {new_level:.2f}")
                else:
                    if self.log_callback:
                        self.log_callback(f"Failed to adjust order {deal_id}: {message}")
                
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error adjusting ladder: {e}")
    
    def configure(self, check_interval=None, adjustment_threshold=None, 
                 trailing_stop_distance=None, max_spread=None):
        """Update configuration parameters"""
        if check_interval is not None:
            self.check_interval = check_interval
        if adjustment_threshold is not None:
            self.adjustment_threshold = adjustment_threshold
        if trailing_stop_distance is not None:
            self.trailing_stop_distance = trailing_stop_distance
        if max_spread is not None:
            self.max_spread = max_spread