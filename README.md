# Incident Harness

Sprint 1 control-plane skeleton for a LangGraph-based microservice incident
diagnostic harness.

## Design

See [docs/agent-design.md](docs/agent-design.md) for the detailed agent
architecture, state contract, extension points, and comparison dimensions.

中文版设计文档见 [docs/agent-design.zh.md](docs/agent-design.zh.md)。

## Run

Create local model configuration:

```bash
cp .env.example .env
```

Then edit `.env` and set `OPENAI_API_KEY` to your DeepSeek API key. DeepSeek's
OpenAI-compatible base URL is prefilled as `https://api.deepseek.com`. The
committed `.env.example` is a template; `.env` is ignored by Git.

The default free local embedding recommendation is `BAAI/bge-small-zh-v1.5`.
Vector retrieval is optional; the harness keeps `INCIDENT_MEMORY_PROVIDER=bm25`
by default so it runs without downloading local embedding dependencies.

Prompts are versioned Markdown files under `prompts/`. Supervisor routing uses
`supervisor_*_v1.md`; structured report generation uses `report_*_v1.md`.

```bash
uv run python main.py "排查用户中心 Token Expired 报错"
```

Show active model role configuration:

```bash
uv run python main.py --show-config "排查用户中心 Token Expired 报错"
```

Run with human approval before simulated fix execution:

```bash
uv run python main.py --human-in-loop "排查用户中心 Token Expired 报错"
```

## Benchmark

```bash
uv run python scripts/run_benchmark.py
```

## Docker

Build the CLI image:

```bash
docker build -t incident-diagnostic-harness:local .
```

Run a diagnosis with local `.env` injected at runtime:

```bash
docker run --rm --env-file .env incident-diagnostic-harness:local "排查用户中心 Token Expired 报错"
```

Run through Docker Compose:

```bash
docker compose run --rm incident-harness "排查用户中心 Token Expired 报错"
```

Show model configuration in the container:

```bash
docker compose run --rm incident-harness --show-config "排查用户中心 Token Expired 报错"
```

Run the benchmark in the container:

```bash
docker compose run --rm --entrypoint uv incident-harness run python scripts/run_benchmark.py
```

## Test

```bash
uv run python -m unittest discover -s tests
```

If `OPENAI_API_KEY` is set, the supervisor uses `ChatOpenAI.with_structured_output`
with the `AgentHandoffCommand` contract. Without an API key, it falls back to a
deterministic local router so the control-plane flow can be validated offline.
