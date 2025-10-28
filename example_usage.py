"""
Example usage of the Polymarket earnings logger.

This script demonstrates how to use the library programmatically
without using the CLI.
"""

import logging
from apps.polymarket_logger.core import (
    gamma_search,
    pick_earnings_market,
    gamma_market_by_slug,
    build_market_record,
    calculate_correctness,
)
from apps.polymarket_logger.fetchcandles import enrich_record_with_prices
from apps.polymarket_logger.sheets import append_row_to_csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Example: Fetch and process a single earnings market."""

    # Configuration
    ticker = "NFLX"
    event_date = "2025-10-20"

    logger.info(f"Processing {ticker} earnings market...")

    # Step 1: Search for markets
    logger.info("Step 1: Searching for earnings markets...")
    search_results = gamma_search(ticker)

    # Step 2: Pick the most relevant earnings market
    logger.info("Step 2: Filtering for earnings markets...")
    market = pick_earnings_market(search_results, query_hint=ticker)

    if not market:
        logger.error(f"No earnings markets found for {ticker}")
        return

    logger.info(f"Found market: {market.title}")

    # Step 3: Get full market details
    logger.info("Step 3: Fetching full market details...")
    details = gamma_market_by_slug(market.slug)

    # Step 4: Build market record
    logger.info("Step 4: Building market record...")
    record = build_market_record(
        ticker=ticker,
        details=details,
        date_utc=event_date,
        # If you know the exact earnings time and session:
        # earnings_datetime_utc="2025-10-20T20:00:00Z",
        # report_session="AMC",
    )

    logger.info(f"Market resolved: {record.resolved}")
    logger.info(f"Resolution side: {record.resolved_side}")
    logger.info(f"Resolution source: {record.resolution_source_url}")

    # Step 5: Enrich with stock price data
    # Note: This requires ALPHA_VANTAGE_API_KEY environment variable
    logger.info("Step 5: Enriching with stock price data...")
    try:
        record = enrich_record_with_prices(record)
        logger.info(f"Gap return: {record.gap_return_open_pct:.2f}%")
        logger.info(f"Day return: {record.day_return_close_pct:.2f}%")
    except Exception as e:
        logger.warning(f"Could not fetch prices: {e}")

    # Step 6: Calculate correctness
    logger.info("Step 6: Calculating prediction correctness...")
    record = calculate_correctness(record)
    logger.info(
        f"Correct on gap: {record.pm_correct_on_price_dir_open}"
    )
    logger.info(
        f"Correct on day: {record.pm_correct_on_price_dir_close}"
    )

    # Step 7: Save to CSV
    logger.info("Step 7: Saving to CSV...")
    append_row_to_csv("example_output.csv", record, write_header=True)
    logger.info("✓ Done! Check example_output.csv")

    # Display the record
    print("\n" + "="*80)
    print(f"Market: {record.pm_market_title}")
    print(f"Ticker: {record.ticker}")
    print(f"Resolved: {record.resolved_side}")
    print(f"Gap Return: {record.gap_return_open_pct:.2f}%" if record.gap_return_open_pct else "N/A")
    print(f"Day Return: {record.day_return_close_pct:.2f}%" if record.day_return_close_pct else "N/A")
    print(f"Prediction Correct (Gap): {bool(record.pm_correct_on_price_dir_open)}")
    print(f"Prediction Correct (Day): {bool(record.pm_correct_on_price_dir_close)}")
    print("="*80)


if __name__ == "__main__":
    main()
