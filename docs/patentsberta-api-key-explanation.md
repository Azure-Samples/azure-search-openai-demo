# PatentSBERTa API Key - Why It's Optional

## How It Works

The PatentSBERTa API key is **optional** because the service implements **conditional authentication**:

### The Logic

Looking at the service code (`custom-embedding-service/app.py`):

```python
def api_key_auth(x_api_key: str | None = Header(default=None)):
    """API key authentication dependency"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

**Key Point:** The check only fails if:
1. `API_KEY` is set in the service (from `PATENTSBERTA_API_KEY` environment variable)
2. AND the provided key doesn't match

### Two Scenarios

#### Scenario 1: API Key NOT Configured (Works Without Key)

**Service Side:**
```python
# In custom-embedding-service/constants.py
API_KEY = os.getenv("PATENTSBERTA_API_KEY")  # Returns None if not set
```

**What Happens:**
- `API_KEY` is `None`
- The check `if API_KEY and x_api_key != API_KEY:` evaluates to `False` (because `API_KEY` is `None`)
- **Authentication is bypassed** - service accepts requests without API key
- ✅ **Works without API key**

**Client Side:**
```python
# In app/backend/prepdocslib/patentsberta_embeddings.py
headers = {'Content-Type': 'application/json'}
if self.api_key:  # This is None, so header not added
    headers['X-API-Key'] = self.api_key
```

#### Scenario 2: API Key IS Configured (Requires Key)

**Service Side:**
```bash
# Set in service environment
export PATENTSBERTA_API_KEY="your-secret-key"
```

**What Happens:**
- `API_KEY` is set to `"your-secret-key"`
- The check `if API_KEY and x_api_key != API_KEY:` will enforce authentication
- Requests without matching key get **401 Unauthorized**
- ✅ **Requires API key** - client must provide matching key

**Client Side:**
```bash
# Must set matching key
export PATENTSBERTA_API_KEY="your-secret-key"
```

```python
# Client includes header
headers = {'Content-Type': 'application/json', 'X-API-Key': 'your-secret-key'}
```

---

## Why This Design?

This **conditional authentication** pattern is useful because:

1. **Development/Testing**: You can run the service locally without authentication for easier testing
2. **Internal Networks**: If the service is behind a VPN/firewall, you might not need API key authentication
3. **Azure Managed Identity**: If using Azure authentication, you might not need API keys
4. **Production Security**: You can enable authentication by simply setting the environment variable

---

## When Does It Work Without API Key?

✅ **Works without API key** when:
- `PATENTSBERTA_API_KEY` is **NOT set** in the service environment
- Service is behind a VPN/firewall (network-level security)
- Service uses Azure Managed Identity for authentication
- Development/testing environment

❌ **Requires API key** when:
- `PATENTSBERTA_API_KEY` **IS set** in the service environment
- Service is publicly accessible and needs protection
- Production environment requiring authentication

---

## How to Check Your Service Configuration

### Check if Service Requires API Key

**Option 1: Check Service Environment**
```bash
# If service is deployed, check environment variables
az containerapp show \
  --name your-patentsberta-service \
  --resource-group your-rg \
  --query "properties.template.containers[0].env"
```

**Option 2: Test the Endpoint**
```bash
# Try without API key
curl -X POST https://your-service.azurewebsites.net/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test"], "normalize": true}'

# If you get 401, service requires API key
# If you get 200, service doesn't require API key
```

**Option 3: Check Service Logs**
```bash
# Look for authentication-related errors
az containerapp logs show \
  --name your-patentsberta-service \
  --resource-group your-rg \
  --tail 50
```

---

## Configuration Examples

### Example 1: Service Without API Key (No Authentication)

**Service Deployment:**
```bash
# Don't set PATENTSBERTA_API_KEY when deploying
az containerapp create \
  --name patentsberta-service \
  --resource-group rg-ai-master-engineer \
  # ... other settings ...
  # No PATENTSBERTA_API_KEY in environment variables
```

**Client Configuration:**
```bash
# Client doesn't need API key
export PATENTSBERTA_ENDPOINT="https://patentsberta-service.azurewebsites.net"
# No PATENTSBERTA_API_KEY needed
```

**Result:** ✅ Works without API key

---

### Example 2: Service With API Key (Authentication Required)

**Service Deployment:**
```bash
# Set API key when deploying service
API_KEY=$(openssl rand -base64 32)
az containerapp create \
  --name patentsberta-service \
  --resource-group rg-ai-master-engineer \
  --env-vars "PATENTSBERTA_API_KEY=$API_KEY" \
  # ... other settings ...
```

**Client Configuration:**
```bash
# Client MUST provide matching API key
export PATENTSBERTA_ENDPOINT="https://patentsberta-service.azurewebsites.net"
export PATENTSBERTA_API_KEY="$API_KEY"  # Same key as service
```

**Result:** ✅ Works with API key (won't work without it)

---

## Security Recommendations

### For Development
```bash
# Optional - skip API key for easier development
# Service: Don't set PATENTSBERTA_API_KEY
# Client: Don't set PATENTSBERTA_API_KEY
```

### For Production
```bash
# Recommended - use API key for security
# Service: Set PATENTSBERTA_API_KEY
# Client: Set matching PATENTSBERTA_API_KEY
```

### For Internal Networks
```bash
# Optional - rely on network security
# Service: Don't set PATENTSBERTA_API_KEY (if behind VPN/firewall)
# Client: Don't set PATENTSBERTA_API_KEY
```

---

## Summary

| Service `PATENTSBERTA_API_KEY` | Client `PATENTSBERTA_API_KEY` | Result |
|-------------------------------|-------------------------------|--------|
| Not set | Not set | ✅ Works (no authentication) |
| Not set | Set | ✅ Works (key ignored) |
| Set | Not set | ❌ 401 Unauthorized |
| Set | Set (matches) | ✅ Works |
| Set | Set (doesn't match) | ❌ 401 Unauthorized |

**Bottom Line:** The API key is optional because the service only enforces authentication **if** the `PATENTSBERTA_API_KEY` environment variable is set on the service side. If it's not set, the service accepts requests without authentication.





