# API Configuration

## IMPORTANT: API URL Configuration

**The only valid API URL for all stages (development, staging, production) is:**

```
https://api.onebor.com/panda
```

## Configuration Details

- **Development**: Uses Vite proxy to forward `/api/*` requests to `https://api.onebor.com/panda/*`
- **Production**: Direct calls to `https://api.onebor.com/panda/*`
- **All Environments**: Never use AWS API Gateway URLs directly

## Files That Reference API URLs

- `vite.config.ts` - Vite proxy configuration
- `src/services/api.ts` - API service configuration
- `scripts/.env` - Environment variables for scripts
- Any test files or deployment scripts

## Common Mistakes to Avoid

❌ **DO NOT USE:**

- `https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com`
- `https://api.onebor.com` (without `/panda`)
- `localhost` API URLs
- Any other AWS API Gateway URLs

✅ **ALWAYS USE:**

- `https://api.onebor.com/panda`

## Proxy Configuration

The Vite proxy should be configured as:

```typescript
server: {
  proxy: {
    "/api": {
      target: "https://api.onebor.com/panda",
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ""),
    },
  },
}
```

This ensures that:

- Frontend calls `/api/get_transactions`
- Proxy forwards to `https://api.onebor.com/panda/get_transactions`
- All API calls use the correct domain
