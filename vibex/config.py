"""
Configuration management for Vibex SDK
Loads VIBEX_TOKEN and VIBEX_SESSION_ID from environment variables
"""

import os
from typing import Optional


class VibexConfig:
    """Configuration for Vibex SDK"""
    
    def __init__(self):
        self.token: Optional[str] = os.getenv('VIBEX_TOKEN')
        self.session_id: Optional[str] = os.getenv('VIBEX_SESSION_ID')
        self.api_url: str = os.getenv('VIBEX_API_URL', 'https://vibex.sh/api/v1/ingest')
        
    def is_valid(self) -> bool:
        """Check if configuration is valid (both token and session_id present)"""
        return bool(self.token and self.session_id)
    
    def get_missing(self) -> list[str]:
        """Get list of missing configuration variables"""
        missing = []
        if not self.token:
            missing.append('VIBEX_TOKEN')
        if not self.session_id:
            missing.append('VIBEX_SESSION_ID')
        return missing

