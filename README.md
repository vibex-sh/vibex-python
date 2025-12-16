# vibex.sh Python SDK

Fail-safe logging handler for sending logs to [vibex.sh](https://vibex.sh).

## Features

- **Fail-Safe**: Silently disables if configuration is missing or invalid
- **Kill Switch**: Permanently disables on 401/403 errors (expired/invalid tokens)
- **Easy Integration**: Drop-in Python logging handler
- **Zero Dependencies** (except `requests`)

## Installation

```bash
pip install vibex_sh
```

## Authentication

Before using the SDK, you need to get your authentication token. Run this command in your terminal:

```bash
npx vibex-sh login
```

This will generate your `VIBEX_TOKEN` that you'll use in the environment variables below.

## Quick Start

1. Set environment variables:
```bash
export VIBEX_TOKEN=vb_live_your_token_here
export VIBEX_SESSION_ID=my-production-app
```

2. Use in your Python application:
```python
import logging
import json
from vibex_sh import VibexHandler

# Get your logger
logger = logging.getLogger('my_app')

# Add Vibex handler
vibex_handler = VibexHandler()
logger.addHandler(vibex_handler)

# Send JSON logs (only JSON logs are sent to Vibex)
logger.info(json.dumps({'cpu': 45, 'memory': 78, 'status': 'healthy'}))
logger.info(json.dumps({'error': 'connection_failed', 'retry_count': 3}))
```

## Configuration

The SDK reads configuration from environment variables:

- `VIBEX_TOKEN` (required): Your Vibex API token
- `VIBEX_SESSION_ID` (required): Your session ID

## Fail-Safe Behavior

The SDK is designed to be fail-safe:

1. **Missing Config**: If `VIBEX_TOKEN` or `VIBEX_SESSION_ID` is missing, the handler silently disables itself
2. **Invalid Token**: On 401/403 responses, the handler permanently disables for the process lifetime
3. **Network Errors**: All network errors are silently handled - your application continues normally
4. **Rate Limits**: On 429 (rate limit), logs are dropped but the handler remains enabled. Logs are still written to console by default (`passthrough_console=True`)

## Console Passthrough Options

By default, logs are forwarded to Vibex and also written to `stderr` (console), ensuring you can always see your logs locally while they're sent to Vibex.

### `passthrough_console` (default: `True`)

When enabled (default), logs are always written to `stderr` in addition to being sent to Vibex. This provides visibility into your logs while forwarding them to Vibex.

```python
# Default behavior - logs written to console and sent to Vibex
vibex_handler = VibexHandler()  # passthrough_console=True by default
logger.addHandler(vibex_handler)

# To disable console output (logs only sent to Vibex)
vibex_handler = VibexHandler(passthrough_console=False)
logger.addHandler(vibex_handler)
```

**Note:** To avoid duplicate log output when using `passthrough_console=True`, either:
- Avoid using `logging.basicConfig()` which adds a default StreamHandler, or
- Configure your logger to not propagate: `logger.propagate = False`

### `passthrough_on_failure` (default: `False`)

When enabled, logs are written to `stderr` when sending to Vibex fails (rate limits, network errors, etc.). This is useful as an additional safety net, but with `passthrough_console=True` by default, it's typically not needed.

```python
# Write logs to console only when sending fails
vibex_handler = VibexHandler(passthrough_console=False, passthrough_on_failure=True)
logger.addHandler(vibex_handler)
```

**Important:** Non-JSON logs are still discarded (only JSON-formatted logs are processed).

## Important: JSON-Only Logging

**Only JSON-formatted logs are sent to Vibex.** Non-JSON logs are automatically discarded. Always stringify your log data:

```python
import json

# ✅ Good - JSON logs are sent
logger.info(json.dumps({'cpu': 45, 'memory': 78}))

# ❌ Bad - Non-JSON logs are discarded
logger.info('Application started')
logger.info('High memory usage: 85%')
```

## Advanced Usage

### Direct Client Usage

```python
from vibex_sh import VibexClient, VibexConfig

config = VibexConfig()
client = VibexClient(config)

# Send custom log
client.send_log('json', {'cpu': 45, 'memory': 78})
```

### Check if Enabled

```python
handler = VibexHandler()
if handler.is_enabled():
    print('Vibex is active')
else:
    print('Vibex is disabled (missing config or expired token)')
```

### Verbose Mode

Enable verbose mode to see status messages when the handler initializes or encounters errors:

```python
vibex_handler = VibexHandler(verbose=True)
logger.addHandler(vibex_handler)
```

## License

MIT

