"""Pydantic contracts used by the control-plane supervisor."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentHandoffCommand(BaseModel):
    """Structured routing decision emitted by the supervisor."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(..., description="Decision rationale for the handoff.")
    next_worker: Literal["Topology_Node", "Memory_Node", "Execute_Fix_Node", "FINISH"] = Field(
        ...,
        description="The next worker node to execute, or FINISH to end diagnosis.",
    )
    instruction: str = Field(..., description="Task instruction for the downstream node.")


class DiagnosticReport(BaseModel):
    """Structured final report emitted by the report generator."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Short report title.")
    impact: str = Field(..., description="Impact surface and affected services.")
    likely_root_cause: str = Field(..., description="Most likely root cause.")
    evidence: list[str] = Field(default_factory=list, description="Evidence bullets.")
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Operator-facing next actions.",
    )
    confidence: Literal["low", "medium", "high"] = Field(..., description="Diagnosis confidence.")
