"""
Vibex Logging Handler
Python logging.Handler implementation for Vibex
"""

import json
import logging
from .client import VibexClient
from .config import VibexConfig


class VibexHandler(logging.Handler):
    """Python logging handler that sends logs to Vibex"""
    
    def __init__(self, config: VibexConfig = None, verbose: bool = False):
        """
        Initialize VibexHandler
        
        Args:
            config: Optional VibexConfig instance. If None, loads from environment.
            verbose: If True, print status messages to stderr when handler is initialized or errors occur.
        """
        super().__init__()
        self.client = VibexClient(config, verbose=verbose)
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Vibex
        
        Args:
            record: LogRecord from Python logging
        """
        if not self.client.is_enabled():
            return
        
        try:
            # Get the actual message content
            if hasattr(record, 'getMessage'):
                message = record.getMessage()
            else:
                message = str(record.msg)
            
            # Try to parse message as JSON - if it's JSON, use it directly as payload
            # Discard non-JSON logs entirely (only send structured JSON data)
            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict):
                    # Message is a JSON object - use it as the payload directly
                    payload = parsed
                    
                    # Add exception info if present
                    if record.exc_info:
                        payload['exc_info'] = self.formatException(record.exc_info)
                    
                    # Send as JSON log
                    self.client.send_log('json', payload, int(record.created * 1000))
                # If parsed is not a dict (string, number, etc.), discard it
            except (json.JSONDecodeError, TypeError):
                # Message is not JSON - discard it completely
                pass
            
        except Exception:
            # Fail-safe: silently ignore all errors
            self.handleError(record)
    
    def is_enabled(self) -> bool:
        """Check if handler is enabled"""
        return self.client.is_enabled()
    
    def get_status(self) -> dict:
        """
        Get detailed status information about the handler
        
        Returns:
            dict with status information
        """
        return self.client.get_status()
    
    def print_status(self):
        """Print current handler status to stderr"""
        self.client.print_status()

