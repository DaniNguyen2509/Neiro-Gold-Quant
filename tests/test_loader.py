"""
Unit Tests for Neiro-Quant Automated Data Ingestion & Cleaning Pipeline.
"""

import pytest
import pandas as pd
import numpy as np

from src.quant_engine.loader import (
    clean_val,
    clean_strike,
    normalize_options_df,
    parse_bookmarklet_csv,
    parse_clipboard_tsv,
    load_options_data,
    compute_tactical_matrix,
    generate_tactical_summary,
    to_options_snapshot,
    to_market_snapshot,
    CANONICAL_COLUMNS,
    BENCHMARK_GCZ26_DATA,
)
from src.quant_engine.dealer import find_walls
from src.quant_engine.strategy import generate_signals


class TestCleaningLogic:
    def test_clean_val_spreadsheets_errors(self):
        assert clean_val("#ERROR!") == 0.0
        assert clean_val("#REF!") == 0.0
        assert clean_val("#VALUE!") == 0.0
        assert clean_val("#N/A") == 0.0
        assert clean_val("#DIV/0!") == 0.0
        assert clean_val("#NUM!") == 0.0

    def test_clean_val_text_tokens(self):
        assert clean_val("unch") == 0.0
        assert clean_val("UNCH") == 0.0
        assert clean_val("N/A") == 0.0
        assert clean_val("nan") == 0.0
        assert clean_val("null") == 0.0
        assert clean_val("-") == 0.0
        assert clean_val("--") == 0.0
        assert clean_val("") == 0.0
        assert clean_val(None) == 0.0

    def test_clean_val_settlement_marker(self):
        assert clean_val("133.40s") == 133.40
        assert clean_val("1.80s") == 1.80
        assert clean_val("0.05s") == 0.05
        assert clean_val("125.30S") == 125.30

    def test_clean_val_percentage_and_commas(self):
        assert clean_val("26.90%") == 26.90
        assert clean_val("4,135.00") == 4135.00
        assert clean_val('"13,340.00"') == 13340.00

    def test_clean_val_formula_prefixes(self):
        assert clean_val("+4150.00") == 4150.00
        assert clean_val("=+4150.50") == 4150.50
        assert clean_val("=123.45") == 123.45

    def test_clean_strike(self):
        assert clean_strike("4,135.00C") == 4135.00
        assert clean_strike("4,135.00P") == 4135.00
        assert clean_strike('"4,150.00"') == 4150.00
        assert clean_strike("+4175") == 4175.00
        assert clean_strike(4200.0) == 4200.00
        assert clean_strike(None) == 0.0


class TestIngestionParsers:
    def test_parse_bookmarklet_csv_with_anomalies(self):
        csv_sample = (
            "strike,callBid,callAsk,callMid,callLatest,callVolume,callOpenInterest,callGamma,callIV,putBid,putAsk,putMid,putLatest,putVolume,putOpenInterest,putGamma,putIV\n"
            "4150.0,125.10,125.50,,125.30s,17,461,0.00360,26.90%,94.10,94.50,,94.30s,15,1162,0.00360,26.90%\n"
            "+4180.0,unch,109.70,,109.50s,#ERROR!,30,0.00378,21.5%,108.30,108.70,,108.50s,63,236,0.00378,21.5%\n"
            "4200.0,99.00,99.40,99.20,99.20,646,2444,0.00370,0.2146,118.00,118.40,118.20,118.20,148,2527,0.00370,0.2146\n"
        )
        df = parse_bookmarklet_csv(csv_sample)
        assert len(df) == 3
        assert list(df.columns) == CANONICAL_COLUMNS
        assert df.loc[df['strike'] == 4150.0, 'callMid'].iloc[0] == 125.30
        assert df.loc[df['strike'] == 4180.0, 'callVolume'].iloc[0] == 0.0
        assert df.loc[df['strike'] == 4150.0, 'callIV'].iloc[0] == pytest.approx(0.2690)
        assert df.loc[df['strike'] == 4200.0, 'callOpenInterest'].iloc[0] == 2444.0

    def test_parse_clipboard_tsv(self):
        tsv_sample = (
            "Strike\tCall Bid\tCall Ask\tCall Vol\tCall OI\tCall Gamma\tPut Bid\tPut Ask\tPut Vol\tPut OI\tPut Gamma\n"
            "4,150.00\t125.10\t125.50\t17\t461\t0.00360\t94.10\t94.50\t15\t1162\t0.00360\n"
            "4,200.00\t99.00\t99.40\t646\t2444\t0.00370\t118.00\t118.40\t148\t2527\t0.00370\n"
        )
        df = parse_clipboard_tsv(tsv_sample)
        assert len(df) == 2
        assert df.loc[df['strike'] == 4150.0, 'callOpenInterest'].iloc[0] == 461.0
        assert df.loc[df['strike'] == 4200.0, 'putOpenInterest'].iloc[0] == 2527.0
        assert df.loc[df['strike'] == 4200.0, 'callMid'].iloc[0] == 99.20

    def test_load_options_data_from_existing_repo(self):
        df = load_options_data(data_dir="data")
        assert len(df) >= 20
        assert "strike" in df.columns
        assert (df['callOpenInterest'] > 0).any()
        assert (df['putOpenInterest'] > 0).any()

    def test_fallback_when_no_source(self):
        df = load_options_data(source="non_existent_file.csv", data_dir="non_existent_dir")
        assert len(df) == 20
        assert df.loc[df['strike'] == 4200.0, 'callOpenInterest'].iloc[0] == 2444.0


class TestStrikeAlignment:
    def test_stacked_mismatched_strikes(self):
        # Calls has 4130 and 4150, Put has 4150 and 4200
        stacked_df = pd.DataFrame([
            {"Strike": "4130.00C", "Bid": 140.0, "Ask": 140.5, "Volume": 5, "Open Int": 50},
            {"Strike": "4150.00C", "Bid": 125.1, "Ask": 125.5, "Volume": 17, "Open Int": 461},
            {"Strike": "4150.00P", "Bid": 94.1, "Ask": 94.5, "Volume": 15, "Open Int": 1162},
            {"Strike": "4200.00P", "Bid": 118.0, "Ask": 118.4, "Volume": 148, "Open Int": 2527},
        ])
        df = normalize_options_df(stacked_df)
        assert len(df) == 3
        assert list(df['strike']) == [4130.0, 4150.0, 4200.0]
        # At 4130, Call has 50 OI, Put has 0 OI
        r4130 = df.loc[df['strike'] == 4130.0].iloc[0]
        assert r4130['callOpenInterest'] == 50.0
        assert r4130['putOpenInterest'] == 0.0
        # At 4200, Call has 0 OI, Put has 2527 OI
        r4200 = df.loc[df['strike'] == 4200.0].iloc[0]
        assert r4200['callOpenInterest'] == 0.0
        assert r4200['putOpenInterest'] == 2527.0


class TestTacticalMatrix:
    def test_compute_tactical_matrix(self):
        df = load_options_data(BENCHMARK_GCZ26_DATA)
        matrix = compute_tactical_matrix(df, spot=4181.10)

        assert matrix['spot_price'] == 4181.10
        assert matrix['call_wall'] == 4200.0
        assert matrix['put_wall'] == 4200.0 or matrix['put_wall'] == 4150.0
        assert 'total_net_gex' in matrix
        assert 'total_net_vex' in matrix
        assert 'total_net_chex' in matrix
        assert 'netVEX' in matrix['df'].columns
        assert 'netCHEX' in matrix['df'].columns
        assert not matrix['df']['netVEX'].isna().any()
        assert not matrix['df']['netCHEX'].isna().any()
        assert 'tactical_table' in matrix

        table = matrix['tactical_table']
        assert len(table) == 4
        assert '1. BAN DINH (Fade Sell)' in table['Chien Luoc'].values
        assert '2. MUA DAY (Rebound Buy)' in table['Chien Luoc'].values
        assert '3. MUA DUOI (Squeeze Break)' in table['Chien Luoc'].values
        assert '4. BAN THAO (Waterfall Break)' in table['Chien Luoc'].values

    def test_generate_tactical_summary_direct(self):
        table = generate_tactical_summary(BENCHMARK_GCZ26_DATA)
        assert isinstance(table, pd.DataFrame)
        assert len(table) == 4
        assert 'Hard SL' in table.columns
        assert 'TP1 / TP2' in table.columns


class TestModelInteroperability:
    def test_to_options_snapshot_and_dealer_walls(self):
        df = load_options_data(BENCHMARK_GCZ26_DATA)
        snapshot = to_options_snapshot(df)
        assert len(snapshot.strikes) == len(df)
        call_walls, put_walls = find_walls(snapshot, top_n=2)
        assert len(call_walls) == 2
        assert len(put_walls) == 2
        assert call_walls[0].strike == 4200.0

    def test_to_market_snapshot_and_strategy_signals(self):
        df = load_options_data(BENCHMARK_GCZ26_DATA)
        snap = to_market_snapshot(df, spot=4181.10, dte_days=1.0)
        signals = generate_signals(snap)
        assert 'gamma_levels' in signals
        assert 'expected_move' in signals
        assert signals['s_implied'] > 4000.0


class TestDynamicDTE:
    def test_dynamic_dte_calculation(self):
        from src.quant_engine.synthetic import compute_dynamic_dte
        import datetime

        now = datetime.datetime(2026, 10, 19, 12, 0, tzinfo=datetime.timezone.utc)
        dte = compute_dynamic_dte("2026-11-24", now=now)
        assert 36.0 < dte < 37.0

    def test_dynamic_dte_fallback(self):
        from src.quant_engine.synthetic import compute_dynamic_dte
        dte = compute_dynamic_dte(None, default_dte=25.0)
        assert dte == 25.0

    def test_to_market_snapshot_with_dynamic_dte(self):
        df = pd.DataFrame(BENCHMARK_GCZ26_DATA)
        df['expirationDate'] = '2026-11-24'
        snap = to_market_snapshot(df)
        assert snap.dte_days > 1.0


class TestCMEOptionsResolver:
    def test_cme_expiry_calculation_dates(self):
        from src.quant_engine.synthetic import get_cme_option_expiry_date
        import datetime

        # Nov 2026 option expires on 4th last business day of Oct 2026
        exp_nov = get_cme_option_expiry_date(2026, 11)
        assert exp_nov == datetime.date(2026, 10, 27)

        # Dec 2026 option expires on 4th last business day of Nov 2026
        exp_dec = get_cme_option_expiry_date(2026, 12)
        assert exp_dec == datetime.date(2026, 11, 25)

    def test_resolve_front_month_cme_option_active_and_rollover(self):
        from src.quant_engine.synthetic import resolve_front_month_cme_option
        import datetime

        # During Oct 2026 before Oct 27
        res1 = resolve_front_month_cme_option(datetime.date(2026, 10, 19))
        assert res1['option_symbol'] == 'OGX26'
        assert res1['expiration_date'] == '2026-10-27'
        assert 'GCZ26' in res1['barchart_url']

        # After Oct 27 expiration -> automatically rolls over to Dec 2026 option (OGZ26)
        res2 = resolve_front_month_cme_option(datetime.date(2026, 10, 28))
        assert res2['option_symbol'] == 'OGZ26'
        assert res2['expiration_date'] == '2026-11-25'
        assert 'GCZ26' in res2['barchart_url']


