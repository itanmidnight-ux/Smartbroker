"""
MetaTrader 5 data feed implementation.
Handles real-time data ingestion from MT5.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple
import time
import asyncio

from config.settings import settings
from config.constants import Timeframe, MT5_TIMEFRAMES
from data.models.market_data import OHLCV, TickData, SpreadData, SymbolInfo
from utils.logger import get_logger
from utils.helpers import timestamp_to_datetime

logger = get_logger(__name__)


class MT5Feed:
    """
    MetaTrader 5 data feed handler.
    Provides real-time and historical market data.
    """
    
    def __init__(self):
        self.connected = False
        self.symbols: List[str] = []
        self.last_tick_time: Dict[str, datetime] = {}
        self._rate_limit_delay = 0.1  # Seconds between requests
        
    async def connect(self) -> bool:
        """
        Initialize connection to MetaTrader 5.
        """
        try:
            # Initialize MT5
            if not mt5.initialize(
                login=settings.mt5_login,
                password=settings.mt5_password,
                server=settings.mt5_server,
                path=settings.mt5_path
            ):
                logger.error("MT5 initialization failed", error=mt5.last_error())
                return False
            
            self.connected = True
            logger.info("Connected to MetaTrader 5")
            
            # Get account info
            account_info = mt5.account_info()
            if account_info:
                logger.info(
                    "MT5 Account Info",
                    login=account_info.login,
                    server=account_info.server,
                    balance=account_info.balance,
                    equity=account_info.equity
                )
            
            return True
            
        except Exception as e:
            logger.error("Error connecting to MT5", error=str(e))
            return False
    
    def disconnect(self):
        """Disconnect from MT5."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MetaTrader 5")
    
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get symbol information."""
        if not self.connected:
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            return SymbolInfo(
                name=info.name,
                description=info.description,
                point=info.point,
                digits=info.digits,
                spread=info.spread,
                trade_contract_size=info.trade_contract_size,
                trade_tick_value=info.trade_tick_value,
                trade_tick_size=info.trade_tick_size,
                volume_min=info.volume_min,
                volume_max=info.volume_max,
                volume_step=info.volume_step
            )
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}", error=str(e))
            return None
    
    async def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        bars: int = 1000,
        start_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data from MT5.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Timeframe enum
            bars: Number of bars to retrieve
            start_date: Optional start date
        
        Returns:
            DataFrame with OHLCV data
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return pd.DataFrame()
        
        try:
            mt5_tf = MT5_TIMEFRAMES.get(timeframe)
            if mt5_tf is None:
                logger.error(f"Invalid timeframe: {timeframe}")
                return pd.DataFrame()
            
            # Ensure symbol is selected
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select symbol: {symbol}")
                return pd.DataFrame()
            
            if start_date:
                rates = mt5.copy_rates_from(
                    symbol,
                    mt5_tf,
                    start_date,
                    bars
                )
            else:
                rates = mt5.copy_rates_from_pos(
                    symbol,
                    mt5_tf,
                    0,
                    bars
                )
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
                'real_volume': 'real_volume'
            })
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df = df.set_index('timestamp')
            
            logger.debug(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data", error=str(e))
            return pd.DataFrame()
    
    async def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """
        Get latest tick data for a symbol.
        """
        if not self.connected:
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return TickData(
                timestamp=timestamp_to_datetime(tick.time),
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                last=(tick.bid + tick.ask) / 2,
                volume=tick.volume
            )
        except Exception as e:
            logger.error(f"Error getting tick for {symbol}", error=str(e))
            return None
    
    async def get_current_spread(self, symbol: str) -> Optional[SpreadData]:
        """
        Get current spread for a symbol.
        """
        if not self.connected:
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            symbol_info = await self.get_symbol_info(symbol)
            if symbol_info is None:
                return None
            
            spread_points = tick.ask - tick.bid
            spread_pips = spread_points / (symbol_info.point * 10)
            
            return SpreadData(
                timestamp=timestamp_to_datetime(tick.time),
                symbol=symbol,
                spread=spread_points,
                spread_pips=spread_pips
            )
        except Exception as e:
            logger.error(f"Error getting spread for {symbol}", error=str(e))
            return None
    
    async def stream_ticks(
        self,
        symbol: str,
        callback,
        duration_seconds: Optional[int] = None
    ):
        """
        Stream tick data for a symbol.
        
        Args:
            symbol: Trading symbol
            callback: Async function to call with each tick
            duration_seconds: How long to stream (None for indefinite)
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return
        
        try:
            # Ensure symbol is selected
            mt5.symbol_select(symbol, True)
            
            start_time = time.time()
            last_tick_time = None
            
            logger.info(f"Starting tick stream for {symbol}")
            
            while True:
                # Check duration limit
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break
                
                tick = await self.get_latest_tick(symbol)
                if tick:
                    # Avoid duplicate ticks
                    if last_tick_time != tick.timestamp:
                        await callback(tick)
                        last_tick_time = tick.timestamp
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in tick stream", error=str(e))
    
    async def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: List[Timeframe],
        bars: int = 100
    ) -> Dict[Timeframe, pd.DataFrame]:
        """
        Get OHLCV data for multiple timeframes.
        """
        results = {}
        
        for tf in timeframes:
            df = await self.get_historical_ohlcv(symbol, tf, bars)
            if not df.empty:
                results[tf] = df
        
        return results
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all available symbols."""
        if not self.connected:
            return []
        
        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                return []
            
            return [s.name for s in symbols if s.visible]
        except Exception as e:
            logger.error("Error getting symbols", error=str(e))
            return []
    
    async def wait_for_new_bar(
        self,
        symbol: str,
        timeframe: Timeframe,
        timeout_seconds: int = 90
    ) -> Optional[OHLCV]:
        """
        Wait for a new bar to form.
        """
        start_time = time.time()
        last_bar_time = None
        
        while time.time() - start_time < timeout_seconds:
            df = await self.get_historical_ohlcv(symbol, timeframe, bars=1)
            
            if df.empty:
                await asyncio.sleep(1)
                continue
            
            current_bar_time = df.index[-1]
            
            if last_bar_time is None:
                last_bar_time = current_bar_time
            elif current_bar_time != last_bar_time:
                # New bar detected
                bar = OHLCV(
                    timestamp=current_bar_time.to_pydatetime(),
                    open=df['open'].iloc[-1],
                    high=df['high'].iloc[-1],
                    low=df['low'].iloc[-1],
                    close=df['close'].iloc[-1],
                    volume=df['volume'].iloc[-1]
                )
                return bar
            
            await asyncio.sleep(1)
        
        return None


# Global feed instance
mt5_feed = MT5Feed()
