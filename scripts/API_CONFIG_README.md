# Scripts API Configuration

## IMPORTANT: API URL for Scripts

**The only valid API URL for all scripts is:**

```
https://api.onebor.com/panda
```

## Environment Variables

When setting up environment variables for scripts, always use:

```bash
API_BASE_URL="https://api.onebor.com/panda"
```

## Common Script Files

- `test_*.py` - Test scripts
- `deploy_*.py` - Deployment scripts
- `api_test.py` - API testing scripts

## Examples

### Python Scripts

```python
import os
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.onebor.com/panda')
```

### Shell Scripts

```bash
export API_BASE_URL="https://api.onebor.com/panda"
```

## Never Use

❌ **DO NOT USE:**

- `https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com`
- `https://api.onebor.com` (without `/panda`)
- Any other AWS API Gateway URLs

✅ **ALWAYS USE:**

- `https://api.onebor.com/panda`
