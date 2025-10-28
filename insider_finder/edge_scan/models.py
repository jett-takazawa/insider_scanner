"""
Pydantic models for Polymarket API responses.

Models include validation and convenience methods for conversion.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Market(BaseModel):
    """Market metadata from Gamma API."""

    condition_id: str = Field(..., description="Unique condition ID")
    title: str = Field(..., description="Market title/question")
    end_time: datetime = Field(..., description="Market resolution time (UTC)")
    yes_token_id: str | None = Field(None, description="YES outcome token ID")
    no_token_id: str | None = Field(None, description="NO outcome token ID")
    slug: str | None = Field(None, description="Market slug")

    model_config = ConfigDict(from_attributes=True)


class Holder(BaseModel):
    """Current holder position in a market."""

    address: str = Field(..., description="Wallet address")
    username: str | None = Field(None, description="Username if available")
    outcome_index: int = Field(..., description="Outcome index (0=NO, 1=YES typically)")
    amount_usd: float = Field(..., description="Position size in USD")

    model_config = ConfigDict(from_attributes=True)


class Trade(BaseModel):
    """Individual trade record."""

    ts: datetime = Field(..., description="Trade timestamp (UTC)")
    side: str = Field(..., description="Trade side (buy/sell or YES/NO)")
    price: float = Field(..., description="Trade price")
    amount: float = Field(..., description="Trade amount in shares")
    amount_usd: float = Field(..., description="Trade amount in USD")
    market: str | None = Field(None, description="Market identifier")

    model_config = ConfigDict(from_attributes=True)


class ClosedPosition(BaseModel):
    """Closed/resolved position record."""

    title: str = Field(..., description="Market title")
    event_id: str | None = Field(None, description="Event ID if available")
    pnl_usd: float = Field(..., description="Realized PnL in USD")
    was_winner: bool = Field(..., description="Whether position was on winning side")
    resolved_at: datetime = Field(..., description="Resolution timestamp (UTC)")
    amount_risked: float | None = Field(None, description="Amount risked in USD")

    model_config = ConfigDict(from_attributes=True)


class OrderBook(BaseModel):
    """Order book snapshot for a token."""

    token_id: str = Field(..., description="Token ID")
    bids: list[tuple[float, float]] = Field(
        default_factory=list, description="List of (price, size) bid tuples"
    )
    asks: list[tuple[float, float]] = Field(
        default_factory=list, description="List of (price, size) ask tuples"
    )
    mid_price: float | None = Field(None, description="Calculated mid price")
    spread: float | None = Field(None, description="Bid-ask spread")

    model_config = ConfigDict(from_attributes=True)

    def calculate_mid(self) -> float | None:
        """Calculate mid price from top of book."""
        if not self.bids or not self.asks:
            return None
        best_bid = max(self.bids, key=lambda x: x[0])[0]
        best_ask = min(self.asks, key=lambda x: x[0])[0]
        return (best_bid + best_ask) / 2


class FeatureVector(BaseModel):
    """Computed features for a wallet."""

    win_rate: float = Field(..., description="Size-weighted win rate [0,1]")
    pnl_per_usd: float = Field(..., description="Normalized PnL per USD risked [0,1]")
    timing_edge: float = Field(..., description="Timing edge score [0,1]")
    conviction_z: float = Field(..., description="Conviction Z-score normalized [0,1]")
    consistency: float = Field(..., description="Directional consistency score [0,1]")

    model_config = ConfigDict(from_attributes=True)


class WalletScore(BaseModel):
    """Complete scoring for a wallet."""

    address: str = Field(..., description="Wallet address")
    username: str | None = Field(None, description="Username if available")
    current_stake_usd: float = Field(..., description="Current position size USD")
    current_side: str = Field(..., description="Current side (YES/NO)")
    features: FeatureVector = Field(..., description="Computed features")
    insider_likelihood_score: float = Field(
        ..., description="Overall edge likelihood score [0,1]"
    )
    signed_contribution: float = Field(
        ..., description="Signed contribution to market signal"
    )
    sample_size: int = Field(..., description="Number of prior earnings positions")
    low_sample_flag: bool = Field(
        False, description="True if below min_sample threshold"
    )

    model_config = ConfigDict(from_attributes=True)


class MarketSignal(BaseModel):
    """Aggregated market signal."""

    holder_signal: float = Field(..., description="Weighted holder signal [-1,1]")
    dir_score: float | None = Field(None, description="Directional score from price [-1,1]")
    final_score: float = Field(..., description="Combined final score [-1,1]")
    direction: str = Field(..., description="Advisory direction (UP/DOWN/FLAT)")
    top_wallets_count: int = Field(..., description="Number of wallets included")
    total_stake_usd: float = Field(..., description="Total stake analyzed USD")

    model_config = ConfigDict(from_attributes=True)


class RunMetadata(BaseModel):
    """Metadata for a complete run."""

    market_slug: str = Field(..., description="Market slug")
    condition_id: str = Field(..., description="Condition ID")
    market_title: str = Field(..., description="Market title")
    run_timestamp: datetime = Field(..., description="Run timestamp UTC")
    config: dict = Field(..., description="Configuration used")
    holders_analyzed: int = Field(..., description="Number of holders analyzed")
    holders_scored: int = Field(..., description="Number with full scores")
    holders_low_sample: int = Field(..., description="Number with low sample flag")

    model_config = ConfigDict(from_attributes=True)
