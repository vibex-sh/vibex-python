"""
Vibex Logging Handler
Python logging.Handler implementation for Vibex
"""

import json
import logging
import sys
from .client import VibexClient
from .config import VibexConfig


class VibexHandler(logging.Handler):
    """Python logging handler that sends logs to Vibex"""
    
    def __init__(self, config: VibexConfig = None, verbose: bool = False, 
                 passthrough_console: bool = True, passthrough_on_failure: bool = False):
        """
        Initialize VibexHandler
        
        Args:
            config: Optional VibexConfig instance. If None, loads from environment.
            verbose: If True, print status messages to stderr when handler is initialized or errors occur.
            passthrough_console: If True, always write logs to stderr in addition to sending to Vibex (default: True).
            passthrough_on_failure: If True, write logs to stderr when sending to Vibex fails (default: False).
        """
        super().__init__()
        self.client = VibexClient(config, verbose=verbose)
        self.passthrough_console = passthrough_console
        self.passthrough_on_failure = passthrough_on_failure
        
        # Prevent propagation to other handlers when console passthrough is enabled
        # to avoid duplicate log output (we handle console output ourselves)
        if passthrough_console:
            self.propagate = False
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Vibex
        
        Args:
            record: LogRecord from Python logging
        """
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
                    payload = parsed.copy()
                    
                    # Add exception info if present
                    if record.exc_info:
                        payload['exc_info'] = self.formatException(record.exc_info)
                    
                    # Track whether we should write to console
                    should_write_to_console = self.passthrough_console
                    send_succeeded = False
                    
                    # Try to send to Vibex if enabled
                    if self.client.is_enabled():
                        send_succeeded = self.client.send_log('json', payload, int(record.created * 1000))
                        # If passthrough_on_failure is enabled and sending failed, write to console
                        if self.passthrough_on_failure and not send_succeeded:
                            should_write_to_console = True
                    elif self.passthrough_on_failure:
                        # Client is disabled, treat as failure
                        should_write_to_console = True
                    
                    # Write to console if needed
                    if should_write_to_console:
                        try:
                            # Format payload with timestamp for console output
                            console_output = {
                                'timestamp': int(record.created * 1000),
                                **payload
                            }
                            # Pretty-print JSON for elegant console output
                            formatted_json = json.dumps(console_output, indent=2, sort_keys=False, ensure_ascii=False)
                            print(formatted_json, file=sys.stderr, flush=True)
                        except Exception:
                            # Fail-safe: silently ignore console write errors
                            pass
                    
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

