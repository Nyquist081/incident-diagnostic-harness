"""Pydantic contracts used by the control-plane supervisor."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentHandoffCommand(BaseModel):
    """Structured routing decision emitted by the supervisor."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(..., description="Decision rationale for the handoff.")
    next_worker: Literal["Topology_Node", "Memory_Node", "FINISH"] = Field(
        ...,
        description="The next worker node to execute, or FINISH to end diagnosis.",
    )
    instruction: str = Field(..., description="Task instruction for the downstream node.")
