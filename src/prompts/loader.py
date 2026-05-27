"""Versioned prompt loading and rendering."""

from __future__ import annotations

from dataclasses import dataclass

from core.paths import PROMPTS_DIR


@dataclass(frozen=True)
class PromptPair:
    system: str
    user: str


class PromptRegistry:
    """Load prompt templates from the repository-level prompts directory."""

    def __init__(self, prompts_dir=PROMPTS_DIR) -> None:
        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}

    def load(self, name: str) -> str:
        if name not in self._cache:
            path = self.prompts_dir / name
            self._cache[name] = path.read_text(encoding="utf-8").strip()
        return self._cache[name]

    def render(self, name: str, **variables: str) -> str:
        return self.load(name).format(**variables)

    def pair(self, system_name: str, user_name: str, **variables: str) -> PromptPair:
        return PromptPair(
            system=self.render(system_name, **variables),
            user=self.render(user_name, **variables),
        )


PROMPTS = PromptRegistry()
