"""Document proxy for official Lok Sabha question-answer + debate PDFs.

The frontend must NOT deep-link `sansad.in/getFile/*` directly: that host is flaky — it has been observed
returning an HTTP 308 redirect to the identical URL (an infinite loop the browser surfaces as
ERR_TOO_MANY_REDIRECTS). We proxy instead: fetch the PDF server-side, disk-cache it, and stream it. A
successful fetch is then served from us forever; an upstream failure/loop degrades to a clean
"temporarily unavailable" page rather than a redirect loop. Mirrors the photo proxy in routers/persons.py.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.deps import get_db

router = APIRouter(tags=["documents"])

_DOC_CACHE = Path(__file__).resolve().parents[2] / ".doc_cache"
_ALLOWED_DOC_HOSTS = ("sansad.in",)
_MAX_DOC_BYTES = 15 * 1024 * 1024  # 15 MB
_SANSAD_QUESTIONS = "https://sansad.in/ls/questions/questions-and-answers"

# route kind -> table. Fixed map (never user input) so the f-string query below is injection-safe.
_TABLE = {"question": "parliamentary_question", "debate": "parliamentary_debate"}


def _is_allowed_doc_url(url: str) -> bool:
    """SSRF guard: only https sansad.in/getFile/* (the sole host these PDFs come from)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.path.startswith("/getFile/")
        and any(host == h or host.endswith("." + h) for h in _ALLOWED_DOC_HOSTS)
    )


def _unavailable(link: str | None) -> Response:
    """Graceful fallback (200 HTML) when the official PDF can't be fetched — never a redirect loop."""
    href = link or _SANSAD_QUESTIONS
    html = (
        "<!doctype html><meta charset=utf-8>"
        "<title>Reply temporarily unavailable</title>"
        "<div style=\"font-family:system-ui,sans-serif;max-width:34rem;margin:12vh auto;padding:0 1.25rem;"
        "line-height:1.6;color:#1f2328\">"
        "<h1 style=\"font-size:1.15rem\">Official reply temporarily unavailable</h1>"
        "<p>The Lok Sabha reply document could not be loaded from the official source (sansad.in) right "
        "now. This is usually temporary — please try again shortly.</p>"
        f"<p><a href=\"{href}\" target=\"_blank\" rel=\"noreferrer\">Open on sansad.in ↗</a></p></div>"
    )
    return Response(content=html, media_type="text/html", headers={"Cache-Control": "no-store"})


def _serve_document(kind: str, row_id: int, db: Session) -> Response:
    url = db.execute(
        text(f"SELECT document_url FROM {_TABLE[kind]} WHERE id = :id"),  # noqa: S608 (table from fixed map)
        {"id": row_id},
    ).scalar()
    if not url:
        raise HTTPException(status_code=404, detail="no document")
    if not _is_allowed_doc_url(url):
        return _unavailable(None)
    _DOC_CACHE.mkdir(exist_ok=True)
    cached = _DOC_CACHE / f"{kind}-{row_id}.pdf"
    if not cached.exists():
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "neta-resume/0.1 (non-commercial; contact sahil@magicweave.xyz)",
                "Referer": "https://sansad.in/",
                "Accept": "application/pdf",
            })
            with urllib.request.urlopen(req, timeout=25) as r:  # noqa: S310 (host+scheme validated above)
                data = r.read(_MAX_DOC_BYTES + 1)
            # A real PDF starts with "%PDF"; a 308-loop/HTML error page does not -> treat as unavailable.
            if not data.startswith(b"%PDF") or len(data) > _MAX_DOC_BYTES:
                return _unavailable(url)
            cached.write_bytes(data)
        except Exception:  # noqa: BLE001 — upstream flaky/looping: degrade gracefully, never error/loop
            return _unavailable(url)
    return Response(
        content=cached.read_bytes(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{kind}-{row_id}.pdf"',
            "Cache-Control": "public, max-age=604800",
        },
    )


@router.get("/questions/{question_id}/document")
def question_document(question_id: int, db: Session = Depends(get_db)) -> Response:
    return _serve_document("question", question_id, db)


@router.get("/debates/{debate_id}/document")
def debate_document(debate_id: int, db: Session = Depends(get_db)) -> Response:
    return _serve_document("debate", debate_id, db)
