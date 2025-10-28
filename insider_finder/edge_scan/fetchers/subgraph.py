"""
Subgraph fetcher (fallback for complete holder enumeration).

Currently a stub - would query Goldsky subgraph for userPositions.
"""

import logging

from ..models import Holder

logger = logging.getLogger(__name__)


def get_all_holders_subgraph(condition_id: str) -> list[Holder]:
    """
    Fetch all holders via subgraph (fallback).

    Args:
        condition_id: Market condition ID

    Returns:
        List of Holder objects

    Note:
        This is a stub implementation. Full implementation would query
        Goldsky subgraph with GraphQL.
    """
    logger.warning("Subgraph fetcher not fully implemented, returning empty list")
    return []
