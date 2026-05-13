from __future__ import annotations

from briefing.domain.ports import SourceAdapter
from briefing.domain.value_objects import SourceName


class SourceRegistry:
    def __init__(self) -> None:
        self._by_name: dict[SourceName, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        if adapter.name in self._by_name:
            raise ValueError(f"source already registered: {adapter.name}")
        self._by_name[adapter.name] = adapter

    def get(self, name: SourceName) -> SourceAdapter | None:
        return self._by_name.get(name)

    def list_all(self) -> list[SourceAdapter]:
        return list(self._by_name.values())
