"""
Vibex Logging Handler
Python logging.Handler implementation for Vibex
"""

import json
import logging
from typing import Any
from .client import VibexClient
from .config import VibexConfig


class VibexHandler(logging.Handler):
    """Python logging handler that sends logs to Vibex"""
    
    def __init__(self, config: VibexConfig = None):
        super().__init__()
        self.client = VibexClient(config)
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Vibex
        
        Args:
            record: LogRecord from Python logging
        """
        if not self.client.is_enabled():
            return
        
        try:
            # Format log message
            msg = self.format(record)
            
            # Create payload based on record type
            if hasattr(record, 'getMessage'):
                message = record.getMessage()
            else:
                message = str(record.msg)
            
            # Build payload with log record data
            payload = {
                'message': message,
                'level': record.levelname,
                'levelno': record.levelno,
                'logger': record.name,
                'module': record.module,
                'funcName': record.funcName,
                'lineno': record.lineno,
                'pathname': record.pathname,
            }
            
            # Add exception info if present
            if record.exc_info:
                payload['exc_info'] = self.formatException(record.exc_info)
            
            # Add extra fields if present
            if hasattr(record, '__dict__'):
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                                  'levelname', 'levelno', 'lineno', 'module', 'msecs',
                                  'message', 'pathname', 'process', 'processName', 'relativeCreated',
                                  'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                        try:
                            # Try to serialize the value
                            json.dumps(value)
                            payload[key] = value
                        except (TypeError, ValueError):
                            # Skip non-serializable values
                            pass
            
            # Send as JSON log
            self.client.send_log('json', payload, int(record.created * 1000))
            
        except Exception:
            # Fail-safe: silently ignore all errors
            self.handleError(record)
    
    def is_enabled(self) -> bool:
        """Check if handler is enabled"""
        return self.client.is_enabled()

