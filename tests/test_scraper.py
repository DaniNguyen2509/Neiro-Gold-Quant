"""Unit tests for Barchart Options Chain Scraper and Parser."""
from __future__ import annotations

import unittest.mock as mock
import pytest
import pandas as pd
from src.collector.parser import clean_num, parse_barchart_json
from src.quant_engine.loader import load_options_data


class TestScraperCleaning:
    """Tests for clean_num helper in parser."""

    def test_clean_num_basic(self):
        assert clean_num("123.45") == 123.45
        assert clean_num(123.45) == 123.45
        assert clean_num("1,234.50") == 1234.50
        assert clean_num("$4,181.10") == 4181.10

    def test_clean_num_anomalies(self):
        assert clean_num("12.5s") == 12.5  # Settlement marker
        assert clean_num("15.5%") == 15.5
        assert clean_num("N/A") == 0.0
        assert clean_num("-") == 0.0
        assert clean_num("--") == 0.0
        assert clean_num("UNCH") == 0.0
        assert clean_num(None) == 0.0


@pytest.fixture
def mock_barchart_api_data():
    """Realistic mock response from Barchart proxies/core-api/v1/options/get."""
    return {
        "count": 4,
        "total": 4,
        "data": [
            {
                "raw": {
                    "strikePrice": "4,175.00",
                    "optionType": "Call",
                    "bidPrice": "44.50",
                    "askPrice": "45.70",
                    "lastPrice": "45.10",
                    "volume": "28",
                    "openInterest": "42",
                    "gamma": "0.0006",
                    "volatility": "21.5%",
                }
            },
            {
                "raw": {
                    "strikePrice": "4,175.00",
                    "optionType": "Put",
                    "bidPrice": "38.50",
                    "askPrice": "39.50",
                    "lastPrice": "39.00",
                    "volume": "78",
                    "openInterest": "231",
                    "gamma": "0.0006",
                    "volatility": "21.8%",
                }
            },
            {
                "raw": {
                    "strikePrice": "4,200.00",
                    "optionType": "Call",
                    "bidPrice": "32.00",
                    "askPrice": "33.20",
                    "lastPrice": "32.60",
                    "volume": "105",
                    "openInterest": "512",
                    "gamma": "0.0004",
                    "volatility": "21.9%",
                }
            },
            {
                "raw": {
                    "strikePrice": "4,200.00",
                    "optionType": "Put",
                    "bidPrice": "51.50",
                    "askPrice": "52.70",
                    "lastPrice": "52.10",
                    "volume": "372",
                    "openInterest": "275",
                    "gamma": "0.0003",
                    "volatility": "22.0%",
                }
            },
        ]
    }


class TestScraperParser:
    """Tests for parse_barchart_json."""

    def test_parse_valid_json(self, mock_barchart_api_data):
        df = parse_barchart_json(mock_barchart_api_data)
        assert len(df) == 2  # 2 distinct strikes: 4175 and 4200
        assert list(df["strike"]) == [4175.0, 4200.0]

        # Strike 4175 checks
        row_4175 = df[df["strike"] == 4175.0].iloc[0]
        assert row_4175["callBid"] == 44.50
        assert row_4175["callAsk"] == 45.70
        assert row_4175["callMid"] == 45.10  # (44.5 + 45.7) / 2
        assert row_4175["callVolume"] == 28
        assert row_4175["callOpenInterest"] == 42
        assert row_4175["callGamma"] == 0.0006
        assert row_4175["callIV"] == 0.215

        assert row_4175["putBid"] == 38.50
        assert row_4175["putAsk"] == 39.50
        assert row_4175["putMid"] == 39.00
        assert row_4175["putVolume"] == 78
        assert row_4175["putOpenInterest"] == 231

    def test_parse_empty_or_invalid_json(self):
        with pytest.raises(ValueError, match="Empty JSON"):
            parse_barchart_json({})

        with pytest.raises(ValueError, match="No valid strike"):
            parse_barchart_json({"data": [{"foo": "bar"}]})

    def test_parser_compatibility_with_quant_engine(self, mock_barchart_api_data, tmp_path):
        """Test that CSV produced by parser is 100% compatible with quant engine loader."""
        df = parse_barchart_json(mock_barchart_api_data)
        csv_file = tmp_path / "test_options.csv"
        df.to_csv(csv_file, index=False)

        # Load with quant_engine
        df_loaded = load_options_data(str(csv_file))
        assert isinstance(df_loaded, pd.DataFrame)
        assert len(df_loaded) == 2
        assert list(df_loaded["strike"]) == [4175.0, 4200.0]

    def test_parse_with_expiration_date(self):
        data = {
            "meta": {"expirationDate": "2026-11-24"},
            "data": [
                {
                    "raw": {
                        "strikePrice": "4180.00",
                        "optionType": "Call",
                        "bidPrice": "40.0",
                        "askPrice": "41.0",
                        "expirationDate": "2026-11-24",
                    }
                },
                {
                    "raw": {
                        "strikePrice": "4180.00",
                        "optionType": "Put",
                        "bidPrice": "39.0",
                        "askPrice": "40.0",
                        "expirationDate": "2026-11-24",
                    }
                }
            ]
        }
        df = parse_barchart_json(data)
        assert len(df) == 1
        assert "expirationDate" in df.columns
        assert df["expirationDate"].iloc[0] == "2026-11-24"
        assert df.attrs.get("expiration_date") == "2026-11-24"


class TestScraperWorkflow:
    def test_get_dynamic_barchart_url(self):
        from src.collector.scraper import get_dynamic_barchart_url
        url = get_dynamic_barchart_url()
        assert "barchart.com" in url
        assert "options" in url

    def test_scrape_and_save_success(self, mock_barchart_api_data, tmp_path):
        from src.collector.scraper import scrape_and_save
        out_csv = tmp_path / "scraped.csv"

        with mock.patch("src.collector.scraper.fetch_barchart_options_playwright", return_value=mock_barchart_api_data):
            saved = scrape_and_save(output_path=str(out_csv))
            assert saved == str(out_csv)
            assert out_csv.exists()
            df = pd.read_csv(out_csv)
            assert len(df) == 2
            assert "strike" in df.columns

    def test_scrape_and_save_fallback_on_network_error(self, tmp_path):
        from src.collector.scraper import scrape_and_save
        out_csv = tmp_path / "fallback.csv"
        out_csv.write_text("strike,callBid,callAsk\n4180,20,21\n", encoding="utf-8")

        with mock.patch("src.collector.scraper.fetch_barchart_options_playwright", side_effect=RuntimeError("Cloudflare timeout")):
            saved = scrape_and_save(output_path=str(out_csv))
            # Gracefully preserves existing dataset
            assert saved == str(out_csv)
            assert out_csv.exists()

    def test_scrape_and_save_raises_if_no_existing_file(self, tmp_path):
        from src.collector.scraper import scrape_and_save
        out_csv = tmp_path / "nonexistent.csv"

        with mock.patch("src.collector.scraper.fetch_barchart_options_playwright", side_effect=RuntimeError("Cloudflare timeout")):
            with pytest.raises(RuntimeError, match="Cloudflare timeout"):
                scrape_and_save(output_path=str(out_csv))
