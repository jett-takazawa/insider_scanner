"""
Polymarket (Gamma) helper:
- Find the 'Beat earnings' market by ticker/company (public-search)
- Get market details (slug → clobTokenIds, end date)
- Extract 'resolved side' + 'resolution text/source' when available

Inputs:
  query         : "NFLX" or "Netflix"
  close_dt_et   : "YYYY-MM-DD 16:00" (America/New_York)  # only used if you later add price snapshots

Outputs (example keys):
{
  "pm_market_id": "...",
  "pm_market_slug": "...",
  "pm_market_title": "Will Netflix beat quarterly earnings?",
  "earnings_datetime_utc": "2025-10-21T20:05:00Z",
  "clob_yes_token_id": "...",
  "resolved": True,
  "resolved_side": "YES" | "NO" | None,
  "resolution_text": "...",
  "resolution_source_url": "https://...",
}
"""

import requests
from datetime import datetime, timezone, timedelta
import zoneinfo

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"  # kept for future price snapshots

def _ensure_dt_et(s, tz="America/New_York"):
    if isinstance(s, datetime):
        return s
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=zoneinfo.ZoneInfo(tz))

def gamma_search(query: str) -> dict:
    r = requests.get(f"{GAMMA_BASE}/public-search", params={"q": query}, timeout=20)
    r.raise_for_status()
    return r.json()

def pick_earnings_market(search_json: dict, query_hint: str | None = None) -> dict:
    # Heuristic: choose first market whose title mentions earnings + (beat or miss)
    markets = search_json.get("markets", [])
    cands = []
    for m in markets:
        title = (m.get("title") or "").lower()
        if "earnings" in title and ("beat" in title or "miss" in title):
            if not query_hint or query_hint.lower() in title:
                cands.append(m)
    if not cands:
        raise ValueError("No Polymarket earnings Beat/Miss market found in public-search.")
    return cands[0]  # You can refine selection if multiple matches

def gamma_market_by_slug(slug: str) -> dict:
    r = requests.get(f"{GAMMA_BASE}/markets/slug/{slug}", timeout=20)
    r.raise_for_status()
    return r.json()

def _extract_yes_token(details: dict) -> str | None:
    # Conventionally clobTokenIds = [YES, NO]; keep robust fallback
    toks = details.get("clobTokenIds") or details.get("clobTokens") or []
    if isinstance(toks, list) and toks:
        return toks[0] if isinstance(toks[0], str) else toks[0].get("id")
    return None

def _extract_resolution_fields(details: dict) -> dict:
    """
    Gamma schemas can vary slightly; try common keys with graceful fallbacks.
    """
    resolved = bool(details.get("resolved") or details.get("isResolved") or details.get("outcome"))
    # Side: "YES" / "NO" or boolean-like outcome
    side = details.get("outcome")
    if side is True:  side = "YES"
    if side is False: side = "NO"

    # Resolution text + source/url live under market or event; try a few places.
    res_text = (
        details.get("resolutionText")
        or (details.get("resolution") or {}).get("text")
        or (details.get("event") or {}).get("resolutionText")
    )
    res_source = (
        details.get("resolutionSource")
        or (details.get("resolution") or {}).get("source")
        or (details.get("event") or {}).get("resolutionSource")
    )
    res_url = (
        details.get("resolutionSourceUrl")
        or (details.get("resolution") or {}).get("sourceUrl")
        or (details.get("event") or {}).get("resolutionSourceUrl")
        or res_source  # sometimes the source itself is a URL
    )

    return {
        "resolved": resolved,
        "resolved_side": side if resolved else None,
        "resolution_text": res_text,
        "resolution_source_url": res_url,
    }

def fetch_gamma_labels_for_ticker(query: str, close_dt_et: str | datetime) -> dict:
    # 1) Search
    s = gamma_search(query)
    pick = pick_earnings_market(s, query_hint=query)
    slug = pick.get("slug") or pick.get("id")
    title = pick.get("title", "")

    # 2) Details (slug → id, endDate, tokens, resolution fields)
    d = gamma_market_by_slug(slug)
    pm_market_id = d.get("id")
    pm_market_slug = d.get("slug") or slug
    pm_market_title = d.get("title", title)

    # Earnings time (UTC) often lives on market 'endDate' or nested event
    earnings_dt_utc = (
        d.get("endDate")
        or (d.get("event") or {}).get("endDate")
        or None
    )

    yes_token = _extract_yes_token(d)
    resolution = _extract_resolution_fields(d)

    # Optional: keep a consistent UTC of the close if you later add snapshots
    close_dt = _ensure_dt_et(close_dt_et)
    close_dt_utc = close_dt.astimezone(timezone.utc).isoformat()

    return {
        "pm_market_id": pm_market_id,
        "pm_market_slug": pm_market_slug,
        "pm_market_title": pm_market_title,
        "earnings_datetime_utc": earnings_dt_utc,  # may be None if Gamma doesn't expose it here
        "clob_yes_token_id": yes_token,
        "close_dt_utc_for_snapshots": close_dt_utc,
        **resolution,  # resolved, resolved_side, resolution_text, resolution_source_url
    }

# ---------------- Example ----------------
if __name__ == "__main__":
    # Example for an LLM-run task: pull labels for 'Netflix' around a given close date
    out = fetch_gamma_labels_for_ticker(
        query="Netflix",           # try "NFLX" too if needed
        close_dt_et="2025-10-21 16:00",
    )
    print(out)
    # Append 'out' to your Google Sheet row for this ticker/date alongside your price fields.
