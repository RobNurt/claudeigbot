"""
Instrument Groups Manager
Allows creating, saving, and loading groups of instruments for batch trading
"""

import json
import os
from typing import Dict, List, Optional


class InstrumentGroups:
    """Manages groups of instruments for batch trading"""
    
    def __init__(self, filename: str = "instrument_groups.json"):
        self.filename = filename
        self.groups: Dict[str, List[str]] = {}
        self.load_groups()
    
    def load_groups(self) -> None:
        """Load instrument groups from JSON file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.groups = json.load(f)
                print(f"✅ Loaded {len(self.groups)} instrument groups")
            except Exception as e:
                print(f"⚠️ Error loading groups: {e}")
                self.groups = {}
        else:
            # Create default groups
            self.groups = {
                "Commodities": ["CS.D.GOLD.TODAY.IP", "CC.D.RUS.USS.IP"],
                "Major Indices": ["IX.D.FTSE.DAILY.IP", "IX.D.DAX.DAILY.IP", "IX.D.DOW.DAILY.IP"],
            }
            self.save_groups()
    
    def save_groups(self) -> None:
        """Save instrument groups to JSON file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.groups, f, indent=2)
            print(f"✅ Saved {len(self.groups)} instrument groups")
        except Exception as e:
            print(f"⚠️ Error saving groups: {e}")
    
    def create_group(self, name: str, epics: List[str]) -> bool:
        """Create a new instrument group"""
        if not name or not epics:
            return False
        
        self.groups[name] = epics
        self.save_groups()
        return True
    
    def delete_group(self, name: str) -> bool:
        """Delete an instrument group"""
        if name in self.groups:
            del self.groups[name]
            self.save_groups()
            return True
        return False
    
    def update_group(self, name: str, epics: List[str]) -> bool:
        """Update an existing group"""
        if name in self.groups:
            self.groups[name] = epics
            self.save_groups()
            return True
        return False
    
    def get_group(self, name: str) -> Optional[List[str]]:
        """Get instruments in a group"""
        return self.groups.get(name)
    
    def get_all_groups(self) -> List[str]:
        """Get all group names"""
        return list(self.groups.keys())
    
    def rename_group(self, old_name: str, new_name: str) -> bool:
        """Rename a group"""
        if old_name in self.groups and new_name:
            self.groups[new_name] = self.groups.pop(old_name)
            self.save_groups()
            return True
        return False