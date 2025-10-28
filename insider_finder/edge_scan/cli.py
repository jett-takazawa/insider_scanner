"""
Command-line interface for edge scanner.

Main entry point for running wallet analysis.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .export import write_csv, write_json, write_markdown, write_run_metadata
from .features import compute_features
from .fetchers.clob import get_order_book
from .fetchers.data_api import get_closed_positions, get_holders, get_trades
from .fetchers.gamma import resolve_market
from .models import RunMetadata
from .scoring import compute_market_signal, compute_wallet_scores

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_analysis(args: argparse.Namespace) -> int:
    """
    Run complete wallet analysis.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    # Setup logging
    setup_logging(args.verbose)

    logger.info("=" * 70)
    logger.info("Polymarket Holder Edge & Insider-Likelihood Scanner")
    logger.info("=" * 70)

    # Load config
    if args.config:
        logger.info(f"Loading config from: {args.config}")
        cfg = Config.from_yaml(args.config)
    else:
        logger.info("Using default configuration")
        cfg = Config.default()

    # Override config with CLI args
    if args.min_sample is not None:
        cfg.history.min_sample = args.min_sample
    if args.since_quarters is not None:
        cfg.history.lookback_quarters = args.since_quarters

    # Resolve market
    logger.info(f"Resolving market: {args.market}")
    try:
        market = resolve_market(args.market)
        logger.info(f"Market resolved: {market.title}")
        logger.info(f"Condition ID: {market.condition_id}")
    except Exception as e:
        logger.error(f"Failed to resolve market: {e}")
        return 1

    # Fetch holders
    logger.info("Fetching current holders...")
    holders = get_holders(market.condition_id, limit=args.limit if hasattr(args, 'limit') else 500)
    logger.info(f"Found {len(holders)} holders")

    if not holders:
        logger.warning("No holders found - cannot perform analysis")
        return 1

    # Fetch order book for price signal
    yes_mid_price = None
    if args.include_book and market.yes_token_id:
        logger.info("Fetching order book...")
        book = get_order_book(market.yes_token_id)
        if book and book.mid_price:
            yes_mid_price = book.mid_price
            logger.info(f"YES mid price: {yes_mid_price:.4f}")

    # Process each wallet
    logger.info("Processing wallets...")
    wallets_data = []

    for i, holder in enumerate(holders, 1):
        if i % 10 == 0:
            logger.info(f"Processing wallet {i}/{len(holders)}...")

        try:
            # Determine current side
            side = "YES" if holder.outcome_index == 1 else "NO"

            # Fetch closed positions
            closed_positions = get_closed_positions(
                holder.address,
                title_filter="earnings" if args.earnings_only else None,
            )

            # Fetch trades
            trades = get_trades(
                condition_id=market.condition_id,
                user_address=holder.address,
            )

            # Compute features
            features, sample_size = compute_features(
                holder.address,
                holder.amount_usd,
                closed_positions,
                trades,
                cfg,
            )

            # Filter by minimum activity (but always include if they have current stake)
            total_activity = sum(abs(p.amount_risked or p.pnl_usd) for p in closed_positions)
            if total_activity < cfg.filters.ignore_low_activity_usd and holder.amount_usd == 0:
                logger.debug(f"Skipping {holder.address[:8]}... - no activity and no current stake")
                continue

            # Always include wallets with current positions, even if no history
            wallets_data.append((
                holder.address,
                holder.username,
                holder.amount_usd,
                side,
                features,
                sample_size,
            ))

        except Exception as e:
            logger.warning(f"Failed to process {holder.address[:8]}...: {e}")
            continue

    logger.info(f"Successfully processed {len(wallets_data)} wallets")

    if not wallets_data:
        logger.warning("No wallets met criteria - cannot generate report")
        return 1

    # Compute scores
    logger.info("Computing scores...")
    wallet_scores = compute_wallet_scores(wallets_data, cfg)

    # Compute market signal
    logger.info("Computing market signal...")
    market_signal = compute_market_signal(wallet_scores, yes_mid_price, cfg)

    logger.info(f"Market Signal: {market_signal.direction} (score: {market_signal.final_score:.4f})")

    # Create run metadata
    run_meta = RunMetadata(
        market_slug=market.slug or args.market,
        condition_id=market.condition_id,
        market_title=market.title,
        run_timestamp=datetime.now(timezone.utc),
        config=cfg.__dict__,
        holders_analyzed=len(wallets_data),
        holders_scored=sum(1 for w in wallet_scores if not w.low_sample_flag),
        holders_low_sample=sum(1 for w in wallet_scores if w.low_sample_flag),
    )

    # Write outputs
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.save_csv:
        write_csv(wallet_scores, outdir / "holders.csv")

    if args.save_json:
        write_json(wallet_scores, market_signal, run_meta, outdir / "holders.json")

    if args.save_md:
        write_markdown(wallet_scores, market_signal, run_meta, outdir / "report.md")

    # Always write metadata
    write_run_metadata(run_meta, outdir / "run_meta.json")

    logger.info("=" * 70)
    logger.info(f"Analysis complete! Results written to: {outdir}")
    logger.info("=" * 70)

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Polymarket Holder Edge & Insider-Likelihood Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m edge_scan run --market pg-quarterly-earnings-nongaap-eps-10-24-2025-1pt9 --outdir ./runs/pg
  python -m edge_scan run --market <condition_id> --save-csv --save-json --save-md --include-book
        """,
    )

    parser.add_argument(
        "command",
        choices=["run"],
        help="Command to run (currently only 'run' is supported)",
    )

    parser.add_argument(
        "--market",
        "-m",
        required=True,
        help="Market slug or condition ID",
    )

    parser.add_argument(
        "--outdir",
        "-o",
        default="./output",
        help="Output directory (default: ./output)",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to config YAML file",
    )

    parser.add_argument(
        "--since-quarters",
        type=int,
        help="Historical lookback in quarters (overrides config)",
    )

    parser.add_argument(
        "--min-sample",
        type=int,
        help="Minimum sample size for full scoring (overrides config)",
    )

    parser.add_argument(
        "--include-book",
        action="store_true",
        help="Include order book for price signal",
    )

    parser.add_argument(
        "--earnings-only",
        action="store_true",
        help="Filter closed positions to earnings markets only",
    )

    parser.add_argument(
        "--save-csv",
        action="store_true",
        help="Save results to CSV",
    )

    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save results to JSON",
    )

    parser.add_argument(
        "--save-md",
        action="store_true",
        help="Save results to Markdown report",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Default to all output formats if none specified
    if not (args.save_csv or args.save_json or args.save_md):
        args.save_csv = True
        args.save_json = True
        args.save_md = True

    if args.command == "run":
        return run_analysis(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
