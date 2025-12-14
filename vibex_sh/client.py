"""
Vibex Client
Handles HTTP requests to the Vibex ingest API
"""

import time
import logging
import sys
from typing import Optional, Dict, Any
from .config import VibexConfig

logger = logging.getLogger(__name__)

# Suppress urllib3 and requests debug logs
# Disable propagation to prevent root logger level from affecting these loggers
# Set to WARNING level to suppress DEBUG and INFO messages
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.WARNING)
urllib3_logger.propagate = False

urllib3_connectionpool_logger = logging.getLogger('urllib3.connectionpool')
urllib3_connectionpool_logger.setLevel(logging.WARNING)
urllib3_connectionpool_logger.propagate = False

requests_logger = logging.getLogger('requests')
requests_logger.setLevel(logging.WARNING)
requests_logger.propagate = False


class VibexClient:
    """Client for sending logs to Vibex API"""
    
    def __init__(self, config: Optional[VibexConfig] = None, verbose: bool = False):
        self.config = config or VibexConfig()
        self.disabled = False
        self.disabled_permanently = False
        self.verbose = verbose
        self._initialization_message_shown = False
        
        if not self.config.is_valid():
            missing = self.config.get_missing()
            self.disabled = True
            if self.verbose:
                self._print_status(f"⚠️  Vibex SDK disabled: Missing configuration: {', '.join(missing)}")
            logger.debug(f'Vibex SDK disabled: Missing configuration: {", ".join(missing)}')
        else:
            self._print_startup_info()
            if self.verbose:
                self._print_status("✅ Vibex SDK enabled and ready")
                logger.debug('Vibex SDK enabled')
    
    def _mask_token(self, token: str) -> str:
        """Mask token for display (show first 6 chars, mask the rest)"""
        if not token or len(token) <= 6:
            return '******'
        return f"{token[:6]}{'*' * (len(token) - 6)}"
    
    def _print_startup_info(self):
        """Print elegant startup information about vibex.sh"""
        masked_token = self._mask_token(self.config.token)
        
        # Box width is 61 chars, "║  Server:  " is 11 chars, " ║" is 2 chars
        # So content width = 61 - 11 - 2 = 48 chars
        content_width = 48
        
        def _format_field(value: str) -> str:
            """Format field value to fit within content width"""
            if not value:
                return ' ' * content_width
            if len(value) > content_width:
                return value[:content_width]
            return value + ' ' * (content_width - len(value))
        
        server = _format_field(self.config.api_url)
        session = _format_field(self.config.session_id)
        token = _format_field(masked_token)
        
        lines = [
            "",
            "                    vibex.sh is in action                      ",
            "═══════════════════════════════════════════════════════════════",
            f"Server:  {server}",
            f"Session: {session}",
            f"Token:   {token}",
            "═══════════════════════════════════════════════════════════════",
            ""
        ]
        print("\n".join(lines), file=sys.stderr, flush=True)
        self._initialization_message_shown = True
    
    def _print_status(self, message: str):
        """Print status message to stderr (visible even when stdout is redirected)"""
        print(message, file=sys.stderr)
        self._initialization_message_shown = True
    
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
                error_msg = '🚫 Vibex SDK permanently disabled: Token expired or invalid (401/403)'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                self.disabled_permanently = True
                return False
            
            # Handle 429 - rate limit exceeded, retry with backoff
            if response.status_code == 429:
                error_msg = '⚠️  Vibex SDK: Rate limit exceeded, dropping log'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return False
            
            # Handle 404 - session not found
            if response.status_code == 404:
                error_msg = '⚠️  Vibex SDK: Session not found (404), dropping log'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return False
            
            # Handle other errors
            if not response.ok:
                error_msg = f'⚠️  Vibex SDK: Failed to send log: {response.status_code}'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return False
            
            return True
            
        except Exception as e:
            # Fail-safe: handle errors
            error_msg = f'⚠️  Vibex SDK: Error sending log: {e}'
            if self.verbose:
                self._print_status(error_msg)
            logger.debug(error_msg)
            return False
    
    def is_enabled(self) -> bool:
        """Check if client is enabled and can send logs"""
        return not self.disabled and not self.disabled_permanently and self.config.is_valid()
    
    def get_status(self) -> dict:
        """
        Get detailed status information about the client
        
        Returns:
            dict with status information including enabled state, reason if disabled, etc.
        """
        status = {
            'enabled': self.is_enabled(),
            'disabled': self.disabled,
            'disabled_permanently': self.disabled_permanently,
            'config_valid': self.config.is_valid(),
        }
        
        if not self.config.is_valid():
            status['missing_config'] = self.config.get_missing()
            status['reason'] = f"Missing configuration: {', '.join(self.config.get_missing())}"
        elif self.disabled_permanently:
            status['reason'] = 'Permanently disabled due to authentication error (401/403)'
        elif self.disabled:
            status['reason'] = 'Disabled'
        else:
            status['reason'] = 'Enabled and ready'
            status['api_url'] = self.config.api_url
            status['session_id'] = self.config.session_id[:10] + '...' if self.config.session_id else None
            status['token_prefix'] = self.config.token[:10] + '...' if self.config.token else None
        
        return status
    
    def print_status(self):
        """Print current status to stderr"""
        status = self.get_status()
        if status['enabled']:
            print("✅ Vibex SDK: Enabled and ready", file=sys.stderr)
        else:
            print(f"⚠️  Vibex SDK: {status['reason']}", file=sys.stderr)

