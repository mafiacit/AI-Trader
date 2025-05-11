import os
import logging
import market_analysis
import trading_bot
from datetime import datetime
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get bot token and admin users from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USERS = os.environ.get("TELEGRAM_ADMIN_USERS", "").split(",")
# Get the web app URL from environment variables
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://trading-bot.replit.app")

if not TELEGRAM_TOKEN:
    logger.warning("No TELEGRAM_TOKEN found in environment variables. Bot will not work without it.")
    
if not ADMIN_USERS or ADMIN_USERS[0] == "":
    logger.warning("No TELEGRAM_ADMIN_USERS defined. Bot access will be restricted to admins only, but no admins are configured.")

# Trading bot instance
bot = trading_bot.TradingBot()

# Admin check decorator
def admin_only(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user = update.effective_user
        user_id = str(user.id) if user and user.id else "unknown"
        username = user.username if user and user.username else "unknown"
        
        # Store user info in context if not already there
        if 'is_admin' not in context.user_data:
            context.user_data['is_admin'] = user_id in ADMIN_USERS or username in ADMIN_USERS
            # Log the access
            if context.user_data['is_admin']:
                logger.info(f"Admin access granted to user {user_id} ({username})")
                # Try to store in database
                try:
                    from app import db
                    from models import TelegramChat, User
                    
                    # Check if chat already exists
                    chat = TelegramChat.query.filter_by(chat_id=str(update.effective_chat.id)).first()
                    
                    if not chat:
                        # Create new chat record
                        chat = TelegramChat(
                            chat_id=str(update.effective_chat.id),
                            username=username,
                            first_name=user.first_name if user else None,
                            last_name=user.last_name if user else None,
                            is_active=True
                        )
                        db.session.add(chat)
                        db.session.commit()
                        logger.info(f"New admin chat registered: {username}")
                    else:
                        # Update last activity
                        chat.last_activity = datetime.utcnow()
                        chat.is_active = True
                        db.session.commit()
                except Exception as e:
                    logger.error(f"Error storing admin chat in database: {e}")
        
        # Check if user is admin
        if context.user_data.get('is_admin', False):
            return func(update, context, *args, **kwargs)
        else:
            # Log unauthorized access attempt
            logger.warning(f"Unauthorized access attempt by user {user_id} ({username})")
            
            # Notify user
            update.message.reply_text(
                "⚠️ Access Restricted: This trading bot is only available to authorized administrators. "
                "Please contact the system administrator for access permissions."
            )
            return None
    return wrapped

# Helper functions
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    is_admin = context.user_data.get('is_admin', False)
    
    # Basic welcome message for all users
    welcome_message = (
        f"👋 Hello {user.first_name if user else 'trader'}!\n\n"
        f"Welcome to the AI Trading Bot. I can help you analyze forex markets, cryptocurrencies, and commodities, and execute trades with AI-powered recommendations.\n\n"
        f"I support multiple trading pairs including:\n"
        f"• Forex: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD\n"
        f"• Commodities: Gold (XAU/USD)\n"
        f"• Crypto: Bitcoin (BTC/USD), Ethereum (ETH/USD)\n\n"
        f"Here's what I can do:\n"
        f"• /analyze [pair] - Analyze a trading pair (e.g. /analyze XAUUSD)\n"
        f"• /trade - Open the trading menu with pair selection\n"
        f"• /status - Check your current trades\n"
        f"• /help - Show complete help message\n\n"
    )
    
    # For admin users, add link to web interface
    if is_admin:
        # Create keyboard with web UI button
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web Dashboard", url=WEB_APP_URL)],
            [InlineKeyboardButton("💼 Trade Now", callback_data="trade")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Add admin-specific message
        welcome_message += (
            f"*Admin Features:*\n"
            f"• Access to the web dashboard for advanced trading\n"
            f"• Pocket options trading with expiry times\n"
            f"• Risk analysis with AI-powered insights\n\n"
            f"Click the button below to access the web dashboard!"
        )
        
        update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Regular welcome message with simple start button
        keyboard = [[InlineKeyboardButton("🚀 Get Started", callback_data="trade")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_message += f"Let's get started! Use /trade to begin."
        
        update.message.reply_text(welcome_message, reply_markup=reply_markup)

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Here are the commands you can use:\n\n"
        "/analyze [currency_pair] - Analyze a currency pair (e.g., /analyze XAUUSD)\n"
        "/trade - Show the trading options with currency selection\n"
        "/status - Check your current trades\n"
        "/history - See your trading history\n"
        "/buy [amount] - Buy a currency pair (e.g., /buy 1000)\n"
        "/sell [amount] - Sell a currency pair (e.g., /sell 1000)\n"
        "/autotrade [amount] - Let AI decide whether to buy or sell (e.g., /autotrade 1000)\n"
        "/pocket_call [amount] [expiry] - Place a pocket option call (e.g., /pocket_call 100 5)\n"
        "/pocket_put [amount] [expiry] - Place a pocket option put (e.g., /pocket_put 100 5)\n"
        "/close [trade_id] - Close a specific trade (e.g., /close 1)\n"
        "/help - Show this help message\n\n"
        "Supported Currency Pairs:\n"
        "• EURUSD - Euro/US Dollar\n"
        "• GBPUSD - British Pound/US Dollar\n"
        "• USDJPY - US Dollar/Japanese Yen\n"
        "• AUDUSD - Australian Dollar/US Dollar\n"
        "• USDCAD - US Dollar/Canadian Dollar\n"
        "• XAUUSD - Gold/US Dollar\n"
        "• BTCUSD - Bitcoin/US Dollar\n"
        "• ETHUSD - Ethereum/US Dollar"
    )
    update.message.reply_text(help_text)

def analyze_command(update: Update, context: CallbackContext) -> None:
    """Analyze a currency pair."""
    # Get currency pair from command arguments
    args = context.args
    currency_pair = "EURUSD"  # Default currency pair
    
    # Valid currency pairs
    valid_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD", "ETHUSD"]
    
    if args and len(args) > 0:
        input_pair = args[0].upper()
        if input_pair in valid_pairs:
            currency_pair = input_pair
        else:
            update.message.reply_text(
                f"❌ Invalid currency pair: {input_pair}\n"
                f"Valid options are: {', '.join(valid_pairs)}"
            )
            return
    
    update.message.reply_text(f"📊 Analyzing {currency_pair}...")
    
    try:
        # Get market analysis
        analysis = market_analysis.analyze_market(currency_pair)
        
        # Try to use Groq AI for enhanced analysis
        try:
            import groq_ai
            ai_analysis = groq_ai.analyze_market_with_ai(analysis, currency_pair)
            
            # Use AI's recommendation if available
            if ai_analysis and not ai_analysis.get('ai_error', False):
                # Format analysis result with AI insights
                message = format_analysis_result(analysis, ai_analysis)
                update.message.reply_text(message)
                return
        except ImportError:
            logger.warning("Groq AI module not found, using standard analysis")
        except Exception as ai_error:
            logger.error(f"Error using Groq AI: {str(ai_error)}")
            
        # Use standard analysis if AI fails
        message = format_analysis_result(analysis)
        update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in market analysis: {str(e)}")
        update.message.reply_text(f"❌ Error analyzing market: {str(e)}")

def format_analysis_result(analysis, ai_analysis=None):
    """Format the analysis result in a nice message."""
    # Get data from analysis
    currency_pair = analysis.get('currency_pair', 'EURUSD')
    current_price = analysis.get('current_price', 0)
    trend = analysis.get('trend', 'neutral')
    recommendation = analysis.get('recommendation', 'hold')
    
    # Get indicators
    indicators = analysis.get('indicators', {})
    rsi = indicators.get('rsi', 'N/A')
    
    # Set emoji based on trend
    trend_emoji = "📈" if trend == 'bullish' else "📉" if trend == 'bearish' else "📊"
    
    # Create message
    message = (
        f"{trend_emoji} *Analysis for {currency_pair}*\n\n"
        f"*Current Price:* {current_price}\n"
        f"*Trend:* {trend.capitalize()}\n"
        f"*Recommendation:* {recommendation.capitalize()}\n\n"
    )
    
    # Add support and resistance
    message += (
        f"*Support:* {analysis.get('support', 'N/A')}\n"
        f"*Resistance:* {analysis.get('resistance', 'N/A')}\n\n"
    )
    
    # Add key indicators
    message += (
        f"*Key Indicators:*\n"
        f"• RSI: {rsi}\n"
        f"• MACD: {indicators.get('macd', 'N/A')}\n"
        f"• MACD Signal: {indicators.get('macd_signal', 'N/A')}\n"
    )
    
    # Add AI insights if available
    if ai_analysis:
        message += (
            f"\n*AI Insights:*\n"
            f"• Confidence: {ai_analysis.get('confidence', 'N/A')}%\n"
            f"• Risk Assessment: {ai_analysis.get('risk_assessment', 'N/A')}\n"
            f"• Timeframe: {ai_analysis.get('timeframe', 'short_term').replace('_', ' ').capitalize()}\n"
            f"\n{ai_analysis.get('reasoning', '')}\n"
        )
    
    return message

def trade_command(update: Update, context: CallbackContext) -> None:
    """Show trading menu."""
    # First row - Trade actions
    trade_options = [
        [
            InlineKeyboardButton("Buy", callback_data="trade_buy"),
            InlineKeyboardButton("Sell", callback_data="trade_sell"),
        ],
        [
            InlineKeyboardButton("Call (Pocket)", callback_data="trade_pocket_call"),
            InlineKeyboardButton("Put (Pocket)", callback_data="trade_pocket_put"),
        ],
        [InlineKeyboardButton("Auto Trade (AI)", callback_data="trade_auto")],
        [InlineKeyboardButton("Check Status", callback_data="trade_status")],
    ]
    
    # Currency pair selection
    currency_options = [
        [
            InlineKeyboardButton("EUR/USD", callback_data="set_pair_EURUSD"),
            InlineKeyboardButton("GBP/USD", callback_data="set_pair_GBPUSD"),
        ],
        [
            InlineKeyboardButton("USD/JPY", callback_data="set_pair_USDJPY"),
            InlineKeyboardButton("AUD/USD", callback_data="set_pair_AUDUSD"),
        ],
        [
            InlineKeyboardButton("USD/CAD", callback_data="set_pair_USDCAD"),
            InlineKeyboardButton("Gold", callback_data="set_pair_XAUUSD"),
        ],
        [
            InlineKeyboardButton("Bitcoin", callback_data="set_pair_BTCUSD"),
            InlineKeyboardButton("Ethereum", callback_data="set_pair_ETHUSD"),
        ],
    ]
    
    # Combine all options
    keyboard = trade_options + [
        [InlineKeyboardButton("Select Currency Pair 💱", callback_data="show_currencies")]
    ]
    
    # Store currency pair options in context
    context.user_data['currency_options'] = currency_options
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🤖 Trading Options:", reply_markup=reply_markup)

def status_command(update: Update, context: CallbackContext) -> None:
    """Show current trade status."""
    try:
        open_trades = bot.get_open_trades()
        
        if not open_trades:
            update.message.reply_text("You don't have any open trades.")
            return
        
        # Format trade information
        message = "*Your Open Trades:*\n\n"
        
        for trade in open_trades:
            trade_id = trade.get('id', 0)
            currency_pair = trade.get('currency_pair', 'UNKNOWN')
            trade_type = trade.get('type', trade.get('trade_type', 'UNKNOWN')).upper()
            amount = trade.get('amount', 0)
            price = trade.get('price', 0)
            
            message += (
                f"*Trade #{trade_id}*\n"
                f"• Pair: {currency_pair}\n"
                f"• Type: {trade_type}\n"
                f"• Amount: ${amount}\n"
                f"• Entry: {price}\n"
                f"• Current P/L: Calculating...\n\n"
            )
        
        keyboard = [[InlineKeyboardButton("Close a Trade", callback_data="close_trade")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error getting trade status: {str(e)}")
        update.message.reply_text(f"❌ Error getting trade status: {str(e)}")

def buy_command(update: Update, context: CallbackContext) -> None:
    """Execute a buy trade."""
    args = context.args
    amount = 1000  # Default amount
    
    if args and len(args) > 0:
        try:
            amount = float(args[0])
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number. Example: /buy 1000")
            return
            
    currency_pair = "EURUSD"  # Default to EURUSD
    
    try:
        # Execute the trade
        result = bot.execute_trade(currency_pair, 'buy', amount)
        
        if result and result.get('status') == 'success':
            message = (
                f"✅ Trade executed successfully!\n\n"
                f"*Buy {currency_pair}*\n"
                f"• Amount: ${amount}\n"
                f"• Price: {result.get('price', 0)}\n"
                f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                f"You can check your trade status with /status"
            )
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error executing buy trade: {str(e)}")
        update.message.reply_text(f"❌ Error executing trade: {str(e)}")

def sell_command(update: Update, context: CallbackContext) -> None:
    """Execute a sell trade."""
    args = context.args
    amount = 1000  # Default amount
    
    if args and len(args) > 0:
        try:
            amount = float(args[0])
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number. Example: /sell 1000")
            return
            
    currency_pair = "EURUSD"  # Default to EURUSD
    
    try:
        # Execute the trade
        result = bot.execute_trade(currency_pair, 'sell', amount)
        
        if result and result.get('status') == 'success':
            message = (
                f"✅ Trade executed successfully!\n\n"
                f"*Sell {currency_pair}*\n"
                f"• Amount: ${amount}\n"
                f"• Price: {result.get('price', 0)}\n"
                f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                f"You can check your trade status with /status"
            )
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error executing sell trade: {str(e)}")
        update.message.reply_text(f"❌ Error executing trade: {str(e)}")

def autotrade_command(update: Update, context: CallbackContext) -> None:
    """Execute an AI-powered automated trade."""
    args = context.args
    amount = 1000  # Default amount
    
    if args and len(args) > 0:
        try:
            amount = float(args[0])
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number. Example: /autotrade 1000")
            return
            
    currency_pair = "EURUSD"  # Default to EURUSD
    
    try:
        # Get market analysis
        analysis = market_analysis.analyze_market(currency_pair)
        
        # Try to use AI evaluation
        try:
            import groq_ai
            trade_plan = groq_ai.evaluate_trade_opportunity(analysis, currency_pair)
            
            if trade_plan and not trade_plan.get('ai_error', False):
                # Use AI trade plan
                if trade_plan.get('execute_trade', False):
                    # Execute the recommended trade
                    trade_type = trade_plan.get('trade_type', analysis.get('recommendation', 'hold'))
                    
                    if trade_type in ['buy', 'sell']:
                        # Override amount with position size if available
                        position_percentage = trade_plan.get('position_size_percentage', 10) / 100
                        recommended_amount = amount * position_percentage
                        
                        # Execute trade
                        result = bot.execute_trade(currency_pair, trade_type, recommended_amount)
                        
                        if result and result.get('status') == 'success':
                            message = (
                                f"✅ AI Trade executed successfully!\n\n"
                                f"*{trade_type.upper()} {currency_pair}*\n"
                                f"• Amount: ${recommended_amount}\n"
                                f"• Price: {result.get('price', 0)}\n"
                                f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                                f"*AI Reasoning:*\n{trade_plan.get('reasoning', 'No reasoning provided')}\n\n"
                                f"You can check your trade status with /status"
                            )
                            update.message.reply_text(message)
                            return
                    else:
                        update.message.reply_text(f"AI recommends to HOLD - No trade executed.")
                        return
                else:
                    update.message.reply_text(
                        f"AI does not recommend trading now:\n{trade_plan.get('reasoning', 'No reasoning provided')}"
                    )
                    return
        except ImportError:
            logger.warning("Groq AI module not found, using standard analysis")
        except Exception as ai_error:
            logger.error(f"Error using Groq AI: {str(ai_error)}")
        
        # Use standard auto-trade if AI fails
        result = bot.auto_trade(currency_pair, amount, analysis=analysis)
        
        if result and result.get('status') == 'success':
            message = (
                f"✅ Auto-trade executed successfully!\n\n"
                f"*{result.get('type', 'UNKNOWN').upper()} {currency_pair}*\n"
                f"• Amount: ${amount}\n"
                f"• Price: {result.get('price', 0)}\n"
                f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                f"You can check your trade status with /status"
            )
            update.message.reply_text(message)
        elif result and result.get('status') == 'skipped':
            message = (
                f"⚠️ Auto-trade skipped\n\n"
                f"Reason: {result.get('reason', 'Unknown')}\n"
                f"Recommendation: {result.get('recommendation', 'Unknown')}"
            )
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"❌ Auto-trade failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error executing auto-trade: {str(e)}")
        update.message.reply_text(f"❌ Error executing auto-trade: {str(e)}")

def close_command(update: Update, context: CallbackContext) -> None:
    """Close a trade by ID."""
    args = context.args
    
    if not args or len(args) == 0:
        update.message.reply_text("❌ Please provide a trade ID to close. Example: /close 1")
        return
        
    try:
        trade_id = int(args[0])
    except ValueError:
        update.message.reply_text("❌ Invalid trade ID. Please provide a number. Example: /close 1")
        return
        
    try:
        # Close the trade
        result = bot.close_trade(trade_id)
        
        if result and result.get('status') == 'success':
            message = (
                f"✅ Trade #{trade_id} closed successfully!\n\n"
                f"• Close Price: {result.get('close_price', 0)}\n"
                f"• Profit/Loss: ${result.get('profit_loss', 0):.2f}\n"
            )
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"❌ Failed to close trade: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error closing trade: {str(e)}")
        update.message.reply_text(f"❌ Error closing trade: {str(e)}")

def pocket_call_command(update: Update, context: CallbackContext) -> None:
    """Execute a pocket option CALL trade (binary option)."""
    args = context.args
    amount = 100  # Default amount
    expiry_minutes = 5  # Default expiry time in minutes
    
    if not args:
        update.message.reply_text("❌ Please provide amount and expiry time. Example: /pocket_call 100 5")
        return
        
    try:
        amount = float(args[0])
        if len(args) > 1:
            expiry_minutes = int(args[1])
    except ValueError:
        update.message.reply_text("❌ Invalid values. Please provide numbers. Example: /pocket_call 100 5")
        return
            
    currency_pair = "EURUSD"  # Default to EURUSD
    
    try:
        # Execute the pocket option trade
        result = bot.execute_trade(
            currency_pair, 
            'call', 
            amount, 
            source='telegram',
            expiry_minutes=expiry_minutes,
            pocket_option=True
        )
        
        if result and result.get('status') == 'success':
            # Calculate expiry time for display
            from datetime import datetime, timedelta
            expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            
            message = (
                f"✅ Pocket Option executed successfully!\n\n"
                f"*CALL {currency_pair}*\n"
                f"• Amount: ${amount}\n"
                f"• Strike Price: {result.get('price', 0)}\n"
                f"• Trade ID: {result.get('trade_id', 0)}\n"
                f"• Expires in: {expiry_minutes} minutes\n"
                f"• Expiry time: {expiry_time.strftime('%H:%M:%S UTC')}\n\n"
                f"You can check your option status with /status"
            )
            update.message.reply_text(message, parse_mode='Markdown')
        else:
            update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error executing pocket call option: {str(e)}")
        update.message.reply_text(f"❌ Error executing pocket option: {str(e)}")

def pocket_put_command(update: Update, context: CallbackContext) -> None:
    """Execute a pocket option PUT trade (binary option)."""
    args = context.args
    amount = 100  # Default amount
    expiry_minutes = 5  # Default expiry time in minutes
    
    if not args:
        update.message.reply_text("❌ Please provide amount and expiry time. Example: /pocket_put 100 5")
        return
        
    try:
        amount = float(args[0])
        if len(args) > 1:
            expiry_minutes = int(args[1])
    except ValueError:
        update.message.reply_text("❌ Invalid values. Please provide numbers. Example: /pocket_put 100 5")
        return
            
    currency_pair = "EURUSD"  # Default to EURUSD
    
    try:
        # Execute the pocket option trade
        result = bot.execute_trade(
            currency_pair, 
            'put', 
            amount, 
            source='telegram',
            expiry_minutes=expiry_minutes,
            pocket_option=True
        )
        
        if result and result.get('status') == 'success':
            # Calculate expiry time for display
            from datetime import datetime, timedelta
            expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            
            message = (
                f"✅ Pocket Option executed successfully!\n\n"
                f"*PUT {currency_pair}*\n"
                f"• Amount: ${amount}\n"
                f"• Strike Price: {result.get('price', 0)}\n"
                f"• Trade ID: {result.get('trade_id', 0)}\n"
                f"• Expires in: {expiry_minutes} minutes\n"
                f"• Expiry time: {expiry_time.strftime('%H:%M:%S UTC')}\n\n"
                f"You can check your option status with /status"
            )
            update.message.reply_text(message, parse_mode='Markdown')
        else:
            update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error executing pocket put option: {str(e)}")
        update.message.reply_text(f"❌ Error executing pocket option: {str(e)}")

def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from inline keyboard buttons."""
    query = update.callback_query
    query.answer()
    
    # Get query data
    data = query.data
    
    # Get user's selected currency pair or use default
    user_data = context.user_data
    currency_pair = user_data.get('selected_currency_pair', 'EURUSD')
    
    # Handle currency pair selection
    if data.startswith("set_pair_"):
        # Extract currency pair from data
        new_pair = data.replace("set_pair_", "")
        user_data['selected_currency_pair'] = new_pair
        
        query.edit_message_text(
            f"Currency pair set to: *{new_pair}*\n\nWhat would you like to do?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Buy", callback_data="trade_buy"),
                    InlineKeyboardButton("Sell", callback_data="trade_sell"),
                ],
                [
                    InlineKeyboardButton("Call (Pocket)", callback_data="trade_pocket_call"),
                    InlineKeyboardButton("Put (Pocket)", callback_data="trade_pocket_put"),
                ],
                [InlineKeyboardButton("Auto Trade (AI)", callback_data="trade_auto")],
                [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")],
            ])
        )
        return
        
    # Show currency pair selection
    elif data == "show_currencies":
        currency_options = user_data.get('currency_options', [])
        if currency_options:
            keyboard = currency_options + [[
                InlineKeyboardButton("« Back to Trading Menu", callback_data="back_to_menu")
            ]]
            query.edit_message_text(
                "Select a currency pair to trade:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            query.edit_message_text("Error: Currency options not available.")
        return
        
    # Back to main trading menu
    elif data == "back_to_menu":
        # Re-invoke the trade command
        query.message.reply_text("Returning to menu...")
        trade_command(update, context)
        return
    
    # Trading operations
    elif data == "trade_buy":
        query.edit_message_text(f"How much do you want to buy of {currency_pair}? (in USD)")
        context.user_data['expecting_buy_amount'] = True
        
    elif data == "trade_sell":
        query.edit_message_text(f"How much do you want to sell of {currency_pair}? (in USD)")
        context.user_data['expecting_sell_amount'] = True
        
    elif data == "trade_auto":
        query.edit_message_text(f"How much do you want to auto-trade {currency_pair}? (in USD)")
        context.user_data['expecting_auto_amount'] = True
        
    elif data == "trade_status":
        open_trades = bot.get_open_trades()
        
        if not open_trades:
            query.edit_message_text("You don't have any open trades.")
            return
        
        # Format trade information
        message = "*Your Open Trades:*\n\n"
        
        for trade in open_trades:
            trade_id = trade.get('id', 0)
            currency_pair = trade.get('currency_pair', 'UNKNOWN')
            trade_type = trade.get('type', trade.get('trade_type', 'UNKNOWN')).upper()
            amount = trade.get('amount', 0)
            price = trade.get('price', 0)
            
            message += (
                f"*Trade #{trade_id}*\n"
                f"• Pair: {currency_pair}\n"
                f"• Type: {trade_type}\n"
                f"• Amount: ${amount}\n"
                f"• Entry: {price}\n"
                f"• Current P/L: Calculating...\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("Close a Trade", callback_data="close_trade")],
            [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(message, reply_markup=reply_markup)
        
    elif data == "close_trade":
        query.edit_message_text("Enter the trade ID you want to close:")
        context.user_data['expecting_close_id'] = True

def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle regular text messages."""
    text = update.message.text.lower()
    user_data = context.user_data
    
    # Get currently selected currency pair or use default
    currency_pair = user_data.get('selected_currency_pair', 'EURUSD')
    
    if user_data.get('expecting_buy_amount', False):
        try:
            amount = float(text)
            result = bot.execute_trade(currency_pair, 'buy', amount)
            
            if result and result.get('status') == 'success':
                message = (
                    f"✅ Trade executed successfully!\n\n"
                    f"*Buy {currency_pair}*\n"
                    f"• Amount: ${amount}\n"
                    f"• Price: {result.get('price', 0)}\n"
                    f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                    f"You can check your trade status with /status"
                )
                update.message.reply_text(message)
            else:
                update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number.")
        except Exception as e:
            logger.error(f"Error executing buy trade: {str(e)}")
            update.message.reply_text(f"❌ Error executing trade: {str(e)}")
            
        # Reset expecting flag
        user_data.pop('expecting_buy_amount', None)
        
    elif user_data.get('expecting_sell_amount', False):
        try:
            amount = float(text)
            result = bot.execute_trade(currency_pair, 'sell', amount)
            
            if result and result.get('status') == 'success':
                message = (
                    f"✅ Trade executed successfully!\n\n"
                    f"*Sell {currency_pair}*\n"
                    f"• Amount: ${amount}\n"
                    f"• Price: {result.get('price', 0)}\n"
                    f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                    f"You can check your trade status with /status"
                )
                update.message.reply_text(message)
            else:
                update.message.reply_text(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number.")
        except Exception as e:
            logger.error(f"Error executing sell trade: {str(e)}")
            update.message.reply_text(f"❌ Error executing trade: {str(e)}")
            
        # Reset expecting flag
        user_data.pop('expecting_sell_amount', None)
        
    elif user_data.get('expecting_auto_amount', False):
        try:
            amount = float(text)
            
            # Get market analysis with AI enhancement
            analysis = market_analysis.analyze_market(currency_pair, use_ai=True)
            
            # Try to use AI evaluation if available
            try:
                import groq_ai
                trade_plan = groq_ai.evaluate_trade_opportunity(analysis, currency_pair)
                
                if trade_plan and not trade_plan.get('ai_error', False):
                    # Use AI trade plan
                    if trade_plan.get('execute_trade', False):
                        # Execute the recommended trade
                        trade_type = trade_plan.get('trade_type', 'hold')
                        
                        if trade_type in ['buy', 'sell']:
                            # Override amount with position size if available
                            position_percentage = trade_plan.get('position_size_percentage', 10)
                            if isinstance(position_percentage, str):
                                try:
                                    position_percentage = float(position_percentage.strip('%'))
                                except:
                                    position_percentage = 10
                            position_percentage = position_percentage / 100
                            recommended_amount = amount * position_percentage
                            
                            # Execute trade with possibly AI recommended leverage
                            leverage = trade_plan.get('leverage', 1)
                            if isinstance(leverage, str):
                                try:
                                    leverage = int(leverage)
                                except:
                                    leverage = 1
                            
                            result = bot.execute_trade(
                                currency_pair, 
                                trade_type, 
                                recommended_amount,
                                leverage=leverage
                            )
                            
                            if result and result.get('status') == 'success':
                                message = (
                                    f"✅ AI-powered trade executed successfully!\n\n"
                                    f"*{trade_type.upper()} {currency_pair}*\n"
                                    f"• Amount: ${recommended_amount:.2f}\n"
                                    f"• Price: {result.get('price', 0)}\n"
                                    f"• Leverage: {leverage}x\n"
                                    f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                                    f"*AI Reasoning:*\n{trade_plan.get('reasoning', 'No reasoning provided')}\n\n"
                                    f"You can check your trade status with /status"
                                )
                                update.message.reply_text(message)
                                return
                        else:
                            message = (
                                f"🤖 AI Analysis Result: HOLD\n\n"
                                f"After analyzing {currency_pair}, the AI recommends to hold.\n\n"
                                f"*Reasoning:*\n{trade_plan.get('reasoning', 'Not enough confidence to enter a trade at this time.')}"
                            )
                            update.message.reply_text(message)
                            return
                    else:
                        update.message.reply_text(
                            f"🤖 AI does not recommend trading {currency_pair} now:\n\n"
                            f"*Reasoning:*\n{trade_plan.get('reasoning', 'Market conditions are not favorable.')}"
                        )
                        return
            except ImportError:
                logger.warning("Groq AI module not found, using standard analysis")
            except Exception as ai_error:
                logger.error(f"Error using Groq AI: {str(ai_error)}")
            
            # Use standard auto-trade if AI fails
            result = bot.auto_trade(currency_pair, amount, analysis=analysis)
            
            if result and result.get('status') == 'success':
                message = (
                    f"✅ Auto-trade executed successfully!\n\n"
                    f"*{result.get('type', 'UNKNOWN').upper()} {currency_pair}*\n"
                    f"• Amount: ${amount}\n"
                    f"• Price: {result.get('price', 0)}\n"
                    f"• Trade ID: {result.get('trade_id', 0)}\n\n"
                    f"You can check your trade status with /status"
                )
                update.message.reply_text(message)
            elif result and result.get('status') == 'skipped':
                message = (
                    f"⚠️ Auto-trade skipped\n\n"
                    f"Reason: {result.get('reason', 'Unknown')}\n"
                    f"Recommendation: {result.get('recommendation', 'Unknown')}"
                )
                update.message.reply_text(message)
            else:
                update.message.reply_text(f"❌ Auto-trade failed: {result.get('message', 'Unknown error')}")
                
        except ValueError:
            update.message.reply_text("❌ Invalid amount. Please provide a number.")
        except Exception as e:
            logger.error(f"Error executing auto-trade: {str(e)}")
            update.message.reply_text(f"❌ Error executing auto-trade: {str(e)}")
            
        # Reset expecting flag
        user_data.pop('expecting_auto_amount', None)
        
    elif user_data.get('expecting_close_id', False):
        try:
            trade_id = int(text)
            result = bot.close_trade(trade_id)
            
            if result and result.get('status') == 'success':
                message = (
                    f"✅ Trade #{trade_id} closed successfully!\n\n"
                    f"• Close Price: {result.get('close_price', 0)}\n"
                    f"• Profit/Loss: ${result.get('profit_loss', 0):.2f}\n"
                )
                update.message.reply_text(message)
            else:
                update.message.reply_text(f"❌ Failed to close trade: {result.get('message', 'Unknown error')}")
                
        except ValueError:
            update.message.reply_text("❌ Invalid trade ID. Please provide a number.")
        except Exception as e:
            logger.error(f"Error closing trade: {str(e)}")
            update.message.reply_text(f"❌ Error closing trade: {str(e)}")
            
        # Reset expecting flag
        user_data.pop('expecting_close_id', None)
        
    else:
        # Default response for text messages
        update.message.reply_text(
            "I'm not sure what you mean. Use /help to see available commands."
        )

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_TOKEN provided. Exiting.")
        return
    
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register command handlers
    # Public commands - available to all users
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Admin-only commands - restricted to authorized users
    dispatcher.add_handler(CommandHandler("analyze", admin_only(analyze_command)))
    dispatcher.add_handler(CommandHandler("trade", admin_only(trade_command)))
    dispatcher.add_handler(CommandHandler("status", admin_only(status_command)))
    dispatcher.add_handler(CommandHandler("buy", admin_only(buy_command)))
    dispatcher.add_handler(CommandHandler("sell", admin_only(sell_command)))
    dispatcher.add_handler(CommandHandler("autotrade", admin_only(autotrade_command)))
    dispatcher.add_handler(CommandHandler("close", admin_only(close_command)))
    
    # Register callback query handler - also restricted to admins
    dispatcher.add_handler(CallbackQueryHandler(admin_only(button_handler)))
    
    # Register message handler for text - also restricted to admins
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, admin_only(handle_text)))
    
    # Start the Bot
    updater.start_polling()
    logger.info("Bot started")
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()