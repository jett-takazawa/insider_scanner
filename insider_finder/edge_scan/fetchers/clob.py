"""
CLOB API fetcher for order book data.

Fetches order book snapshots for price discovery.
"""

import logging

from ..models import OrderBook
from ..utils import http_get

logger = logging.getLogger(__name__)

CLOB_BASE_URL = "https://clob.polymarket.com"


def get_order_book(token_id: str) -> OrderBook | None:
    """
    Fetch order book for a token.

    Args:
        token_id: Token ID

    Returns:
        OrderBook object or None if fetch fails
    """
    url = f"{CLOB_BASE_URL}/book"
    params = {"token_id": token_id}

    logger.debug(f"Fetching order book for token {token_id}")

    try:
        data = http_get(url, params=params)
    except Exception as e:
        logger.warning(f"Failed to fetch order book: {e}")
        return None

    # Parse order book
    bids = []
    asks = []

    if "bids" in data:
        for bid in data["bids"]:
            if isinstance(bid, dict):
                price = float(bid.get("price", 0))
                size = float(bid.get("size", 0))
                bids.append((price, size))

    if "asks" in data:
        for ask in data["asks"]:
            if isinstance(ask, dict):
                price = float(ask.get("price", 0))
                size = float(ask.get("size", 0))
                asks.append((price, size))

    book = OrderBook(token_id=token_id, bids=bids, asks=asks)
    book.mid_price = book.calculate_mid()

    if book.mid_price and bids and asks:
        best_bid = max(bids, key=lambda x: x[0])[0]
        best_ask = min(asks, key=lambda x: x[0])[0]
        book.spread = best_ask - best_bid

    return book
