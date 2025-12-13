"""
Vibex Client
Handles HTTP requests to the Vibex ingest API
"""

import time
import logging
from typing import Optional, Dict, Any
from .config import VibexConfig

logger = logging.getLogger(__name__)


class VibexClient:
    """Client for sending logs to Vibex API"""
    
    def __init__(self, config: Optional[VibexConfig] = None):
        self.config = config or VibexConfig()
        self.disabled = False
        self.disabled_permanently = False
        
        if not self.config.is_valid():
            missing = self.config.get_missing()
            logger.debug(f'Vibex SDK disabled: Missing configuration: {", ".join(missing)}')
            self.disabled = True
    
    def send_log(self, log_type: str, payload: Any, timestamp: Optional[int] = None) -> bool:
        """
        Send a log to the Vibex API
        
        Args:
            log_type: Type of log ('json' or 'text')
            payload: Log payload (dict for json, str for text)
            timestamp: Optional timestamp in milliseconds
        
        Returns:
            True if sent successfully, False otherwise
        """
        if self.disabled or self.disabled_permanently:
            return False
        
        if not self.config.is_valid():
            self.disabled = True
            return False
        
        try:
            import requests
            
            url = self.config.api_url
            headers = {
                'Authorization': f'Bearer {self.config.token}',
                'Content-Type': 'application/json',
            }
            
            body = {
                'sessionId': self.config.session_id,
                'logs': [{
                    'type': log_type,
                    'payload': payload,
                    'timestamp': timestamp or int(time.time() * 1000),
                }],
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=5)
            
            # Handle 403/401 - permanently disable
            if response.status_code in (401, 403):
                logger.warning('Vibex SDK permanently disabled: Token expired or invalid')
                self.disabled_permanently = True
                return False
            
            # Handle 429 - rate limit exceeded, retry with backoff
            if response.status_code == 429:
                logger.warning('Vibex SDK: Rate limit exceeded, dropping log')
                return False
            
            # Handle 404 - session not found
            if response.status_code == 404:
                logger.warning('Vibex SDK: Session not found, dropping log')
                return False
            
            # Handle other errors
            if not response.ok:
                logger.warning(f'Vibex SDK: Failed to send log: {response.status_code}')
                return False
            
            return True
            
        except Exception as e:
            # Fail-safe: silently handle all errors
            logger.debug(f'Vibex SDK: Error sending log: {e}')
            return False
    
    def is_enabled(self) -> bool:
        """Check if client is enabled and can send logs"""
        return not self.disabled and not self.disabled_permanently and self.config.is_valid()

