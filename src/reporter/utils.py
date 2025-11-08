"""Reporter utilities: load session events from JSONL and aggregate summaries."""
from __future__ import annotations
from typing import List, Dict, Any, Tuple


def load_session_from_jsonl(path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Load session events from a JSONL file.

    Each line is expected to be a JSON object with at least:
    {"session_id": str, "ts": str, "type": str, "data": {...}}
    Returns (session_id, events)
    """
    import json
    session_id: str | None = None
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if session_id is None:
                    session_id = rec.get("session_id")
                events.append({"ts": rec.get("ts"), "type": rec.get("type"), "data": rec.get("data", {})})
            except Exception:
                # Skip malformed lines rather than failing the entire load
                continue
    return (session_id or "unknown-session", events)


def aggregate_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate counts by event type and collect warnings/errors from event data."""
    from collections import Counter

    counts = Counter(ev.get("type") for ev in events)
    warnings: List[str] = []
    errors: List[str] = []
    for ev in events:
        data = ev.get("data") or {}
        ws = data.get("warnings") or []
        es = data.get("errors") or []
        if isinstance(ws, list):
            warnings.extend(str(w) for w in ws)
        if isinstance(es, list):
            errors.extend(str(e) for e in es)
    return {
        "counts": dict(counts),
        "warnings": warnings,
        "errors": errors,
    }
