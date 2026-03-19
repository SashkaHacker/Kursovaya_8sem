from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HistoryEntry:
    id: int
    created_at: str
    recognized_text: str

    @property
    def date_str(self) -> str:
        return self.created_at.split(" ")[0] if " " in self.created_at else self.created_at

    @property
    def time_str(self) -> str:
        if " " not in self.created_at:
            return "--:--"
        return self.created_at.split(" ")[1][:5]
