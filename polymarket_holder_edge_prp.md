# PRP: Polymarket Holder Edge & Insider-Likelihood Scanner
_A context-rich, validation-loop PRP for Claude to generate a Python tool that rates every wallet in a market by **behaviorally inferred insider-likelihood** (non-legal, probabilistic)._

> **Legal/Language guardrail:** This tool does **not** assert illegal activity. Use terms like **edge**, **likelihood**, **probable advantage**, **behavioral signal**. Avoid the words “illegal,” “criminal,” or definitive labels like “insider.”

---

## Purpose
Build a **Python CLI** that accepts a **Polymarket market input** (slug or conditionId), enumerates **all current holders** and their **activity history**, computes **per-wallet features** that correlate with having an **edge near earnings events**, and produces a **ranked report**: CSV, JSON, and human-readable Markdown.

The user will manually supply the target markets (e.g., those for large‑weight SPDR constituents). The tool focuses on **GAAP EPS earnings markets**, but allows you to **tune filters** via a config file.

---

## Core Principles
1. **Context is King** — bake all API endpoints and data contracts into fetchers.
2. **Validation Loops** — include tests, type checks, and lint; fail loudly with hints.
3. **Information Dense** — feature names & weights defined in a single configurable schema.
4. **Progressive Success** — fetch → parse → score → export; partial data produces partial, clearly-flagged reports.
5. **Global Rules** — deterministic scoring; reproducible via `--seed`; clear CLI & docstrings.

---

## Goal (End-State)
A single command like:
```bash
python -m edge_scan run \
  --market "txn-quarterly-earnings-gaap-eps-10-21-2025-1pt49" \
  --outdir ./runs/txn_q3_2025 \
  --since-quarters 16 \
  --min-sample 5 \
  --include-book \
  --save-csv --save-json --save-md
```
**Delivers:**
- `holders.csv` — ranked wallets with features & scores
- `holders.json` — same as JSON with run metadata
- `report.md` — clean tables + commentary on the market
- `run_meta.json` — parameters, timestamps, and endpoint versions

---

## Why
- You can **manually pick** the mega-cap earnings markets; this tool answers: **“Who are the meaningful wallets, how strong is their historical edge, and how are they leaning now?”**
- This transforms vague on-chain browsing into a **repeatable, auditable** input for a direction call or a **pass**.

---

## What (User-Visible Behavior & Technical Requirements)
- **Inputs**
  - `--market` (slug _or_ conditionId; tool resolves IDs)
  - `--since-quarters` (default: 16) historical lookback
  - `--earnings-title-regex` (default: `(?i)(earnings|EPS|quarterly)`)
  - `--min-sample` prior resolved positions to qualify for full scoring (default: 5)
  - `--include-book` to pull order book depth/spread for sanity checks
  - `--config` path to YAML that overrides weights, filters, and caps
  - `--seed` for reproducibility

- **Outputs**
  - **CSV/JSON/MD** with all computed features, scores, missingness flags
  - An optional **MarketSignal**: score-weighted side across top holders

- **Robustness**
  - Retries with backoff and jitter for network/rate limits
  - Partial failure toleration; still write a report with explicit gaps

- **Language/Presentation**
  - “InsiderLikelihoodScore” is **bounded [0,1]** and described as **behavioral likelihood of edge**; never imply illegality

---

## Success Criteria
- [ ] Accepts market **slug or conditionId** and resolves required IDs
- [ ] Enumerates **all holders** via Data API + Subgraph fallback
- [ ] Computes **bounded [0,1]** scores for wallets meeting `--min-sample`
- [ ] Produces **CSV, JSON, MD** and a **MarketSignal** summary
- [ ] Passes unit tests, mypy, and ruff; clear docstrings & CLI help
- [ ] Handles **rate limits** and **partial data** gracefully

---

## All Needed Context

### Documentation & References (include in Claude’s context)
```yaml
- url: https://gamma-api.polymarket.com/
  why: Resolve market by slug/id → conditionId, token ids, title, end time

- url: https://data-api.polymarket.com/
  why: Holders (per market), Trades (per user/market), Closed Positions (per user)

- url: https://docs.goldsky.com/
  why: Public subgraphs fallback to enumerate all userPositions for a conditionId

- docfile: THIS_PRP.md
  why: Source of truth for scoring, config schema, CLI contracts, and tests
```

> **Note:** You (Claude) should use **Data API** for speed & simplicity; if holder coverage appears truncated, use the **Subgraph** fallback to enumerate full positions.
  
**Common endpoints to use** (exact routes may vary by version):
- Market by slug → `GET /markets/slug/{slug}` → `conditionId`, `token_ids`, `endTime`
- Top holders → `GET /holders?market={conditionId}&limit=500`
- All trades for market & user → `GET /trades?market={conditionId}&user={address}`
- Closed positions (user) → `GET /closed-positions?user={address}&title=earnings`
- (Optional) Order book snapshot → `GET /book?token_id={yes_token_id}` (and NO)  

All timestamps should be treated as **UTC** internally.

---

## Desired Codebase Tree (create new project)
```bash
edge_scan/
  __init__.py
  cli.py                  # Typer/Click CLI (+ argparse fallback)
  config.py               # dataclasses for weights, thresholds, filters
  fetchers/
    __init__.py
    gamma.py              # slug/id → market metadata (conditionId, tokens, endTime)
    data_api.py           # holders, trades, closed positions
    subgraph.py           # fallback: enumerate all userPositions for conditionId
    clob.py               # optional: order book depth/spread, mid
  models.py               # pydantic models for API responses
  features.py             # per-wallet feature engineering
  scoring.py              # InsiderLikelihoodScore & MarketSignal
  export.py               # CSV/JSON/Markdown writers
  utils.py                # retries, logging, time parsing, math helpers
tests/
  test_cli.py
  test_fetchers.py
  test_features.py
  test_scoring.py
  test_export.py
pyproject.toml            # ruff, mypy, pytest, requests/httpx pinned
README.md                 # quickstart, glossary, caveats
```

---

## Known Gotchas & Library Quirks
```python
# CRITICAL: Implement exponential backoff with jitter on all HTTP calls.
# CRITICAL: Normalize token amounts to USD consistently; be explicit about decimals.
# CRITICAL: Market titles vary: use both title regex AND (optional) curated eventId allowlist.
# NOTE: Some wallets will have zero closed earnings positions → apply shrinkage toward 0.5.
# NOTE: Use winsorization on features; cap any single wallet's influence when aggregating.
# NOTE: Prefer UTC everywhere; expose --tz if you need local times in report.md.
```

---

## Implementation Blueprint

### Config (easy tweak surface, no code edits needed)
`config.yaml` (defaults — can be overridden at runtime)
```yaml
history:
  earnings_title_regex: "(?i)(earnings|EPS|quarterly)"
  lookback_quarters: 16
  min_sample: 5

weights:                # tweak freely; normalized internally
  win_rate: 0.35
  pnl_per_usd: 0.25
  timing_edge: 0.20
  conviction_z: 0.15
  consistency: 0.05

filters:
  ignore_low_activity_usd: 250    # lifetime risk floor across earnings
  ignore_total_trades_lt: 10

caps:
  feature_clip_pct: 0.95          # winsorize each feature
  max_influence_single_wallet: 0.33

scoring:
  shrinkage_prior: 0.50           # prior for win-rate & pnl if sample small
  score_floor: 0.00
  score_ceiling: 1.00

market_signal:
  use_dir_from_price: true        # include DirScore from YES midprice (optional)
  dir_weight: 0.30
  holder_weight: 0.70
```

### Feature Engineering (per wallet A)
We **never** label “insider.” We score **behavioral edge** on prior **earnings-type** markets and current activity.

Let `Sᴀ` be A’s current stake (USD) in the target market and `sideᴀ ∈ {+1 for YES, -1 for NO}`.

1) **WinRate** — size‑weighted % of resolved earnings markets where A held the winning outcome. Apply Bayesian shrinkage toward `0.5` using `min_sample` and `shrinkage_prior`.
2) **PnL per USD** — median realized PnL per $ risked on earnings markets; winsorize to `caps.feature_clip_pct`, shrink to prior if low sample.
3) **Timing Edge** — fraction of A’s size added within **T−24h → T−1h** before resolution vs their own baseline timing distribution.
4) **Conviction Z** — Z‑score of A’s **current stake** vs their **median stake** on prior earnings markets.
5) **Consistency** — alignment of A’s side on **this ticker/sector** vs their historical side (helps spot specialists).

Normalize each feature to `[0,1]` (min‑max or robust scaling), then compute:

```
InsiderLikelihoodScore(A) =
  w1·WinRate + w2·PnLperUSD + w3·TimingEdge + w4·ConvictionZ + w5·Consistency
# clip to [score_floor, score_ceiling]
```

**Direction Contribution** (for market aggregation):
```
SignedContribution(A) = InsiderLikelihoodScore(A) · normalize(Sᴀ) · sideᴀ
```

**MarketSignal (optional):**
- **HolderSignal** = Σ SignedContribution(A)  (cap any single wallet’s influence per `caps.max_influence_single_wallet`)
- **DirScore** = transform(YES_midprice) = (p − 0.5) * 2  ∈ [−1, +1]
- **FinalScore** = holder_weight·HolderSignal + dir_weight·DirScore

Direction (advisory):
- UP if FinalScore ≥ +0.25  
- DOWN if FinalScore ≤ −0.25  
- else FLAT / PASS

### Data Contracts (expected fields)
- **Market metadata**: `conditionId`, `title`, `endTime`, `tokenYesId`, `tokenNoId`
- **Holders**: `address`, `amountUSD`, `outcomeIndex` (0/1), `username?`
- **Trades**: `ts`, `side`, `price`, `amount`, `amountUSD`, `market`
- **Closed positions**: `marketTitle`, `eventId?`, `pnlUSD`, `wasWinner`, `resolvedAt`

---

## Tasks (in order)

### Task 1 — Project Scaffolding
- Create tree above; set `pyproject.toml` with `requests` or `httpx`, `pydantic`, `typer`/`click`, `pandas`, `pytest`, `ruff`, `mypy`.

### Task 2 — Fetchers
- `gamma.py`: resolve slug → market metadata
- `data_api.py`: holders (top 500+ paging), trades (by market/user), closed positions (by user)
- `subgraph.py`: fallback for complete holders via `userPositions(conditionId)`
- `clob.py`: order book snapshot for YES/NO → midprice & top-of-book depth

### Task 3 — Models
- Pydantic response models with `.from_api()` helpers and `.to_df()` conversions

### Task 4 — Features & Scoring
- Implement feature extraction (per wallet) with robust scaling, winsorization, and shrinkage
- Implement `InsiderLikelihoodScore` + `MarketSignal` aggregation

### Task 5 — Exports
- CSV/JSON writers and a `report.md` generator (pretty tables, top 20 wallets, signals, caveats)

### Task 6 — CLI
- `edge_scan run --market ...` with options; print concise run summary; write artifacts to `outdir`

### Task 7 — Validation Loop
- Add tests for: fetchers (mocked JSON), features (toy data), scoring (deterministic), exports (schema), CLI (arg parsing)
- Add `ruff`, `mypy`, `pytest` runners to README

---

## Per-Task Pseudocode (critical bits)

```python
# features.py
def compute_features(user_history: History, current_market: Market, cfg: Config) -> FeatureVector:
    # WinRate with shrinkage
    wr_obs = user_history.earnings_observations  # list of (was_winner: bool, stake_usd: float)
    wr_raw = weighted_mean([w for w,_ in wr_obs], weights=[s for _,s in wr_obs])
    wr = shrink_to_prior(wr_raw, prior=cfg.scoring.shrinkage_prior, n=len(wr_obs), n0=cfg.history.min_sample)

    # PnL per USD (median), winsorized
    pnl_ratios = winsorize([pnl/usd for pnl,usd in user_history.pnl_pairs if usd>0], clip=cfg.caps.feature_clip_pct)
    pnl_norm = robust_scale(median(pnl_ratios))

    # Timing edge
    recent_frac = fraction_of_size_in_window(user_history.trades_on_target, window_hours=(24,1))
    timing = compare_to_baseline(recent_frac, user_history.baseline_timing_distribution)

    # Conviction z
    z = z_score(current_market.current_stake_usd, user_history.median_stake_usd, user_history.stake_std)

    # Consistency
    consistency = directional_alignment(current_market.ticker_or_sector, user_history)

    return FeatureVector(win_rate=wr, pnl_per_usd=pnl_norm, timing_edge=timing, conviction_z=z, consistency=consistency)
```

```python
# scoring.py
def insider_likelihood(feat: FeatureVector, w: Weights, cfg: Config) -> float:
    s = (w.win_rate*feat.win_rate +
         w.pnl_per_usd*feat.pnl_per_usd +
         w.timing_edge*feat.timing_edge +
         w.conviction_z*feat.conviction_z +
         w.consistency*feat.consistency)
    return clip(normalize_unit_interval(s), cfg.scoring.score_floor, cfg.scoring.score_ceiling)
```

```python
# export.py
def write_report_md(run: RunMeta, market: Market, rows: list[WalletRow], outpath: Path):
    # include a header with market title, endTime (UTC + local), sample counts
    # render top N by score; add a small glossary; add caveats language
    ...
```

---

## CLI Examples

### Basic
```bash
python -m edge_scan run --market "aapl-quarterly-earnings-gaap-eps-10-28-2025" --outdir ./runs/aapl_q3
```

### Tight filters & custom weights
```bash
python -m edge_scan run --market "msft-..." --config ./configs/strict.yaml --min-sample 8 --since-quarters 12
```

### With order book sanity
```bash
python -m edge_scan run --market "goog-..." --include-book --save-csv --save-json --save-md
```

---

## Validation Loop

### Level 1 — Syntax & Style
```bash
ruff check . --fix
mypy edge_scan
```

### Level 2 — Unit Tests
```bash
pytest -q
```

**Tests to include**
- Happy path end-to-end with mocked API JSON
- Missing trades / no closed positions → shrinkage kicks in
- Rate limit → retries then partial report with flags
- Deterministic scoring with `--seed`

### Level 3 — Manual Dry-Run
```bash
python -m edge_scan run --market "<your-market>" --outdir ./runs/test --save-md
```

---

## Final Checklist
- [ ] Slug → conditionId resolution works
- [ ] Holder enumeration is near-complete (Data API + Subgraph fallback)
- [ ] Every wallet gets a bounded score (or a “Low Sample” flag)
- [ ] Outputs written; report.md readable with tables
- [ ] No legal assertions; wording follows guardrail
- [ ] Tests/type/lint all pass

---

## Anti‑Patterns to Avoid
- ❌ Inferring illegality or intent; stick to **behavioral likelihood of edge**
- ❌ Silent failures; always annotate missing data in outputs
- ❌ Hardcoding weights inside code; keep them in **config.yaml**
- ❌ Single‑wallet dominance; cap influence when aggregating signals
- ❌ Timezone mishaps; keep UTC internally

---

## Appendix: Minimal Data Schemas (pydantic sketch)
```python
class Market(BaseModel):
    condition_id: str
    title: str
    end_time: datetime
    yes_token_id: str | None = None
    no_token_id: str | None = None

class Holder(BaseModel):
    address: str
    username: str | None = None
    outcome_index: int               # 1 for YES, 0 for NO (or vice versa per API)
    amount_usd: float

class Trade(BaseModel):
    ts: datetime
    side: str                        # 'buy'/'sell' or YES/NO
    price: float
    amount: float
    amount_usd: float

class ClosedPosition(BaseModel):
    title: str
    event_id: str | None = None
    pnl_usd: float
    was_winner: bool
    resolved_at: datetime
```

**Done.** Hand this PRP to Claude and ask it to scaffold `edge_scan/` per spec, then fill in fetchers, features, scoring, exports, and tests.
