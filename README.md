# Incident Harness

Sprint 1 control-plane skeleton for a LangGraph-based microservice incident
diagnostic harness.

## Design

See [docs/agent-design.md](docs/agent-design.md) for the detailed agent
architecture, state contract, extension points, and comparison dimensions.

中文版设计文档见 [docs/agent-design.zh.md](docs/agent-design.zh.md)。

## Run

```bash
uv run python main.py "排查用户中心 Token Expired 报错"
```

## Test

```bash
uv run python -m unittest discover -s tests
```

If `OPENAI_API_KEY` is set, the supervisor uses `ChatOpenAI.with_structured_output`
with the `AgentHandoffCommand` contract. Without an API key, it falls back to a
deterministic local router so the control-plane flow can be validated offline.
