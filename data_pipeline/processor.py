import pandas as pd
import numpy as np
from loguru import logger

class DataProcessor:
    @staticmethod
    def clean_daily_bars(df):
        if df.empty:
            return df

        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')
        
        df = df.sort_values(['ts_code', 'trade_date'])
        df['close'] = df['close'].ffill()
        df['open'] = df['open'].fillna(df['close'])
        df['high'] = df['high'].fillna(df['close'])
        df['low'] = df['low'].fillna(df['close'])
        df['volume'] = df['volume'].fillna(0)
        df['amount'] = df['amount'].fillna(0)
        
        df = df[df['close'] > 0]
        
        return df

    @staticmethod
    def clean_ohlcv(df):
        return DataProcessor.clean_daily_bars(
            df.rename(columns={'time': 'trade_date', 'address': 'ts_code'})
        )

    @staticmethod
    def add_basic_factors(df):
        # Log Returns
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        
        # Realized Volatility
        df['volatility'] = df['log_ret'].rolling(window=20).std()
        
        # Volume Shock
        vol_ma = df['volume'].rolling(window=20).mean() + 1e-6
        df['vol_shock'] = df['volume'] / vol_ma
        
        # Price Trend
        ma_long = df['close'].rolling(window=60).mean()
        df['trend'] = np.where(df['close'] > ma_long, 1, -1)
        
        # Robust Normalization
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        return df
