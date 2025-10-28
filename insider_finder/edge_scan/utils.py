"""
Utility functions for HTTP requests, retries, logging, and data transformations.
"""

import logging
import random
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry HTTP requests with exponential backoff and jitter.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    last_exception = e

                    # Don't retry on client errors (4xx) except 429
                    if isinstance(e, httpx.HTTPStatusError):
                        if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                            raise

                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2**attempt), max_delay)

                        # Add jitter
                        if jitter:
                            delay = delay * (0.5 + random.random())

                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Request failed after {max_attempts} attempts: {e}"
                        )

            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception

            raise RuntimeError("Unexpected error in retry logic")

        return wrapper

    return decorator


@with_retry(max_attempts=3)
def http_get(url: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """
    Make HTTP GET request with retry logic.

    Args:
        url: URL to request
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        JSON response as dictionary

    Raises:
        httpx.HTTPStatusError: If request fails after retries
    """
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def parse_datetime(dt_str: str | int | float) -> datetime:
    """
    Parse datetime from various formats to UTC datetime.

    Args:
        dt_str: Datetime as string, Unix timestamp (int), or ISO string

    Returns:
        Datetime object in UTC

    Raises:
        ValueError: If datetime format cannot be parsed
    """
    if isinstance(dt_str, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(dt_str, tz=timezone.utc)

    if isinstance(dt_str, str):
        # Try ISO format
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        # Try other common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    raise ValueError(f"Unable to parse datetime: {dt_str}")


def clip(value: float, min_val: float, max_val: float) -> float:
    """Clip value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def normalize_to_unit(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize value to [0, 1] using min-max scaling.

    Args:
        value: Value to normalize
        min_val: Minimum value in range
        max_val: Maximum value in range

    Returns:
        Normalized value in [0, 1]
    """
    if max_val == min_val:
        return 0.5  # Default to middle if no variance

    return (value - min_val) / (max_val - min_val)


def robust_scale(values: list[float], clip_pct: float = 0.95) -> list[float]:
    """
    Robust scaling using percentiles instead of min/max.

    Args:
        values: List of values to scale
        clip_pct: Percentile to clip at (default 95th percentile)

    Returns:
        Scaled values in approximately [0, 1]
    """
    if not values:
        return []

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    lower_idx = int(n * (1 - clip_pct) / 2)
    upper_idx = int(n * (1 + clip_pct) / 2)

    lower_bound = sorted_vals[lower_idx] if lower_idx < n else sorted_vals[0]
    upper_bound = sorted_vals[upper_idx] if upper_idx < n else sorted_vals[-1]

    if upper_bound == lower_bound:
        return [0.5] * len(values)

    return [clip((v - lower_bound) / (upper_bound - lower_bound), 0.0, 1.0) for v in values]


def winsorize(values: list[float], clip_pct: float = 0.95) -> list[float]:
    """
    Winsorize values by clipping to percentiles.

    Args:
        values: List of values
        clip_pct: Percentile to clip at

    Returns:
        Winsorized values
    """
    if not values:
        return []

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    lower_idx = int(n * (1 - clip_pct) / 2)
    upper_idx = int(n * (1 + clip_pct) / 2)

    lower_bound = sorted_vals[lower_idx] if lower_idx < n else sorted_vals[0]
    upper_bound = sorted_vals[upper_idx] if upper_idx < n else sorted_vals[-1]

    return [clip(v, lower_bound, upper_bound) for v in values]


def shrink_to_prior(
    observed: float, prior: float, n_observations: int, n_prior: int
) -> float:
    """
    Bayesian shrinkage of observed value toward prior.

    Args:
        observed: Observed value
        prior: Prior value
        n_observations: Number of observations
        n_prior: Effective sample size of prior

    Returns:
        Shrunk value
    """
    if n_observations + n_prior == 0:
        return prior

    weight_obs = n_observations / (n_observations + n_prior)
    weight_prior = n_prior / (n_observations + n_prior)

    return weight_obs * observed + weight_prior * prior


def weighted_mean(values: list[float], weights: list[float]) -> float:
    """
    Calculate weighted mean.

    Args:
        values: List of values
        weights: List of weights (same length as values)

    Returns:
        Weighted mean

    Raises:
        ValueError: If inputs have different lengths or weights sum to zero
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")

    if not values:
        return 0.0

    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("Weights sum to zero")

    return sum(v * w for v, w in zip(values, weights)) / total_weight
