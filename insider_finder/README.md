# Polymarket Holder Edge & Insider-Likelihood Scanner

A Python CLI tool that analyzes Polymarket wallet behavior to identify holders with probable informational advantages in earnings markets.

## ⚠️ Important Legal Disclaimer

**This tool performs behavioral analysis only.** It computes a "likelihood of edge" score based on historical trading patterns. It makes **NO CLAIMS** about illegal activity, insider trading, or criminal behavior. All scores are probabilistic estimates of informational advantage derived from observable on-chain activity.

Use terms like "edge," "likelihood," and "probable advantage." Never assert illegal activity.

## Features

- **Wallet Analysis**: Computes behavioral edge scores for all holders in a market
- **Feature Engineering**: Win rate, PnL per USD, timing edge, conviction, consistency
- **Market Signals**: Aggregated directional signal from top holders
- **Multiple Outputs**: CSV, JSON, and human-readable Markdown reports
- **Configurable**: YAML-based configuration for weights, filters, and thresholds
- **Robust**: Retry logic with exponential backoff, partial failure tolerance

## Installation

```bash
cd insider_finder
pip install httpx pydantic pyyaml pytest ruff mypy
```

## Quick Start

```bash
# Basic usage
python -m edge_scan run --market pg-quarterly-earnings-nongaap-eps-10-24-2025-1pt9 --outdir ./runs/pg

# With all outputs
python -m edge_scan run --market <slug> --save-csv --save-json --save-md --include-book

# With custom config
python -m edge_scan run --market <slug> --config ./custom_config.yaml --outdir ./output
```

## Configuration

Default configuration is in `config.yaml`. Override via `--config` or CLI args.

```yaml
history:
  earnings_title_regex: "(?i)(earnings|EPS|quarterly)"
  lookback_quarters: 16
  min_sample: 5

weights:  # Normalized internally
  win_rate: 0.35
  pnl_per_usd: 0.25
  timing_edge: 0.20
  conviction_z: 0.15
  consistency: 0.05

filters:
  ignore_low_activity_usd: 250
  ignore_total_trades_lt: 10

caps:
  feature_clip_pct: 0.95
  max_influence_single_wallet: 0.33

scoring:
  shrinkage_prior: 0.50
  score_floor: 0.00
  score_ceiling: 1.00

market_signal:
  use_dir_from_price: true
  dir_weight: 0.30
  holder_weight: 0.70
```

## Output Files

### `holders.csv`
Ranked wallets with features and scores:
- address, username, stake, side
- insider_likelihood_score [0-1]
- Individual features (win_rate, pnl_per_usd, etc.)
- sample_size, low_sample_flag

### `holders.json`
Complete JSON with metadata, market signal, and all wallet scores

### `report.md`
Human-readable Markdown report with:
- Market signal summary
- Top 20 wallets table
- Important caveats and glossary

### `run_meta.json`
Run metadata including config, timestamps, and counts

## Feature Descriptions

### Insider Likelihood Score
Weighted combination of behavioral features [0-1]. Higher scores indicate stronger historical edge on earnings markets.

### Individual Features

- **Win Rate**: Size-weighted % of resolved earnings markets where wallet held winning outcome (with Bayesian shrinkage)
- **PnL per USD**: Median realized PnL per dollar risked (winsorized, robust scaled)
- **Timing Edge**: Concentration of activity near resolution events
- **Conviction Z**: Z-score of current stake vs historical distribution
- **Consistency**: Directional alignment within ticker/sector

## Market Signal

Aggregates individual wallet signals into overall market direction:

- **Holder Signal**: Sum of signed contributions (capped for single-wallet influence)
- **Dir Score**: Directional score from YES mid price (optional)
- **Final Score**: Weighted combination → Direction (UP/DOWN/FLAT)

## CLI Arguments

```
python -m edge_scan run [OPTIONS]

Required:
  --market, -m TEXT          Market slug or condition ID

Optional:
  --outdir, -o TEXT          Output directory (default: ./output)
  --config, -c PATH          Path to config YAML
  --since-quarters INT       Historical lookback quarters
  --min-sample INT           Min sample size for full scoring
  --include-book             Include order book for price signal
  --earnings-only            Filter to earnings markets only
  --save-csv                 Save to CSV
  --save-json                Save to JSON
  --save-md                  Save to Markdown
  --verbose, -v              Enable debug logging
```

## Development

### Run Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Linting
ruff check edge_scan/

# Formatting
ruff format edge_scan/

# Type checking
mypy edge_scan/
```

## Project Structure

```
insider_finder/
├── edge_scan/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Config dataclasses
│   ├── models.py           # Pydantic models
│   ├── features.py         # Feature engineering
│   ├── scoring.py          # Scoring logic
│   ├── export.py           # CSV/JSON/MD writers
│   ├── utils.py            # Utilities (retry, math, etc.)
│   └── fetchers/
│       ├── gamma.py        # Market metadata
│       ├── data_api.py     # Holders/trades/positions
│       ├── subgraph.py     # Subgraph fallback
│       └── clob.py         # Order book
├── tests/
├── config.yaml
├── pyproject.toml
└── README.md
```

## API Endpoints Used

- **Gamma API**: Market metadata resolution
- **Data API**: Holders, trades, closed positions
- **CLOB API**: Order book snapshots
- **Subgraph**: Fallback for complete holder enumeration

## Caveats & Limitations

- **Historical Performance**: Past edge does not guarantee future results
- **Sample Size**: Low-sample wallets have unreliable scores
- **Market Context**: Always consider fundamentals and market conditions
- **No Real-Time**: Analysis is snapshot-based, not live monitoring
- **Timing Edge (Stub)**: Full timing analysis not implemented in MVP
- **Consistency (Stub)**: Ticker/sector alignment not fully implemented

## Roadmap

- [ ] Full timing edge implementation (T-24h to T-1h analysis)
- [ ] Consistency feature (sector/ticker directional patterns)
- [ ] Subgraph integration for complete holder coverage
- [ ] Real-time monitoring mode
- [ ] Historical backtest framework
- [ ] Web dashboard visualization

## License

Educational and research use only.

## Support

Refer to:
- PRP: `polymarket_holder_edge_prp.md`
- General guidelines: `CLAUDE_GUIDE.md`