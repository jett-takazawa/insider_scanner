# Polymarket Earnings → Ground-Truth → Stock Move Logger (PRP)

**Name:** Polymarket Earnings → Ground-Truth → Stock Move Logger  
**Purpose:** Automate collection of past Polymarket earnings Beat/Miss markets, extract each market’s resolved side + resolution source, and compare that to the next-day stock move. Output rows to Google Sheets (or CSV) for analysis of predictive accuracy and tradability.

## Core Principles
1. API-first, reproducible snapshots (UTC timestamps; no manual copy/paste).
2. Separation of concerns: discovery → labeling → prices → scoring → logging.
3. Backfillable: able to reconstruct missed times from historical endpoints.
4. Minimal dependencies: use Polymarket (Gamma + CLOB) and a single equities OHLCV source (Alpha Vantage helper function provided).
5. Validation loops: include sanity checks (ticker ↔ company match, wording clarity, resolved=true).

---

## Goal
Build a Python module + small CLI that, given a ticker (e.g., “NFLX”) and a date window, will:
- Find matching Polymarket “Will {Company} beat quarterly earnings?” markets.
- Pull resolved side (YES/NO) and resolution text/source URL (labels).
- Fetch prev close, next open, next close OHLCV for the underlying equity on the correct dates.
- Compute gap% (open vs prev close) and day% (close vs prev close).
- Emit one row per market to Google Sheets (or CSV) with standardized columns.

This runs for past markets (closed/settled). Later we can add near-close probability snapshots, but the MVP focuses on ground truth + price moves.

## Why
- Quantify whether Polymarket’s earnings markets (and any “insider” leans) map to actual stock moves.
- Establish a clean historical baseline before building any live strategy.
- Produce a reusable dataset for calibration and hit-rate studies by session (AMC/BMO).

## What (User-visible behavior)
**CLI example:**
```bash
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --until 2025-10-31 --sheet 'PolymarketEarnings'
```
**Columns written:**
```
date_utc, ticker, report_session(AMC/BMO), earnings_datetime_utc,
pm_market_id, pm_market_title, resolved, resolved_side, resolution_text, resolution_source_url,
px_prev_close, px_next_open, px_next_close, gap_return_open(%), day_return_close(%),
pm_correct_on_price_dir_open(1/0), pm_correct_on_price_dir_close(1/0),
wording_clear(Y/N), notes
```

### Success Criteria
- [ ] ≥ 20 past markets across ≥ 5 tickers with non-empty resolved_side and valid resolution_source_url.
- [ ] Deterministic outputs; robust to missing/ambiguous markets.
- [ ] Unit tests for discovery, labels, OHLCV stitching, returns.

---

## All Needed Context

### Documentation & References
- GET https://gamma-api.polymarket.com/public-search?q=QUERY — Discover markets by ticker or company name.
- GET https://gamma-api.polymarket.com/markets/slug/{slug} — Market details, clobTokenIds, resolved state, resolution fields.
- GET https://clob.polymarket.com/prices-history?market=<YES_TOKEN_ID>&startTs=&endTs=&fidelity=1 — Optional minute bars.
- Alpha Vantage helper: fetch_recent_ohlcv(symbol, resolution_min, n_bars) — Modify to add start_date/end_date.

### Desired Codebase Tree
```
apps/
  polymarket_logger/
    __init__.py
    cli.py
    core.py
    models.py
    sheets.py
    tests/
      test_discovery.py
      test_labels.py
      test_prices.py
      test_integration.py
```

### Known Gotchas & Library Quirks
```
- Normalize all times to UTC; handle 16:00 ET close and 09:30 ET open.
- Store resolution_text and resolution_source_url; market definition matters (GAAP vs non-GAAP, EPS vs revenue).
- Modify Alpha Vantage signature to accept start_date/end_date.
- Search both ticker and company name in Gamma.
```

## Implementation Blueprint

### Data models and structure (pydantic)
```python
from pydantic import BaseModel
from typing import Optional

class MarketRecord(BaseModel):
    date_utc: str
    ticker: str
    report_session: Optional[str] = None
    earnings_datetime_utc: Optional[str] = None
    pm_market_id: str
    pm_market_slug: str
    pm_market_title: str
    resolved: bool
    resolved_side: Optional[str] = None
    resolution_text: Optional[str] = None
    resolution_source_url: Optional[str] = None
    px_prev_close: Optional[float] = None
    px_next_open: Optional[float] = None
    px_next_close: Optional[float] = None
    gap_return_open_pct: Optional[float] = None
    day_return_close_pct: Optional[float] = None
    pm_correct_on_price_dir_open: Optional[int] = None
    pm_correct_on_price_dir_close: Optional[int] = None
    wording_clear: str = "Y"
    notes: Optional[str] = None
```

### Tasks

**Task 1 — Discovery & Labels (`core.py`)**
- gamma_search(query) — /public-search?q=<query>
- pick_earnings_market(search_json, query_hint)
- gamma_market_by_slug(slug) — /markets/slug/{slug}
- extract_resolution_fields(details) — resolved, resolved_side, resolution_text, resolution_source_url
- build_market_record(ticker, details)

**Task 2 — Prices (Alpha Vantage helper)**
- Modify signature:
```python
def fetch_recent_ohlcv(symbol: str, resolution_min: int, n_bars: int,
                       start_date: str | None = None, end_date: str | None = None):
    """Return bars in UTC sliced by date range when provided."""
```
- Add:
```python
def get_prev_close_next_open_next_close(symbol: str, event_datetime_utc: str) -> tuple[float, float, float]:
    """AMC: prev_close=same-day close; BMO: prev_close=prior day; compute next open/close accordingly."""
```

**Task 3 — CLI (`cli.py`)**
- Args: --ticker, --since, --until, --sheet, --csv
- Loop tickers & days → discovery → details → if resolved → prices → returns → correctness → append

**Task 4 — Sheets/CSV (`sheets.py`)**
- append_row_to_sheet(sheet_name, record)
- append_row_to_csv(path, record)

**Task 5 — Tests**
- test_discovery.py, test_labels.py, test_prices.py, test_integration.py

## Pseudocode (key flows)

**Resolution extraction**
```python
def extract_resolution_fields(details: dict) -> dict:
    resolved = bool(details.get("resolved") or details.get("isResolved") or details.get("outcome"))
    side = details.get("outcome")
    if side is True:  side = "YES"
    if side is False: side = "NO"
    res_text = details.get("resolutionText") or (details.get("resolution") or {}).get("text") or (details.get("event") or {}).get("resolutionText")
    res_url  = details.get("resolutionSourceUrl") or (details.get("resolution") or {}).get("sourceUrl") or (details.get("event") or {}).get("resolutionSourceUrl")
    return {"resolved": resolved, "resolved_side": side if resolved else None, "resolution_text": res_text, "resolution_source_url": res_url}
```

**Correctness vs price direction**
```python
exp = "Up" if rec.resolved_side == "YES" else "Down" if rec.resolved_side == "NO" else None
def _dir(x): return "Up" if (x or 0) > 0 else ("Down" if (x or 0) < 0 else "Flat")
rec.pm_correct_on_price_dir_open  = int(exp == _dir(rec.gap_return_open_pct))  if exp else None
rec.pm_correct_on_price_dir_close = int(exp == _dir(rec.day_return_close_pct)) if exp else None
```

---

## Integration Points
- POLYMARKET_GAMMA_BASE (default: https://gamma-api.polymarket.com)
- POLYMARKET_CLOB_BASE  (default: https://clob.polymarket.com)
- ALPHA_VANTAGE_API_KEY / AV_BASE_URL
- SHEETS_CREDENTIALS / CSV_PATH

**Entrypoint:**
```bash
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --until 2025-10-31 --csv ./out.csv
```

## Validation Loop
- ruff + mypy clean
- Unit tests for discovery/labels/prices
- Integration run over a month window

## Final Checklist
- ≥ 20 historical markets processed without error
- All rows have resolved=True and non-empty resolution_source_url
- Returns populated; correctness flags present
- Tests pass; lints clean

## Anti-Patterns
- Dropping resolution_text/source
- Mixing ET and UTC
- Assuming ticker always in title
- Hardcoding AMC/BMO rules without tests

## Claude — Starter signatures
```python
def gamma_search(query: str) -> dict: ...
def pick_earnings_market(search_json: dict, query_hint: str | None = None) -> dict: ...
def gamma_market_by_slug(slug: str) -> dict: ...
def extract_resolution_fields(details: dict) -> dict: ...
def build_market_record(ticker: str, details: dict) -> "MarketRecord": ...

def fetch_recent_ohlcv(symbol: str, resolution_min: int, n_bars: int,
                       start_date: str | None = None, end_date: str | None = None): ...
def get_prev_close_next_open_next_close(symbol: str, event_datetime_utc: str) -> tuple[float, float, float]: ...
```
