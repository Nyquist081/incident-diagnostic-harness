# Example: Payment Timeout

## Incident Query

```bash
uv run python main.py "订单 checkout 支付超时"
```

## Expected Route

```text
Supervisor -> Topology_Node -> Supervisor -> Memory_Node -> Supervisor -> FINISH
```

## Evidence Sources

- `data/mock/topology.json`
  - expected service match: `order-service`
  - downstream: `payment-service`, `inventory-service`
- `data/mock/incidents.json`
  - payment timeout, connection pool exhaustion, callback issues, DNS cache, risk-service latency

## Expected Report Focus

- The issue starts from checkout but likely propagates into `payment-service`.
- Similar incidents should mention payment timeout, payment connection pool, or risk verification latency.
- Recommended actions should include checking payment-service latency, connection pool saturation, retry rate, and risk-service dependency health.

## Useful Commands

```bash
uv run python main.py --show-config "订单 checkout 支付超时"
uv run python scripts/run_benchmark.py
```
