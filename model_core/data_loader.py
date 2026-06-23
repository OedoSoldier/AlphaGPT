import pandas as pd
import sqlalchemy
import torch

from .config import ModelConfig
from .factors import FeatureEngineer


class AStockDataLoader:
    def __init__(self):
        self.engine = sqlalchemy.create_engine(ModelConfig.DB_URL)
        self.feat_tensor = None
        self.raw_data_cache = None
        self.target_ret = None
        self.ts_codes = []
        self.addresses = self.ts_codes
        self.trade_dates = []

    def load_data(self, limit_securities=500, limit_tokens=None):
        if limit_tokens is not None:
            limit_securities = limit_tokens
        limit = max(1, int(limit_securities))

        print("Loading A-share daily bars from SQL...")
        top_query = f"""
        SELECT s.ts_code
        FROM securities s
        WHERE EXISTS (
            SELECT 1 FROM daily_bars b WHERE b.ts_code = s.ts_code
        )
        ORDER BY s.ts_code
        LIMIT {limit}
        """
        self.ts_codes = pd.read_sql(top_query, self.engine)["ts_code"].tolist()
        if not self.ts_codes:
            raise ValueError("No securities found. Run data_pipeline.run_pipeline first.")

        code_str = "'" + "','".join(self.ts_codes) + "'"
        data_query = f"""
        SELECT trade_date, ts_code, open, high, low, close, volume, amount
        FROM daily_bars
        WHERE ts_code IN ({code_str})
        ORDER BY trade_date ASC, ts_code ASC
        """
        df = pd.read_sql(data_query, self.engine)
        self.load_from_dataframe(df, self.ts_codes)
        print(f"A-share data ready. Shape: {self.feat_tensor.shape}")
        return self

    def load_from_dataframe(self, df, ts_codes=None):
        if df is None or df.empty:
            raise ValueError("No daily bars provided.")

        work = df.copy()
        work["trade_date"] = pd.to_datetime(work["trade_date"])
        work["ts_code"] = work["ts_code"].astype(str).str.upper()
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            work[col] = pd.to_numeric(work[col], errors="coerce")

        if ts_codes is None:
            ts_codes = sorted(work["ts_code"].dropna().unique().tolist())
        self.ts_codes = [str(code).upper() for code in ts_codes]
        self.addresses = self.ts_codes

        all_dates = sorted(work["trade_date"].dropna().unique())
        self.trade_dates = list(pd.to_datetime(all_dates))

        def pivot_raw(col):
            pivot = work.pivot_table(
                index="trade_date",
                columns="ts_code",
                values=col,
                aggfunc="last",
            )
            return pivot.reindex(index=all_dates, columns=self.ts_codes)

        close_raw = pivot_raw("close")
        volume_raw = pivot_raw("volume")
        tradable = close_raw.notna() & (volume_raw.fillna(0.0) > 0)

        def price_tensor(col):
            pivot = pivot_raw(col).ffill().bfill().fillna(0.0)
            values = pivot.to_numpy(dtype="float32").T
            return torch.tensor(values, dtype=torch.float32, device=ModelConfig.DEVICE)

        def flow_tensor(col):
            pivot = pivot_raw(col).fillna(0.0)
            values = pivot.to_numpy(dtype="float32").T
            return torch.tensor(values, dtype=torch.float32, device=ModelConfig.DEVICE)

        tradable_tensor = torch.tensor(
            tradable.to_numpy(dtype="float32").T,
            dtype=torch.float32,
            device=ModelConfig.DEVICE,
        )

        self.raw_data_cache = {
            "open": price_tensor("open"),
            "high": price_tensor("high"),
            "low": price_tensor("low"),
            "close": price_tensor("close"),
            "volume": flow_tensor("volume"),
            "amount": flow_tensor("amount"),
            "tradable_mask": tradable_tensor,
        }
        self.feat_tensor = FeatureEngineer.compute_features(self.raw_data_cache)

        open_ = self.raw_data_cache["open"]
        open_t1 = torch.roll(open_, -1, dims=1)
        open_t2 = torch.roll(open_, -2, dims=1)
        target = torch.log((open_t2 + 1e-9) / (open_t1 + 1e-9))

        mask_t1 = torch.roll(tradable_tensor, -1, dims=1) > 0
        mask_t2 = torch.roll(tradable_tensor, -2, dims=1) > 0
        target = torch.where(mask_t1 & mask_t2, target, torch.zeros_like(target))
        target[:, -2:] = 0.0
        self.target_ret = torch.nan_to_num(target, nan=0.0, posinf=0.0, neginf=0.0)
        return self


CryptoDataLoader = AStockDataLoader
