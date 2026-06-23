import json
import os

import pandas as pd
import sqlalchemy
from dotenv import load_dotenv

load_dotenv()


class DashboardService:
    def __init__(self):
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "password")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "astock_quant")
        self.engine = sqlalchemy.create_engine(
            f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )

    def get_database_stats(self):
        query = """
        SELECT
            (SELECT COUNT(*) FROM securities) AS security_count,
            (SELECT COUNT(*) FROM daily_bars) AS bar_count,
            (SELECT MAX(trade_date) FROM daily_bars) AS latest_trade_date
        """
        try:
            return pd.read_sql(query, self.engine).iloc[0].to_dict()
        except Exception:
            return {
                "security_count": 0,
                "bar_count": 0,
                "latest_trade_date": None,
            }

    def load_strategy_info(self):
        try:
            with open("best_astock_strategy.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"formula": "Not trained yet", "market": "A-share daily"}

    def get_market_overview(self, limit=100):
        limit = max(1, int(limit))
        query = f"""
        WITH latest AS (
            SELECT MAX(trade_date) AS trade_date FROM daily_bars
        )
        SELECT
            s.ts_code,
            s.symbol,
            s.name,
            COALESCE(s.industry, 'Unknown') AS industry,
            b.trade_date,
            b.open,
            b.high,
            b.low,
            b.close,
            b.volume,
            b.amount,
            CASE
                WHEN b.open > 0 THEN (b.close - b.open) / b.open
                ELSE 0
            END AS pct_chg
        FROM daily_bars b
        JOIN latest l ON b.trade_date = l.trade_date
        JOIN securities s ON b.ts_code = s.ts_code
        ORDER BY b.amount DESC NULLS LAST
        LIMIT {limit}
        """
        try:
            return pd.read_sql(query, self.engine)
        except Exception:
            return pd.DataFrame()

    def get_industry_overview(self):
        query = """
        WITH latest AS (
            SELECT MAX(trade_date) AS trade_date FROM daily_bars
        ),
        snapshot AS (
            SELECT
                COALESCE(s.industry, 'Unknown') AS industry,
                b.amount,
                CASE
                    WHEN b.open > 0 THEN (b.close - b.open) / b.open
                    ELSE 0
                END AS pct_chg
            FROM daily_bars b
            JOIN latest l ON b.trade_date = l.trade_date
            JOIN securities s ON b.ts_code = s.ts_code
        )
        SELECT
            industry,
            COUNT(*) AS security_count,
            SUM(amount) AS amount,
            AVG(pct_chg) AS avg_pct_chg
        FROM snapshot
        GROUP BY industry
        ORDER BY amount DESC NULLS LAST
        """
        try:
            return pd.read_sql(query, self.engine)
        except Exception:
            return pd.DataFrame()

    def get_recent_bars(self, ts_code, limit=120):
        if not ts_code:
            return pd.DataFrame()
        query = """
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_bars
        WHERE ts_code = %(ts_code)s
        ORDER BY trade_date DESC
        LIMIT %(limit)s
        """
        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={"ts_code": ts_code, "limit": int(limit)},
            )
            return df.sort_values("trade_date")
        except Exception:
            return pd.DataFrame()

    def get_recent_logs(self, n=50):
        log_file = "strategy.log"
        if not os.path.exists(log_file):
            return []

        with open(log_file, "r") as f:
            lines = f.readlines()
            return lines[-n:]
