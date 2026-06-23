from datetime import date

import pandas as pd

from data_pipeline.providers.tushare import TushareProvider


def test_stock_basic_normalization_filters_universe():
    raw = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "area": "深圳",
                "industry": "银行",
                "market": "主板",
                "exchange": "SZSE",
                "list_date": "19910403",
                "list_status": "L",
            },
            {
                "ts_code": "000002.SZ",
                "symbol": "000002",
                "name": "*ST 测试",
                "area": "深圳",
                "industry": "地产",
                "market": "主板",
                "exchange": "SZSE",
                "list_date": "19910403",
                "list_status": "L",
            },
            {
                "ts_code": "688001.SH",
                "symbol": "688001",
                "name": "新股",
                "area": "上海",
                "industry": "电子",
                "market": "科创板",
                "exchange": "SSE",
                "list_date": "20231201",
                "list_status": "L",
            },
            {
                "ts_code": "000003.SZ",
                "symbol": "000003",
                "name": "退市股",
                "area": "深圳",
                "industry": "综合",
                "market": "主板",
                "exchange": "SZSE",
                "list_date": "19910403",
                "list_status": "D",
            },
        ]
    )

    normalized = TushareProvider.normalize_stock_basic(
        raw,
        min_list_days=180,
        exclude_st=True,
        as_of=date(2024, 1, 1),
    )

    assert normalized["ts_code"].tolist() == ["000001.SZ"]
    assert normalized.loc[0, "list_date"] == date(1991, 4, 3)


def test_daily_bar_normalization_maps_fields_and_sorts():
    raw = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "trade_date": "20240103",
                "open": "10.1",
                "high": "10.5",
                "low": "10.0",
                "close": "10.3",
                "vol": "2000",
                "amount": "20500",
            },
            {
                "ts_code": "000001.SZ",
                "trade_date": "20240102",
                "open": "10.0",
                "high": "10.2",
                "low": "9.9",
                "close": "10.1",
                "vol": "1000",
                "amount": "10100",
            },
        ]
    )

    normalized = TushareProvider.normalize_daily_bars(raw, source="tushare:qfq")

    assert normalized["trade_date"].tolist() == [date(2024, 1, 2), date(2024, 1, 3)]
    assert normalized["volume"].tolist() == [1000.0, 2000.0]
    assert normalized["source"].unique().tolist() == ["tushare:qfq"]
