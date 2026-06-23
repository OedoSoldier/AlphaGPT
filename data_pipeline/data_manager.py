import asyncio
from datetime import date, datetime, timedelta
from loguru import logger
from .config import Config
from .db_manager import DBManager
from .providers.tushare import TushareProvider

class DataManager:
    def __init__(self, provider=None):
        self.db = DBManager()
        self.provider = provider or TushareProvider()
        
    async def initialize(self):
        await self.db.connect()
        await self.db.init_schema()

    async def close(self):
        await self.db.close()

    async def pipeline_sync_daily(self):
        logger.info("Step 1: Loading A-share universe from Tushare...")
        limit = Config.TUSHARE_UNIVERSE_LIMIT or None
        universe = await asyncio.to_thread(self.provider.get_stock_universe, limit)

        if universe.empty:
            logger.warning("No securities passed the universe filters.")
            return

        security_records = self.provider.securities_to_records(universe)
        await self.db.upsert_securities(security_records)
        logger.info(f"Universe ready: {len(security_records)} securities.")

        ts_codes = universe["ts_code"].tolist()
        latest_map = {}
        if Config.TUSHARE_INCREMENTAL:
            latest_map = await self.db.get_latest_trade_dates(ts_codes)

        end_date = Config.TUSHARE_END_DATE or date.today().strftime("%Y%m%d")
        total_bars = 0
        skipped = 0

        logger.info(f"Step 2: Syncing daily bars through {end_date}...")
        for idx, ts_code in enumerate(ts_codes, start=1):
            start_date = self._start_date_for(ts_code, latest_map)
            if start_date > end_date:
                skipped += 1
                continue

            bars = await asyncio.to_thread(
                self.provider.fetch_daily_bars,
                ts_code,
                start_date,
                end_date,
            )
            records = self.provider.daily_bars_to_records(bars)
            if records:
                await self.db.batch_upsert_daily_bars(records)
                total_bars += len(records)

            if idx % 20 == 0 or idx == len(ts_codes):
                logger.info(
                    f"Processed {idx}/{len(ts_codes)} securities. "
                    f"Inserted/updated {total_bars} bars. Skipped {skipped}."
                )

            if Config.TUSHARE_REQUEST_INTERVAL_SECONDS > 0:
                await asyncio.sleep(Config.TUSHARE_REQUEST_INTERVAL_SECONDS)

        logger.success(f"Pipeline complete. Daily bars inserted/updated: {total_bars}")

    @staticmethod
    def _start_date_for(ts_code, latest_map):
        latest = latest_map.get(ts_code)
        if not latest:
            return Config.TUSHARE_START_DATE

        if isinstance(latest, datetime):
            latest_date = latest.date()
        else:
            latest_date = latest
        next_date = latest_date + timedelta(days=1)
        configured = datetime.strptime(Config.TUSHARE_START_DATE, "%Y%m%d").date()
        if next_date < configured:
            next_date = configured
        return next_date.strftime("%Y%m%d")
