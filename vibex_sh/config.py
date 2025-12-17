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
        
        # Determine API URL - use Worker URL (not web URL)
        # Match CLI architecture: use ingest endpoint on Worker
        api_url_env = os.getenv('VIBEX_API_URL')
        worker_url = os.getenv('VIBEX_WORKER_URL')
        
        if api_url_env:
            self.api_url = api_url_env
        elif worker_url:
            # Use explicit Worker URL if set
            self.api_url = f"{worker_url.rstrip('/')}/api/v1/ingest"
        else:
            # Production default - use Worker URL (not web URL)
            # For local development, set VIBEX_WORKER_URL=http://localhost:8787
            self.api_url = 'https://ingest.vibex.sh/api/v1/ingest'
        
    def _normalize_session_id(self, session_id: Optional[str]) -> Optional[str]:
        """Normalize session ID to always have vibex- prefix if missing"""
        if not session_id:
            return None
        # If it doesn't start with 'vibex-', add it
        if not session_id.startswith('vibex-'):
            return f'vibex-{session_id}'
        return session_id
    
    def is_valid(self) -> bool:
        """Check if configuration is valid (both token and session_id required)"""
        return bool(self.token and self.session_id)
    
    def get_missing(self) -> list[str]:
        """Get list of missing configuration variables"""
        missing = []
        if not self.token:
            missing.append('VIBEX_TOKEN')
        if not self.session_id:
            missing.append('VIBEX_SESSION_ID')
        return missing
    
    def get_session_id(self) -> Optional[str]:
        """Get normalized session ID"""
        return self._normalize_session_id(self.session_id)

