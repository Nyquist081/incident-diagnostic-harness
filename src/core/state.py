"""Global state definition for the incident diagnostic graph."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class EngineState(TypedDict):
    """Shared state carried across supervisor and worker nodes."""

    messages: Annotated[list[BaseMessage], operator.add]
    current_phase: str
    impact_summary: str
    memory_summary: str
    final_report: str
    handoff_trace: Annotated[list[dict[str, str]], operator.add]
    routing_errors: Annotated[list[str], operator.add]
