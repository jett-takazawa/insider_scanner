"""
Configuration dataclasses for edge scanner.

Loads from YAML and provides defaults with validation.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class HistoryConfig:
    """Historical data lookback configuration."""

    earnings_title_regex: str = r"(?i)(earnings|EPS|quarterly)"
    lookback_quarters: int = 16
    min_sample: int = 5


@dataclass
class Weights:
    """Feature weights for scoring (normalized internally)."""

    win_rate: float = 0.35
    pnl_per_usd: float = 0.25
    timing_edge: float = 0.20
    conviction_z: float = 0.15
    consistency: float = 0.05

    def normalize(self) -> "Weights":
        """Return normalized weights summing to 1.0."""
        total = (
            self.win_rate
            + self.pnl_per_usd
            + self.timing_edge
            + self.conviction_z
            + self.consistency
        )
        if total == 0:
            raise ValueError("All weights are zero")
        return Weights(
            win_rate=self.win_rate / total,
            pnl_per_usd=self.pnl_per_usd / total,
            timing_edge=self.timing_edge / total,
            conviction_z=self.conviction_z / total,
            consistency=self.consistency / total,
        )


@dataclass
class FiltersConfig:
    """Filters for excluding low-activity wallets."""

    ignore_low_activity_usd: float = 250.0
    ignore_total_trades_lt: int = 10


@dataclass
class CapsConfig:
    """Caps and limits for feature engineering."""

    feature_clip_pct: float = 0.95
    max_influence_single_wallet: float = 0.33


@dataclass
class ScoringConfig:
    """Scoring parameters."""

    shrinkage_prior: float = 0.50
    score_floor: float = 0.00
    score_ceiling: float = 1.00


@dataclass
class MarketSignalConfig:
    """Market signal aggregation configuration."""

    use_dir_from_price: bool = True
    dir_weight: float = 0.30
    holder_weight: float = 0.70


@dataclass
class Config:
    """Complete configuration for edge scanner."""

    history: HistoryConfig = field(default_factory=HistoryConfig)
    weights: Weights = field(default_factory=Weights)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    caps: CapsConfig = field(default_factory=CapsConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    market_signal: MarketSignalConfig = field(default_factory=MarketSignalConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Config instance with values from YAML

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML structure is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            history=HistoryConfig(**data.get("history", {})),
            weights=Weights(**data.get("weights", {})),
            filters=FiltersConfig(**data.get("filters", {})),
            caps=CapsConfig(**data.get("caps", {})),
            scoring=ScoringConfig(**data.get("scoring", {})),
            market_signal=MarketSignalConfig(**data.get("market_signal", {})),
        )

    @classmethod
    def default(cls) -> "Config":
        """Return default configuration."""
        return cls()
