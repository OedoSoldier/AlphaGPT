import asyncpg
from loguru import logger
from .config import Config


class DBManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=Config.DB_DSN)
            logger.info("Database connection established.")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS securities (
                    ts_code TEXT PRIMARY KEY,
                    symbol TEXT,
                    name TEXT,
                    area TEXT,
                    industry TEXT,
                    market TEXT,
                    exchange TEXT,
                    list_date DATE,
                    list_status TEXT,
                    last_updated TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_bars (
                    trade_date DATE NOT NULL,
                    ts_code TEXT NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION,
                    amount DOUBLE PRECISION,
                    source TEXT,
                    PRIMARY KEY (trade_date, ts_code)
                );
            """)

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_bars_ts_code ON daily_bars (ts_code);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_bars_trade_date ON daily_bars (trade_date);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_securities_industry ON securities (industry);")

    async def upsert_securities(self, securities):
        if not securities:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO securities (
                    ts_code, symbol, name, area, industry, market, exchange,
                    list_date, list_status, last_updated
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                ON CONFLICT (ts_code) DO UPDATE
                SET symbol = EXCLUDED.symbol,
                    name = EXCLUDED.name,
                    area = EXCLUDED.area,
                    industry = EXCLUDED.industry,
                    market = EXCLUDED.market,
                    exchange = EXCLUDED.exchange,
                    list_date = EXCLUDED.list_date,
                    list_status = EXCLUDED.list_status,
                    last_updated = NOW();
                """,
                securities,
            )

    async def batch_upsert_daily_bars(self, records):
        if not records:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO daily_bars (
                    trade_date, ts_code, open, high, low, close, volume, amount, source
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (trade_date, ts_code) DO UPDATE
                SET open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    source = EXCLUDED.source;
                """,
                records,
            )

    async def get_latest_trade_dates(self, ts_codes):
        if not ts_codes:
            return {}
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ts_code, MAX(trade_date) AS latest
                FROM daily_bars
                WHERE ts_code = ANY($1::text[])
                GROUP BY ts_code
                """,
                list(ts_codes),
            )
        return {row["ts_code"]: row["latest"] for row in rows}

    async def upsert_tokens(self, tokens):
        if not tokens: return
        async with self.pool.acquire() as conn:
            # tokens: list of (address, symbol, name, decimals, chain)
            await conn.executemany("""
                INSERT INTO tokens (address, symbol, name, decimals, chain, last_updated)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (address) DO UPDATE 
                SET symbol = EXCLUDED.symbol, last_updated = NOW();
            """, tokens)

    async def batch_insert_ohlcv(self, records):
        if not records: return
        async with self.pool.acquire() as conn:
            try:
                await conn.copy_records_to_table(
                    'ohlcv',
                    records=records,
                    columns=['time', 'address', 'open', 'high', 'low', 'close', 
                             'volume', 'liquidity', 'fdv', 'source'],
                    timeout=60
                )
            except asyncpg.UniqueViolationError:
                pass # 忽略重复
            except Exception as e:
                logger.error(f"Batch insert error: {e}")
