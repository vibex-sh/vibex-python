"""
Vibex Client
Handles HTTP requests to the Vibex ingest API with async batching for performance
"""

import time
import logging
import sys
import queue
import threading
import atexit
from typing import Optional, Dict, Any, List, Tuple
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

# Batch configuration
BATCH_SIZE = 50  # Max logs per batch
BATCH_INTERVAL_MS = 100  # Max time to wait before sending batch (milliseconds)
MAX_QUEUE_SIZE = 1000  # Prevent memory issues


class VibexClient:
    """Client for sending logs to Vibex API with async batching"""
    
    def __init__(self, config: Optional[VibexConfig] = None, verbose: bool = False):
        self.config = config or VibexConfig()
        self.disabled = False
        self.disabled_permanently = False
        self.verbose = verbose
        self._initialization_message_shown = False
        
        # Batching queue and worker thread
        self._log_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._worker_thread = None
        self._shutdown_event = threading.Event()
        self._worker_started = False
        self._last_batch_time = time.time()
        
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
            
            # Start background worker thread
            self._start_worker()
            # Register graceful shutdown
            atexit.register(self.flush)
    
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
        session = _format_field(self.config.get_session_id())
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
    
    def _start_worker(self):
        """Start background worker thread for processing log batches"""
        if self._worker_started or self.disabled or self.disabled_permanently:
            return
        
        self._worker_started = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.debug('Vibex SDK: Background worker thread started')
    
    def _worker_loop(self):
        """Background worker loop that processes log batches"""
        batch: List[Tuple[str, Any, int]] = []
        
        while not self._shutdown_event.is_set():
            try:
                # Try to get a log with timeout
                timeout = BATCH_INTERVAL_MS / 1000.0  # Convert to seconds
                try:
                    log_entry = self._log_queue.get(timeout=timeout)
                    batch.append(log_entry)
                    self._log_queue.task_done()
                except queue.Empty:
                    # Timeout - send batch if not empty
                    pass
                
                # Check if we should send batch (size limit or time limit)
                current_time = time.time()
                should_send = (
                    len(batch) >= BATCH_SIZE or
                    (batch and (current_time - self._last_batch_time) >= (BATCH_INTERVAL_MS / 1000.0))
                )
                
                if should_send and batch:
                    self._send_batch(batch)
                    batch = []
                    self._last_batch_time = current_time
                    
            except Exception as e:
                logger.debug(f'Vibex SDK: Error in worker loop: {e}')
                # Continue processing even on errors
                batch = []
        
        # Flush remaining batch on shutdown
        if batch:
            self._send_batch(batch)
    
    def _send_batch(self, batch: List[Tuple[str, Any, int]]):
        """Send a batch of logs to the API"""
        if not batch or self.disabled or self.disabled_permanently:
            return
        
        if not self.config.is_valid():
            self.disabled = True
            return
        
        try:
            import requests
            
            url = self.config.api_url
            session_id = self.config.get_session_id()
            
            # Build logs array from batch
            logs = []
            for log_type, payload, timestamp in batch:
                logs.append({
                    'type': log_type,
                    'payload': payload,
                    'timestamp': timestamp,
                })
            
            body = {
                'sessionId': session_id,
                'logs': logs,
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.token}',
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=5)
            
            # Handle 403/401 - permanently disable
            if response.status_code in (401, 403):
                error_msg = '🚫 Vibex SDK permanently disabled: Token expired or invalid (401/403)'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                self.disabled_permanently = True
                return
            
            # Handle 429 - rate limit exceeded or history limit reached
            if response.status_code == 429:
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Rate limit exceeded')
                    error_type = error_data.get('error', 'Rate limit exceeded')
                    
                    if 'History Limit' in error_type or 'history limit' in error_message.lower():
                        error_msg = f'🚫 Vibex SDK: {error_message}'
                        self.disabled_permanently = True
                    else:
                        error_msg = f'⚠️  Vibex SDK: {error_message}'
                except:
                    error_msg = '⚠️  Vibex SDK: Rate limit exceeded, dropping batch'
                
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return
            
            # Handle 404 - session not found
            if response.status_code == 404:
                error_msg = '⚠️  Vibex SDK: Session not found (404), dropping batch'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return
            
            # Handle other errors
            if not response.ok:
                error_msg = f'⚠️  Vibex SDK: Failed to send batch: {response.status_code}'
                if self.verbose:
                    self._print_status(error_msg)
                logger.warning(error_msg)
                return
            
            logger.debug(f'Vibex SDK: Successfully sent batch of {len(batch)} logs')
            
        except Exception as e:
            error_msg = f'⚠️  Vibex SDK: Error sending batch: {e}'
            if self.verbose:
                self._print_status(error_msg)
            logger.debug(error_msg)
    
    def send_log(self, log_type: str, payload: Any, timestamp: Optional[int] = None) -> bool:
        """
        Queue a log to be sent to the Vibex API (non-blocking)
        
        Args:
            log_type: Type of log ('json' or 'text')
            payload: Log payload (dict for json, str for text)
            timestamp: Optional timestamp in milliseconds
        
        Returns:
            True if queued successfully, False otherwise
        """
        if self.disabled or self.disabled_permanently:
            return False
        
        if not self.config.is_valid():
            self.disabled = True
            return False
        
        # Ensure worker is running
        if not self._worker_started:
            self._start_worker()
        
        try:
            # Queue the log (non-blocking if queue is full, it will drop)
            log_entry = (log_type, payload, timestamp or int(time.time() * 1000))
            self._log_queue.put_nowait(log_entry)
            return True
        except queue.Full:
            # Queue is full - drop log to prevent memory issues
            logger.debug('Vibex SDK: Log queue full, dropping log')
            return False
        except Exception as e:
            logger.debug(f'Vibex SDK: Error queueing log: {e}')
            return False
    
    def flush(self):
        """
        Flush all queued logs immediately (blocking)
        Useful for graceful shutdown or ensuring logs are sent
        """
        if not self._worker_started:
            return
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for queue to be processed
        try:
            self._log_queue.join(timeout=2.0)  # Wait up to 2 seconds
        except:
            pass
        
        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
    
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
            'queue_size': self._log_queue.qsize(),
            'worker_running': self._worker_started and self._worker_thread and self._worker_thread.is_alive(),
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
            session_id = self.config.get_session_id()
            status['session_id'] = session_id[:10] + '...' if session_id else None
            status['token_prefix'] = self.config.token[:10] + '...' if self.config.token else None
        
        return status
    
    def print_status(self):
        """Print current status to stderr"""
        status = self.get_status()
        if status['enabled']:
            queue_size = status.get('queue_size', 0)
            queue_info = f" (queue: {queue_size})" if queue_size > 0 else ""
            print(f"✅ Vibex SDK: Enabled and ready{queue_info}", file=sys.stderr)
        else:
            print(f"⚠️  Vibex SDK: {status['reason']}", file=sys.stderr)
