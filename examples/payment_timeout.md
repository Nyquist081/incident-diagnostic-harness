# Example: Payment Timeout

## Incident Query

```bash
uv run python main.py "订单 checkout 支付超时"
```

## Expected Route

```text
Supervisor -> Topology_Node -> Supervisor -> Log_Node -> Supervisor -> Metrics_Node -> Supervisor -> Memory_Node -> Supervisor -> FINISH
```

## Evidence Sources

- `data/mock/topology.json`
  - expected service match: `order-service`
  - downstream: `payment-service`, `inventory-service`
- `data/mock/incidents.json`
  - payment timeout, connection pool exhaustion, callback issues, DNS cache, risk-service latency
- `data/mock/logs.json`
  - checkout timeout, payment connection pool saturation, risk latency
- `data/mock/metrics.json`
  - checkout timeout rate, payment p95 latency, payment pool utilization

## Expected Report Focus

- The issue starts from checkout but likely propagates into `payment-service`.
- Similar incidents should mention payment timeout, payment connection pool, or risk verification latency.
- Recommended actions should include checking payment-service latency, connection pool saturation, retry rate, and risk-service dependency health.

## Useful Commands

```bash
uv run python main.py --show-config "订单 checkout 支付超时"
uv run python scripts/run_benchmark.py
```
