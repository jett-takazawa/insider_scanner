# The Insider - Polymarket Earnings Logger

Automate collection of historical Polymarket earnings Beat/Miss markets and compare them to actual stock price movements.
** I have shifted my focus to building an intricate machine learning system, I will prototype using the scikit learn SDK then use Pytorch for a deeper learning model. ** 

## Overview

This tool fetches resolved Polymarket earnings markets, extracts resolution data (YES/NO outcomes and sources), and compares predictions to next-day stock moves. The output is structured data in Google Sheets or CSV format for predictive accuracy analysis. My repository includes additional PRP's which show the extent of my contextual coding. 

## Features

- **Market Discovery**: Search Polymarket Gamma API for earnings-related markets
- **Resolution Extraction**: Defensive parsing of resolution data across different API response formats
- **Stock Price Integration**: Fetch OHLCV data from Alpha Vantage with AMC/BMO session handling
- **Return Calculations**: Compute gap% (open vs prev close) and day% (close vs prev close)
- **Correctness Metrics**: Determine if Polymarket predictions matched actual price direction
- **Flexible Output**: Export to Google Sheets or CSV

## Installation

### Requirements

- Python 3.11+
- Alpha Vantage API key (free at https://www.alphavantage.co/support/#api-key)
- Google Sheets credentials (optional, for Sheets output)

### Setup

```bash
# Clone or download the repository
cd The_Insider

# Install dependencies
pip install httpx pydantic gspread google-auth

# Install development dependencies (optional)
pip install pytest pytest-cov ruff mypy
```

### Environment Variables

Set your Alpha Vantage API key:

```bash
export ALPHA_VANTAGE_API_KEY="your_api_key_here"
```

For Google Sheets output, set the credentials path (defaults to `./Credentials.json`):

```bash
export GOOGLE_SHEETS_CREDENTIALS="/path/to/credentials.json"
```

## Usage

### Basic CLI Usage

```bash
# Single ticker to CSV
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --until 2025-10-31 --csv ./out.csv

# Multiple tickers to Google Sheets
python -m apps.polymarket_logger --ticker NFLX AAPL GOOGL --since 2025-09-01 --sheet 'PolymarketEarnings'

# Both outputs with verbose logging
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --csv ./out.csv --sheet 'Earnings' -v

# Include unresolved markets
python -m apps.polymarket_logger --ticker NFLX --since 2025-09-01 --csv ./out.csv --include-unresolved
```

### CLI Arguments

- `--ticker, -t`: One or more stock ticker symbols (required)
- `--since, -s`: Start date for search window in YYYY-MM-DD format (required)
- `--until, -u`: End date for search window (defaults to today)
- `--csv, -c`: Path to CSV output file
- `--sheet`: Name of Google Sheet to append results
- `--credentials`: Path to Google Sheets service account credentials JSON
- `--include-unresolved`: Include unresolved markets (default: resolved only)
- `--verbose, -v`: Enable verbose logging

## Output Format

Each record contains the following fields:

| Field | Description |
|-------|-------------|
| `date_utc` | Event date in UTC (YYYY-MM-DD) |
| `ticker` | Stock ticker symbol |
| `report_session` | Earnings session (AMC/BMO) |
| `earnings_datetime_utc` | Earnings announcement time (ISO 8601) |
| `pm_market_id` | Polymarket market ID |
| `pm_market_slug` | Polymarket market slug |
| `pm_market_title` | Market question/title |
| `resolved` | Whether market is resolved |
| `resolved_side` | Outcome (YES/NO) |
| `resolution_text` | Resolution explanation |
| `resolution_source_url` | URL to resolution source |
| `px_prev_close` | Previous day's closing price |
| `px_next_open` | Next session's opening price |
| `px_next_close` | Next session's closing price |
| `gap_return_open_pct` | Gap return percentage |
| `day_return_close_pct` | Day return percentage |
| `pm_correct_on_price_dir_open` | 1 if prediction matched gap direction, 0 otherwise |
| `pm_correct_on_price_dir_close` | 1 if prediction matched day direction, 0 otherwise |
| `wording_clear` | Market wording clarity (Y/N) |
| `notes` | Additional notes |

## Development

### Project Structure

```
The_Insider/
├── apps/
│   └── polymarket_logger/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py           # CLI entry point
│       ├── core.py          # Market discovery & resolution extraction
│       ├── fetchcandles.py  # Stock price fetching (AMC/BMO logic)
│       ├── models.py        # Pydantic data models
│       ├── sheets.py        # Google Sheets/CSV output
│       └── tests/           # Unit tests
├── CLAUDE.md                # Project-specific guidance
├── CLAUDE_GUIDE.md          # General Python development practices
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest apps/polymarket_logger/tests/ -v

# Run with coverage
pytest --cov=apps --cov-report=html
```

### Code Quality

```bash
# Check linting
ruff check apps/

# Auto-fix linting issues
ruff check --fix apps/

# Format code
ruff format apps/

# Type checking
mypy apps/
```

## AMC vs BMO Session Logic

The tool correctly handles different earnings release timings:

**AMC (After Market Close)**
- Earnings released after 16:00 ET
- `prev_close`: Same trading day's 16:00 close
- `next_open`: Next trading day's 09:30 open
- `next_close`: Next trading day's 16:00 close

**BMO (Before Market Open)**
- Earnings released before 09:30 ET
- `prev_close`: Prior trading day's 16:00 close
- `next_open`: Same trading day's 09:30 open
- `next_close`: Same trading day's 16:00 close

## Known Limitations

- Holiday trading schedules not accounted for (uses simple weekend skip logic)
- Ticker-to-company name mapping is basic (searches by ticker only)
- No live market probability snapshots (focused on historical ground truth)
- Alpha Vantage rate limits apply (5 API calls/minute for free tier)

## Contributing

Follow the guidelines in `CLAUDE_GUIDE.md` for:
- Code structure (max 500 lines/file, 50 lines/function)
- Testing practices (TDD, >80% coverage)
- Type hints and docstrings
- PRP-driven development for new features

## License

This project is for educational and research purposes.

## Support

For issues or questions, refer to:
- `CLAUDE.md`: Project-specific implementation details
- `Polymarket_Earnings_GroundTruth_Logger_PRP.md`: Full specification
- Alpha Vantage docs: https://www.alphavantage.co/documentation/
- Polymarket API docs: https://docs.polymarket.com/
