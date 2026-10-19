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

DEFAULT_BARCHART_URL = "https://www.barchart.com/futures/quotes/GCZ26/options/OGX26?futuresOptionsView=merged"
ALL_FIELDS = "strikePrice,optionType,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,expirationDate,volatility,delta,gamma,theta,vega"


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
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        captured_data: list[dict[str, Any]] = []

        # Listen to any background network responses for options API
        async def handle_response(response):
            if "proxies/core-api" in response.url or ("options" in response.url and "get" in response.url):
                try:
                    if response.ok and "json" in response.headers.get("content-type", ""):
                        body = await response.json()
                        if isinstance(body, dict) and (body.get("data") or body.get("count")):
                            captured_data.append(body)
                            logger.info("Intercepted Barchart options response from: %s", response.url)
                except Exception:
                    pass

        page.on("response", handle_response)

        logger.info("Navigating to: %s", page_url)
        try:
            await page.goto(page_url, timeout=timeout_ms, wait_until="domcontentloaded")
            await asyncio.sleep(4.0)
        except Exception as e:
            logger.warning("Page navigation notice (proceeding to evaluate): %s", e)
            await asyncio.sleep(3.0)

        # Check if we already intercepted a valid API response
        for data in captured_data:
            records = data.get("data") if isinstance(data, dict) else data
            if isinstance(records, list) and len(records) > 0:
                first_rec = records[0].get("raw", records[0]) if isinstance(records[0], dict) else {}
                if first_rec.get("strikePrice") is not None or first_rec.get("strike") is not None:
                    await browser.close()
                    logger.info("Using intercepted response with %d records", len(records))
                    return data

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
        result = None
        for attempt in range(2):
            try:
                result = await page.evaluate(js_code)
                if result:
                    break
            except Exception as e:
                logger.warning("Evaluation attempt %d error: %s", attempt + 1, e)
                await asyncio.sleep(3.0)

        await browser.close()

        if result:
            logger.info("Successfully fetched options data via in-page API evaluation!")
            return result

        raise RuntimeError("Failed to obtain Barchart options data via browser evaluation")


def scrape_and_save(
    output_path: str = "data/options_prices_GCZ26.csv",
    page_url: str = DEFAULT_BARCHART_URL,
    dry_run: bool = False,
) -> str:
    """Scrape Barchart options chain and save to CSV file with weekend/offline fallback."""
    logger.info("Initiating scrape for CME options from: %s", page_url)
    out_file = Path(output_path)
    df = None
    try:
        raw_json = asyncio.run(fetch_barchart_options_playwright(page_url=page_url))
        df = parse_barchart_json(raw_json)
    except Exception as e:
        if out_file.exists():
            logger.warning("Live scrape notice (%s). Preserving existing active dataset at %s", e, out_file)
            drive_data_dir = Path("H:/My Drive/Neiro-Quant/data")
            if drive_data_dir.exists():
                try:
                    import shutil
                    shutil.copy2(out_file, drive_data_dir / out_file.name)
                    logger.info("Synced existing valid data to Google Drive: %s", drive_data_dir / out_file.name)
                except Exception:
                    pass
            return str(out_file)
        raise e

    if dry_run:
        logger.info("[DRY RUN] Parsed %d strikes successfully. No file written.", len(df))
        return ""

    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    logger.info("Saved %d strikes to %s (file size: %d bytes)", len(df), out_file, out_file.stat().st_size)

    # Mirror to Google Drive Desktop if folder exists
    drive_data_dir = Path("H:/My Drive/Neiro-Quant/data")
    if drive_data_dir.exists():
        try:
            drive_file = drive_data_dir / out_file.name
            df.to_csv(drive_file, index=False)
            logger.info("Mirrored to Google Drive Desktop: %s", drive_file)
        except Exception as e:
            logger.warning("Could not mirror to Google Drive: %s", e)

    return str(out_file)


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Barchart Options Scraper")
    parser.add_argument("--url", default=DEFAULT_BARCHART_URL, help="Barchart Options Chain page URL")
    parser.add_argument("--output", default="data/options_prices_GCZ26.csv", help="Path to save output CSV")
    parser.add_argument("--dry-run", action="store_true", help="Test scraping without saving to file")
    args = parser.parse_args()

    try:
        scrape_and_save(output_path=args.output, page_url=args.url, dry_run=args.dry_run)
    except Exception as e:
        logger.error("Scraper failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
