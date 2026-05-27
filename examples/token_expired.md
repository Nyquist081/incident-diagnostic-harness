# Example: Token Expired

## Incident Query

```bash
uv run python main.py "排查用户中心 Token Expired 报错"
```

## Expected Route

```text
Supervisor -> Topology_Node -> Supervisor -> Log_Node -> Supervisor -> Metrics_Node -> Supervisor -> Memory_Node -> Supervisor -> FINISH
```

With human-in-the-loop enabled:

```bash
uv run python main.py --human-in-loop "排查用户中心 Token Expired 报错"
```

Expected route:

```text
Supervisor -> Topology_Node -> Supervisor -> Log_Node -> Supervisor -> Metrics_Node -> Supervisor -> Memory_Node -> Supervisor -> Execute_Fix_Node -> FINISH
```

## Evidence Sources

- `data/mock/topology.json`
  - service: `user-center`
  - upstream: `api-gateway`, `web-console`
  - downstream: `auth-service`, `redis-session`, `mysql-user`
- `data/mock/incidents.json`
  - similar incidents around JWT issuer, JWKS cache, key rotation, and clock skew
- `data/mock/logs.json`
  - TokenExpiredError, stale JWKS cache, key rotation logs
- `data/mock/metrics.json`
  - token expired count, 401 rate, JWKS key rotation events

## Expected Report Focus

- The affected blast radius is centered on `user-center`.
- The most relevant dependency is `auth-service`.
- Likely causes include stale JWKS cache, issuer mismatch, key rotation, or clock skew.
- Recommended actions should include JWKS refresh, signing key verification, and NTP checks.

## LLM Mode

```bash
INCIDENT_ENABLE_LLM_ROUTING=true INCIDENT_ENABLE_LLM_REPORT=true \
uv run python main.py "排查用户中心 Token Expired 报错"
```
