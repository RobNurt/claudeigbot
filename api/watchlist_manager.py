"""
Watchlist Manager
Manages user's watchlist of instruments to monitor
"""
import json
import os
from datetime import datetime


class WatchlistManager:
    """Manages watchlist of instruments"""
    
    def __init__(self, watchlist_file='watchlist.json'):
        self.watchlist_file = watchlist_file
        self.watchlist = []
        self.load()
    
    def load(self):
        """Load watchlist from file"""
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r') as f:
                    data = json.load(f)
                    self.watchlist = data.get('instruments', [])
            except Exception as e:
                print(f"Error loading watchlist: {e}")
                self.watchlist = self._get_default_watchlist()
                self.save()
        else:
            # Create default watchlist with major instruments
            self.watchlist = self._get_default_watchlist()
            self.save()
    
    def _get_default_watchlist(self):
        """Get default watchlist with major commodities and indices"""
        return [
            # Commodities
            {
                'epic': 'CS.D.USCGC.TODAY.IP',
                'name': 'Gold',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'CS.D.USSLV.TODAY.IP',
                'name': 'Silver',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'CS.D.USCRD.TODAY.IP',
                'name': 'Crude Oil',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'CS.D.NGCUSD.TODAY.IP',
                'name': 'Natural Gas',
                'added': str(datetime.now().date())
            },
            # Major US Indices
            {
                'epic': 'IX.D.SPTRD.DAILY.IP',
                'name': 'S&P 500',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'IX.D.DOW.DAILY.IP',
                'name': 'Dow Jones',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'IX.D.NASDAQ.DAILY.IP',
                'name': 'NASDAQ',
                'added': str(datetime.now().date())
            },
            {
                'epic': 'IX.D.RUSSELL.DAILY.IP',
                'name': 'Russell 2000',
                'added': str(datetime.now().date())
            },
            # UK Indices
            {
                'epic': 'IX.D.FTSE.DAILY.IP',
                'name': 'FTSE 100',
                'added': str(datetime.now().date())
            },
            # European Indices
            {
                'epic': 'IX.D.DAX.DAILY.IP',
                'name': 'DAX',
                'added': str(datetime.now().date())
            },
            # Asian Indices
            {
                'epic': 'IX.D.NIKKEI.DAILY.IP',
                'name': 'Nikkei 225',
                'added': str(datetime.now().date())
            },
        ]
    
    def save(self):
        """Save watchlist to file"""
        try:
            data = {'instruments': self.watchlist}
            with open(self.watchlist_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving watchlist: {e}")
            return False
    
    def add(self, epic, name=None):
        """Add instrument to watchlist"""
        # Check if already in watchlist
        if any(item['epic'] == epic for item in self.watchlist):
            return False, "Already in watchlist"
        
        instrument = {
            'epic': epic,
            'name': name or epic,
            'added': str(datetime.now().date())
        }
        
        self.watchlist.append(instrument)
        self.save()
        return True, "Added to watchlist"
    
    def remove(self, epic):
        """Remove instrument from watchlist"""
        original_length = len(self.watchlist)
        self.watchlist = [item for item in self.watchlist if item['epic'] != epic]
        
        if len(self.watchlist) < original_length:
            self.save()
            return True, "Removed from watchlist"
        else:
            return False, "Not in watchlist"
    
    def get_all(self):
        """Get all instruments in watchlist"""
        return self.watchlist
    
    def get_epics(self):
        """Get list of epic codes"""
        return [item['epic'] for item in self.watchlist]
    
    def is_in_watchlist(self, epic):
        """Check if instrument is in watchlist"""
        return any(item['epic'] == epic for item in self.watchlist)
    
    def clear(self):
        """Clear entire watchlist"""
        self.watchlist = []
        self.save()
    
    def reset_to_default(self):
        """Reset watchlist to default instruments"""
        self.watchlist = self._get_default_watchlist()
        self.save()