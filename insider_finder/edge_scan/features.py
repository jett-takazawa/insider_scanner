"""
Feature engineering for wallet scoring.

Computes behavioral edge features from trading history.
"""

import logging
import re
from datetime import datetime, timedelta

from .config import Config
from .models import ClosedPosition, FeatureVector, Trade
from .utils import clip, normalize_to_unit, shrink_to_prior, weighted_mean, winsorize

logger = logging.getLogger(__name__)


def compute_features(
    address: str,
    current_stake_usd: float,
    closed_positions: list[ClosedPosition],
    trades: list[Trade],
    cfg: Config,
) -> tuple[FeatureVector, int]:
    """
    Compute feature vector for a wallet.

    Args:
        address: Wallet address
        current_stake_usd: Current stake in target market (USD)
        closed_positions: Historical closed positions
        trades: Trade history
        cfg: Configuration

    Returns:
        Tuple of (FeatureVector, sample_size)
    """
    # Filter for earnings-related positions
    pattern = re.compile(cfg.history.earnings_title_regex)
    earnings_positions = [p for p in closed_positions if pattern.search(p.title)]

    sample_size = len(earnings_positions)

    # Compute individual features
    win_rate = _compute_win_rate(earnings_positions, cfg)
    pnl_per_usd = _compute_pnl_per_usd(earnings_positions, cfg)
    timing_edge = _compute_timing_edge(trades, cfg)
    conviction_z = _compute_conviction_z(current_stake_usd, earnings_positions, cfg)
    consistency = _compute_consistency(earnings_positions, cfg)

    return (
        FeatureVector(
            win_rate=win_rate,
            pnl_per_usd=pnl_per_usd,
            timing_edge=timing_edge,
            conviction_z=conviction_z,
            consistency=consistency,
        ),
        sample_size,
    )


def _compute_win_rate(positions: list[ClosedPosition], cfg: Config) -> float:
    """Compute size-weighted win rate with shrinkage."""
    if not positions:
        return cfg.scoring.shrinkage_prior

    winners = [p for p in positions if p.was_winner]
    stakes = [abs(p.amount_risked or p.pnl_usd) for p in positions]

    if sum(stakes) == 0:
        return cfg.scoring.shrinkage_prior

    win_values = [1.0 if p.was_winner else 0.0 for p in positions]

    observed_wr = weighted_mean(win_values, stakes)

    # Apply shrinkage
    shrunk_wr = shrink_to_prior(
        observed_wr,
        cfg.scoring.shrinkage_prior,
        len(positions),
        cfg.history.min_sample,
    )

    return clip(shrunk_wr, 0.0, 1.0)


def _compute_pnl_per_usd(positions: list[ClosedPosition], cfg: Config) -> float:
    """Compute PnL per USD risked with winsorization."""
    if not positions:
        return 0.5

    pnl_ratios = []
    for p in positions:
        risked = abs(p.amount_risked or p.pnl_usd)
        if risked > 0:
            ratio = p.pnl_usd / risked
            pnl_ratios.append(ratio)

    if not pnl_ratios:
        return 0.5

    # Winsorize
    winsorized = winsorize(pnl_ratios, cfg.caps.feature_clip_pct)

    # Take median
    sorted_ratios = sorted(winsorized)
    median_pnl = sorted_ratios[len(sorted_ratios) // 2]

    # Normalize to [0, 1] - assume typical range [-0.5, 1.5]
    normalized = normalize_to_unit(median_pnl, -0.5, 1.5)

    return clip(normalized, 0.0, 1.0)


def _compute_timing_edge(trades: list[Trade], cfg: Config) -> float:
    """
    Compute timing edge score.

    Fraction of activity in critical window before resolution.
    For MVP, return 0.5 (neutral) - full implementation would analyze timing.
    """
    # Stub: would analyze trades within 24-1 hours before market resolution
    return 0.5


def _compute_conviction_z(
    current_stake: float, positions: list[ClosedPosition], cfg: Config
) -> float:
    """
    Compute conviction Z-score.

    How unusual is current stake vs historical distribution.
    """
    if not positions:
        return 0.5

    stakes = [abs(p.amount_risked or p.pnl_usd) for p in positions if p.amount_risked or p.pnl_usd]

    if not stakes:
        return 0.5

    mean_stake = sum(stakes) / len(stakes)
    variance = sum((s - mean_stake) ** 2 for s in stakes) / len(stakes)
    std_stake = variance**0.5

    if std_stake == 0:
        return 0.5

    z = (current_stake - mean_stake) / std_stake

    # Normalize Z-score to [0, 1] assuming range [-3, 3]
    normalized = normalize_to_unit(z, -3.0, 3.0)

    return clip(normalized, 0.0, 1.0)


def _compute_consistency(positions: list[ClosedPosition], cfg: Config) -> float:
    """
    Compute consistency score.

    For MVP, return 0.5 (neutral) - full implementation would analyze
    directional consistency within ticker/sector.
    """
    # Stub: would analyze side alignment within same ticker/sector
    return 0.5
