import os
import logging
import market_analysis
import trading_bot
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ContextTypes
from telegram.ext import Application

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TelegramBot')

# Initialize the trading bot
trader = trading_bot.TradingBot()

# Get the Telegram bot token and admin users from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USERS = os.environ.get("TELEGRAM_ADMIN_USERS", "").split(",")
if not TELEGRAM_TOKEN:
    logger.warning("No TELEGRAM_TOKEN found in environment variables. Bot will not work without it.")
if not ADMIN_USERS or ADMIN_USERS[0] == "":
    logger.warning("No TELEGRAM_ADMIN_USERS defined. Only admin users will be able to use the bot.")

# Admin check decorator
def admin_only(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user = update.effective_user
        user_id = str(user.id)
        username = user.username
        
        # Check if user is in the admin list
        if user_id in ADMIN_USERS or (username and username in ADMIN_USERS):
            return await func(update, context, *args, **kwargs)
        else:
            logger.warning(f"Unauthorized access attempt by user {user_id} ({username})")
            await update.message.reply_text(
                "⚠️ Sorry, this bot is only available to authorized administrators. "
                "Please contact your system administrator for access."
            )
            return None
    return wrapped

# Helper functions
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        f"Welcome to the AI Trading Bot. I can help you analyze the forex market and execute trades.\n\n"
        f"Here's what I can do:\n"
        f"• /analyze EURUSD - Analyze a currency pair\n"
        f"• /trade - Open the trading menu\n"
        f"• /status - Check the status of your trades\n"
        f"• /help - Show this help message\n\n"
        f"Let's start trading! 🚀"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_message = (
        "🤖 *AI Trading Bot Commands*\n\n"
        "*Analysis Commands:*\n"
        "/analyze EURUSD - Analyze EUR/USD pair\n"
        "/analyze GBPUSD - Analyze GBP/USD pair\n"
        "/analyze USDJPY - Analyze USD/JPY pair\n\n"
        "*Trading Commands:*\n"
        "/trade - Open trading menu\n"
        "/buy EURUSD 1000 - Buy EUR/USD for $1000\n"
        "/sell EURUSD 1000 - Sell EUR/USD for $1000\n"
        "/autotrade EURUSD 1000 - Let AI decide whether to buy or sell\n\n"
        "*Account Commands:*\n"
        "/status - Check current trades\n"
        "/close 1 - Close trade with ID 1\n"
        "/history - View trade history\n\n"
        "Need more help? Contact support@aitradingbot.com"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze a currency pair."""
    # Get the currency pair from the message
    try:
        # Check if any arguments were provided
        if context.args and len(context.args) > 0:
            currency_pair = context.args[0].upper()
            timeframe = "1d"  # Default timeframe
            
            if len(context.args) > 1:
                timeframe = context.args[1].lower()
        else:
            # Default to EURUSD if no currency pair specified
            currency_pair = "EURUSD"
            timeframe = "1d"
            
        # Send loading message
        message = await update.message.reply_text(f"📊 Analyzing {currency_pair} on {timeframe} timeframe... Please wait.")
        
        try:
            # Perform the analysis
            analysis = market_analysis.analyze_market(currency_pair, timeframe)
            
            # Format the analysis result
            analysis_message = format_analysis_result(analysis)
            
            # Create inline keyboard for actions
            keyboard = [
                [
                    InlineKeyboardButton("📈 Buy", callback_data=f"buy_{currency_pair}_1000"),
                    InlineKeyboardButton("📉 Sell", callback_data=f"sell_{currency_pair}_1000"),
                ],
                [
                    InlineKeyboardButton("🤖 Auto Trade", callback_data=f"auto_{currency_pair}_1000"),
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"analyze_{currency_pair}_{timeframe}"),
                ],
                [
                    InlineKeyboardButton("📋 Other Pairs", callback_data="analyze_menu"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit the loading message with the analysis result
            await message.edit_text(analysis_message, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Log successful analysis
            logger.info(f"Analyzed {currency_pair} on {timeframe} timeframe")
            
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            await message.edit_text(f"⚠️ Error analyzing {currency_pair}: {str(e)}")
    except Exception as e:
        # Show a list of available pairs if any error occurred with the command
        logger.error(f"Command error: {str(e)}")
        keyboard = [
            [
                InlineKeyboardButton("EUR/USD", callback_data="analyze_EURUSD_1d"),
                InlineKeyboardButton("GBP/USD", callback_data="analyze_GBPUSD_1d"),
            ],
            [
                InlineKeyboardButton("USD/JPY", callback_data="analyze_USDJPY_1d"),
                InlineKeyboardButton("USD/CHF", callback_data="analyze_USDCHF_1d"),
            ],
            [
                InlineKeyboardButton("AUD/USD", callback_data="analyze_AUDUSD_1d"),
                InlineKeyboardButton("⚙️ Change Timeframe", callback_data="timeframe_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please select a currency pair to analyze:", 
            reply_markup=reply_markup
        )

def format_analysis_result(analysis):
    """Format the analysis result in a nice message."""
    # Emojis for different trends
    trend_emoji = "🔴" if analysis['trend'] == 'bearish' else "🟢" if analysis['trend'] == 'bullish' else "🟡"
    rec_emoji = "🟢" if analysis['recommendation'] == 'buy' else "🔴" if analysis['recommendation'] == 'sell' else "🟡"
    
    message = (
        f"*Analysis for {analysis['currency_pair']}*\n"
        f"*Time:* {analysis['timestamp']}\n"
        f"*Current Price:* ${analysis['current_price']}\n\n"
        f"*Trend:* {trend_emoji} {analysis['trend'].capitalize()} (Strength: {analysis['strength']}%)\n"
        f"*Support:* ${analysis['support']}\n"
        f"*Resistance:* ${analysis['resistance']}\n\n"
        f"*Recommendation:* {rec_emoji} {analysis['recommendation'].upper()}\n"
        f"*Confidence:* {analysis['confidence']}%\n\n"
        f"*Technical Indicators:*\n"
        f"• RSI: {analysis['indicators']['rsi']}\n"
        f"• MACD: {analysis['indicators']['macd']}\n"
        f"• MACD Signal: {analysis['indicators']['macd_signal']}\n"
        f"• SMA 20: {analysis['indicators']['sma_20']}\n"
    )
    return message

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show trading menu."""
    keyboard = [
        [
            InlineKeyboardButton("Buy EUR/USD", callback_data="buy_EURUSD_1000"),
            InlineKeyboardButton("Sell EUR/USD", callback_data="sell_EURUSD_1000"),
        ],
        [
            InlineKeyboardButton("Buy GBP/USD", callback_data="buy_GBPUSD_1000"),
            InlineKeyboardButton("Sell GBP/USD", callback_data="sell_GBPUSD_1000"),
        ],
        [
            InlineKeyboardButton("Buy USD/JPY", callback_data="buy_USDJPY_1000"),
            InlineKeyboardButton("Sell USD/JPY", callback_data="sell_USDJPY_1000"),
        ],
        [
            InlineKeyboardButton("🤖 Auto Trade EUR/USD", callback_data="auto_EURUSD_1000"),
        ],
        [
            InlineKeyboardButton("📊 Analyze Market", callback_data="analyze_menu"),
            InlineKeyboardButton("👁️ View Status", callback_data="status"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 *Trading Menu*\nChoose an action:", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current trade status."""
    open_trades = trader.get_open_trades()
    
    if not open_trades:
        await update.message.reply_text("You don't have any open trades.")
        return
    
    message = "*Your Open Trades:*\n\n"
    
    for i, trade in enumerate(open_trades):
        profit_loss = trader.get_current_price(trade['currency_pair']) - trade['price'] if trade['type'] == 'buy' else trade['price'] - trader.get_current_price(trade['currency_pair'])
        profit_loss *= trade['amount']
        
        emoji = "🟢" if profit_loss > 0 else "🔴"
        
        message += (
            f"*Trade #{i+1}*\n"
            f"Pair: {trade['currency_pair']}\n"
            f"Type: {trade['type'].upper()}\n"
            f"Amount: ${trade['amount']}\n"
            f"Price: ${trade['price']}\n"
            f"P/L: {emoji} ${profit_loss:.2f}\n\n"
        )
    
    # Add inline keyboard to close trades
    keyboard = []
    row = []
    for i in range(len(open_trades)):
        if i % 3 == 0 and i > 0:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(f"Close #{i+1}", callback_data=f"close_{i+1}"))
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show trade history."""
    trade_history = trader.get_trade_history()
    
    if not trade_history:
        await update.message.reply_text("You don't have any trade history yet.")
        return
    
    message = "*Your Trade History:*\n\n"
    
    for i, trade in enumerate(trade_history):
        emoji = "🟢" if trade.get('profit_loss', 0) > 0 else "🔴" if trade.get('profit_loss', 0) < 0 else "⚪"
        status_emoji = "✅" if trade['status'] == 'closed' else "⏳"
        
        message += (
            f"*Trade #{i+1}*\n"
            f"Pair: {trade['currency_pair']}\n"
            f"Type: {trade['type'].upper()}\n"
            f"Amount: ${trade['amount']}\n"
            f"Price: ${trade['price']}\n"
            f"Status: {status_emoji} {trade['status'].capitalize()}\n"
        )
        
        if trade['status'] == 'closed':
            message += f"P/L: {emoji} ${trade.get('profit_loss', 0):.2f}\n"
            
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute a buy trade."""
    if context.args and len(context.args) >= 2:
        currency_pair = context.args[0].upper()
        try:
            amount = float(context.args[1])
            
            result = trader.execute_trade(currency_pair, 'buy', amount)
            
            await update.message.reply_text(
                f"✅ Buy order executed:\n"
                f"Currency Pair: {result['currency_pair']}\n"
                f"Amount: ${result['amount']}\n"
                f"Price: ${result['price']}\n"
                f"Trade ID: {result['trade_id']}"
            )
        except ValueError:
            await update.message.reply_text("⚠️ Invalid amount. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error executing buy trade: {str(e)}")
            await update.message.reply_text(f"⚠️ Error executing buy trade: {str(e)}")
    else:
        await update.message.reply_text("⚠️ Please provide a currency pair and amount.\nExample: /buy EURUSD 1000")

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute a sell trade."""
    if context.args and len(context.args) >= 2:
        currency_pair = context.args[0].upper()
        try:
            amount = float(context.args[1])
            
            result = trader.execute_trade(currency_pair, 'sell', amount)
            
            await update.message.reply_text(
                f"✅ Sell order executed:\n"
                f"Currency Pair: {result['currency_pair']}\n"
                f"Amount: ${result['amount']}\n"
                f"Price: ${result['price']}\n"
                f"Trade ID: {result['trade_id']}"
            )
        except ValueError:
            await update.message.reply_text("⚠️ Invalid amount. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error executing sell trade: {str(e)}")
            await update.message.reply_text(f"⚠️ Error executing sell trade: {str(e)}")
    else:
        await update.message.reply_text("⚠️ Please provide a currency pair and amount.\nExample: /sell EURUSD 1000")

async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute an AI-powered automated trade."""
    if context.args and len(context.args) >= 2:
        currency_pair = context.args[0].upper()
        try:
            amount = float(context.args[1])
            
            # First analyze the market
            await update.message.reply_text(f"🤖 Analyzing {currency_pair} market conditions...")
            analysis = market_analysis.analyze_market(currency_pair)
            
            # Then execute the auto trade
            result = trader.auto_trade(currency_pair, amount, analysis)
            
            if result['status'] == 'success':
                await update.message.reply_text(
                    f"✅ AI Auto-Trade executed:\n"
                    f"Type: {result['type'].upper()}\n"
                    f"Currency Pair: {result['currency_pair']}\n"
                    f"Amount: ${result['amount']}\n"
                    f"Price: ${result['price']}\n"
                    f"Trade ID: {result['trade_id']}\n\n"
                    f"*AI Analysis:*\n"
                    f"Trend: {analysis['trend'].capitalize()}\n"
                    f"Recommendation: {analysis['recommendation'].upper()}\n"
                    f"Confidence: {analysis['confidence']}%",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"⚠️ AI decided not to trade:\n"
                    f"Reason: {result['reason']}\n"
                    f"Recommendation: {result['recommendation']}\n\n"
                    f"*AI Analysis:*\n"
                    f"Trend: {analysis['trend'].capitalize()}\n"
                    f"Confidence: {analysis['confidence']}%",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text("⚠️ Invalid amount. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error executing auto trade: {str(e)}")
            await update.message.reply_text(f"⚠️ Error executing auto trade: {str(e)}")
    else:
        await update.message.reply_text("⚠️ Please provide a currency pair and amount.\nExample: /autotrade EURUSD 1000")

async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close a trade by ID."""
    if context.args and len(context.args) > 0:
        try:
            trade_id = int(context.args[0])
            
            result = trader.close_trade(trade_id)
            
            if result['status'] == 'success':
                emoji = "🟢" if result['profit_loss'] > 0 else "🔴"
                await update.message.reply_text(
                    f"✅ Trade #{trade_id} closed:\n"
                    f"Close Price: ${result['close_price']}\n"
                    f"Profit/Loss: {emoji} ${result['profit_loss']:.2f}"
                )
            else:
                await update.message.reply_text(f"⚠️ Error closing trade: {result['message']}")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid trade ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error closing trade: {str(e)}")
            await update.message.reply_text(f"⚠️ Error closing trade: {str(e)}")
    else:
        await update.message.reply_text("⚠️ Please provide a trade ID.\nExample: /close 1")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboard buttons."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action.startswith("buy_"):
        parts = action.split("_")
        if len(parts) >= 3:
            currency_pair = parts[1]
            amount = float(parts[2])
            
            await query.edit_message_text(f"💰 Executing buy order for {currency_pair}... Please wait.")
            
            try:
                result = trader.execute_trade(currency_pair, 'buy', amount)
                
                # Create keyboard for additional actions
                keyboard = [
                    [
                        InlineKeyboardButton("📊 New Analysis", callback_data=f"analyze_{currency_pair}_1d"),
                        InlineKeyboardButton("❌ Close Trade", callback_data=f"close_{result['trade_id']}"),
                    ],
                    [
                        InlineKeyboardButton("👁️ View All Trades", callback_data="status"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ *Buy order executed:*\n"
                    f"Currency Pair: {result['currency_pair']}\n"
                    f"Amount: ${result['amount']}\n"
                    f"Price: ${result['price']}\n"
                    f"Trade ID: {result['trade_id']}\n\n"
                    f"What would you like to do next?",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error executing buy trade: {str(e)}")
                await query.edit_message_text(f"⚠️ Error executing buy trade: {str(e)}")
    
    elif action.startswith("sell_"):
        parts = action.split("_")
        if len(parts) >= 3:
            currency_pair = parts[1]
            amount = float(parts[2])
            
            await query.edit_message_text(f"💰 Executing sell order for {currency_pair}... Please wait.")
            
            try:
                result = trader.execute_trade(currency_pair, 'sell', amount)
                
                # Create keyboard for additional actions
                keyboard = [
                    [
                        InlineKeyboardButton("📊 New Analysis", callback_data=f"analyze_{currency_pair}_1d"),
                        InlineKeyboardButton("❌ Close Trade", callback_data=f"close_{result['trade_id']}"),
                    ],
                    [
                        InlineKeyboardButton("👁️ View All Trades", callback_data="status"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ *Sell order executed:*\n"
                    f"Currency Pair: {result['currency_pair']}\n"
                    f"Amount: ${result['amount']}\n"
                    f"Price: ${result['price']}\n"
                    f"Trade ID: {result['trade_id']}\n\n"
                    f"What would you like to do next?",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error executing sell trade: {str(e)}")
                await query.edit_message_text(f"⚠️ Error executing sell trade: {str(e)}")
    
    elif action.startswith("auto_"):
        parts = action.split("_")
        if len(parts) >= 3:
            currency_pair = parts[1]
            amount = float(parts[2])
            
            await query.edit_message_text(f"🤖 AI is analyzing {currency_pair} market conditions... Please wait.")
            
            try:
                # First analyze the market
                analysis = market_analysis.analyze_market(currency_pair)
                
                # Then execute the auto trade
                result = trader.auto_trade(currency_pair, amount, analysis)
                
                # Create keyboard for additional actions
                keyboard = [
                    [
                        InlineKeyboardButton("📊 New Analysis", callback_data=f"analyze_{currency_pair}_1d"),
                        InlineKeyboardButton("🔄 Try Again", callback_data=f"auto_{currency_pair}_{amount}"),
                    ],
                    [
                        InlineKeyboardButton("👁️ View Trades", callback_data="status"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if result['status'] == 'success':
                    await query.edit_message_text(
                        f"✅ *AI Auto-Trade executed:*\n"
                        f"Type: {result['type'].upper()}\n"
                        f"Currency Pair: {result['currency_pair']}\n"
                        f"Amount: ${result['amount']}\n"
                        f"Price: ${result['price']}\n"
                        f"Trade ID: {result['trade_id']}\n\n"
                        f"*AI Analysis:*\n"
                        f"Trend: {analysis['trend'].capitalize()}\n"
                        f"Recommendation: {analysis['recommendation'].upper()}\n"
                        f"Confidence: {analysis['confidence']}%\n\n"
                        f"What would you like to do next?",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(
                        f"⚠️ *AI decided not to trade:*\n"
                        f"Reason: {result['reason']}\n"
                        f"Recommendation: {result['recommendation']}\n\n"
                        f"*AI Analysis:*\n"
                        f"Trend: {analysis['trend'].capitalize()}\n"
                        f"Confidence: {analysis['confidence']}%\n\n"
                        f"What would you like to do next?",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error executing auto trade: {str(e)}")
                await query.edit_message_text(f"⚠️ Error executing auto trade: {str(e)}")
    
    elif action.startswith("analyze_"):
        parts = action.split("_")
        if len(parts) >= 2:
            if parts[1] == "menu":
                # Show analysis menu
                keyboard = [
                    [
                        InlineKeyboardButton("EUR/USD", callback_data="analyze_EURUSD_1d"),
                        InlineKeyboardButton("GBP/USD", callback_data="analyze_GBPUSD_1d"),
                    ],
                    [
                        InlineKeyboardButton("USD/JPY", callback_data="analyze_USDJPY_1d"),
                        InlineKeyboardButton("USD/CHF", callback_data="analyze_USDCHF_1d"),
                    ],
                    [
                        InlineKeyboardButton("AUD/USD", callback_data="analyze_AUDUSD_1d"),
                        InlineKeyboardButton("⚙️ Change Timeframe", callback_data="timeframe_menu"),
                    ],
                    [
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📊 *Market Analysis*\nSelect a currency pair to analyze:", 
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            elif len(parts) >= 3:
                # Analyze specific currency pair
                currency_pair = parts[1]
                timeframe = parts[2] if len(parts) >= 3 else "1d"
                
                await query.edit_message_text(f"📊 Analyzing {currency_pair} on {timeframe} timeframe... Please wait.")
                
                try:
                    analysis = market_analysis.analyze_market(currency_pair, timeframe)
                    analysis_message = format_analysis_result(analysis)
                    
                    # Create inline keyboard for actions
                    keyboard = [
                        [
                            InlineKeyboardButton("📈 Buy", callback_data=f"buy_{currency_pair}_1000"),
                            InlineKeyboardButton("📉 Sell", callback_data=f"sell_{currency_pair}_1000"),
                        ],
                        [
                            InlineKeyboardButton("🤖 Auto Trade", callback_data=f"auto_{currency_pair}_1000"),
                            InlineKeyboardButton("🔄 Refresh", callback_data=f"analyze_{currency_pair}_{timeframe}"),
                        ],
                        [
                            InlineKeyboardButton("⏱️ Change Timeframe", callback_data=f"timeframe_{currency_pair}"),
                            InlineKeyboardButton("📋 Other Pairs", callback_data="analyze_menu"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        analysis_message, 
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error in analysis: {str(e)}")
                    await query.edit_message_text(f"⚠️ Error analyzing {currency_pair}: {str(e)}")
    
    elif action.startswith("timeframe_"):
        parts = action.split("_")
        if len(parts) >= 2:
            currency_pair = parts[1]
            
            # Show timeframe selection menu
            keyboard = [
                [
                    InlineKeyboardButton("1 Hour", callback_data=f"analyze_{currency_pair}_1h"),
                    InlineKeyboardButton("4 Hours", callback_data=f"analyze_{currency_pair}_4h"),
                ],
                [
                    InlineKeyboardButton("1 Day", callback_data=f"analyze_{currency_pair}_1d"),
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data=f"analyze_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⏱️ *Select Timeframe for {currency_pair}*\n"
                f"Choose the timeframe for your analysis:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif parts[1] == "menu":
            # Generic timeframe menu
            keyboard = [
                [
                    InlineKeyboardButton("EUR/USD 1h", callback_data="analyze_EURUSD_1h"),
                    InlineKeyboardButton("EUR/USD 4h", callback_data="analyze_EURUSD_4h"),
                ],
                [
                    InlineKeyboardButton("EUR/USD 1d", callback_data="analyze_EURUSD_1d"),
                ],
                [
                    InlineKeyboardButton("📋 Other Pairs", callback_data="analyze_menu"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⏱️ *Select Timeframe*\n"
                "Choose the currency pair and timeframe for your analysis:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    elif action.startswith("close_"):
        parts = action.split("_")
        if len(parts) >= 2:
            try:
                trade_id = int(parts[1])
                
                await query.edit_message_text(f"📝 Closing trade #{trade_id}... Please wait.")
                
                result = trader.close_trade(trade_id)
                
                if result['status'] == 'success':
                    emoji = "🟢" if result['profit_loss'] > 0 else "🔴"
                    
                    # Create keyboard for additional actions
                    keyboard = [
                        [
                            InlineKeyboardButton("📊 New Analysis", callback_data="analyze_menu"),
                            InlineKeyboardButton("🛒 New Trade", callback_data="trade_menu"),
                        ],
                        [
                            InlineKeyboardButton("👁️ View Trades", callback_data="status"),
                            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"✅ *Trade #{trade_id} closed successfully*\n"
                        f"Close Price: ${result['close_price']}\n"
                        f"Profit/Loss: {emoji} ${result['profit_loss']:.2f}\n\n"
                        f"What would you like to do next?",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(f"⚠️ Error closing trade: {result['message']}")
            except Exception as e:
                logger.error(f"Error closing trade: {str(e)}")
                await query.edit_message_text(f"⚠️ Error closing trade: {str(e)}")
    
    elif action == "main_menu":
        # Main menu with all options
        keyboard = [
            [
                InlineKeyboardButton("📊 Market Analysis", callback_data="analyze_menu"),
                InlineKeyboardButton("🛒 Trading Menu", callback_data="trade_menu"),
            ],
            [
                InlineKeyboardButton("👁️ View Open Trades", callback_data="status"),
                InlineKeyboardButton("📝 Trade History", callback_data="history"),
            ],
            [
                InlineKeyboardButton("🤖 Auto Trade EUR/USD", callback_data="auto_EURUSD_1000"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏠 *Main Menu*\n"
            "Welcome to AI Trading Bot! What would you like to do?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == "trade_menu":
        # Trading menu
        keyboard = [
            [
                InlineKeyboardButton("Buy EUR/USD", callback_data="buy_EURUSD_1000"),
                InlineKeyboardButton("Sell EUR/USD", callback_data="sell_EURUSD_1000"),
            ],
            [
                InlineKeyboardButton("Buy GBP/USD", callback_data="buy_GBPUSD_1000"),
                InlineKeyboardButton("Sell GBP/USD", callback_data="sell_GBPUSD_1000"),
            ],
            [
                InlineKeyboardButton("Buy USD/JPY", callback_data="buy_USDJPY_1000"),
                InlineKeyboardButton("Sell USD/JPY", callback_data="sell_USDJPY_1000"),
            ],
            [
                InlineKeyboardButton("🤖 Auto Trade EUR/USD", callback_data="auto_EURUSD_1000"),
            ],
            [
                InlineKeyboardButton("📊 Analyze First", callback_data="analyze_menu"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🛒 *Trading Menu*\n"
            "Select the trade you want to execute:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == "status":
        # Show open trades status
        open_trades = trader.get_open_trades()
        
        if not open_trades:
            # No open trades, show options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Market Analysis", callback_data="analyze_menu"),
                    InlineKeyboardButton("🛒 New Trade", callback_data="trade_menu"),
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👁️ *Trade Status*\n"
                "You don't have any open trades currently.\n\n"
                "Would you like to analyze the market or place a new trade?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        message = "👁️ *Your Open Trades:*\n\n"
        
        for i, trade in enumerate(open_trades):
            profit_loss = trader.get_current_price(trade['currency_pair']) - trade['price'] if trade['type'] == 'buy' else trade['price'] - trader.get_current_price(trade['currency_pair'])
            profit_loss *= trade['amount']
            
            emoji = "🟢" if profit_loss > 0 else "🔴"
            
            message += (
                f"*Trade #{i+1}*\n"
                f"Pair: {trade['currency_pair']}\n"
                f"Type: {trade['type'].upper()}\n"
                f"Amount: ${trade['amount']}\n"
                f"Price: ${trade['price']}\n"
                f"P/L: {emoji} ${profit_loss:.2f}\n\n"
            )
        
        # Add inline keyboard to close trades
        keyboard = []
        row = []
        for i in range(len(open_trades)):
            if i % 3 == 0 and i > 0:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(f"Close #{i+1}", callback_data=f"close_{i+1}"))
        if row:
            keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("📊 Analysis", callback_data="analyze_menu"),
            InlineKeyboardButton("🛒 New Trade", callback_data="trade_menu"),
            InlineKeyboardButton("🏠 Menu", callback_data="main_menu"),
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif action == "history":
        # Show trade history
        trade_history = trader.get_trade_history()
        
        if not trade_history:
            # No trade history, show options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Market Analysis", callback_data="analyze_menu"),
                    InlineKeyboardButton("🛒 New Trade", callback_data="trade_menu"),
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 *Trade History*\n"
                "You don't have any trade history yet.\n\n"
                "Would you like to analyze the market or place a new trade?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Limit to last 5 trades to avoid message size limits
        recent_trades = trade_history[-5:] if len(trade_history) > 5 else trade_history
        
        message = "📝 *Your Trade History:*\n\n"
        
        for i, trade in enumerate(recent_trades):
            emoji = "🟢" if trade.get('profit_loss', 0) > 0 else "🔴" if trade.get('profit_loss', 0) < 0 else "⚪"
            status_emoji = "✅" if trade['status'] == 'closed' else "⏳"
            
            message += (
                f"*Trade #{len(trade_history) - len(recent_trades) + i + 1}*\n"
                f"Pair: {trade['currency_pair']}\n"
                f"Type: {trade['type'].upper()}\n"
                f"Amount: ${trade['amount']}\n"
                f"Price: ${trade['price']}\n"
                f"Status: {status_emoji} {trade['status'].capitalize()}\n"
            )
            
            if trade['status'] == 'closed':
                message += f"P/L: {emoji} ${trade.get('profit_loss', 0):.2f}\n"
                
            message += "\n"
        
        # Add navigation buttons
        keyboard = [
            [
                InlineKeyboardButton("👁️ Open Trades", callback_data="status"),
                InlineKeyboardButton("🛒 New Trade", callback_data="trade_menu"),
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    
    elif action == "settings":
        # Settings menu
        keyboard = [
            [
                InlineKeyboardButton("💰 Set Default Amount", callback_data="set_amount"),
                InlineKeyboardButton("⏱️ Set Default Timeframe", callback_data="timeframe_menu"),
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Settings*\n"
            "Configure your trading preferences:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages."""
    message = update.message.text.lower()
    
    # Check if the message is a command-like format (e.g., "/analyze eurusd" without using a proper command)
    if message.startswith("/analyze") or message.startswith("analyze"):
        parts = message.split()
        if len(parts) > 1:
            # Extract the currency pair
            pair = parts[1].upper() 
            
            # Check if it's a valid currency pair
            valid_pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]
            if pair in valid_pairs:
                # Set up context args and call the analyze command
                context.args = [pair]
                if len(parts) > 2:
                    # Include timeframe if provided
                    timeframe = parts[2].lower()
                    valid_timeframes = ["1h", "4h", "1d"]
                    if timeframe in valid_timeframes:
                        context.args.append(timeframe)
                
                await analyze_command(update, context)
                return
    
    # Check for currency pair analysis in general text
    if "analyze" in message or "analysis" in message:
        # Extract possible currency pair
        for pair in ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"]:
            if pair.lower() in message.lower():
                # Call analyze with the extracted pair
                context.args = [pair.upper()]
                await analyze_command(update, context)
                return
        
        # If no currency pair found, show analyze menu
        await analyze_command(update, context)
    
    elif "trade" in message or "buy" in message or "sell" in message:
        await trade_command(update, context)
    
    elif "status" in message or "position" in message:
        await status_command(update, context)
    
    elif "help" in message:
        await help_command(update, context)
    
    else:
        # Default response with suggestions
        keyboard = [
            [
                InlineKeyboardButton("📊 Analyze Market", callback_data="analyze_menu"),
                InlineKeyboardButton("🛒 Trading Menu", callback_data="trade_menu"),
            ],
            [
                InlineKeyboardButton("👁️ Check Status", callback_data="status"),
                InlineKeyboardButton("❓ Help", callback_data="help"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "I'm not sure what you're looking for. Here are some options:", 
            reply_markup=reply_markup
        )

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No Telegram token found. Please set the TELEGRAM_TOKEN environment variable.")
        return
    
    # Create the application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("sell", sell_command))
    application.add_handler(CommandHandler("autotrade", autotrade_command))
    application.add_handler(CommandHandler("close", close_command))
    
    # Callback query handler for inline keyboard buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler for regular text
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start the Bot
    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main()