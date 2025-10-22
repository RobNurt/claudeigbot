"""
Position Monitor
Watches for working orders becoming positions and auto-attaches stops/limits
"""
import threading
import time
from datetime import datetime

class PositionMonitor:
    """Monitors positions and auto-attaches stops when orders fill"""
    
    def __init__(self, ig_client):
        self.ig_client = ig_client
        self.running = False
        self.monitor_thread = None
        self.known_positions = set()  # Track position deal IDs we've already processed
        self.known_working_orders = set()  # Track working order deal IDs
        
        # Configuration
        self.auto_stop_enabled = False
        self.auto_stop_distance = 20
        
        self.auto_trailing_enabled = False
        self.trailing_distance = 15
        self.trailing_step = 5
        
        self.auto_limit_enabled = False
        self.auto_limit_distance = 5
        
        self.check_interval = 10  # Check every 10 seconds
        
    def configure(self, auto_stop=False, stop_distance=20, 
                  auto_trailing=False, trailing_distance=15, trailing_step=5,
                  auto_limit=False, limit_distance=5):
        """Update monitor configuration"""
        self.auto_stop_enabled = auto_stop
        self.auto_stop_distance = stop_distance
        
        self.auto_trailing_enabled = auto_trailing
        self.trailing_distance = trailing_distance
        self.trailing_step = trailing_step
        
        self.auto_limit_enabled = auto_limit
        self.auto_limit_distance = limit_distance
    
    def start(self, log_func):
        """Start monitoring positions"""
        if self.running:
            log_func("Position monitor already running")
            return
        
        self.running = True
        self.log_func = log_func
        
        # Initialize known positions and orders
        try:
            positions = self.ig_client.get_open_positions()
            self.known_positions = {p.get("position", {}).get("dealId") for p in positions if p.get("position", {}).get("dealId")}
            
            working_orders = self.ig_client.get_working_orders()
            self.known_working_orders = {o.get("workingOrderData", {}).get("dealId") for o in working_orders if o.get("workingOrderData", {}).get("dealId")}
            
            log_func(f"Position monitor started - tracking {len(self.known_positions)} positions, {len(self.known_working_orders)} orders")
        except Exception as e:
            log_func(f"Error initializing monitor: {str(e)}")
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        if hasattr(self, 'log_func'):
            self.log_func("Position monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_for_new_positions()
            except Exception as e:
                if hasattr(self, 'log_func'):
                    self.log_func(f"Monitor error: {str(e)}")
            
            # Wait before next check
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_for_new_positions(self):
        """Check for newly opened positions and attach stops/limits"""
        try:
            # Get current positions
            positions = self.ig_client.get_open_positions()
            current_position_ids = {p.get("position", {}).get("dealId") for p in positions if p.get("position", {}).get("dealId")}
            
            # Find NEW positions (not in our known set)
            new_position_ids = current_position_ids - self.known_positions
            
            if new_position_ids:
                self.log_func(f"🔔 Detected {len(new_position_ids)} new position(s)")
                
                for pos in positions:
                    deal_id = pos.get("position", {}).get("dealId")
                    
                    if deal_id in new_position_ids:
                        # This is a new position - process it
                        self._process_new_position(pos)
                        self.known_positions.add(deal_id)
            
            # Update our known positions list
            self.known_positions = current_position_ids
            
        except Exception as e:
            if hasattr(self, 'log_func'):
                self.log_func(f"Error checking positions: {str(e)}")
    
    def _process_new_position(self, position):
        """Process a newly opened position - attach stops/limits"""
        try:
            deal_id = position.get("position", {}).get("dealId")
            epic = position.get("market", {}).get("epic", "Unknown")
            direction = position.get("position", {}).get("direction")
            size = position.get("position", {}).get("dealSize")
            level = position.get("position", {}).get("level")
            
            self.log_func(f"📍 Processing new position: {epic} {direction} {size} @ {level}")
            
            # Check if it needs stops/limits attached
            needs_update = self.auto_stop_enabled or self.auto_limit_enabled
            
            if not needs_update:
                self.log_func(f"  ℹ️ Auto-attach disabled, skipping")
                return
            
            # Prepare update parameters
            stop_distance = self.auto_stop_distance if self.auto_stop_enabled else None
            limit_distance = self.auto_limit_distance if self.auto_limit_enabled else None
            
            trailing_stop = self.auto_trailing_enabled and self.auto_stop_enabled
            trailing_distance = self.trailing_distance if trailing_stop else None
            trailing_step = self.trailing_step if trailing_stop else None
            
            # Apply the update
            success, message = self.ig_client.update_position_stops(
                deal_id=deal_id,
                stop_distance=stop_distance,
                trailing_stop=trailing_stop,
                trailing_distance=trailing_distance,
                trailing_step=trailing_step,
                limit_distance=limit_distance
            )
            
            if success:
                parts = []
                if self.auto_stop_enabled:
                    if trailing_stop:
                        parts.append(f"trailing stop ({trailing_distance}/{trailing_step})")
                    else:
                        parts.append(f"stop ({stop_distance}pts)")
                if self.auto_limit_enabled:
                    parts.append(f"limit ({limit_distance}pts)")
                
                self.log_func(f"  ✅ Auto-attached {', '.join(parts)} to {deal_id}")
            else:
                self.log_func(f"  ❌ Failed to attach stops: {message}")
            
            # Small delay to avoid hammering API
            time.sleep(0.5)
            
        except Exception as e:
            self.log_func(f"Error processing position {deal_id}: {str(e)}")