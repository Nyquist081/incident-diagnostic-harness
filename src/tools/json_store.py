"""Small JSON repository used by Sprint 2 mock data tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    """Read-only JSON store with a tiny in-process cache."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._cache: dict[str, Any] = {}

    def load(self, name: str) -> Any:
        if name not in self._cache:
            path = self.base_dir / name
            self._cache[name] = json.loads(path.read_text(encoding="utf-8"))
        return self._cache[name]
