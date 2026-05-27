# Example: Redis Session Timeout

## Incident Query

```bash
uv run python main.py "redis session 查询超时导致登录失败"
```

## Expected Route

```text
Supervisor -> Topology_Node -> Supervisor -> Memory_Node -> Supervisor -> FINISH
```

## Evidence Sources

- `data/mock/topology.json`
  - expected service match: `redis-session`
  - upstream: `user-center`, `auth-service`
- `data/mock/incidents.json`
  - Redis memory pressure, failover, TTL mismatch, CPU saturation, cache prefix changes

## Expected Report Focus

- The blast radius affects login and token/session validation flows.
- Similar incidents should focus on Redis session lookup timeout, eviction, TTL inconsistency, or failover.
- Recommended actions should include checking Redis latency, memory pressure, eviction rate, TTL distribution, and recent failover events.

## Human-in-the-loop Mode

```bash
uv run python main.py --human-in-loop "redis session 查询超时导致登录失败"
```
