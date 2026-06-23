import pandas as pd
import torch

from model_core.data_loader import AStockDataLoader
from model_core.vocab import FEATURE_NAMES


def test_loader_builds_features_and_missing_day_mask():
    df = pd.DataFrame(
        [
            ("2024-01-02", "000001.SZ", 10.0, 10.5, 9.8, 10.2, 1000, 10000),
            ("2024-01-02", "000002.SZ", 20.0, 20.5, 19.8, 20.2, 1500, 30000),
            ("2024-01-03", "000001.SZ", 10.2, 10.6, 10.1, 10.4, 1100, 11000),
            ("2024-01-04", "000001.SZ", 10.4, 10.8, 10.2, 10.7, 1300, 14000),
            ("2024-01-04", "000002.SZ", 20.2, 20.4, 19.9, 20.0, 1200, 24000),
            ("2024-01-05", "000001.SZ", 10.7, 11.0, 10.5, 10.9, 1600, 17000),
            ("2024-01-05", "000002.SZ", 20.0, 20.6, 19.8, 20.5, 1700, 35000),
            ("2024-01-08", "000001.SZ", 10.9, 11.1, 10.6, 10.8, 900, 9800),
            ("2024-01-08", "000002.SZ", 20.5, 21.0, 20.1, 20.9, 2000, 41000),
        ],
        columns=[
            "trade_date",
            "ts_code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ],
    )

    loader = AStockDataLoader()
    loader.load_from_dataframe(df, ["000001.SZ", "000002.SZ"])

    assert loader.feat_tensor.shape == (2, len(FEATURE_NAMES), 5)
    assert loader.target_ret.shape == (2, 5)
    assert not torch.isnan(loader.feat_tensor).any()
    assert not torch.isinf(loader.feat_tensor).any()
    assert loader.raw_data_cache["tradable_mask"].cpu()[1, 1].item() == 0.0
