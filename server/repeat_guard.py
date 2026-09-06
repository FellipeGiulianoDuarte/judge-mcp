"""Return no_match when a search surfaces a section this conversation already saw.

Measured on the benchmark: a model that keeps searching and keeps getting the
same nearest-junk section — "What's the difference between 'up to' and 'any
amount'", nine rounds running — concludes the sources lack an answer it in fact
knew, and refuses. Telling it "nothing new matches these terms" instead let it
move on and recovered 11 of 42 such losses.

The benchmark harness did this in its own tool loop. A judge on the real
connector gets no such loop, so the server has to do it per session. Sessions
are keyed on the MCP session id when the transport gives one, else on a single
shared key — a shared stdio process is one conversation anyway.
"""

from __future__ import annotations

import time
from collections import defaultdict

_SEEN: dict[str, dict[str, float]] = defaultdict(dict)
_TTL = 60 * 30       # a tournament conversation, not forever


def _session_key() -> str:
    try:
        from mcp.server.request_state import get_request_state  # type: ignore
        rs = get_request_state()
        sid = getattr(rs, "session_id", None) or getattr(rs, "request_id", None)
        if sid:
            return str(sid)
    except Exception:
        pass
    return "default"


def _top(result: dict) -> str | None:
    hits = ((result.get("exceptions") or []) + (result.get("rulings") or [])
            + (result.get("documents") or []) + (result.get("mechanics") or [])
            + (result.get("results") or []))
    if not hits:
        return None
    h = hits[0]
    return h.get("citation") or h.get("heading")


def guard(tool: str, result: dict) -> dict:
    if result.get("no_match"):
        return result
    top = _top(result)
    if not top:
        return result
    key = _session_key()
    seen = _SEEN[key]
    now = time.time()
    for k, t in list(seen.items()):
        if now - t > _TTL:
            del seen[k]
    mark = f"{tool}:{top}"
    if mark in seen:
        return {"no_match": True,
                "note": (f"Nothing new matches these terms — the best hit ({top}) was "
                         f"already returned for an earlier search in this conversation. "
                         f"The corpus does not appear to cover this; try a different "
                         f"tool, or answer from what you already have.")}
    seen[mark] = now
    return result


def reset(session: str | None = None) -> None:
    """For tests, and for a client that starts a new conversation."""
    if session is None:
        _SEEN.clear()
    else:
        _SEEN.pop(session, None)
