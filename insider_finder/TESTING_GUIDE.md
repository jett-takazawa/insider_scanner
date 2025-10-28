# Testing Guide for Polymarket Holder Edge Scanner

## URL Support Added ✅

The scanner now supports **three input formats**:

1. **Full URL**: `https://polymarket.com/event/slug-here?tid=123`
2. **Slug only**: `slug-here`
3. **Condition ID**: `0x1234abcd...`

### Examples

```bash
# Using full URL
python -m edge_scan run --market "https://polymarket.com/event/aapl-q3-earnings?tid=123" --outdir ./output

# Using slug
python -m edge_scan run --market "aapl-q3-earnings" --outdir ./output

# Using condition ID
python -m edge_scan run --market "0x1234..." --outdir ./output
```

## Finding Real Markets to Test

The provided test slug `pg-quarterly-earnings-nongaap-eps-10-24-2025-1pt9` appears to be a hypothetical/future market that doesn't exist in the Gamma API yet.

### How to Find Active Earnings Markets

1. **Visit Polymarket Website**
   - Go to https://polymarket.com
   - Search for "earnings" or specific companies (AAPL, MSFT, GOOGL, etc.)
   - Look for active markets with current holders

2. **Check Market URL**
   - Click on an active earnings market
   - Copy the full URL from your browser
   - URL format: `https://polymarket.com/event/{slug}?tid={transaction_id}`

3. **Verify Market is Active**
   - Check that the market has:
     - Current holders (not zero)
     - Has not resolved yet (or recently resolved)
     - Related to earnings (contains "earnings", "EPS", "quarterly")

### Example of Finding a Market

1. Go to https://polymarket.com
2. Search for recent big tech earnings (e.g., "Apple earnings Q4 2024")
3. Click on the market
4. Copy URL: `https://polymarket.com/event/aapl-q4-2024-earnings-beat?tid=12345`
5. Run: `python -m edge_scan run --market "<that_url>" --outdir ./output`

## Testing with Mock Data

If no real markets are available, you can test the core functionality:

### Test Individual Components

```python
# Test URL extraction
from edge_scan.fetchers.gamma import extract_slug_from_url

url = "https://polymarket.com/event/test-market-slug?tid=123"
slug = extract_slug_from_url(url)
print(f"Extracted: {slug}")  # Should print: test-market-slug

# Test feature computation with mock data
from edge_scan.features import compute_features
from edge_scan.config import Config
from edge_scan.models import ClosedPosition

cfg = Config.default()
positions = [
    ClosedPosition(
        title="AAPL Quarterly Earnings Q3 2024",
        event_id="test",
        pnl_usd=100.0,
        was_winner=True,
        resolved_at="2024-10-01T00:00:00Z",
        amount_risked=500.0,
    )
]

features, sample_size = compute_features(
    address="0x1234...",
    current_stake_usd=1000.0,
    closed_positions=positions,
    trades=[],
    cfg=cfg,
)

print(f"Features: {features}")
print(f"Sample size: {sample_size}")
```

## Common Issues

### 422 Unprocessable Entity
**Cause**: Slug doesn't exist in Gamma API
**Solution**: Verify the market exists on polymarket.com and use the exact slug from the URL

### 400 Bad Request on Holders
**Cause**: Invalid condition_id format or market identifier
**Solution**: Ensure you're using a real, active market with actual holders

### Empty Holders List
**Cause**: Market has no current positions or is archived
**Solution**: Choose an active market with visible holders on the website

## API Endpoint Reference

### Gamma API (Market Metadata)
- Base: `https://gamma-api.polymarket.com`
- Get by slug: `GET /markets/{slug}`
- Search: `GET /markets?condition_id={id}`

### Data API (Wallet Data)
- Base: `https://data-api.polymarket.com`
- Holders: `GET /holders?market={condition_id}`
- Trades: `GET /trades?market={condition_id}&user={address}`
- Closed Positions: `GET /closed-positions?user={address}`

### CLOB API (Order Book)
- Base: `https://clob.polymarket.com`
- Book: `GET /book?token_id={token_id}`

## Successful Test Checklist

A successful test run should show:

```
======================================================================
Polymarket Holder Edge & Insider-Likelihood Scanner
======================================================================
Using default configuration
Resolving market: <your_input>
Extracted slug from URL: <slug>         # If using URL
Fetching market by slug: <slug>
Market resolved: <market_title>
Condition ID: <condition_id>
Fetching current holders...
Found X holders                          # X > 0
Processing wallets...
Processing wallet 10/X...
Successfully processed Y wallets         # Y > 0
Computing scores...
Market Signal: UP/DOWN/FLAT (score: 0.XXXX)
======================================================================
Analysis complete! Results written to: ./output
======================================================================
```

## Next Steps After Finding Real Markets

Once you have a real, active earnings market:

1. **Run full analysis**
   ```bash
   python -m edge_scan run \
     --market "<real_market_url>" \
     --outdir ./runs/test \
     --include-book \
     --save-csv --save-json --save-md \
     --verbose
   ```

2. **Review outputs**
   - Check `holders.csv` for ranked wallets
   - Read `report.md` for human-readable analysis
   - Inspect `holders.json` for complete data

3. **Tune configuration**
   - Edit `config.yaml` to adjust weights
   - Rerun with `--config custom_config.yaml`

4. **Compare signals**
   - Run on multiple earnings markets
   - Track signal accuracy over time
   - Build historical backtest dataset

## Support

If you continue to have issues:

1. Verify the market exists on polymarket.com
2. Check that the market has active holders (not empty)
3. Ensure it's an earnings-related market
4. Try a different, more recent earnings market

For API issues, check Polymarket's documentation or Discord for API changes.
