# Quick Start Guide

Get up and running with the Polymarket Earnings Logger in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Git (optional)
- Alpha Vantage API key (free)

## Setup Steps

### 1. Get an Alpha Vantage API Key

1. Visit https://www.alphavantage.co/support/#api-key
2. Enter your email and click "GET FREE API KEY"
3. Copy your API key (looks like: `ABC123XYZ456`)

### 2. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:ALPHA_VANTAGE_API_KEY="DA7HRX4GDRJMC1X9"
```

**Windows (Command Prompt):**
```cmd
set ALPHA_VANTAGE_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export ALPHA_VANTAGE_API_KEY="your_api_key_here"
```

### 3. Install Dependencies

```bash
pip install httpx pydantic gspread google-auth pytest ruff
```

### 4. Run Your First Query

```bash
python -m apps.polymarket_logger --ticker TESLA --since 2025-08-01 --csv output.csv
```

This will:
- Search for Netflix earnings markets since September 1, 2025
- Fetch resolution data and stock prices
- Save results to `output.csv`

### 5. View the Results

Open `output.csv` in Excel, Google Sheets, or any spreadsheet application.

## Example Output

Your CSV will contain columns like:

| ticker | resolved_side | gap_return_open_pct | pm_correct_on_price_dir_open |
|--------|---------------|---------------------|------------------------------|
| NFLX   | YES           | 5.23                | 1                            |

Where:
- `resolved_side`: What Polymarket predicted (YES = beat, NO = miss)
- `gap_return_open_pct`: Actual stock move (positive = up, negative = down)
- `pm_correct_on_price_dir_open`: 1 if prediction matched reality, 0 if wrong

## Common Use Cases

### Process Multiple Tickers

```bash
python -m apps.polymarket_logger \
  --ticker NFLX AAPL GOOGL MSFT \
  --since 2025-01-01 \
  --csv multi_ticker_output.csv
```

### Enable Verbose Logging

```bash
python -m apps.polymarket_logger \
  --ticker NFLX \
  --since 2025-09-01 \
  --csv output.csv \
  --verbose
```

### Export to Google Sheets

1. Set up Google Sheets credentials (see [Google Sheets Setup](#google-sheets-setup))
2. Run:

```bash
python -m apps.polymarket_logger \
  --ticker NFLX \
  --since 2025-09-01 \
  --sheet "My Earnings Data"
```

## Google Sheets Setup (Optional)

To export to Google Sheets:

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account
4. Download credentials JSON to `./Credentials.json`
5. Share your Google Sheet with the service account email

Detailed instructions: https://docs.gspread.org/en/latest/oauth2.html

## Troubleshooting

### "ALPHA_VANTAGE_API_KEY environment variable not set"

Set the environment variable as shown in Step 2 above.

### "No earnings markets found"

The ticker may not have had earnings markets during the specified date range, or the market hasn't been created yet on Polymarket.

### Rate Limit Errors

Alpha Vantage free tier allows 5 API calls/minute. If you hit the limit:
- Wait 1 minute and try again
- Process fewer tickers at once
- Upgrade to a paid Alpha Vantage plan

### Missing Price Data

Some dates may not have OHLCV data (holidays, weekends, delisted stocks). The tool will log warnings and leave price fields as `None`.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CLAUDE.md](CLAUDE.md) for architecture details
- Review [example_usage.py](example_usage.py) for programmatic usage
- Run tests: `pytest apps/polymarket_logger/tests/ -v`

## Tips

1. **Start with a short date range** to avoid hitting API rate limits
2. **Use verbose mode** (`-v`) when debugging
3. **Check resolution_source_url** to verify Polymarket's ground truth
4. **Focus on resolved markets** (default behavior) for accurate analysis
5. **Cross-reference multiple sources** before making trading decisions

## Support

For bugs or feature requests, refer to:
- Project documentation in `CLAUDE.md`
- PRP specification in `Polymarket_Earnings_GroundTruth_Logger_PRP.md`
- General Python guidelines in `CLAUDE_GUIDE.md`
