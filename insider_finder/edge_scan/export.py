"""
Export utilities for writing results to CSV, JSON, and Markdown.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from .models import MarketSignal, RunMetadata, WalletScore

logger = logging.getLogger(__name__)


def write_csv(wallet_scores: list[WalletScore], output_path: Path) -> None:
    """
    Write wallet scores to CSV.

    Args:
        wallet_scores: List of wallet scores
        output_path: Output CSV path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            "address",
            "username",
            "current_stake_usd",
            "current_side",
            "insider_likelihood_score",
            "win_rate",
            "pnl_per_usd",
            "timing_edge",
            "conviction_z",
            "consistency",
            "signed_contribution",
            "sample_size",
            "low_sample_flag",
        ])

        # Write rows
        for score in sorted(wallet_scores, key=lambda x: x.insider_likelihood_score, reverse=True):
            writer.writerow([
                score.address,
                score.username or "",
                f"{score.current_stake_usd:.2f}",
                score.current_side,
                f"{score.insider_likelihood_score:.4f}",
                f"{score.features.win_rate:.4f}",
                f"{score.features.pnl_per_usd:.4f}",
                f"{score.features.timing_edge:.4f}",
                f"{score.features.conviction_z:.4f}",
                f"{score.features.consistency:.4f}",
                f"{score.signed_contribution:.2f}",
                score.sample_size,
                score.low_sample_flag,
            ])

    logger.info(f"Wrote {len(wallet_scores)} wallet scores to {output_path}")


def write_json(
    wallet_scores: list[WalletScore],
    market_signal: MarketSignal,
    run_meta: RunMetadata,
    output_path: Path,
) -> None:
    """
    Write complete results to JSON.

    Args:
        wallet_scores: List of wallet scores
        market_signal: Market signal
        run_meta: Run metadata
        output_path: Output JSON path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "metadata": run_meta.model_dump(mode="json"),
        "market_signal": market_signal.model_dump(mode="json"),
        "wallets": [score.model_dump(mode="json") for score in wallet_scores],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Wrote JSON output to {output_path}")


def write_markdown(
    wallet_scores: list[WalletScore],
    market_signal: MarketSignal,
    run_meta: RunMetadata,
    output_path: Path,
) -> None:
    """
    Write human-readable markdown report.

    Args:
        wallet_scores: List of wallet scores
        market_signal: Market signal
        run_meta: Run metadata
        output_path: Output markdown path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# Polymarket Holder Edge Analysis\n\n")
        f.write(f"**Market:** {run_meta.market_title}\n\n")
        f.write(f"**Condition ID:** `{run_meta.condition_id}`\n\n")
        f.write(f"**Analysis Time:** {run_meta.run_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

        # Market Signal
        f.write(f"## Market Signal\n\n")
        f.write(f"- **Direction:** {market_signal.direction}\n")
        f.write(f"- **Final Score:** {market_signal.final_score:.4f}\n")
        f.write(f"- **Holder Signal:** {market_signal.holder_signal:.4f}\n")
        if market_signal.dir_score is not None:
            f.write(f"- **Price Direction Score:** {market_signal.dir_score:.4f}\n")
        f.write(f"- **Wallets Analyzed:** {market_signal.top_wallets_count}\n")
        f.write(f"- **Total Stake:** ${market_signal.total_stake_usd:,.2f}\n\n")

        # Summary Stats
        f.write(f"## Summary\n\n")
        f.write(f"- **Total Holders Analyzed:** {run_meta.holders_analyzed}\n")
        f.write(f"- **Holders with Full Scores:** {run_meta.holders_scored}\n")
        f.write(f"- **Holders with Low Sample:** {run_meta.holders_low_sample}\n\n")

        # Top Wallets
        f.write(f"## Top 20 Wallets by Insider Likelihood Score\n\n")
        f.write(f"| Rank | Address | Stake USD | Side | Score | Win Rate | PnL/USD | Sample | Low Sample |\n")
        f.write(f"|------|---------|-----------|------|-------|----------|---------|--------|------------|\n")

        sorted_wallets = sorted(wallet_scores, key=lambda x: x.insider_likelihood_score, reverse=True)[:20]

        for i, score in enumerate(sorted_wallets, 1):
            addr_short = f"{score.address[:6]}...{score.address[-4:]}"
            f.write(
                f"| {i} | `{addr_short}` | ${score.current_stake_usd:,.0f} | "
                f"{score.current_side} | {score.insider_likelihood_score:.3f} | "
                f"{score.features.win_rate:.3f} | {score.features.pnl_per_usd:.3f} | "
                f"{score.sample_size} | {'Yes' if score.low_sample_flag else 'No'} |\n"
            )

        # Caveats
        f.write(f"\n## Important Caveats\n\n")
        f.write(f"- **Behavioral Analysis Only:** Scores represent behavioral likelihood of informational edge based on historical patterns.\n")
        f.write(f"- **No Legal Assertion:** This tool makes no claims about illegal activity or insider trading.\n")
        f.write(f"- **Historical Performance:** Past performance does not guarantee future results.\n")
        f.write(f"- **Sample Size:** Wallets with `Low Sample = Yes` have limited historical data and scores may be unreliable.\n")
        f.write(f"- **Market Context:** Always consider broader market conditions and fundamental analysis.\n\n")

        # Glossary
        f.write(f"## Glossary\n\n")
        f.write(f"- **Insider Likelihood Score:** Weighted combination of behavioral edge features [0-1]\n")
        f.write(f"- **Win Rate:** Historical success rate on earnings markets, weighted by stake size\n")
        f.write(f"- **PnL/USD:** Median profit/loss ratio per dollar risked\n")
        f.write(f"- **Timing Edge:** Activity concentration near resolution events\n")
        f.write(f"- **Conviction Z:** How unusual current stake is vs historical distribution\n")
        f.write(f"- **Consistency:** Directional alignment within ticker/sector\n\n")

    logger.info(f"Wrote markdown report to {output_path}")


def write_run_metadata(run_meta: RunMetadata, output_path: Path) -> None:
    """
    Write run metadata to JSON.

    Args:
        run_meta: Run metadata
        output_path: Output path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(run_meta.model_dump(mode="json"), f, indent=2, default=str)

    logger.info(f"Wrote run metadata to {output_path}")
