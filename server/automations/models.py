from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class AutomationRule:
    id: str
    name: str
    schedule: str
    enabled: bool
    patterns: List[str]
    target_folders: List[str]

    @staticmethod
    def from_dict(data: dict) -> "AutomationRule":
        return AutomationRule(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            schedule=str(data.get("schedule", "")),
            enabled=bool(data.get("enabled", True)),
            patterns=list(data.get("patterns", []) or []),
            target_folders=list(data.get("target_folders", []) or []),
        )
