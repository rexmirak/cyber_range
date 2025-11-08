"""Session Manager: captures lab lifecycle events with timestamps.

Stores session events in-memory and can flush to a JSONL file.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class SessionEvent:
    ts: str
    type: str
    data: Dict[str, Any]


class SessionManager:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or _now_iso()
        self.events: List[SessionEvent] = []

    def record(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(SessionEvent(ts=_now_iso(), type=event_type, data=data or {}))

    def to_jsonl(self) -> str:
        lines = []
        for ev in self.events:
            rec = {"session_id": self.session_id, **asdict(ev)}
            lines.append(json.dumps(rec))
        return "\n".join(lines)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_jsonl())
