"""
Notification System
Sends rally alerts via Windows notifications
"""
import platform
from datetime import datetime


class NotificationSystem:
    """Manages rally notifications"""
    
    def __init__(self):
        self.enabled = True
        self.last_notifications = {}  # Track last notification time per instrument
        self.cooldown_period = 300  # 5 minutes between notifications for same instrument
        
        # Check if we can use Windows notifications
        self.windows_toast_available = False
        if platform.system() == 'Windows':
            try:
                from win10toast import ToastNotifier
                self.toaster = ToastNotifier()
                self.windows_toast_available = True
            except ImportError:
                print("win10toast not available - install with: pip install win10toast")
                self.toaster = None
        else:
            self.toaster = None
    
    def send_rally_notification(self, trend_data):
        """
        Send a rally notification
        
        Args:
            trend_data: Dictionary with trend analysis data
        """
        if not self.enabled:
            return False
        
        epic = trend_data.get('epic')
        timeframe = trend_data.get('timeframe')
        
        # Check cooldown
        if not self._check_cooldown(epic, timeframe):
            return False
        
        # Build notification message
        title, message = self._build_notification_message(trend_data)
        
        # Send notification
        success = self._send_windows_notification(title, message)
        
        if success:
            # Update last notification time
            key = f"{epic}_{timeframe}"
            self.last_notifications[key] = datetime.now()
        
        return success
    
    def _check_cooldown(self, epic, timeframe):
        """Check if we can send notification (not in cooldown period)"""
        key = f"{epic}_{timeframe}"
        
        if key not in self.last_notifications:
            return True
        
        last_time = self.last_notifications[key]
        elapsed = (datetime.now() - last_time).total_seconds()
        
        return elapsed >= self.cooldown_period
    
    def _build_notification_message(self, trend_data):
        """Build notification title and message"""
        epic = trend_data.get('epic', 'Unknown')
        timeframe = trend_data.get('timeframe', '')
        price = trend_data.get('current_price', 0)
        change_1 = trend_data.get('change_1_bar', 0)
        change_5 = trend_data.get('change_5_bars', 0)
        rsi = trend_data.get('rsi')
        momentum = trend_data.get('momentum_score', 0)
        volume_ratio = trend_data.get('volume_ratio', 1.0)
        
        # Extract instrument name from epic
        instrument_name = self._epic_to_friendly_name(epic)
        
        # Build title
        if change_1 > 0:
            title = f"🚀 RALLY: {instrument_name} UP {abs(change_1):.1f}%"
        else:
            title = f"📉 DROP: {instrument_name} DOWN {abs(change_1):.1f}%"
        
        # Build message
        message_parts = [
            f"Timeframe: {timeframe}",
            f"Price: {price}",
            f"5-bar change: {change_5:+.1f}%"
        ]
        
        if rsi:
            if rsi < 35:
                message_parts.append(f"RSI: {rsi:.0f} (Oversold!)")
            elif rsi > 65:
                message_parts.append(f"RSI: {rsi:.0f} (Overbought!)")
            else:
                message_parts.append(f"RSI: {rsi:.0f}")
        
        if volume_ratio and volume_ratio > 1.5:
            message_parts.append(f"Volume: {volume_ratio:.1f}x avg (SPIKE!)")
        
        message_parts.append(f"Momentum: {momentum:.0f}/100")
        
        message = "\n".join(message_parts)
        
        return title, message
    
    def _send_windows_notification(self, title, message):
        """Send Windows toast notification"""
        if not self.windows_toast_available or not self.toaster:
            # Fallback to console
            print(f"\n{'='*60}")
            print(f"📢 NOTIFICATION: {title}")
            print(f"{message}")
            print(f"{'='*60}\n")
            return True
        
        try:
            # Send Windows notification (non-blocking)
            self.toaster.show_toast(
                title,
                message,
                duration=10,  # Show for 10 seconds
                icon_path=None,
                threaded=True  # Don't block
            )
            return True
        except Exception as e:
            print(f"Notification error: {e}")
            return False
    
    def _epic_to_friendly_name(self, epic):
        """Convert epic to friendly instrument name"""
        name_map = {
            'CS.D.USCGC.TODAY.IP': 'Gold',
            'CS.D.USCGC.DAILY.IP': 'Gold',
            'IX.D.RUSSELL.DAILY.IP': 'Russell 2000',
            'IX.D.FTSE.DAILY.IP': 'FTSE 100',
            'IX.D.SPTRD.DAILY.IP': 'S&P 500',
            'IX.D.DOW.DAILY.IP': 'Dow Jones',
            'IX.D.NASDAQ.DAILY.IP': 'NASDAQ',
            'IX.D.DAX.DAILY.IP': 'DAX',
            'IX.D.NIKKEI.DAILY.IP': 'Nikkei 225',
            'CS.D.USCRD.TODAY.IP': 'Crude Oil',
            'CS.D.USSLV.TODAY.IP': 'Silver',
            'CS.D.NGCUSD.TODAY.IP': 'Natural Gas',
        }
        
        return name_map.get(epic, epic)
    
    def enable(self):
        """Enable notifications"""
        self.enabled = True
    
    def disable(self):
        """Disable notifications"""
        self.enabled = False
    
    def set_cooldown(self, seconds):
        """Set cooldown period between notifications"""
        self.cooldown_period = seconds
    
    def test_notification(self):
        """Send a test notification"""
        test_data = {
            'epic': 'CS.D.USCGC.TODAY.IP',
            'timeframe': '3m',
            'current_price': 2650.50,
            'change_1_bar': 1.2,
            'change_5_bars': 2.8,
            'rsi': 72,
            'momentum_score': 85,
            'volume_ratio': 2.3
        }
        
        return self.send_rally_notification(test_data)