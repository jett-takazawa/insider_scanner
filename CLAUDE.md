# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**The Insider** - Polymarket earnings prediction tracker that collects historical Polymarket earnings Beat/Miss markets, compares them to actual stock price movements, and logs results for analysis.

### Core Purpose
- Fetch resolved Polymarket earnings markets via Gamma API
- Extract resolution data (YES/NO outcome, resolution source, resolution text)
- Collect corresponding stock OHLCV data around earnings events
- Compute gap% (open vs prev close) and day% (close vs prev close)
- Output structured data to Google Sheets/CSV for predictive accuracy analysis

## Project Structure

```
The_Insider/
├── Credentials.json                    # Google Sheets API credentials
├── googlesheets_demo.py               # Google Sheets integration (empty)
├── fetchcandles.py                    # OHLCV fetching utilities (empty)
├── polymarketfetch.py                 # Polymarket API client (empty)
├── prp_base.md                        # PRP template for feature planning
├── Polymarket_Earnings_GroundTruth_Logger_PRP.md  # Main project spec
└── CLAUDE_GUIDE.md                    # General Python development guidelines
```

### Planned Architecture (from PRP)
```
apps/
  polymarket_logger/
    __init__.py
    cli.py          # CLI entry point (--ticker, --since, --until, --sheet)
    core.py         # Discovery, resolution extraction, market record building
    models.py       # Pydantic models (MarketRecord)
    sheets.py       # Google Sheets/CSV output
    tests/
      test_discovery.py
      test_labels.py
      test_prices.py
      test_integration.py
```

## API Endpoints & Data Sources

### Polymarket (Gamma API)
- **Market Search**: `GET https://gamma-api.polymarket.com/public-search?q=QUERY`
- **Market Details**: `GET https://gamma-api.polymarket.com/markets/slug/{slug}`
- **Resolution Fields**: Extract `resolved`, `resolved_side`, `resolution_text`, `resolution_source_url`

### Polymarket (CLOB API)
- **Price History**: `GET https://clob.polymarket.com/prices-history?market=<YES_TOKEN_ID>&startTs=&endTs=&fidelity=1`

### Stock Data
- **Alpha Vantage**: OHLCV bars (modify helper to accept start_date/end_date)
- **Critical**: Handle AMC (after-market-close) vs BMO (before-market-open) session timing
  - AMC: prev_close = same-day close
  - BMO: prev_close = prior day close

## Key Data Model

```python
class MarketRecord(BaseModel):
    date_utc: str
    ticker: str
    report_session: Optional[str] = None  # AMC/BMO
    earnings_datetime_utc: Optional[str] = None
    pm_market_id: str
    pm_market_slug: str
    pm_market_title: str
    resolved: bool
    resolved_side: Optional[str] = None  # YES/NO
    resolution_text: Optional[str] = None
    resolution_source_url: Optional[str] = None
    px_prev_close: Optional[float] = None
    px_next_open: Optional[float] = None
    px_next_close: Optional[float] = None
    gap_return_open_pct: Optional[float] = None
    day_return_close_pct: Optional[float] = None
    pm_correct_on_price_dir_open: Optional[int] = None  # 1/0
    pm_correct_on_price_dir_close: Optional[int] = None  # 1/0
    wording_clear: str = "Y"
    notes: Optional[str] = None
```

## Critical Implementation Details

### Time Handling
- **All times in UTC** - critical for AMC/BMO session logic
- US market hours: 09:30-16:00 ET (14:30-21:00 UTC during DST, 15:30-22:00 UTC standard)
- Store `earnings_datetime_utc` and normalize all price timestamps to UTC

### Resolution Extraction Pattern
Resolution fields may be nested differently across Polymarket responses. Use defensive extraction:

```python
def extract_resolution_fields(details: dict) -> dict:
    resolved = bool(details.get("resolved") or
                   details.get("isResolved") or
                   details.get("outcome"))

    side = details.get("outcome")
    if side is True:  side = "YES"
    if side is False: side = "NO"

    res_text = (details.get("resolutionText") or
                (details.get("resolution") or {}).get("text") or
                (details.get("event") or {}).get("resolutionText"))

    res_url = (details.get("resolutionSourceUrl") or
               (details.get("resolution") or {}).get("sourceUrl") or
               (details.get("event") or {}).get("resolutionSourceUrl"))

    return {
        "resolved": resolved,
        "resolved_side": side if resolved else None,
        "resolution_text": res_text,
        "resolution_source_url": res_url
    }
```

### Market Discovery
- Search by both ticker symbol AND company name (e.g., "NFLX" and "Netflix")
- Filter for earnings-specific markets (look for "beat", "earnings", "EPS" in title)
- Validate ticker matches to avoid false positives

### Stock Price Stitching (AMC/BMO Logic)
```python
# AMC (After Market Close, e.g., 16:05 ET)
# prev_close = same trading day's 16:00 close
# next_open = next trading day's 09:30 open
# next_close = next trading day's 16:00 close

# BMO (Before Market Open, e.g., 07:00 ET)
# prev_close = prior trading day's 16:00 close
# next_open = same trading day's 09:30 open
# next_close = same trading day's 16:00 close
```

## Development Commands

```bash
# Run the CLI (once implemented)
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --until 2025-10-31 --sheet 'PolymarketEarnings'

# Run tests (follow CLAUDE_GUIDE.md patterns)
uv run pytest
uv run pytest apps/polymarket_logger/tests/test_discovery.py -v

# Linting and formatting
uv run ruff check .
uv run ruff format .
uv run mypy apps/
```

## PRP-Driven Development

This project follows a structured PRP (Product Requirements Plan) approach:

1. **Always read the PRP first**: `Polymarket_Earnings_GroundTruth_Logger_PRP.md` contains the canonical spec
2. **Use `prp_base.md` template** for any new features
3. **Key PRP principles**:
   - Context is king: include all docs, examples, gotchas
   - Validation loops: implement tests that can be run and fixed iteratively
   - Progressive success: start simple, validate, enhance
   - Follow all rules in CLAUDE_GUIDE.md

## Google Sheets Integration

- Uses `Credentials.json` for authentication
- Service account pattern (not OAuth)
- Append-only writes to avoid data loss
- Output columns match MarketRecord schema exactly

## Success Criteria (from PRP)

- Process ≥20 past markets across ≥5 tickers
- All records have `resolved=True` and non-empty `resolution_source_url`
- Deterministic outputs (same inputs → same outputs)
- Robust to missing/ambiguous markets
- Unit tests for discovery, labels, OHLCV stitching, returns calculation

## Common Gotchas

1. **Mixing ET and UTC** - always normalize to UTC before calculations
2. **Market definition ambiguity** - some markets track GAAP EPS, others non-GAAP or revenue
3. **Ticker in title assumption** - not all markets include ticker; search by company name too
4. **Hardcoding AMC/BMO** - session timing requires tests for edge cases (holidays, pre-market moves)
5. **Dropping resolution metadata** - `resolution_text` and `resolution_source_url` are critical for analysis

## Anti-Patterns to Avoid

- Skipping validation loops - always run ruff/mypy/pytest before claiming completion
- Creating new patterns when existing ones work (follow CLAUDE_GUIDE.md conventions)
- Ignoring failing tests - fix the root cause, never mock to pass
- Hardcoding values that should be config (API endpoints, date ranges, thresholds)
- Using sync functions in async contexts (if async is introduced)

## Related Documentation

- **CLAUDE_GUIDE.md**: General Python development practices (KISS, YAGNI, TDD, UV usage)
- **Polymarket_Earnings_GroundTruth_Logger_PRP.md**: Full implementation spec
- **prp_base.md**: Template for creating new PRPs

## Notes

- This is a data collection/ETL project, not a trading system
- Focus is on historical ground truth, not live prediction (yet)
- Output dataset will be used for calibration and hit-rate studies
- No environment variables or .env file currently used; add if needed for API keys
