"""
Trading Bot ML - Simulador de Trading con Datos Reales
Simulación de operaciones con gestión de riesgo y estadísticas
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import json
import os

from trading_bot.config.settings import (
    SIMULATOR_CONFIG,
    OPERATION_MODES,
    TIMEFRAME_CONFIG,
    LOGS_DIR
)

logger = logging.getLogger(__name__)


class Trade:
    """Clase que representa una operación individual"""
    
    def __init__(self, symbol: str, direction: int, entry_price: float,
                 position_size: float, stop_loss: float, take_profit: float,
                 timeframe: str, timestamp: datetime):
        self.symbol = symbol
        self.direction = direction  # 1=LONG, -1=SHORT
        self.entry_price = entry_price
        self.position_size = position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.timeframe = timeframe
        self.open_time = timestamp
        self.close_time = None
        self.close_price = None
        self.close_reason = None  # 'TP', 'SL', 'MANUAL'
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.max_drawdown = 0.0
        self.max_profit = 0.0
        
    def update(self, current_price: float):
        """Actualizar PnL con precio actual"""
        if self.direction == 1:  # LONG
            self.pnl = (current_price - self.entry_price) * self.position_size
        else:  # SHORT
            self.pnl = (self.entry_price - current_price) * self.position_size
            
        self.pnl_pct = (self.pnl / (self.entry_price * self.position_size)) * 100
        
        # Track max profit y drawdown
        if self.pnl > self.max_profit:
            self.max_profit = self.pnl
        if -self.pnl > self.max_drawdown:
            self.max_drawdown = -self.pnl
    
    def close(self, price: float, reason: str = 'MANUAL'):
        """Cerrar la operación"""
        self.close_price = price
        self.close_time = datetime.now()
        self.close_reason = reason
        
        if self.direction == 1:
            self.pnl = (price - self.entry_price) * self.position_size
        else:
            self.pnl = (self.entry_price - price) * self.position_size
            
        self.pnl_pct = (self.pnl / (self.entry_price * self.position_size)) * 100
        
        return self.pnl
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        return {
            'symbol': self.symbol,
            'direction': 'LONG' if self.direction == 1 else 'SHORT',
            'entry_price': self.entry_price,
            'position_size': self.position_size,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'timeframe': self.timeframe,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'close_price': self.close_price,
            'close_reason': self.close_reason,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'max_profit': self.max_profit,
            'max_drawdown': self.max_drawdown,
            'status': 'OPEN' if self.close_time is None else 'CLOSED'
        }


class TradingSimulator:
    """Simulador de trading con datos reales"""
    
    def __init__(self, initial_balance: float = None):
        config = SIMULATOR_CONFIG
        self.initial_balance = initial_balance or config['initial_balance']
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.commission_pct = config['commission_pct']
        self.slippage_pct = config['slippage_pct']
        self.max_open_positions = config['max_open_positions']
        
        self.open_positions: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.daily_stats: Dict[str, Dict] = {}
        
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = self.initial_balance
        
        logger.info(f"Simulador inicializado con balance: ${self.initial_balance:,.2f}")
    
    def open_position(self, symbol: str, direction: int, entry_price: float,
                      position_size: float, atr: float, timeframe: str,
                      mode: str = 'normal') -> Optional[Trade]:
        """
        Abrir una posición
        
        Args:
            symbol: Símbolo del activo
            direction: 1 para LONG, -1 para SHORT
            entry_price: Precio de entrada
            position_size: Tamaño de la posición
            atr: ATR actual para calcular SL/TP
            timeframe: Timeframe de la operación
            mode: Modo de operación (safe, normal, aggressive, very_active)
            
        Returns:
            Trade object si se abrió, None si no
        """
        # Verificar límite de posiciones
        if len(self.open_positions) >= self.max_open_positions:
            logger.warning("Máximo de posiciones abiertas alcanzado")
            return None
        
        # Obtener configuración del modo
        mode_config = OPERATION_MODES.get(mode, OPERATION_MODES['normal'])
        tf_config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG['1h'])
        
        # Calcular SL y TP basados en ATR
        atr_multiplier_sl = tf_config['atr_multiplier_sl']
        atr_multiplier_tp = tf_config['atr_multiplier_tp']
        
        sl_distance = atr * atr_multiplier_sl
        tp_distance = atr * atr_multiplier_tp
        
        if direction == 1:  # LONG
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # SHORT
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Aplicar slippage
        if direction == 1:
            actual_entry = entry_price * (1 + self.slippage_pct)
        else:
            actual_entry = entry_price * (1 - self.slippage_pct)
        
        # Calcular comisión
        commission = actual_entry * position_size * self.commission_pct
        
        # Verificar si hay suficiente balance
        required_margin = actual_entry * position_size
        if required_margin + commission > self.balance:
            logger.warning("Balance insuficiente")
            return None
        
        # Crear trade
        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_price=actual_entry,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timeframe=timeframe,
            timestamp=datetime.now()
        )
        
        # Deducir comisión
        self.balance -= commission
        
        self.open_positions.append(trade)
        self.total_trades += 1
        
        logger.info(f"Posición abierta: {symbol} {'LONG' if direction==1 else 'SHORT'} @ {actual_entry:.4f}")
        
        return trade
    
    def update_positions(self, prices: Dict[str, float]):
        """
        Actualizar todas las posiciones abiertas con precios actuales
        
        Args:
            prices: Diccionario símbolo -> precio actual
        """
        positions_to_close = []
        
        for trade in self.open_positions:
            if trade.symbol not in prices:
                continue
                
            current_price = prices[trade.symbol]
            
            # Actualizar PnL
            trade.update(current_price)
            
            # Track max drawdown global
            current_equity = self.balance + sum(t.pnl for t in self.open_positions)
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
            
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
            
            # Verificar SL
            if trade.direction == 1 and current_price <= trade.stop_loss:
                positions_to_close.append((trade, current_price, 'SL'))
            elif trade.direction == -1 and current_price >= trade.stop_loss:
                positions_to_close.append((trade, current_price, 'SL'))
            
            # Verificar TP
            if trade.direction == 1 and current_price >= trade.take_profit:
                positions_to_close.append((trade, current_price, 'TP'))
            elif trade.direction == -1 and current_price <= trade.take_profit:
                positions_to_close.append((trade, current_price, 'TP'))
        
        # Cerrar posiciones
        for trade, price, reason in positions_to_close:
            self._close_position(trade, price, reason)
        
        # Actualizar equity
        self.equity = self.balance + sum(t.pnl for t in self.open_positions)
        
        # Registrar en curva de equity
        self.equity_curve.append({
            'timestamp': datetime.now().isoformat(),
            'equity': self.equity,
            'balance': self.balance,
            'open_pnl': sum(t.pnl for t in self.open_positions),
            'open_positions': len(self.open_positions)
        })
        
        # Mantener solo últimos 10000 puntos
        if len(self.equity_curve) > 10000:
            self.equity_curve = self.equity_curve[-10000:]
    
    def _close_position(self, trade: Trade, price: float, reason: str):
        """Cerrar una posición específica"""
        pnl = trade.close(price, reason)
        
        # Calcular comisión de cierre
        commission = price * trade.position_size * self.commission_pct
        pnl -= commission
        
        # Actualizar balance
        self.balance += pnl
        
        # Mover a cerradas
        self.open_positions.remove(trade)
        self.closed_trades.append(trade)
        
        # Actualizar estadísticas
        self.total_pnl += pnl
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        logger.info(f"Posición cerrada: {trade.symbol} {reason} PnL: ${pnl:,.2f}")
    
    def close_all_positions(self, prices: Dict[str, float]):
        """Cerrar todas las posiciones"""
        for trade in self.open_positions[:]:  # Copia para iterar
            if trade.symbol in prices:
                self._close_position(trade, prices[trade.symbol], 'MANUAL')
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas completas del simulador"""
        total_closed = len(self.closed_trades)
        win_rate = self.winning_trades / max(1, total_closed) * 100
        
        # Calcular profit factor
        gross_profit = sum(t.pnl for t in self.closed_trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.closed_trades if t.pnl < 0))
        profit_factor = gross_profit / max(1, gross_loss)
        
        # Calcular average win/loss
        avg_win = gross_profit / max(1, self.winning_trades)
        avg_loss = gross_loss / max(1, self.losing_trades)
        
        # Sharpe ratio simplificado (anualizado)
        if len(self.equity_curve) > 10:
            returns = pd.Series([e['equity'] for e in self.equity_curve]).pct_change()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 24) if returns.std() > 0 else 0
        else:
            sharpe = 0
        
        # Mejor y peor trade
        best_trade = max((t.pnl for t in self.closed_trades), default=0)
        worst_trade = min((t.pnl for t in self.closed_trades), default=0)
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for trade in self.closed_trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        stats = {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance,
            'current_equity': self.equity,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': (self.total_pnl / self.initial_balance) * 100,
            'total_trades': total_closed,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'expectancy': (win_rate/100 * avg_win) - ((1-win_rate/100) * avg_loss),
            'sharpe_ratio': sharpe,
            'max_drawdown': self.max_drawdown * 100,
            'max_drawdown_amount': self.peak_equity - self.equity,
            'peak_equity': self.peak_equity,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'open_positions': len(self.open_positions),
            'total_trades_opened': self.total_trades
        }
        
        return stats
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Obtener últimas operaciones"""
        recent = self.closed_trades[-limit:]
        return [t.to_dict() for t in reversed(recent)]
    
    def get_open_positions(self) -> List[Dict]:
        """Obtener posiciones abiertas"""
        return [t.to_dict() for t in self.open_positions]
    
    def get_equity_curve(self, points: int = 1000) -> List[Dict]:
        """Obtener curva de equity"""
        if len(self.equity_curve) <= points:
            return self.equity_curve
        
        step = len(self.equity_curve) // points
        return self.equity_curve[::step]
    
    def reset(self):
        """Reiniciar simulador"""
        self.__init__(self.initial_balance)
        logger.info("Simulador reiniciado")
    
    def save_results(self, filename: str = None):
        """Guardar resultados en archivo"""
        if filename is None:
            filename = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(LOGS_DIR, filename)
        
        results = {
            'statistics': self.get_statistics(),
            'trades': [t.to_dict() for t in self.closed_trades],
            'open_positions': self.get_open_positions(),
            'equity_curve': self.get_equity_curve()
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Resultados guardados en {filepath}")
        return filepath


class Backtester:
    """Backtester para evaluar estrategias con datos históricos"""
    
    def __init__(self, simulator: TradingSimulator = None):
        self.simulator = simulator or TradingSimulator()
        self.results = None
        
    def run(self, df: pd.DataFrame, signals: pd.Series, 
            symbol: str = 'TEST', timeframe: str = '1h',
            mode: str = 'normal') -> Dict:
        """
        Ejecutar backtest
        
        Args:
            df: DataFrame con datos OHLCV e indicadores
            signals: Serie con señales (1=BUY, -1=SELL, 0=HOLD)
            symbol: Símbolo del activo
            timeframe: Timeframe
            mode: Modo de operación
            
        Returns:
            Diccionario con resultados del backtest
        """
        logger.info(f"Iniciando backtest: {len(df)} velas")
        
        # Reiniciar simulador
        self.simulator.reset()
        
        # Iterar sobre datos
        for idx in range(len(df)):
            if idx < 50:  # Esperar a tener suficientes datos para indicadores
                continue
            
            row = df.iloc[idx]
            signal = signals.iloc[idx] if isinstance(signals, pd.Series) else 0
            
            # Actualizar precios
            prices = {symbol: row['Close']}
            self.simulator.update_positions(prices)
            
            # Si hay señal y no hay posiciones abiertas
            if signal != 0 and len(self.simulator.open_positions) == 0:
                atr = row.get('atr', row['Close'] * 0.02)
                
                self.simulator.open_position(
                    symbol=symbol,
                    direction=signal,
                    entry_price=row['Close'],
                    position_size=self.simulator.balance * 0.1 / row['Close'],  # 10% del balance
                    atr=atr,
                    timeframe=timeframe,
                    mode=mode
                )
        
        # Cerrar todas las posiciones al final
        if self.simulator.open_positions:
            last_price = df.iloc[-1]['Close']
            self.simulator.close_all_positions({symbol: last_price})
        
        # Obtener resultados
        self.results = self.simulator.get_statistics()
        self.results['backtest_complete'] = True
        self.results['bars_tested'] = len(df)
        
        logger.info(f"Backtest completado. Win Rate: {self.results['win_rate']:.2f}%")
        
        return self.results
