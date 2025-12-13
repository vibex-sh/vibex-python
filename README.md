# Vibex Python SDK

Fail-safe logging handler for sending logs to [vibex.sh](https://vibex.sh).

## Features

- **Fail-Safe**: Silently disables if configuration is missing or invalid
- **Kill Switch**: Permanently disables on 401/403 errors (expired/invalid tokens)
- **Easy Integration**: Drop-in Python logging handler
- **Zero Dependencies** (except `requests`)

## Installation

```bash
pip install vibex
```

## Quick Start

1. Set environment variables:
```bash
export VIBEX_TOKEN=vb_live_your_token_here
export VIBEX_SESSION_ID=my-production-app
```

2. Use in your Python application:
```python
import logging
from vibex import VibexHandler

# Get your logger
logger = logging.getLogger('my_app')

# Add Vibex handler
vibex_handler = VibexHandler()
logger.addHandler(vibex_handler)

# Use normally
logger.info('Application started')
logger.warning('High memory usage', extra={'memory': 85})
logger.error('Failed to connect', exc_info=True)
```

## Configuration

The SDK reads configuration from environment variables:

- `VIBEX_TOKEN` (required): Your Vibex API token
- `VIBEX_SESSION_ID` (required): Your session ID
- `VIBEX_API_URL` (optional): API endpoint (default: `https://vibex.sh/api/v1/ingest`)

## Fail-Safe Behavior

The SDK is designed to be fail-safe:

1. **Missing Config**: If `VIBEX_TOKEN` or `VIBEX_SESSION_ID` is missing, the handler silently disables itself
2. **Invalid Token**: On 401/403 responses, the handler permanently disables for the process lifetime
3. **Network Errors**: All network errors are silently handled - your application continues normally
4. **Rate Limits**: On 429 (rate limit), logs are dropped but the handler remains enabled

## Advanced Usage

### Direct Client Usage

```python
from vibex import VibexClient, VibexConfig

config = VibexConfig()
client = VibexClient(config)

# Send custom log
client.send_log('json', {'cpu': 45, 'memory': 78})
```

### Check if Enabled

```python
handler = VibexHandler()
if handler.is_enabled():
    logger.info('Vibex is active')
else:
    logger.info('Vibex is disabled (missing config or expired token)')
```

## License

MIT

