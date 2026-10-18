"""Barchart Playwright Headless Scraper for CME Gold Options (GCZ26).

Runs headless Chromium to cleanly navigate Barchart, execute internal
API query within the authenticated browser context, and extract full
options chain (Prices, Volume, OI, Greeks).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .parser import parse_barchart_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_BARCHART_URL = "https://www.barchart.com/futures/quotes/GCZ26/options/IG4V26?futuresOptionsView=merged"
ALL_FIELDS = "strikePrice,optionType,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,volatility,delta,gamma,theta,vega"


async def fetch_barchart_options_playwright(
    page_url: str = DEFAULT_BARCHART_URL,
    timeout_ms: int = 45000,
) -> dict[str, Any] | list[Any]:
    """Launch headless Chromium, bypass Cloudflare, and fetch options JSON via internal API."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("Playwright is not installed. Install via: pip install playwright && playwright install chromium")

    logger.info("Starting Playwright headless browser for Barchart...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        captured_data: list[dict[str, Any]] = []

        # Listen to any background network responses for options API
        async def handle_response(response):
            if "proxies/core-api" in response.url or ("options" in response.url and "get" in response.url):
                try:
                    if response.ok and "json" in response.headers.get("content-type", ""):
                        body = await response.json()
                        captured_data.append(body)
                        logger.info("Intercepted Barchart options response from: %s", response.url)
                except Exception:
                    pass

        page.on("response", handle_response)

        logger.info("Navigating to: %s", page_url)
        try:
            await page.goto(page_url, timeout=timeout_ms, wait_until="domcontentloaded")
            # Brief wait for initial scripts and Cloudflare challenge to pass
            await asyncio.sleep(4.0)
        except Exception as e:
            logger.warning("Page navigation notice (proceeding to evaluate): %s", e)

        # Check if we already intercepted the API response
        if captured_data:
            await browser.close()
            return captured_data[0]

        # Execute direct API call in browser context (using active XSRF token)
        logger.info("Evaluating internal API fetch in browser context...")
        js_code = f"""
        async () => {{
            function getCookie(n) {{
                let m = document.cookie.match(new RegExp('(^|;\\\\s*)(' + n + ')=([^;]*)'));
                return m ? decodeURIComponent(m[3]) : '';
            }}
            let xsrf = getCookie('XSRF-TOKEN');
            let perf = performance.getEntriesByType('resource').map(e => e.name);
            let apiUrls = perf.filter(u => u.includes('proxies/core-api') || (u.includes('options') && u.includes('get')));
            let targetUrl = apiUrls.length > 0 ? apiUrls[apiUrls.length - 1] : '/proxies/core-api/v1/options/get';
            
            if (targetUrl.includes('fields=')) {{
                targetUrl = targetUrl.replace(/fields=[^&]+/, 'fields=' + encodeURIComponent('{ALL_FIELDS}'));
            }} else {{
                targetUrl += (targetUrl.includes('?') ? '&' : '?') + 'fields=' + encodeURIComponent('{ALL_FIELDS}');
            }}
            if (!targetUrl.includes('raw=1')) targetUrl += '&raw=1';

            let res = await fetch(targetUrl, {{
                headers: {{
                    'X-XSRF-TOKEN': xsrf,
                    'Accept': 'application/json'
                }}
            }});
            if (res.ok) {{
                return await res.json();
            }}
            return null;
        }}
        """
        result = await page.evaluate(js_code)
        await browser.close()

        if result:
            logger.info("Successfully fetched options data via in-page API evaluation!")
            return result

        raise RuntimeError("Failed to obtain Barchart options data via browser evaluation")


def scrape_and_save(output_path: str = "data/options_prices_GCZ26.csv", dry_run: bool = False) -> str:
    """Scrape Barchart options chain and save to CSV file."""
    logger.info("Initiating scrape for CME GCZ26 options...")
    raw_json = asyncio.run(fetch_barchart_options_playwright())
    df = parse_barchart_json(raw_json)

    if dry_run:
        logger.info("[DRY RUN] Parsed %d strikes successfully. No file written.", len(df))
        return ""

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    logger.info("Saved %d strikes to %s (file size: %d bytes)", len(df), out_file, out_file.stat().st_size)
    return str(out_file)


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Barchart Options Scraper")
    parser.add_argument("--output", default="data/options_prices_GCZ26.csv", help="Path to save output CSV")
    parser.add_argument("--dry-run", action="store_true", help="Test scraping without saving to file")
    args = parser.parse_args()

    try:
        scrape_and_save(output_path=args.output, dry_run=args.dry_run)
    except Exception as e:
        logger.error("Scraper failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
