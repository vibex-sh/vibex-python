"""
Vibex Logging Handler
Python logging.Handler implementation for Vibex
Phase 1.7: Updated to support hybrid JSON structure and text logs
"""

import json
import logging
import sys
from .client import VibexClient
from .config import VibexConfig
from .normalize import normalize_to_hybrid, normalize_level


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
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Vibex
        Phase 1.7: Always constructs hybrid JSON structure, supports text logs
        
        Args:
            record: LogRecord from Python logging
        """
        try:
            # Get the actual message content
            if hasattr(record, 'getMessage'):
                message = record.getMessage()
            else:
                message = str(record.msg)
            
            # Extract level from record
            level = normalize_level(record.levelname)
            
            # Get extra fields from record
            extra = {}
            if hasattr(record, '__dict__'):
                # Filter out standard logging fields
                standard_fields = {
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'message', 'pathname', 'process', 'processName', 'relativeCreated',
                    'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
                }
                for key, value in record.__dict__.items():
                    if key not in standard_fields:
                        extra[key] = value
            
            # Try to parse message as JSON
            payload = None
            is_text_log = False
            
            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict):
                    # Message is a JSON object - use it as payload
                    payload = parsed.copy()
                else:
                    # Parsed but not a dict - treat as text
                    is_text_log = True
            except (json.JSONDecodeError, TypeError):
                # Message is not JSON - treat as text log
                is_text_log = True
            
            # Normalize to hybrid structure
            if is_text_log:
                # Text log: send message as-is, level from logger
                hybrid = {
                    'message': message,  # Text content
                    'level': level,
                    'metrics': {},
                    'context': {},
                }
            else:
                # JSON log: normalize to hybrid structure
                hybrid = normalize_to_hybrid(
                    message=message,
                    level=level,
                    payload=payload or {},
                    extra=extra
                )
            
            # Add exception info if present
            if record.exc_info:
                hybrid['exc_info'] = self.formatException(record.exc_info)
            
            # Track whether we should write to console
            should_write_to_console = self.passthrough_console
            send_succeeded = False
            
            # Try to send to Vibex if enabled
            if self.client.is_enabled():
                send_succeeded = self.client.send_log('json', hybrid, int(record.created * 1000))
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
                        **hybrid
                    }
                    # Pretty-print JSON for elegant console output
                    formatted_json = json.dumps(console_output, indent=2, sort_keys=False, ensure_ascii=False)
                    print(formatted_json, file=sys.stderr, flush=True)
                except Exception:
                    # Fail-safe: silently ignore console write errors
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

