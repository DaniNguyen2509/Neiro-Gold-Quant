"""Neiro-Quant Collector entry point.

Can run as a one-shot sync CLI or a background daemon scheduled for
market sessions (Asia, Europe, US).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from pathlib import Path

from .scraper import scrape_and_save, scrape_multi_expiry_and_save

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Collector) %(message)s",
)
logger = logging.getLogger(__name__)


def run_one_shot(
    output_path: str = "data/options_prices_GCZ26.csv",
    multi_expiry: bool = True,
) -> bool:
    """Execute options chain collection (Weekly + Monthly aggregated by default)."""
    try:
        if multi_expiry:
            out_dir = str(Path(output_path).parent)
            saved_files = scrape_multi_expiry_and_save(output_dir=out_dir, underlying_futures="GCZ26")
            logger.info("Multi-expiry collection complete: %d files saved (%s)", len(saved_files), saved_files)
        else:
            saved_file = scrape_and_save(output_path=output_path)
            logger.info("One-shot collection complete: %s", saved_file)
        return True
    except Exception as e:
        logger.error("Collection failed: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Options Chain Collector")
    parser.add_argument("--output", default="data/options_prices_GCZ26.csv", help="Output CSV path")
    parser.add_argument("--once", action="store_true", default=True, help="Run once and exit (default)")
    parser.add_argument("--single-expiry", action="store_true", help="Scrape only single front-month contract")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without writing")
    args = parser.parse_args()

    if args.dry_run:
        scrape_and_save(output_path=args.output, dry_run=True)
        return

    success = run_one_shot(output_path=args.output, multi_expiry=not args.single_expiry)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
