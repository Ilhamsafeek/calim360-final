"""
Datetime formatting utilities
"""
from datetime import datetime
from typing import Optional


def format_datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO format with UTC timezone indicator
    
    Args:
        dt: datetime object or None
        
    Returns:
        ISO string with 'Z' suffix (e.g., "2025-01-09T10:30:00Z") or None
    """
    if dt is None:
        return None
    
    # Format as ISO with 'Z' to indicate UTC
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')