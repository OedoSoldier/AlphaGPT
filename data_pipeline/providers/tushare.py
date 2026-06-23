from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd
import tushare as ts
from loguru import logger

from ..config import Config


DAILY_COLUMNS = [
    "trade_date",
    "ts_code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "source",
]


class TushareProvider:
    def __init__(self, token: str | None = None, pro_client=None):
        self.token = token if token is not None else Config.TUSHARE_TOKEN
        self.pro = pro_client
        if self.pro is None and self.token:
            with self._without_proxy():
                ts.set_token(self.token)
                self.pro = ts.pro_api(self.token)

    @staticmethod
    @contextmanager
    def _without_proxy():
        proxy_keys = (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        )
        no_proxy_keys = ("NO_PROXY", "no_proxy")
        if not Config.TUSHARE_NO_PROXY:
            yield
            return

        saved = {key: os.environ.get(key) for key in proxy_keys + no_proxy_keys}
        try:
            for key in proxy_keys:
                os.environ.pop(key, None)
            no_proxy_hosts = ["api.tushare.pro", "tushare.pro"]
            for key in no_proxy_keys:
                current = os.environ.get(key, "")
                parts = [item.strip() for item in current.split(",") if item.strip()]
                for host in no_proxy_hosts:
                    if host not in parts:
                        parts.append(host)
                os.environ[key] = ",".join(parts)
            yield
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _require_client(self):
        if self.pro is None:
            raise ValueError("TUSHARE_TOKEN is required for live Tushare requests.")
        return self.pro

    @staticmethod
    def _empty_daily_frame() -> pd.DataFrame:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    @staticmethod
    def _normalize_adj(adj: str | None) -> str | None:
        if adj is None:
            return None
        value = adj.strip().lower()
        if value in {"", "none", "raw", "unadjusted", "no"}:
            return None
        if value not in {"qfq", "hfq"}:
            raise ValueError("TUSHARE_ADJ must be one of qfq, hfq, none/raw.")
        return value

    @staticmethod
    def _parse_yyyymmdd(value) -> date | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except ValueError:
            parsed = pd.to_datetime(text, errors="coerce")
            if pd.isna(parsed):
                return None
            return parsed.date()

    @staticmethod
    def normalize_stock_basic(
        df: pd.DataFrame,
        *,
        min_list_days: int = Config.TUSHARE_MIN_LIST_DAYS,
        exclude_st: bool = Config.TUSHARE_EXCLUDE_ST,
        as_of: date | None = None,
        markets: Iterable[str] | None = None,
        ts_codes: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "ts_code",
                    "symbol",
                    "name",
                    "area",
                    "industry",
                    "market",
                    "exchange",
                    "list_date",
                    "list_status",
                ]
            )

        work = df.copy()
        for col in ["ts_code", "symbol", "name", "area", "industry", "market", "exchange"]:
            if col not in work.columns:
                work[col] = ""
        if "list_status" not in work.columns:
            work["list_status"] = "L"
        if "list_date" not in work.columns:
            work["list_date"] = None

        work["ts_code"] = work["ts_code"].astype(str).str.strip().str.upper()
        work["list_status"] = work["list_status"].fillna("L").astype(str).str.strip().str.upper()
        work = work[(work["ts_code"] != "") & (work["list_status"] == "L")]

        if exclude_st:
            names = work["name"].fillna("").astype(str).str.upper()
            work = work[~names.str.contains("ST", regex=False)]

        market_filter = {m.strip() for m in (markets or []) if m and m.strip()}
        if market_filter:
            work = work[work["market"].fillna("").astype(str).isin(market_filter)]

        code_filter = {c.strip().upper() for c in (ts_codes or []) if c and c.strip()}
        if code_filter:
            work = work[work["ts_code"].isin(code_filter)]

        work["list_date"] = work["list_date"].apply(TushareProvider._parse_yyyymmdd)
        if min_list_days > 0:
            cutoff = (as_of or date.today()) - timedelta(days=min_list_days)
            work = work[work["list_date"].notna() & (work["list_date"] <= cutoff)]

        work = work.sort_values("ts_code").drop_duplicates("ts_code", keep="last")
        if limit and limit > 0:
            work = work.head(limit)

        cols = [
            "ts_code",
            "symbol",
            "name",
            "area",
            "industry",
            "market",
            "exchange",
            "list_date",
            "list_status",
        ]
        return work[cols].reset_index(drop=True)

    def get_stock_universe(self, limit: int | None = None) -> pd.DataFrame:
        pro = self._require_client()
        fields = "ts_code,symbol,name,area,industry,market,exchange,list_date,list_status"
        with self._without_proxy():
            raw = pro.stock_basic(exchange="", list_status="L", fields=fields)
        return self.normalize_stock_basic(
            raw,
            min_list_days=Config.TUSHARE_MIN_LIST_DAYS,
            exclude_st=Config.TUSHARE_EXCLUDE_ST,
            markets=Config.TUSHARE_MARKETS,
            ts_codes=Config.TUSHARE_CODES,
            limit=limit,
        )

    @staticmethod
    def securities_to_records(df: pd.DataFrame):
        records = []
        for row in df.itertuples(index=False):
            list_date = row.list_date
            if pd.isna(list_date):
                list_date = None
            records.append(
                (
                    row.ts_code,
                    row.symbol,
                    row.name,
                    row.area,
                    row.industry,
                    row.market,
                    row.exchange,
                    list_date,
                    row.list_status,
                )
            )
        return records

    @staticmethod
    def normalize_daily_bars(
        df: pd.DataFrame,
        *,
        source: str = "tushare:qfq",
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return TushareProvider._empty_daily_frame()

        work = df.copy()
        required = {"ts_code", "trade_date", "open", "high", "low", "close"}
        missing = required.difference(work.columns)
        if missing:
            raise ValueError(f"Tushare daily bars missing fields: {sorted(missing)}")

        if "vol" in work.columns:
            volume_col = "vol"
        elif "volume" in work.columns:
            volume_col = "volume"
        else:
            work["vol"] = 0.0
            volume_col = "vol"

        if "amount" not in work.columns:
            work["amount"] = 0.0

        for col in ["open", "high", "low", "close", volume_col, "amount"]:
            work[col] = pd.to_numeric(work[col], errors="coerce")

        work["trade_date"] = work["trade_date"].apply(TushareProvider._parse_yyyymmdd)
        work["ts_code"] = work["ts_code"].astype(str).str.strip().str.upper()
        work = work.dropna(subset=["trade_date", "ts_code", "open", "high", "low", "close"])

        normalized = pd.DataFrame(
            {
                "trade_date": work["trade_date"],
                "ts_code": work["ts_code"],
                "open": work["open"],
                "high": work["high"],
                "low": work["low"],
                "close": work["close"],
                "volume": work[volume_col].fillna(0.0),
                "amount": work["amount"].fillna(0.0),
                "source": source,
            }
        )
        normalized = normalized.sort_values(["ts_code", "trade_date"])
        normalized = normalized.drop_duplicates(["trade_date", "ts_code"], keep="last")
        return normalized[DAILY_COLUMNS].reset_index(drop=True)

    @staticmethod
    def daily_bars_to_records(df: pd.DataFrame):
        return [tuple(row) for row in df[DAILY_COLUMNS].itertuples(index=False, name=None)]

    def fetch_daily_bars(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        *,
        adj: str | None = None,
        max_retries: int = Config.TUSHARE_MAX_RETRIES,
    ) -> pd.DataFrame:
        self._require_client()
        normalized_adj = self._normalize_adj(Config.TUSHARE_ADJ if adj is None else adj)
        source = f"tushare:{normalized_adj or 'none'}"

        for attempt in range(1, max_retries + 1):
            try:
                with self._without_proxy():
                    raw = ts.pro_bar(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        freq="D",
                        asset="E",
                        adj=normalized_adj,
                        api=self.pro,
                    )
                return self.normalize_daily_bars(raw, source=source)
            except Exception as exc:
                logger.warning(
                    f"Tushare fetch failed for {ts_code} ({attempt}/{max_retries}): {exc}"
                )
                if attempt < max_retries:
                    time.sleep(min(2 * attempt, 8))

        logger.error(f"Tushare fetch exhausted retries for {ts_code}.")
        return self._empty_daily_frame()
