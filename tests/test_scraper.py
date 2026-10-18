"""Unit tests for Barchart Options Chain Scraper and Parser."""
from __future__ import annotations

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


class TestScraperParser:
    """Tests for parse_barchart_json."""

    @pytest.fixture
    def mock_barchart_api_data(self):
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
                        "bidPrice": "32.80",
                        "askPrice": "33.60",
                        "lastPrice": "33.20",
                        "volume": "448",
                        "openInterest": "366",
                        "gamma": "0.0006",
                        "volatility": "21.2%",
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
