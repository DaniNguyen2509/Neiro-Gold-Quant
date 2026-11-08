"""Barchart Playwright Headless Scraper for CME Gold Options (GCZ26).

Runs headless Chromium to cleanly navigate Barchart, execute internal
API query within the authenticated browser context, and extract full
options chain (Prices, Volume, OI, Greeks).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .parser import parse_barchart_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_dynamic_barchart_url() -> str:
    try:
        from src.quant_engine.synthetic import resolve_front_month_cme_option
        resolved = resolve_front_month_cme_option()
        return resolved["barchart_url"]
    except Exception:
        return "https://www.barchart.com/futures/quotes/GCZ26/options?futuresOptionsView=merged"


DEFAULT_BARCHART_URL = get_dynamic_barchart_url()
ALL_FIELDS = "strike,strikePrice,optionType,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,expirationDate,volatility,delta,gamma,theta,vega"


def _extract_records(data_cand: Any) -> list[dict[str, Any]]:
    """Helper to extract option records whether response is list, dict, or Call/Put partitioned."""
    if isinstance(data_cand, list):
        return data_cand
    if isinstance(data_cand, dict):
        d = data_cand.get("data") or data_cand.get("results") or data_cand
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            recs = []
            for k in ("Call", "Put", "calls", "puts"):
                if k in d and isinstance(d[k], list):
                    recs.extend(d[k])
            if recs:
                return recs
            for v in d.values():
                if isinstance(v, list):
                    recs.extend(v)
            return recs
    return []


async def fetch_barchart_options_playwright(
    page_url: str | None = None,
    timeout_ms: int = 45000,
) -> dict[str, Any] | list[Any]:
    if not page_url:
        page_url = get_dynamic_barchart_url()
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

        # Listen to background network responses for options / quotes API
        async def handle_response(response):
            if "proxies/core-api" in response.url or ("options" in response.url and "get" in response.url) or "quotes/get" in response.url:
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
        except Exception as e:
            logger.warning("Page navigation notice (proceeding to evaluate): %s", e)

        # Poll up to 12s for background interception
        for _ in range(24):
            for data in captured_data:
                records = _extract_records(data)
                if records:
                    first_rec = records[0].get("raw", records[0]) if isinstance(records[0], dict) else {}
                    if first_rec.get("strikePrice") is not None or first_rec.get("strike") is not None:
                        await browser.close()
                        logger.info("Using intercepted response with %d records", len(records))
                        return data
            await asyncio.sleep(0.5)

        # Fallback: Execute direct API call in browser context (using active XSRF token)
        logger.info("Evaluating internal API fetch in browser context...")
        js_code = f"""
        async () => {{
            function getCookie(n) {{
                let m = document.cookie.match(new RegExp('(^|;\\\\s*)(' + n + ')=([^;]*)'));
                return m ? decodeURIComponent(m[3]) : '';
            }}
            let xsrf = getCookie('XSRF-TOKEN');
            let perf = performance.getEntriesByType('resource').map(e => e.name);
            let apiUrls = perf.filter(u => u.includes('proxies/core-api') && (u.includes('quotes/get') || u.includes('options')));
            let targetUrl = apiUrls.length > 0 ? apiUrls[apiUrls.length - 1] : '/proxies/core-api/v1/quotes/get?symbol=GCZ26&list=futures.options&groupBy=optionType&orderBy=strike&orderDir=asc';
            
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


def _enrich_options_iv_and_greeks(df: pd.DataFrame, dte_days: float = 23.0) -> pd.DataFrame:
    """Enriches scraped options chain with calibrated Black-76 IV if Barchart provides 0."""
    if df is None or df.empty or "strike" not in df.columns:
        return df

    from src.quant_engine.dealer import solve_black76_iv
    ref_p = 4000.0
    try:
        from src.quant_engine.basis import fetch_live_cme_futures_price
        lp = fetch_live_cme_futures_price()
        if lp and lp > 500.0:
            ref_p = lp
    except Exception:
        pass

    t_years = max(1.0 / 365.0, float(dte_days) / 365.0)
    r = 0.045

    if "callIV" in df.columns and (df["callIV"] <= 0.01).all():
        solved_c = []
        for _, row in df.iterrows():
            k = float(row.get("strike", 0))
            mid = float(row.get("callMid", 0))
            if mid <= 0:
                bid = float(row.get("callBid", 0))
                ask = float(row.get("callAsk", 0))
                mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else float(row.get("callLatest", 0))
            iv = solve_black76_iv(ref_p, k, t_years, mid, is_call=True, r=r) if mid > 0 else 0.20
            solved_c.append(round(iv, 4))
        df["callIV"] = solved_c

    if "putIV" in df.columns and (df["putIV"] <= 0.01).all():
        solved_p = []
        for _, row in df.iterrows():
            k = float(row.get("strike", 0))
            mid = float(row.get("putMid", 0))
            if mid <= 0:
                bid = float(row.get("putBid", 0))
                ask = float(row.get("putAsk", 0))
                mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else float(row.get("putLatest", 0))
            iv = solve_black76_iv(ref_p, k, t_years, mid, is_call=False, r=r) if mid > 0 else 0.20
            solved_p.append(round(iv, 4))
        df["putIV"] = solved_p

    return df


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

    if df is not None and len(df) > 0:
        from src.collector.validator import validate_options_frame
        ref_price = 4000.0
        try:
            from src.quant_engine.basis import fetch_live_cme_futures_price
            lp = fetch_live_cme_futures_price()
            if lp and lp > 500.0:
                ref_price = lp
        except Exception:
            pass
        val = validate_options_frame(df, reference_price=ref_price)
        if not val.ok and out_file.exists():
            logger.warning(
                "Scraped options chain failed validation (%s). Preserving existing active dataset at %s",
                val.errors,
                out_file,
            )
            return str(out_file)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    if "scraped_at_utc" not in df.columns:
        df["scraped_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    df = _enrich_options_iv_and_greeks(df)
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


def scrape_multi_expiry_and_save(
    output_dir: str = "data",
    underlying_futures: str = "GCZ26",
    weekly_count: int = 1,
    dry_run: bool = False,
) -> list[str]:
    """Scrape both nearest Weekly and Front-Month Monthly contracts and aggregate them into primary dataset."""
    from src.quant_engine.synthetic import resolve_active_expirations
    from src.quant_engine.loader import aggregate_options_dataframes

    expirations = resolve_active_expirations(underlying_futures=underlying_futures, weekly_count=weekly_count)
    logger.info("Targeting %d active CME expirations (Weekly + Monthly)", len(expirations))

    saved_files = []
    scraped_dfs = []
    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    for exp in expirations:
        sym = exp["option_symbol"]
        url = exp["barchart_url"]
        sub_csv = out_dir_path / f"options_prices_{underlying_futures}_{sym}.csv"

        try:
            logger.info("Scraping %s (%s) from %s", exp["name"], sym, url)
            raw_json = asyncio.run(fetch_barchart_options_playwright(page_url=url))
            df = parse_barchart_json(raw_json)
            if df is not None and len(df) > 0 and "strike" in df.columns:
                min_k = float(df["strike"].min())
                max_k = float(df["strike"].max())
                if max_k < 3000.0 or min_k > 5000.0:
                    logger.warning(
                        "Scraped strikes [%.1f, %.1f] for %s (%s) do not match active Gold market (3000-5000). Discarding corrupt data.",
                        min_k, max_k, exp["name"], sym
                    )
                    continue
                df = _enrich_options_iv_and_greeks(df, dte_days=float(exp.get("dte", 23.0)))
                df.attrs["expiration_date"] = exp["expiration_date"]
                df.attrs["dte_days"] = exp["dte"]
                df.attrs["option_symbol"] = sym
                scraped_dfs.append(df)
                if not dry_run:
                    df.to_csv(sub_csv, index=False)
                    saved_files.append(str(sub_csv))
                    logger.info("Saved %s options chain with %d strikes to %s", sym, len(df), sub_csv)
        except Exception as e:
            logger.warning("Could not scrape %s (%s): %s", exp["name"], sym, e)
            if sub_csv.exists():
                try:
                    df = pd.read_csv(sub_csv)
                    if (
                        df is not None
                        and not df.empty
                        and "strike" in df.columns
                        and float(df["strike"].max()) >= 3000.0
                        and float(df["strike"].min()) <= 5000.0
                    ):
                        df.attrs["expiration_date"] = exp["expiration_date"]
                        df.attrs["dte_days"] = exp["dte"]
                        df.attrs["option_symbol"] = sym
                        scraped_dfs.append(df)
                        logger.info("Loaded cached dataset for %s: %s", sym, sub_csv)
                except Exception:
                    pass

    # Aggregate all scraped chains into the master options_prices_GCZ26.csv
    if scraped_dfs:
        logger.info("Superimposing %d options chains into master aggregated dataset...", len(scraped_dfs))
        agg_df = aggregate_options_dataframes(scraped_dfs)
        master_path = out_dir_path / f"options_prices_{underlying_futures}.csv"
        if not dry_run and not agg_df.empty:
            from src.collector.validator import validate_options_frame
            ref_price = 4000.0
            try:
                from src.quant_engine.basis import fetch_live_cme_futures_price
                live_p = fetch_live_cme_futures_price()
                if live_p and live_p > 500.0:
                    ref_price = live_p
            except Exception:
                pass

            val = validate_options_frame(agg_df, reference_price=ref_price)
            if not val.ok and master_path.exists():
                logger.warning(
                    "Aggregated options chain failed validation (%s). Preserving existing active dataset at %s",
                    val.errors,
                    master_path,
                )
            else:
                if "scraped_at_utc" not in agg_df.columns:
                    agg_df["scraped_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                agg_df = _enrich_options_iv_and_greeks(agg_df)
                agg_df.to_csv(master_path, index=False)
                saved_files.append(str(master_path))
                logger.info("Master aggregated dataset saved to %s (%d strikes)", master_path, len(agg_df))

    return saved_files


def main():
    parser = argparse.ArgumentParser(description="Neiro-Quant Barchart Options Scraper")
    parser.add_argument("--url", default=DEFAULT_BARCHART_URL, help="Barchart Options Chain page URL")
    parser.add_argument("--output", default="data/options_prices_GCZ26.csv", help="Path to save output CSV")
    parser.add_argument("--dry-run", action="store_true", help="Test scraping without saving to file")
    parser.add_argument("--multi-expiry", action="store_true", default=True, help="Scrape both Weekly and Monthly contracts")
    parser.add_argument("--single-expiry", action="store_true", help="Scrape only single URL without multi-expiry")
    parser.add_argument("--weekly-count", type=int, default=2, help="Number of weekly contracts to scrape")
    args = parser.parse_args()

    try:
        if args.single_expiry:
            scrape_and_save(output_path=args.output, page_url=args.url, dry_run=args.dry_run)
        else:
            out_dir = str(Path(args.output).parent)
            scrape_multi_expiry_and_save(
                output_dir=out_dir,
                underlying_futures="GCZ26",
                weekly_count=args.weekly_count,
                dry_run=args.dry_run,
            )
    except Exception as e:
        logger.error("Scraper failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
