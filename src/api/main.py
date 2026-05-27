"""FastAPI service for the incident diagnostic harness."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from api.schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    RunsResponse,
    state_to_response,
    state_to_stream_event,
)
from core.config import load_model_settings
from core.runner import DiagnosticRunner
from telemetry.recorder import summarize_latest_runs

app = FastAPI(
    title="Incident Diagnostic Harness API",
    version="0.1.0",
    description="HTTP control plane for microservice incident diagnostics.",
)
runner = DiagnosticRunner()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, object]:
    settings = load_model_settings()
    return {
        "llm_routing": settings.enable_llm_routing,
        "primary_model": settings.primary_model,
        "supervisor_model": settings.supervisor_model,
        "fallback_model": settings.fallback_model,
        "report_model": settings.report_model,
        "llm_report": settings.enable_llm_report,
        "memory_provider": settings.memory_provider,
        "embedding_provider": settings.embedding_provider,
        "rag_embedding_model": settings.rag_embedding_model,
        "deepseek_thinking": settings.deepseek_thinking,
        "base_url_configured": bool(settings.openai_base_url),
        "api_key_configured": settings.has_openai_credentials,
    }


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    result = await runner.arun(
        request.query.strip(),
        enable_fix_execution=request.enable_fix_execution,
    )
    return state_to_response(result.run_id, result.final_state)


@app.post("/diagnose/stream")
async def diagnose_stream(request: DiagnoseRequest) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        async for step in runner.astream(
            request.query.strip(),
            enable_fix_execution=request.enable_fix_execution,
        ):
            event = state_to_stream_event(step.run_id, step.phase, step.state)
            payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
            yield f"event: diagnostic_step\ndata: {payload}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/runs", response_model=RunsResponse)
def runs(limit: int = 10) -> RunsResponse:
    safe_limit = min(max(limit, 1), 100)
    return RunsResponse(runs=summarize_latest_runs(limit=safe_limit))
