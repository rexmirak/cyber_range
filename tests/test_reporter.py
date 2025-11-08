import os
import json
import pytest

from src.session.manager import SessionManager
from src.reporter.utils import load_session_from_jsonl, aggregate_events
from src.reporter.pdf_reporter import generate_pdf_from_events


def test_load_and_aggregate_events(tmp_path):
    sm = SessionManager(session_id="sess-123")
    sm.record("validate", {"warnings": ["w1", "w2"], "errors": []})
    sm.record("plan", {"warnings": [], "errors": ["e1"]})
    sm.record("provision", {"warnings": [], "errors": []})
    log_path = tmp_path / "session.jsonl"
    sm.save(str(log_path))

    sess_id, events = load_session_from_jsonl(str(log_path))
    assert sess_id == "sess-123"
    assert len(events) == 3
    agg = aggregate_events(events)
    assert agg["counts"].get("validate") == 1
    assert "w1" in agg["warnings"] and "w2" in agg["warnings"]
    assert "e1" in agg["errors"]


def test_generate_pdf_from_events(tmp_path):
    pytest.importorskip("reportlab")
    events = [
        {"ts": "2024-01-01T00:00:00Z", "type": "validate", "data": {"warnings": ["warn"], "errors": []}},
        {"ts": "2024-01-01T00:01:00Z", "type": "plan", "data": {"warnings": [], "errors": []}},
    ]
    pdf_path = tmp_path / "report.pdf"
    generate_pdf_from_events(str(pdf_path), "sess-xyz", events)
    assert pdf_path.exists()
    assert os.path.getsize(pdf_path) > 100
