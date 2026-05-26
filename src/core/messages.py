"""Message helpers shared by CLI, graph nodes, and benchmark scripts."""

from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage


def message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


def latest_user_request(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message_text(message)
    return ""
