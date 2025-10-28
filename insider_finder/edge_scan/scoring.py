"""
Scoring logic for insider likelihood and market signals.

Computes behavioral edge scores and aggregates market signals.
"""

import logging

from .config import Config
from .models import FeatureVector, MarketSignal, WalletScore
from .utils import clip

logger = logging.getLogger(__name__)


def compute_insider_likelihood_score(feat: FeatureVector, cfg: Config) -> float:
    """
    Compute insider likelihood score from features.

    Args:
        feat: Feature vector
        cfg: Configuration with weights

    Returns:
        Insider likelihood score in [0, 1]
    """
    # Normalize weights
    w = cfg.weights.normalize()

    score = (
        w.win_rate * feat.win_rate
        + w.pnl_per_usd * feat.pnl_per_usd
        + w.timing_edge * feat.timing_edge
        + w.conviction_z * feat.conviction_z
        + w.consistency * feat.consistency
    )

    return clip(score, cfg.scoring.score_floor, cfg.scoring.score_ceiling)


def compute_wallet_scores(
    wallets_data: list[tuple[str, str | None, float, str, FeatureVector, int]],
    cfg: Config,
) -> list[WalletScore]:
    """
    Compute scores for all wallets.

    Args:
        wallets_data: List of (address, username, stake_usd, side, features, sample_size)
        cfg: Configuration

    Returns:
        List of WalletScore objects
    """
    scores = []

    for address, username, stake_usd, side, features, sample_size in wallets_data:
        # Compute insider likelihood score
        ils = compute_insider_likelihood_score(features, cfg)

        # Determine signed contribution
        side_sign = 1.0 if side == "YES" else -1.0
        signed_contribution = ils * stake_usd * side_sign

        # Flag low sample
        low_sample = sample_size < cfg.history.min_sample

        scores.append(
            WalletScore(
                address=address,
                username=username,
                current_stake_usd=stake_usd,
                current_side=side,
                features=features,
                insider_likelihood_score=ils,
                signed_contribution=signed_contribution,
                sample_size=sample_size,
                low_sample_flag=low_sample,
            )
        )

    return scores


def compute_market_signal(
    wallet_scores: list[WalletScore],
    yes_mid_price: float | None,
    cfg: Config,
) -> MarketSignal:
    """
    Compute aggregated market signal.

    Args:
        wallet_scores: List of wallet scores
        yes_mid_price: YES token mid price (0-1)
        cfg: Configuration

    Returns:
        MarketSignal with aggregated direction
    """
    if not wallet_scores:
        return MarketSignal(
            holder_signal=0.0,
            dir_score=None,
            final_score=0.0,
            direction="FLAT",
            top_wallets_count=0,
            total_stake_usd=0.0,
        )

    # Compute holder signal
    total_stake = sum(w.current_stake_usd for w in wallet_scores)

    if total_stake == 0:
        holder_signal = 0.0
    else:
        # Normalize contributions by total stake
        contributions = []
        for w in wallet_scores:
            # Cap single wallet influence
            weight = min(
                w.current_stake_usd / total_stake,
                cfg.caps.max_influence_single_wallet,
            )
            contributions.append(w.insider_likelihood_score * weight * (1 if w.current_side == "YES" else -1))

        holder_signal = sum(contributions)

    # Clip to [-1, 1]
    holder_signal = clip(holder_signal, -1.0, 1.0)

    # Compute direction score from price
    dir_score = None
    if yes_mid_price is not None and cfg.market_signal.use_dir_from_price:
        # Transform price [0,1] to direction score [-1, 1]
        dir_score = (yes_mid_price - 0.5) * 2

    # Compute final score
    if dir_score is not None:
        final_score = (
            cfg.market_signal.holder_weight * holder_signal
            + cfg.market_signal.dir_weight * dir_score
        )
    else:
        final_score = holder_signal

    final_score = clip(final_score, -1.0, 1.0)

    # Determine direction
    if final_score >= 0.25:
        direction = "UP"
    elif final_score <= -0.25:
        direction = "DOWN"
    else:
        direction = "FLAT"

    return MarketSignal(
        holder_signal=holder_signal,
        dir_score=dir_score,
        final_score=final_score,
        direction=direction,
        top_wallets_count=len(wallet_scores),
        total_stake_usd=total_stake,
    )
