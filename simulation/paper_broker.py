"""
Paper Trading Simulation Engine.
Simulates realistic trading with spread, slippage, and latency.
"""
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from enum import Enum
import numpy as np

from config.settings import settings
from config.constants import OrderType, OrderStatus, TradeDirection
from strategies.base_strategy import Signal
from utils.logger import get_logger
from utils.helpers import calculate_profit_loss, add_noise

logger = get_logger(__name__)


class Trade:
    """Represents a simulated trade."""
    
    def __init__(
        self,
        trade_id: str,
        symbol: str,
        direction: TradeDirection,
        entry_price: float,
        lots: float,
        timestamp: datetime,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: str = "",
    ):
        self.trade_id = trade_id
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.lots = lots
        self.timestamp = timestamp
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy = strategy
        
        self.status = OrderStatus.OPEN
        self.exit_price: Optional[float] = None
        self.exit_timestamp: Optional[datetime] = None
        self.profit_loss: float = 0.0
        self.profit_loss_pips: float = 0.0
        self.max_drawdown: float = 0.0
        self.max_profit: float = 0.0
    
    def update_price(self, price: float):
        """Update trade with current price (for tracking max DD/profit)."""
        if self.direction == TradeDirection.LONG:
            unrealized_pnl = (price - self.entry_price) * self.lots * 100000
        else:
            unrealized_pnl = (self.entry_price - price) * self.lots * 100000
        
        self.max_profit = max(self.max_profit, unrealized_pnl)
        self.max_drawdown = min(self.max_drawdown, unrealized_pnl)
    
    def close(
        self,
        exit_price: float,
        timestamp: datetime,
        reason: str = ""
    ) -> float:
        """Close the trade and calculate P&L."""
        self.exit_price = exit_price
        self.exit_timestamp = timestamp
        self.status = OrderStatus.CLOSED
        
        # Calculate profit/loss
        if self.direction == TradeDirection.LONG:
            self.profit_loss = (exit_price - self.entry_price) * self.lots * 100000
            self.profit_loss_pips = (exit_price - self.entry_price) * 10000
        else:
            self.profit_loss = (self.entry_price - exit_price) * self.lots * 100000
            self.profit_loss_pips = (self.entry_price - exit_price) * 10000
        
        return self.profit_loss
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary."""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'lots': self.lots,
            'timestamp': self.timestamp.isoformat(),
            'exit_timestamp': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit_loss': self.profit_loss,
            'profit_loss_pips': self.profit_loss_pips,
            'max_drawdown': self.max_drawdown,
            'max_profit': self.max_profit,
            'status': self.status.value,
            'strategy': self.strategy,
        }


class PaperBroker:
    """
    Paper trading broker simulation.
    Simulates realistic trading conditions including spread, slippage, and latency.
    """
    
    def __init__(
        self,
        initial_balance: float = None,
        simulate_slippage: bool = None,
        slippage_pips: float = None,
        simulate_latency_ms: int = None,
    ):
        self.initial_balance = initial_balance or settings.initial_balance
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        
        self.simulate_slippage = simulate_slippage if simulate_slippage is not None else settings.simulate_slippage
        self.slippage_pips = slippage_pips if slippage_pips is not None else settings.slippage_pips
        self.simulate_latency_ms = simulate_latency_ms if simulate_latency_ms is not None else settings.simulate_latency_ms
        
        self.open_trades: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.trade_counter = 0
        
        # Performance metrics
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Drawdown tracking
        self.peak_equity = self.initial_balance
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
    
    def execute_signal(
        self,
        signal: Signal,
        current_bid: float,
        current_ask: float,
        position_size: Optional[float] = None
    ) -> Optional[Trade]:
        """
        Execute a trading signal.
        
        Args:
            signal: Trading signal
            current_bid: Current bid price
            current_ask: Current ask price
            position_size: Optional position size (lots)
        
        Returns:
            Trade object if executed, None otherwise
        """
        if not signal.is_valid:
            logger.warning("Invalid signal", signal=signal)
            return None
        
        # Check max open trades
        if len(self.open_trades) >= settings.max_open_trades:
            logger.warning("Max open trades reached")
            return None
        
        # Determine direction and execution price
        if signal.direction == OrderType.BUY:
            direction = TradeDirection.LONG
            base_price = current_ask  # Buy at ask
        else:
            direction = TradeDirection.SHORT
            base_price = current_bid  # Sell at bid
        
        # Apply slippage simulation
        if self.simulate_slippage:
            slippage = add_noise(0, self.slippage_pips / 10000)
            if direction == TradeDirection.LONG:
                execution_price = base_price + slippage
            else:
                execution_price = base_price - slippage
        else:
            execution_price = base_price
        
        # Calculate position size if not provided
        if position_size is None:
            position_size = self._calculate_position_size(signal)
        
        # Create trade
        self.trade_counter += 1
        trade_id = f"TRD-{self.trade_counter:06d}"
        
        trade = Trade(
            trade_id=trade_id,
            symbol=signal.symbol,
            direction=direction,
            entry_price=execution_price,
            lots=position_size,
            timestamp=datetime.now(timezone.utc),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy,
        )
        
        self.open_trades[trade_id] = trade
        
        logger.info(
            f"Trade opened: {trade_id}",
            symbol=signal.symbol,
            direction=direction.value,
            entry_price=execution_price,
            lots=position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        
        return trade
    
    def update_trades(self, current_bid: float, current_ask: float, symbol: str):
        """
        Update all open trades with current prices.
        Check for stop loss and take profit hits.
        """
        trades_to_close = []
        
        for trade_id, trade in self.open_trades.items():
            if trade.symbol != symbol:
                continue
            
            # Update trade with current price
            if trade.direction == TradeDirection.LONG:
                current_price = current_bid
            else:
                current_price = current_ask
            
            trade.update_price(current_price)
            
            # Check stop loss
            if trade.stop_loss:
                if trade.direction == TradeDirection.LONG and current_price <= trade.stop_loss:
                    trades_to_close.append((trade_id, current_price, "STOP_LOSS"))
                    continue
                
                if trade.direction == TradeDirection.SHORT and current_price >= trade.stop_loss:
                    trades_to_close.append((trade_id, current_price, "STOP_LOSS"))
                    continue
            
            # Check take profit
            if trade.take_profit:
                if trade.direction == TradeDirection.LONG and current_price >= trade.take_profit:
                    trades_to_close.append((trade_id, current_price, "TAKE_PROFIT"))
                    continue
                
                if trade.direction == TradeDirection.SHORT and current_price <= trade.take_profit:
                    trades_to_close.append((trade_id, current_price, "TAKE_PROFIT"))
                    continue
        
        # Close trades
        for trade_id, exit_price, reason in trades_to_close:
            self.close_trade(trade_id, exit_price, reason)
        
        # Update equity
        self._update_equity(current_bid, current_ask)
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "MANUAL"
    ) -> float:
        """Close a specific trade."""
        if trade_id not in self.open_trades:
            logger.warning(f"Trade not found: {trade_id}")
            return 0.0
        
        trade = self.open_trades[trade_id]
        
        # Apply slippage on exit
        if self.simulate_slippage:
            slippage = add_noise(0, self.slippage_pips / 10000)
            if trade.direction == TradeDirection.LONG:
                exit_price -= slippage  # Sell at slightly worse price
            else:
                exit_price += slippage
        
        # Close trade
        pnl = trade.close(exit_price, datetime.now(timezone.utc), reason)
        
        # Update balance
        self.balance += pnl
        
        # Move to closed trades
        del self.open_trades[trade_id]
        self.closed_trades.append(trade)
        
        # Update metrics
        if pnl > 0:
            self.total_profit += pnl
            self.winning_trades += 1
        else:
            self.total_loss += abs(pnl)
            self.losing_trades += 1
        
        logger.info(
            f"Trade closed: {trade_id}",
            exit_price=exit_price,
            pnl=pnl,
            reason=reason,
        )
        
        return pnl
    
    def _calculate_position_size(self, signal: Signal) -> float:
        """Calculate position size based on risk parameters."""
        risk_amount = self.balance * (settings.risk_per_trade_pct / 100)
        
        if signal.stop_loss and signal.entry_price:
            risk_pips = abs(signal.entry_price - signal.stop_loss) * 10000
            if risk_pips > 0:
                lot_size = risk_amount / (risk_pips * 10)  # $10 per pip per standard lot
                return max(0.01, round(lot_size, 2))
        
        return settings.default_lot_size
    
    def _update_equity(self, current_bid: float, current_ask: float):
        """Update equity based on open trades."""
        unrealized_pnl = 0.0
        
        for trade in self.open_trades.values():
            if trade.direction == TradeDirection.LONG:
                price = current_bid
            else:
                price = current_ask
            
            if trade.direction == TradeDirection.LONG:
                unrealized_pnl += (price - trade.entry_price) * trade.lots * 100000
            else:
                unrealized_pnl += (trade.entry_price - price) * trade.lots * 100000
        
        self.equity = self.balance + unrealized_pnl
        
        # Update drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        self.current_drawdown = (self.peak_equity - self.equity) / self.peak_equity
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics."""
        total_trades = self.winning_trades + self.losing_trades
        
        winrate = self.winning_trades / max(total_trades, 1)
        profit_factor = self.total_profit / max(self.total_loss, 1)
        avg_win = self.total_profit / max(self.winning_trades, 1)
        avg_loss = self.total_loss / max(self.losing_trades, 1)
        
        return {
            'balance': self.balance,
            'equity': self.equity,
            'total_return': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'winrate': winrate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'current_drawdown': self.current_drawdown * 100,
            'max_drawdown': self.max_drawdown * 100,
            'open_trades': len(self.open_trades),
        }
    
    def get_open_trades(self) -> List[Dict]:
        """Get list of open trades."""
        return [trade.to_dict() for trade in self.open_trades.values()]
    
    def get_closed_trades(self, limit: int = 100) -> List[Dict]:
        """Get list of closed trades."""
        return [trade.to_dict() for trade in self.closed_trades[-limit:]]
