"""
Gamma API fetcher for market metadata resolution.

Resolves market slug or condition ID to full market details.
"""

import logging

from ..models import Market
from ..utils import http_get, parse_datetime

logger = logging.getLogger(__name__)

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


def get_market_by_slug(slug: str) -> Market:
    """
    Fetch market metadata by slug.

    Args:
        slug: Market slug

    Returns:
        Market object with metadata

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"{GAMMA_BASE_URL}/markets/slug/{slug}"
    logger.info(f"Fetching market by slug: {slug}")

    data = http_get(url)

    return _parse_market_response(data, slug=slug)


def get_market_by_condition_id(condition_id: str) -> Market:
    """
    Fetch market metadata by condition ID.

    Args:
        condition_id: Condition ID

    Returns:
        Market object with metadata

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"{GAMMA_BASE_URL}/markets"
    params = {"condition_id": condition_id}
    logger.info(f"Fetching market by condition ID: {condition_id}")

    data = http_get(url, params=params)

    # API might return list or single object
    if isinstance(data, list):
        if not data:
            raise ValueError(f"No market found for condition_id: {condition_id}")
        data = data[0]

    return _parse_market_response(data, condition_id=condition_id)


def _parse_market_response(data: dict, slug: str | None = None, condition_id: str | None = None) -> Market:
    """
    Parse market response from Gamma API.

    Args:
        data: Raw API response
        slug: Market slug (if known)
        condition_id: Condition ID (if known)

    Returns:
        Market object
    """
    # Extract condition ID
    cond_id = (
        condition_id
        or data.get("condition_id")
        or data.get("conditionId")
        or data.get("id")
    )

    if not cond_id:
        raise ValueError("No condition_id found in market response")

    # Extract title
    title = data.get("question") or data.get("title") or data.get("description") or ""

    # Extract end time
    end_time_raw = data.get("endDate") or data.get("end_date") or data.get("endTime")
    if end_time_raw:
        end_time = parse_datetime(end_time_raw)
    else:
        # Default to far future if not available
        from datetime import datetime, timezone
        end_time = datetime(2099, 12, 31, tzinfo=timezone.utc)
        logger.warning(f"No end_time found for market {cond_id}, using default")

    # Extract token IDs
    yes_token_id = None
    no_token_id = None

    # Try different response formats
    if "tokens" in data:
        tokens = data["tokens"]
        if isinstance(tokens, list) and len(tokens) >= 2:
            yes_token_id = tokens[1].get("token_id") if len(tokens) > 1 else None
            no_token_id = tokens[0].get("token_id") if len(tokens) > 0 else None
    elif "clobTokenIds" in data:
        tokens = data["clobTokenIds"]
        if isinstance(tokens, list) and len(tokens) >= 2:
            yes_token_id = tokens[1] if len(tokens) > 1 else None
            no_token_id = tokens[0] if len(tokens) > 0 else None

    # Alternative field names
    yes_token_id = yes_token_id or data.get("yesTokenId") or data.get("yes_token_id")
    no_token_id = no_token_id or data.get("noTokenId") or data.get("no_token_id")

    market_slug = slug or data.get("slug")

    return Market(
        condition_id=cond_id,
        title=title,
        end_time=end_time,
        yes_token_id=yes_token_id,
        no_token_id=no_token_id,
        slug=market_slug,
    )


def extract_slug_from_url(url: str) -> str:
    """
    Extract market slug from Polymarket URL.

    Args:
        url: Polymarket URL (e.g., https://polymarket.com/event/slug?tid=123)

    Returns:
        Extracted slug

    Examples:
        >>> extract_slug_from_url("https://polymarket.com/event/my-market?tid=123")
        'my-market'
        >>> extract_slug_from_url("polymarket.com/event/my-market")
        'my-market'
    """
    import re

    # Remove protocol if present
    url = url.replace("https://", "").replace("http://", "")

    # Pattern to match /event/SLUG or /market/SLUG
    pattern = r"(?:event|market)/([a-zA-Z0-9\-]+)"
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    raise ValueError(f"Could not extract slug from URL: {url}")


def resolve_market(market_input: str) -> Market:
    """
    Resolve market from URL, slug, or condition ID.

    Tries URL extraction first, then slug, then condition ID.

    Args:
        market_input: Polymarket URL, market slug, or condition ID

    Returns:
        Market object

    Raises:
        ValueError: If market cannot be resolved
    """
    # Check if it's a URL (contains polymarket.com or starts with http)
    if "polymarket.com" in market_input or market_input.startswith("http"):
        try:
            slug = extract_slug_from_url(market_input)
            logger.info(f"Extracted slug from URL: {slug}")
            return get_market_by_slug(slug)
        except Exception as e:
            logger.debug(f"Failed to extract/resolve from URL: {e}")

    # Try as slug first (slugs typically have hyphens)
    if "-" in market_input:
        try:
            return get_market_by_slug(market_input)
        except Exception as e:
            logger.debug(f"Failed to resolve as slug: {e}")

    # Try as condition ID
    try:
        return get_market_by_condition_id(market_input)
    except Exception as e:
        logger.debug(f"Failed to resolve as condition_id: {e}")

    raise ValueError(f"Unable to resolve market: {market_input}")
