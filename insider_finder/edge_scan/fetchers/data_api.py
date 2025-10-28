"""
Data API fetcher for holders, trades, and closed positions.

Uses Polymarket Data API for wallet activity data.
"""

import logging
from datetime import datetime

from ..models import ClosedPosition, Holder, Trade
from ..utils import http_get, parse_datetime

logger = logging.getLogger(__name__)

DATA_API_BASE_URL = "https://data-api.polymarket.com"


def get_holders(condition_id: str, limit: int = 500) -> list[Holder]:
    """
    Fetch current holders for a market.

    Args:
        condition_id: Market condition ID
        limit: Maximum number of holders to fetch

    Returns:
        List of Holder objects
    """
    url = f"{DATA_API_BASE_URL}/holders"
    params = {"market": condition_id, "limit": limit}

    logger.info(f"Fetching holders for condition_id: {condition_id}")

    try:
        data = http_get(url, params=params)
    except Exception as e:
        logger.error(f"Failed to fetch holders: {e}")
        return []

    holders = []

    # API might return dict with 'data' key or direct list
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if not isinstance(data, list):
        logger.warning(f"Unexpected holders response format: {type(data)}")
        return []

    # API returns array of tokens, each with nested holders array
    for token_group in data:
        if not isinstance(token_group, dict):
            continue

        token_id = token_group.get("token")
        token_holders = token_group.get("holders", [])

        for holder_data in token_holders:
            try:
                holders.append(_parse_holder(holder_data))
            except Exception as e:
                logger.warning(f"Failed to parse holder: {e}")
                continue

    logger.info(f"Found {len(holders)} holders")
    return holders


def get_trades(
    condition_id: str | None = None,
    user_address: str | None = None,
    limit: int = 1000,
) -> list[Trade]:
    """
    Fetch trades for a market and/or user.

    Args:
        condition_id: Market condition ID (optional)
        user_address: User wallet address (optional)
        limit: Maximum number of trades

    Returns:
        List of Trade objects
    """
    url = f"{DATA_API_BASE_URL}/trades"
    params = {"limit": limit}

    if condition_id:
        params["market"] = condition_id
    if user_address:
        params["user"] = user_address

    logger.debug(f"Fetching trades (market={condition_id}, user={user_address[:8] if user_address else None}...)")

    try:
        data = http_get(url, params=params)
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")
        return []

    trades = []

    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if not isinstance(data, list):
        logger.warning(f"Unexpected trades response format: {type(data)}")
        return []

    for item in data:
        try:
            trades.append(_parse_trade(item))
        except Exception as e:
            logger.warning(f"Failed to parse trade: {e}")
            continue

    return trades


def get_closed_positions(
    user_address: str,
    title_filter: str | None = None,
    limit: int = 500,
) -> list[ClosedPosition]:
    """
    Fetch closed positions for a user.

    Args:
        user_address: User wallet address
        title_filter: Optional title filter (e.g., "earnings")
        limit: Maximum number of positions

    Returns:
        List of ClosedPosition objects
    """
    url = f"{DATA_API_BASE_URL}/closed-positions"
    params = {"user": user_address, "limit": limit}

    if title_filter:
        params["title"] = title_filter

    logger.debug(f"Fetching closed positions for {user_address[:8]}...")

    try:
        data = http_get(url, params=params)
    except Exception as e:
        logger.warning(f"Failed to fetch closed positions for {user_address[:8]}: {e}")
        return []

    positions = []

    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if not isinstance(data, list):
        logger.warning(f"Unexpected closed positions response format: {type(data)}")
        return []

    for item in data:
        try:
            positions.append(_parse_closed_position(item))
        except Exception as e:
            logger.warning(f"Failed to parse closed position: {e}")
            continue

    return positions


def _parse_holder(data: dict) -> Holder:
    """Parse holder from API response."""
    # Address can be in multiple fields
    address = (
        data.get("proxyWallet")
        or data.get("user")
        or data.get("address")
        or data.get("userAddress")
    )
    if not address:
        raise ValueError("No address found in holder data")

    # Username fallback chain
    username = data.get("name") or data.get("username") or data.get("pseudonym")

    # Outcome index: typically 0=NO, 1=YES
    # Use explicit None check to handle outcomeIndex=0 correctly
    outcome_index = data.get("outcomeIndex")
    if outcome_index is None:
        outcome_index = data.get("outcome_index")
    if outcome_index is None:
        outcome_index = data.get("outcome")
    if outcome_index is None:
        outcome_index = 1  # Default to YES if not specified

    # Amount can be in shares or USD
    amount_usd = (
        data.get("amountUSD")
        or data.get("amount_usd")
        or data.get("valueUSD")
        or data.get("value_usd")
        or data.get("amount")  # Fallback to amount field
        or 0.0
    )

    return Holder(
        address=address,
        username=username,
        outcome_index=int(outcome_index),
        amount_usd=float(amount_usd),
    )


def _parse_trade(data: dict) -> Trade:
    """Parse trade from API response."""
    # Timestamp
    ts_raw = data.get("timestamp") or data.get("ts") or data.get("time")
    if ts_raw:
        ts = parse_datetime(ts_raw)
    else:
        ts = datetime.now()

    # Side
    side = data.get("side") or data.get("type") or "buy"

    # Price
    price = data.get("price") or data.get("fillPrice") or 0.0

    # Amount
    amount = data.get("amount") or data.get("size") or data.get("quantity") or 0.0

    # Amount USD
    amount_usd = data.get("amountUSD") or data.get("amount_usd") or (float(amount) * float(price))

    # Market
    market = data.get("market") or data.get("condition_id")

    return Trade(
        ts=ts,
        side=str(side),
        price=float(price),
        amount=float(amount),
        amount_usd=float(amount_usd),
        market=market,
    )


def _parse_closed_position(data: dict) -> ClosedPosition:
    """Parse closed position from API response."""
    # Title
    title = data.get("title") or data.get("marketTitle") or data.get("question") or ""

    # Event ID
    event_id = data.get("eventId") or data.get("event_id")

    # PnL
    pnl_usd = data.get("pnlUSD") or data.get("pnl_usd") or data.get("pnl") or 0.0

    # Was winner
    was_winner = data.get("wasWinner") or data.get("was_winner") or data.get("won") or False

    # Resolved at
    resolved_at_raw = data.get("resolvedAt") or data.get("resolved_at") or data.get("closedAt")
    if resolved_at_raw:
        resolved_at = parse_datetime(resolved_at_raw)
    else:
        resolved_at = datetime.now()

    # Amount risked
    amount_risked = data.get("amountRisked") or data.get("amount_risked") or data.get("investment")

    return ClosedPosition(
        title=title,
        event_id=event_id,
        pnl_usd=float(pnl_usd),
        was_winner=bool(was_winner),
        resolved_at=resolved_at,
        amount_risked=float(amount_risked) if amount_risked else None,
    )
