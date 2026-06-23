import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_csv(name):
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "astock_quant")
    DB_DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    DATA_SOURCE = os.getenv("DATA_SOURCE", "tushare")
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
    TUSHARE_ADJ = os.getenv("TUSHARE_ADJ", "qfq").strip().lower()
    TUSHARE_START_DATE = os.getenv("TUSHARE_START_DATE", "20180101").strip()
    TUSHARE_END_DATE = os.getenv("TUSHARE_END_DATE", "").strip()
    TUSHARE_CODES = _get_csv("TUSHARE_CODES")
    TUSHARE_MARKETS = _get_csv("TUSHARE_MARKETS")
    TUSHARE_MIN_LIST_DAYS = _get_int("TUSHARE_MIN_LIST_DAYS", 180)
    TUSHARE_EXCLUDE_ST = _get_bool("TUSHARE_EXCLUDE_ST", True)
    TUSHARE_UNIVERSE_LIMIT = _get_int("TUSHARE_UNIVERSE_LIMIT", 0)
    TUSHARE_INCREMENTAL = _get_bool("TUSHARE_INCREMENTAL", True)
    TUSHARE_REQUEST_INTERVAL_SECONDS = _get_float("TUSHARE_REQUEST_INTERVAL_SECONDS", 0.25)
    TUSHARE_MAX_RETRIES = _get_int("TUSHARE_MAX_RETRIES", 3)
    TUSHARE_NO_PROXY = _get_bool("TUSHARE_NO_PROXY", True)

    # Legacy crypto settings kept so old modules remain importable when the
    # optional crypto-legacy dependencies are installed.
    CHAIN = "solana"
    TIMEFRAME = "1m" # 也支持 15min
    MIN_LIQUIDITY_USD = 500000.0  
    MIN_FDV = 10000000.0            
    MAX_FDV = float('inf') 
    BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
    BIRDEYE_BASE_URL = os.getenv("BIRDEYE_BASE_URL", "https://public-api.birdeye.so")
    BASE_URL = BIRDEYE_BASE_URL
    BIRDEYE_IS_PAID = True
    USE_DEXSCREENER = False
    CONCURRENCY = 20
    HISTORY_DAYS = 7
