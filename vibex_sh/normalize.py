"""
Phase 1.7: Log Normalization
Intelligently transforms log records into hybrid JSON structure
"""

from typing import Dict, Any, Optional
import re


def normalize_level(level: Any) -> str:
    """Normalize log level from various formats"""
    if not level:
        return 'debug'
    
    level_str = str(level).upper()
    
    # Map common variations
    if level_str in ('DEBUG', 'DBG', 'TRACE'):
        return 'debug'
    if level_str in ('INFO', 'INFORMATION', 'LOG'):
        return 'info'
    if level_str in ('WARN', 'WARNING', 'WRN'):
        return 'warn'
    if level_str in ('ERROR', 'ERR', 'EXCEPTION', 'FATAL', 'CRITICAL'):
        return 'error'
    
    return 'debug'  # Default


def extract_metrics(payload: Dict[str, Any]) -> Dict[str, float]:
    """Extract metrics from payload (predictive)"""
    metrics: Dict[str, float] = {}
    
    if not payload or not isinstance(payload, dict):
        return metrics
    
    # If metrics object exists, use it
    if 'metrics' in payload and isinstance(payload['metrics'], dict):
        for key, value in payload['metrics'].items():
            if isinstance(value, (int, float)):
                metrics[key] = float(value)
        return metrics
    
    # Otherwise, predict from top-level numeric fields
    known_context_fields = {
        'trace_id', 'traceId', 'user_id', 'userId', 'request_id', 'requestId',
        'correlation_id', 'correlationId', 'span_id', 'spanId', 'session_id', 'sessionId',
        'id', 'pid', 'port', 'year', 'timestamp', 'time', 'date', 'createdAt', 'updatedAt',
        'datetime', 'ts', 'utc', 'iso', 'exc_info', 'exception', 'error'
    }
    
    for key, value in payload.items():
        key_lower = key.lower()
        
        # Skip known context fields
        if key_lower in known_context_fields:
            continue
        
        # Skip timestamp fields
        if 'timestamp' in key_lower or 'time' in key_lower or 'date' in key_lower:
            continue
        
        # Extract numeric values as potential metrics
        if isinstance(value, (int, float)):
            # Recognize common metric patterns
            if (key.endswith('_ms') or key.endswith('_count') or key.endswith('_size') or
                key.endswith('Ms') or key.endswith('Count') or key.endswith('Size') or
                any(pattern in key_lower for pattern in ['cpu', 'memory', 'latency', 'response_time', 'duration'])):
                metrics[key] = float(value)
    
    return metrics


def extract_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract context from payload (predictive)"""
    context: Dict[str, Any] = {}
    
    if not payload or not isinstance(payload, dict):
        return context
    
    # If context object exists, use it
    if 'context' in payload and isinstance(payload['context'], dict):
        return payload['context']
    
    # Otherwise, predict from known context fields
    known_context_fields = {
        'trace_id': 'trace_id',
        'traceId': 'trace_id',
        'user_id': 'user_id',
        'userId': 'user_id',
        'request_id': 'request_id',
        'requestId': 'request_id',
        'correlation_id': 'correlation_id',
        'correlationId': 'correlation_id',
        'span_id': 'span_id',
        'spanId': 'span_id',
        'session_id': 'session_id',
        'sessionId': 'session_id',
    }
    
    for field, normalized_key in known_context_fields.items():
        if field in payload:
            context[normalized_key] = payload[field]
    
    return context


def normalize_to_hybrid(
    message: Optional[str],
    level: Optional[str],
    payload: Optional[Dict[str, Any]],
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Normalize log record to hybrid JSON structure
    
    Args:
        message: Log message (can be None)
        level: Log level (can be None, will be normalized)
        payload: Log payload dict (can be None)
        extra: Extra fields from logger (can be None)
    
    Returns:
        Hybrid JSON structure with timestamp, message, level, metrics, context
    """
    # Merge payload and extra
    merged = {}
    if payload:
        merged.update(payload)
    if extra:
        merged.update(extra)
    
    # Extract message
    normalized_message = message
    if not normalized_message and 'message' in merged:
        normalized_message = merged.get('message')
    if not normalized_message and 'msg' in merged:
        normalized_message = merged.get('msg')
    # Don't invent default values - can be None
    
    # Extract and normalize level
    normalized_level = normalize_level(level or merged.get('level') or merged.get('severity') or merged.get('log_level'))
    
    # Extract metrics
    metrics = extract_metrics(merged)
    
    # Extract context
    context = extract_context(merged)
    
    # Extract annotation if present
    annotation = merged.get('_annotation')
    
    # Build hybrid structure
    hybrid = {
        'message': normalized_message,  # Can be None
        'level': normalized_level,
        'metrics': metrics,
        'context': context,
    }
    
    if annotation:
        hybrid['_annotation'] = annotation
    
    # Preserve original payload fields that aren't in hybrid structure
    # This allows backward compatibility
    for key, value in merged.items():
        if key not in ('message', 'msg', 'level', 'severity', 'log_level', 'metrics', 'context', '_annotation'):
            if key not in hybrid:
                hybrid[key] = value
    
    return hybrid

