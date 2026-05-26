"""Runtime configuration for model and provider selection."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from core.paths import PROJECT_ROOT


def _load_dotenv(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


def _env_bool(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class ModelSettings(BaseModel):
    """Model role mapping for the incident diagnostic harness."""

    openai_api_key: str | None = Field(default=None)
    openai_base_url: str | None = Field(default="https://api.deepseek.com")
    primary_model: str = Field(default="deepseek-v4-pro")
    fallback_model: str = Field(default="deepseek-v4-flash")
    supervisor_model: str = Field(default="deepseek-v4-flash")
    report_model: str = Field(default="deepseek-v4-pro")
    embedding_provider: str = Field(default="fastembed")
    rag_embedding_model: str = Field(default="BAAI/bge-small-zh-v1.5")
    memory_provider: str = Field(default="bm25")
    llm_temperature: float = Field(default=0.0)
    deepseek_thinking: str = Field(default="disabled")
    enable_llm_routing: bool = Field(default=False)
    enable_llm_report: bool = Field(default=False)

    @property
    def has_openai_credentials(self) -> bool:
        return bool(self.openai_api_key)


def load_model_settings(*, dotenv_path: Path | None = None) -> ModelSettings:
    _load_dotenv(dotenv_path or PROJECT_ROOT / ".env", override=dotenv_path is not None)
    return ModelSettings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com") or None,
        primary_model=os.getenv("INCIDENT_PRIMARY_MODEL", "deepseek-v4-pro"),
        fallback_model=os.getenv("INCIDENT_FALLBACK_MODEL", "deepseek-v4-flash"),
        supervisor_model=os.getenv("INCIDENT_SUPERVISOR_MODEL", "deepseek-v4-flash"),
        report_model=os.getenv("INCIDENT_REPORT_MODEL", "deepseek-v4-pro"),
        embedding_provider=os.getenv("INCIDENT_EMBEDDING_PROVIDER", "fastembed"),
        rag_embedding_model=os.getenv("INCIDENT_RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
        memory_provider=os.getenv("INCIDENT_MEMORY_PROVIDER", "bm25"),
        llm_temperature=float(os.getenv("INCIDENT_LLM_TEMPERATURE", "0")),
        deepseek_thinking=os.getenv("INCIDENT_DEEPSEEK_THINKING", "disabled"),
        enable_llm_routing=_env_bool("INCIDENT_ENABLE_LLM_ROUTING", default=False),
        enable_llm_report=_env_bool("INCIDENT_ENABLE_LLM_REPORT", default=False),
    )
