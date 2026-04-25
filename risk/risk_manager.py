"""
Risk Management System.
Handles position sizing, drawdown protection, and kill switch.
"""
from datetime import datetime, timezone
from typing import Dict, Optional, List
import numpy as np

from config.settings import settings
from config.constants import MAX_DRAWDOWN_THRESHOLD, KILL_SWITCH_DRAWDOWN
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    Comprehensive risk management system.
    """
    
    def __init__(
        self,
        max_drawdown_pct: float = None,
        kill_switch_dd: float = None,
        max_position_size: float = None,
        risk_per_trade: float = None,
        max_open_trades: int = None,
    ):
        # Configuration
        self.max_drawdown_pct = max_drawdown_pct or settings.max_drawdown_pct
        self.kill_switch_dd = kill_switch_dd or KILL_SWITCH_DRAWDOWN
        self.max_position_size = max_position_size or settings.max_position_size
        self.risk_per_trade = risk_per_trade or settings.risk_per_trade_pct
        self.max_open_trades = max_open_trades or settings.max_open_trades
        
        # State
        self.is_active = True
        self.kill_switch_triggered = False
        self.kill_switch_reason: Optional[str] = None
        
        # Tracking
        self.peak_equity = settings.initial_balance
        self.current_equity = settings.initial_balance
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        
        # Daily limits
        self.daily_loss_limit = settings.initial_balance * 0.03  # 3% daily loss limit
        self.daily_profit_target = settings.initial_balance * 0.05  # 5% daily profit target
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now(timezone.utc).date()
        
        # Consecutive losses
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5
        self.consecutive_wins = 0
        
        # Trade frequency limits
        self.trades_today = 0
        self.max_trades_per_day = 20
    
    def check_kill_switch(self, equity: float) -> bool:
        """
        Check if kill switch should be triggered.
        
        Args:
            equity: Current account equity
        
        Returns:
            True if trading should stop
        """
        # Update peak and drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        self.current_equity = equity
        self.current_drawdown = (self.peak_equity - equity) / self.peak_equity
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        # Check reset date for daily metrics
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset_date:
            self._reset_daily_metrics()
        
        # Kill switch conditions
        reasons = []
        
        # 1. Max drawdown exceeded
        if self.current_drawdown >= self.kill_switch_dd:
            reasons.append(f"Max drawdown exceeded: {self.current_drawdown*100:.2f}%")
        
        # 2. Daily loss limit hit
        if self.daily_pnl <= -self.daily_loss_limit:
            reasons.append(f"Daily loss limit hit: ${self.daily_pnl:.2f}")
        
        # 3. Too many consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            reasons.append(f"Too many consecutive losses: {self.consecutive_losses}")
        
        # 4. Max trades per day exceeded
        if self.trades_today >= self.max_trades_per_day:
            reasons.append(f"Max trades per day exceeded: {self.trades_today}")
        
        if reasons:
            self.kill_switch_triggered = True
            self.kill_switch_reason = "; ".join(reasons)
            self.is_active = False
            
            logger.warning(
                "KILL SWITCH TRIGGERED",
                reasons=reasons,
                drawdown=self.current_drawdown * 100,
                daily_pnl=self.daily_pnl,
            )
            
            return True
        
        return False
    
    def can_open_trade(
        self,
        current_open_trades: int,
        signal_score: float,
        min_score: float = 60
    ) -> tuple[bool, str]:
        """
        Check if a new trade can be opened.
        
        Args:
            current_open_trades: Number of currently open trades
            signal_score: Score of the trading signal
            min_score: Minimum acceptable score
        
        Returns:
            Tuple of (can_open, reason)
        """
        # Check if system is active
        if not self.is_active:
            return False, "System inactive"
        
        # Check kill switch
        if self.kill_switch_triggered:
            return False, f"Kill switch triggered: {self.kill_switch_reason}"
        
        # Check max open trades
        if current_open_trades >= self.max_open_trades:
            return False, f"Max open trades reached: {current_open_trades}"
        
        # Check signal score
        if signal_score < min_score:
            return False, f"Signal score too low: {signal_score} < {min_score}"
        
        # Check daily trade limit
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached: {self.trades_today}"
        
        # Check reduced activity after losses
        if self.consecutive_losses >= 3:
            if signal_score < 80:  # Require higher confidence
                return False, "Reduced activity after losses - need higher confidence"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss: Optional[float],
        symbol: str = ""
    ) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            balance: Account balance
            entry_price: Entry price
            stop_loss: Stop loss price
            symbol: Trading symbol
        
        Returns:
            Position size in lots
        """
        # Base risk amount
        risk_amount = balance * (self.risk_per_trade / 100)
        
        # Reduce position size after losses
        if self.consecutive_losses >= 2:
            risk_amount *= 0.75  # Reduce by 25%
        if self.consecutive_losses >= 4:
            risk_amount *= 0.5  # Reduce by 50%
        
        # Increase position size after wins (cautiously)
        if self.consecutive_wins >= 3:
            risk_amount *= 1.1  # Increase by 10%
        
        # Calculate position size based on stop loss distance
        if stop_loss and entry_price:
            risk_pips = abs(entry_price - stop_loss) * 10000
            
            if risk_pips > 0:
                # $10 per pip per standard lot
                lot_size = risk_amount / (risk_pips * 10)
            else:
                lot_size = settings.default_lot_size
        else:
            # No stop loss - use minimum size
            lot_size = settings.default_lot_size * 0.5
        
        # Apply maximum position size
        lot_size = min(lot_size, self.max_position_size)
        
        # Ensure minimum
        lot_size = max(lot_size, 0.01)
        
        # Round to 2 decimal places
        lot_size = round(lot_size, 2)
        
        return lot_size
    
    def record_trade_result(
        self,
        profit_loss: float,
        is_winner: bool
    ):
        """
        Record the result of a closed trade.
        
        Args:
            profit_loss: P&L of the trade
            is_winner: Whether the trade was profitable
        """
        # Update daily PnL
        self.daily_pnl += profit_loss
        
        # Update consecutive wins/losses
        if is_winner:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Increment trade count
        self.trades_today += 1
        
        logger.debug(
            "Trade result recorded",
            pnl=profit_loss,
            is_winner=is_winner,
            consecutive_losses=self.consecutive_losses,
            daily_pnl=self.daily_pnl,
        )
    
    def _reset_daily_metrics(self):
        """Reset daily tracking metrics."""
        logger.info("Resetting daily metrics")
        
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
    
    def reset_kill_switch(self):
        """Manually reset the kill switch."""
        logger.info("Kill switch manually reset")
        self.kill_switch_triggered = False
        self.kill_switch_reason = None
        self.is_active = True
    
    def get_risk_status(self) -> Dict:
        """Get current risk status."""
        return {
            'is_active': self.is_active,
            'kill_switch_triggered': self.kill_switch_triggered,
            'kill_switch_reason': self.kill_switch_reason,
            'current_drawdown': self.current_drawdown * 100,
            'max_drawdown': self.max_drawdown * 100,
            'daily_pnl': self.daily_pnl,
            'trades_today': self.trades_today,
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
        }
    
    def get_dynamic_parameters(self) -> Dict:
        """Get dynamically adjusted risk parameters."""
        # Adjust parameters based on recent performance
        risk_mult = 1.0
        
        if self.consecutive_losses >= 3:
            risk_mult = 0.5
        elif self.consecutive_losses >= 2:
            risk_mult = 0.75
        elif self.consecutive_wins >= 3:
            risk_mult = 1.1
        
        return {
            'risk_per_trade': self.risk_per_trade * risk_mult,
            'max_position_size': self.max_position_size * risk_mult,
            'effective_max_trades': max(1, self.max_open_trades - self.consecutive_losses),
        }
