"""Model factory for chat and embedding roles."""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import ModelSettings, load_model_settings


class ModelFactory:
    """Create provider clients from named model roles."""

    def __init__(self, settings: ModelSettings | None = None) -> None:
        self.settings = settings or load_model_settings()

    def chat(self, model_name: str) -> ChatOpenAI:
        kwargs = {
            "model": model_name,
            "temperature": self.settings.llm_temperature,
            "api_key": self.settings.openai_api_key,
            "extra_body": {"thinking": {"type": self.settings.deepseek_thinking}},
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return ChatOpenAI(**kwargs)

    def primary_chat(self) -> ChatOpenAI:
        return self.chat(self.settings.primary_model)

    def fallback_chat(self) -> ChatOpenAI:
        return self.chat(self.settings.fallback_model)

    def supervisor_chat(self) -> ChatOpenAI:
        return self.chat(self.settings.supervisor_model)

    def report_chat(self) -> ChatOpenAI:
        return self.chat(self.settings.report_model)

    def rag_embeddings(self) -> OpenAIEmbeddings:
        if self.settings.embedding_provider != "openai":
            raise ValueError(
                "OpenAIEmbeddings requires INCIDENT_EMBEDDING_PROVIDER=openai. "
                "Use the memory provider factory for local FastEmbed retrieval."
            )
        kwargs = {
            "model": self.settings.rag_embedding_model,
            "api_key": self.settings.openai_api_key,
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return OpenAIEmbeddings(**kwargs)
