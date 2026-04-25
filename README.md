# SmartBroker Trading System

A production-grade autonomous trading intelligence platform with machine learning capabilities.

## Features

- **Real-time Market Data**: Connects to MetaTrader 5 for live price feeds
- **Multi-Strategy System**: Runs trend following, mean reversion, and breakout strategies in parallel
- **Confluence-Based Scoring**: Signals are scored 0-100 based on indicator agreement
- **Paper Trading**: Realistic simulation with spread, slippage, and latency
- **Machine Learning**: Market regime classification and adaptive parameter tuning
- **Risk Management**: Drawdown protection, kill switch, dynamic position sizing
- **FastAPI Backend**: RESTful API for monitoring and control

## Architecture

```
app/                    # Main application
config/                 # Configuration and settings
data/
    feeds/              # Market data feeds (MT5)
    models/             # Data models
    processors/         # Feature engineering
strategies/             # Trading strategies
indicators/             # Technical indicators
engine/                 # Signal and scoring engines
simulation/             # Paper trading simulation
ml/                     # Machine learning models
optimization/           # Parameter optimization
risk/                   # Risk management
database/               # Database models
api/                    # FastAPI routes
utils/                  # Utilities and helpers
```

## Installation

### Prerequisites

- Python 3.11+
- MetaTrader 5 (optional, for live data)
- PostgreSQL (optional, defaults to SQLite)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file:

```env
# MT5 Connection (optional)
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=sqlite+aiosqlite:///./trading.db

# Trading Settings
INITIAL_BALANCE=10000.0
DEFAULT_SYMBOL=EURUSD
MAX_DRAWDOWN_PCT=5.0
```

## Running the System

### Start the API Server

```bash
cd app
python main.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint |
| `/api/status` | GET | System status |
| `/api/signals` | GET | Recent trading signals |
| `/api/trades` | GET | Trade history |
| `/api/performance` | GET | Performance metrics |
| `/api/risk-status` | GET | Risk management status |
| `/api/strategies` | GET | Strategy information |
| `/api/start` | POST | Start trading loop |
| `/api/stop` | POST | Stop trading loop |
| `/api/control/reset-kill-switch` | POST | Reset kill switch |

## Strategies

### Trend Following
- Uses MA alignment, ADX, MACD, RSI, and Ichimoku
- Enters trades in direction of established trend
- Best performance in trending markets

### Mean Reversion
- Trades oversold/overbought conditions
- Uses RSI, Bollinger Bands, Stochastic
- Best performance in ranging markets

### Breakout
- Detects consolidation breakouts with volume confirmation
- Uses support/resistance levels, ADX, volume analysis
- Best performance during volatility expansion

## Risk Management

- **Max Drawdown**: Stops trading at 10% drawdown
- **Daily Loss Limit**: 3% daily loss limit
- **Position Sizing**: Dynamic based on risk per trade
- **Kill Switch**: Automatic halt on adverse conditions
- **Consecutive Loss Protection**: Reduces size after losses

## Machine Learning

The system includes:

1. **Market Regime Classifier** (LightGBM)
   - Classifies: TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOLATILITY, LOW_VOLATILITY
   - Retrains periodically with new data

2. **Adaptive Parameter Tuning**
   - Adjusts strategy parameters based on performance
   - Tracks optimal parameters per market condition

## Monitoring

View logs in the `logs/` directory or stream via API:

```bash
curl http://localhost:8000/api/info
```

## Development

### Add a New Strategy

1. Create a new file in `strategies/`
2. Inherit from `BaseStrategy`
3. Implement `generate_signal()` method
4. Register in `SignalEngine`

### Add a New Indicator

1. Create function in `indicators/technical_indicators.py`
2. Add to `calculate_all_indicators()`
3. Include in feature engineering pipeline

## Disclaimer

This system is for educational and research purposes. Paper trading results do not guarantee future performance. Always test thoroughly before considering live deployment.

## License

MIT License
