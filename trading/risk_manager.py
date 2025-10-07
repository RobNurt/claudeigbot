"""
Risk Management System
Monitors account status and enforces trading limits
"""
import time
from datetime import datetime, timedelta


class RiskManager:
    """Risk management and position monitoring"""

    def __init__(self, ig_client):
        self.ig_client = ig_client

        # Risk limits - adjust these to your comfort level
        self.max_daily_loss = 200.0  # GBP - adjust based on your account size
        self.max_position_size = 5.0  # Maximum size per position
        self.max_total_exposure = 1000.0  # Total notional exposure limit
        self.max_margin_usage = 0.3  # 30% maximum margin usage
        self.max_positions = 10  # Maximum number of open positions

        # Daily tracking
        self.daily_start_balance = None
        self.session_start_time = datetime.now()

        def calculate_required_margin(self, epic, size):
            """Estimate margin required for a new position"""
            try:
                # Get market info to find margin factor
                url = f"{self.ig_client.base_url}/markets/{epic}"
                response = self.ig_client.session.get(url)

                if response.status_code == 200:
                    data = response.json()
                    dealing_rules = data.get('dealingRules', {})
                    margin_factor = float(dealing_rules.get(
                        'marketOrderPreference', {}).get('marginFactor', 0.05))

                    # Get current price
                    price_data = self.ig_client.get_market_price(epic)
                    if price_data and price_data['mid']:
                        notional_value = size * price_data['mid']
                        required_margin = notional_value * margin_factor
                        return required_margin

                return None
            except Exception as e:
                print(f"Margin calculation error: {e}")
                return None

    def check_margin_for_order(self, epic, size, margin_limit=0.3):
        """Check if placing this order would exceed margin limit"""
        account_info = self.get_account_info()
        if not account_info:
            return False, "Cannot check margin - account info unavailable", None

        required_margin = self.calculate_required_margin(epic, size)
        if required_margin is None:
            return False, "Cannot calculate required margin", None

        available = account_info['available']
        total_funds = account_info['deposit']

        if total_funds > 0:
            current_margin_used = total_funds - available
            new_margin_used = current_margin_used + required_margin
            new_margin_ratio = new_margin_used / total_funds

            would_exceed = new_margin_ratio > margin_limit

            return not would_exceed, new_margin_ratio, required_margin

        return False, "Cannot calculate margin", None

    def get_account_info(self):
        """Get account balance and margin info"""
        try:
            url = f"{self.ig_client.base_url}/accounts"
            response = self.ig_client.session.get(url)

            if response.status_code == 200:
                accounts = response.json().get('accounts', [])
                if accounts:
                    account = accounts[0]  # Primary account
                    return {
                        'balance': float(account.get('balance', {}).get('balance', 0)),
                        'available': float(account.get('balance', {}).get('available', 0)),
                        'deposit': float(account.get('balance', {}).get('deposit', 0)),
                        'profit_loss': float(account.get('balance', {}).get('profitLoss', 0))
                    }
            return None

        except Exception as e:
            print(f"Account info error: {e}")
            return None

    def calculate_daily_pnl(self):
        """Calculate profit/loss for today"""
        account_info = self.get_account_info()
        if not account_info:
            return None

        # Initialize daily start balance if not set
        if self.daily_start_balance is None:
            self.daily_start_balance = account_info['balance'] - \
                account_info['profit_loss']

        current_balance = account_info['balance']
        daily_pnl = current_balance - self.daily_start_balance

        return {
            'daily_pnl': daily_pnl,
            'current_balance': current_balance,
            'start_balance': self.daily_start_balance,
            'unrealized_pnl': account_info['profit_loss']
        }
    
    def check_margin_for_order(self, epic, size, margin_limit=0.3):
        """Check if placing this order would exceed margin limit"""
        account_info = self.get_account_info()
        if not account_info:
            return True, None, None  # Can't check, allow it
        
        balance = account_info['balance']
        current_margin = account_info['deposit']
        
        if balance <= 0:
            return True, None, None
        
        # Get current price to estimate required margin
        price_data = self.ig_client.get_market_price(epic)
        if not price_data or not price_data['mid']:
            return True, None, None  # Can't estimate, allow it
        
        # Rough estimate: margin = 5% of notional value for most instruments
        # (This is approximate - actual margin varies by instrument)
        notional_value = size * price_data['mid']
        estimated_margin_required = notional_value * 0.05
        
        new_total_margin = current_margin + estimated_margin_required
        new_margin_ratio = new_total_margin / balance
        
        would_exceed = new_margin_ratio > margin_limit
        
        return not would_exceed, new_margin_ratio, estimated_margin_required

    def check_position_limits(self, proposed_size, epic=None):
        """Check if new position would exceed limits"""
        positions = self.ig_client.get_open_positions()

        # Check maximum positions
        if len(positions) >= self.max_positions:
            return False, f"Maximum positions limit reached ({self.max_positions})"

        # Check individual position size
        if proposed_size > self.max_position_size:
            return False, f"Position size {proposed_size} exceeds maximum {self.max_position_size}"

        # Calculate total exposure
        total_exposure = 0
        for pos in positions:
            pos_data = pos.get('position', {})
            market_data = pos.get('market', {})

            size = pos_data.get('dealSize', 0)
            current_price = market_data.get(
                'offer', 0)  # Conservative estimate

            if size and current_price:
                total_exposure += abs(size * current_price)

        # Add proposed position exposure (estimate)
        if epic:
            price_data = self.ig_client.get_market_price(epic)
            if price_data and price_data['mid']:
                proposed_exposure = abs(proposed_size * price_data['mid'])
                total_exposure += proposed_exposure

        if total_exposure > self.max_total_exposure:
            return False, f"Total exposure {total_exposure:.2f} exceeds limit {self.max_total_exposure}"

        return True, "Position limits OK"

    def check_daily_loss_limit(self):
        """Check if daily loss limit has been breached"""
        pnl_data = self.calculate_daily_pnl()
        if not pnl_data:
            return True, "Cannot calculate P&L"

        daily_pnl = pnl_data['daily_pnl']

        if daily_pnl <= -self.max_daily_loss:
            return False, f"Daily loss limit breached: {daily_pnl:.2f} GBP (limit: {self.max_daily_loss})"

        return True, f"Daily P&L: {daily_pnl:.2f} GBP"

    def check_margin_usage(self):
        """Check margin usage against limits"""
        account_info = self.get_account_info()
        if not account_info:
            return True, "Cannot check margin"

        available = account_info['available']
        total_funds = account_info['deposit']

        if total_funds > 0:
            margin_used = total_funds - available
            margin_usage_ratio = margin_used / total_funds

            if margin_usage_ratio > self.max_margin_usage:
                return False, f"Margin usage {margin_usage_ratio:.1%} exceeds limit {self.max_margin_usage:.1%}"

            return True, f"Margin usage: {margin_usage_ratio:.1%}"

        return True, "Margin check inconclusive"

    def can_trade(self, proposed_size=1.0, epic=None):
        """Comprehensive trading safety check"""
        checks = []
        overall_safe = True

        # Daily loss check
        loss_ok, loss_msg = self.check_daily_loss_limit()
        checks.append(("Daily Loss", loss_ok, loss_msg))
        if not loss_ok:
            overall_safe = False

        # Position limits check
        pos_ok, pos_msg = self.check_position_limits(proposed_size, epic)
        checks.append(("Position Limits", pos_ok, pos_msg))
        if not pos_ok:
            overall_safe = False

        # Margin check
        margin_ok, margin_msg = self.check_margin_usage()
        checks.append(("Margin Usage", margin_ok, margin_msg))
        if not margin_ok:
            overall_safe = False

        return overall_safe, checks

    def get_risk_summary(self):
        """Get comprehensive risk summary for display"""
        account_info = self.get_account_info()
        pnl_data = self.calculate_daily_pnl()
        positions = self.ig_client.get_open_positions()

        summary = {
            'account_balance': account_info['balance'] if account_info else 0,
            'available_funds': account_info['available'] if account_info else 0,
            'daily_pnl': pnl_data['daily_pnl'] if pnl_data else 0,
            'unrealized_pnl': pnl_data['unrealized_pnl'] if pnl_data else 0,
            'open_positions': len(positions),
            'max_positions': self.max_positions,
            'daily_loss_limit': self.max_daily_loss,
            'position_size_limit': self.max_position_size
        }

        return summary

    def reset_daily_tracking(self):
        """Reset daily tracking (call at start of trading day)"""
        self.daily_start_balance = None
        self.session_start_time = datetime.now()
