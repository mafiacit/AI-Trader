# AI-Powered Trading Bot

A sophisticated trading bot that analyzes multiple asset classes (forex, crypto, commodities) using AI-powered market analysis.

## Features

- Multi-asset trading support (forex, crypto, commodities)
- AI-powered market analysis using Groq AI
- Web interface for trade management
- Telegram bot interface for remote trading
- Technical indicators (RSI, MACD, etc.)
- Admin-only access control for Telegram bot
- Simulated trading with virtual balance

## Supported Assets

- **Forex**: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD
- **Commodities**: Gold (XAU/USD)
- **Cryptocurrencies**: Bitcoin (BTC/USD), Ethereum (ETH/USD)

## Setup Instructions

1. Clone the repository
2. Copy `.env.sample` to `.env` and fill in your API keys and configuration
3. Install dependencies with `pip install -r requirements.txt`
4. Run the web application with `python main.py`

## Telegram Bot Configuration

The Telegram bot provides remote access to trading functionality but requires proper security configuration.

### Admin-Only Access

For security reasons, the Telegram bot is configured with admin-only access mode. Only users explicitly listed in the `TELEGRAM_ADMIN_USERS` environment variable can use the bot's trading and analysis commands.

To configure admin access:

1. Find your Telegram username (without the @ symbol) or your numeric Telegram user ID
2. Add these to the `.env` file as comma-separated values (no spaces):
   ```
   TELEGRAM_ADMIN_USERS=username1,123456789,username2
   ```
3. Both usernames and numeric IDs are supported
4. Restart the bot for changes to take effect

### Available Commands

- `/start` - Displays welcome message (available to all users)
- `/help` - Shows available commands (available to all users)
- `/analyze [pair]` - Analyze a currency pair (admin only)
- `/trade` - Show trading menu (admin only)
- `/status` - Check open trades (admin only)
- `/buy [amount]` - Execute a buy trade (admin only)
- `/sell [amount]` - Execute a sell trade (admin only)
- `/autotrade [amount]` - Let AI decide whether to buy/sell (admin only)
- `/close [trade_id]` - Close a specific trade (admin only)

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| GROQ_API_KEY | Groq API key for AI analysis |
| TELEGRAM_TOKEN | Telegram Bot token |
| TELEGRAM_ADMIN_USERS | Comma-separated list of admin usernames/IDs |
| SECRET_KEY | Flask secret key |
| LOG_LEVEL | Logging level (INFO, DEBUG, etc.) |

## Architecture

The application is built with Flask and uses SQLAlchemy for database operations. The system consists of several modules:

- `main.py` - Application entry point
- `app.py` - Flask web application
- `models.py` - Database models
- `market_analysis.py` - Market data and analysis logic
- `groq_ai.py` - AI integration with Groq API
- `trading_bot.py` - Core trading logic
- `telegram_bot_simple.py` - Telegram bot interface

## Security Features

The bot implements several security features to protect trading functionality:

1. **Admin-only access**: Only authorized administrators can access trading commands
2. **Encrypted storage**: User passwords are securely hashed
3. **Environment separation**: Sensitive credentials are stored in environment variables
4. **Rate limiting**: API calls are rate-limited to prevent abuse