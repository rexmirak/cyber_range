"""PDF Reporter: generate a report from a session log.

Uses reportlab to create a PDF with session metadata, summary counts,
warnings/errors, and a paginated event list.
"""
from __future__ import annotations
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from typing import Tuple

from .utils import aggregate_events


def _draw_wrapped_text(c: canvas.Canvas, x: float, y: float, text: str, max_width: float, line_height: float) -> float:
    # Naive wrap by splitting into chunks that fit max_width
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if stringWidth(test, "Helvetica", 10) > max_width:
            c.drawString(x, y, line)
            y -= line_height
            line = w
        else:
            line = test
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y


def generate_pdf_from_events(pdf_path: str, session_id: str, events: List[Dict[str, Any]]) -> None:
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, f"Cyber Range Session Report")
    y -= 1 * cm
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Session: {session_id}")
    y -= 1 * cm

    # Summary section
    agg = aggregate_events(events)
    counts = agg.get("counts", {})
    warnings = agg.get("warnings", [])
    errors = agg.get("errors", [])

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Summary:")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    for etype, cnt in sorted(counts.items()):
        c.drawString(2 * cm, y, f"- {etype}: {cnt}")
        y -= 0.45 * cm

    if warnings:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Warnings:")
        y -= 0.6 * cm
        c.setFont("Helvetica", 10)
        for w in warnings[:50]:
            if y < 2 * cm:
                c.showPage(); y = height - 2 * cm; c.setFont("Helvetica", 10)
            y = _draw_wrapped_text(c, 2 * cm, y, f"- {w}", width - 4 * cm, 0.45 * cm)

    if errors:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Errors:")
        y -= 0.6 * cm
        c.setFont("Helvetica", 10)
        for e in errors[:50]:
            if y < 2 * cm:
                c.showPage(); y = height - 2 * cm; c.setFont("Helvetica", 10)
            y = _draw_wrapped_text(c, 2 * cm, y, f"- {e}", width - 4 * cm, 0.45 * cm)

    # Events section
    c.setFont("Helvetica-Bold", 12)
    if y < 3 * cm:
        c.showPage(); y = height - 2 * cm
    c.drawString(2 * cm, y, "Events:")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)

    for ev in events[:200]:  # cap for one-page simplicity
        line = f"{ev.get('ts','')}  {ev.get('type','')}  {str(ev.get('data',''))[:120]}"
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm

    c.showPage()
    c.save()
