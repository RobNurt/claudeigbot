"""
Watchlist Manager
Manages user's watchlist of instruments to monitor
"""
import json
import os


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
                self.watchlist = []
        else:
            # Create default watchlist
            self.watchlist = [
                {
                    'epic': 'CS.D.USCGC.TODAY.IP',
                    'name': 'Gold',
                    'added': '2025-11-10'
                },
                {
                    'epic': 'IX.D.RUSSELL.DAILY.IP',
                    'name': 'Russell 2000',
                    'added': '2025-11-10'
                }
            ]
            self.save()
    
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


# Import datetime for the add method
from datetime import datetime