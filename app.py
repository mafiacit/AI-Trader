import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import market_analysis
import trading_bot
import datetime
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
# Generate a secure random secret key if not provided in environment
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
# Handle the case where DATABASE_URL starts with postgres:// instead of postgresql://
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///trading_bot.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models
    import models  # noqa: F401
    
    # Check if we need to recreate tables
    try:
        # Try a simple query to check if tables are correctly structured
        from models import Trade, MarketAnalysis
        Trade.query.limit(1).all()
        MarketAnalysis.query.limit(1).all()
        logger.info("Database tables verified successfully")
    except Exception as e:
        logger.warning(f"Database tables need to be recreated: {str(e)}")
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        logger.info("Database tables recreated successfully")

# Helper function to ensure app context for database operations
def with_app_context(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app:
            # If we're already in an app context, just run the function
            return f(*args, **kwargs)
        else:
            # Otherwise, create an app context
            with app.app_context():
                return f(*args, **kwargs)
    return decorated_function

# Initialize trading bot
bot = trading_bot.TradingBot()

@app.route('/')
def index():
    # Get some basic stats for the dashboard
    bot_status = {
        'telegram_connected': bool(os.environ.get('TELEGRAM_TOKEN')),
        'bot_name': 'AI Trading Bot',
        'current_price': {
            'EURUSD': bot.get_current_price('EURUSD'),
            'GBPUSD': bot.get_current_price('GBPUSD'),
            'USDJPY': bot.get_current_price('USDJPY')
        },
        'open_trades': len(bot.get_open_trades()),
        'total_trades': len(bot.get_trade_history())
    }
    
    # Get latest analysis for a few currency pairs
    try:
        eurusd_analysis = market_analysis.analyze_market('EURUSD')
        bot_status['eurusd_recommendation'] = eurusd_analysis['recommendation']
        bot_status['eurusd_trend'] = eurusd_analysis['trend']
    except:
        # If analysis fails, provide defaults
        bot_status['eurusd_recommendation'] = 'unknown'
        bot_status['eurusd_trend'] = 'neutral'
    
    return render_template('index.html', bot_status=bot_status)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if request.method == 'POST':
        currency_pair = request.form.get('currency_pair', 'EURUSD')
        timeframe = request.form.get('timeframe', '1d')
        
        try:
            analysis_result = market_analysis.analyze_market(currency_pair, timeframe)
            session['analysis_result'] = analysis_result
            
            # Log the successful analysis
            logger.info(f"Market analysis completed for {currency_pair} on {timeframe} timeframe")
            
            return render_template('analysis.html', 
                                  currency_pair=currency_pair,
                                  timeframe=timeframe,
                                  analysis=analysis_result)
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            flash(f"Analysis error: {str(e)}", "danger")
            return render_template('analysis.html', error=str(e))
    
    # Default to EURUSD analysis for GET requests
    currency_pair = request.args.get('currency_pair', 'EURUSD')
    timeframe = request.args.get('timeframe', '1d')
    
    try:
        analysis_result = market_analysis.analyze_market(currency_pair, timeframe)
        session['analysis_result'] = analysis_result
        
        return render_template('analysis.html', 
                              currency_pair=currency_pair,
                              timeframe=timeframe,
                              analysis=analysis_result)
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return render_template('analysis.html', error=str(e))

@app.route('/analyze/<currency_pair>', methods=['GET'])
def analyze_currency(currency_pair):
    timeframe = request.args.get('timeframe', '1d')
    
    try:
        analysis_result = market_analysis.analyze_market(currency_pair, timeframe)
        session['analysis_result'] = analysis_result
        
        return render_template('analysis.html', 
                              currency_pair=currency_pair,
                              timeframe=timeframe,
                              analysis=analysis_result)
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return render_template('analysis.html', error=str(e))

@app.route('/trading', methods=['GET', 'POST'])
def trading():
    # Get open trades to display
    open_trades = bot.get_open_trades()
    
    if request.method == 'POST':
        action = request.form.get('action')
        currency_pair = request.form.get('currency_pair', 'EURUSD')
        amount = float(request.form.get('amount', 1000))
        
        # Initialize result to None
        result = None
        
        try:
            if action == 'buy':
                result = bot.execute_trade(currency_pair, 'buy', amount)
                flash(f"Buy order executed: {currency_pair} at {result['price']}", "success")
            elif action == 'sell':
                result = bot.execute_trade(currency_pair, 'sell', amount)
                flash(f"Sell order executed: {currency_pair} at {result['price']}", "success")
            elif action == 'close':
                trade_id = int(request.form.get('trade_id', 0))
                if trade_id > 0:
                    result = bot.close_trade(trade_id)
                    flash(f"Trade closed with P/L: {result.get('profit_loss', 0):.2f}", "success")
                else:
                    flash("Invalid trade ID", "danger")
            elif action == 'auto':
                # Use the latest analysis to make trading decision
                analysis = session.get('analysis_result', None)
                if not analysis:
                    analysis = market_analysis.analyze_market(currency_pair, '1d')
                
                result = bot.auto_trade(currency_pair, amount, analysis=analysis)
                if result and result.get('status') == 'success':
                    flash(f"Auto trade executed: {currency_pair} at {result.get('price', 0)}", "success")
                elif result and result.get('status') == 'skipped':
                    flash(f"Auto trade skipped: {result.get('reason', 'Unknown reason')}", "info")
                else:
                    flash("No trade was executed", "info")
            
            # Refresh open trades list after action
            open_trades = bot.get_open_trades()
            
            return render_template('trading.html', 
                                  result=result, 
                                  currency_pair=currency_pair,
                                  open_trades=open_trades)
        except Exception as e:
            logger.error(f"Trading error: {str(e)}")
            flash(f"Trading error: {str(e)}", "danger")
            return render_template('trading.html', error=str(e), open_trades=open_trades)
    
    # GET request - just display trading page with open trades
    return render_template('trading.html', open_trades=open_trades)

@app.route('/api/market_data/<currency_pair>')
def get_market_data(currency_pair):
    timeframe = request.args.get('timeframe', '1d')
    try:
        # Get historical data for the chart
        data = market_analysis.get_historical_data(currency_pair, timeframe)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Market data error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/analyze_risk', methods=['POST'])
def analyze_trade_risk():
    """
    API endpoint to analyze the risk of a potential trade using Groq AI.
    
    Expects JSON POST with:
    - trade_details: Details of the trade (type, amount, entry price, etc.)
    - currency_pair: The currency pair to analyze
    - include_portfolio: Whether to include user portfolio in analysis (optional)
    
    Returns a comprehensive risk analysis.
    """
    try:
        # Import here to avoid circular imports
        import groq_ai
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Required fields
        if 'trade_details' not in data or 'currency_pair' not in data:
            return jsonify({'error': 'Missing required fields: trade_details, currency_pair'}), 400
            
        trade_details = data['trade_details']
        currency_pair = data['currency_pair']
        
        # Check for valid format
        required_trade_fields = ['trade_type', 'amount']
        for field in required_trade_fields:
            if field not in trade_details:
                return jsonify({'error': f'Missing required field in trade_details: {field}'}), 400
        
        # Get current market data for the currency pair
        market_data = market_analysis.analyze_market(currency_pair, use_ai=False)
        
        # Get portfolio information if requested
        portfolio_info = None
        if data.get('include_portfolio', False):
            # In a real application, you would get this from the logged-in user
            # For now, we'll use a demo portfolio
            portfolio_info = {
                'balance': 10000.0,  # Demo balance
                'open_trades': trading_bot.TradingBot().get_open_trades()
            }
            
        # Call the risk analyzer
        risk_analysis = groq_ai.analyze_trade_risk(
            trade_details=trade_details,
            market_data=market_data,
            currency_pair=currency_pair,
            portfolio_info=portfolio_info
        )
        
        # Log the successful analysis
        logger.info(f"Risk analysis completed for {currency_pair}: {risk_analysis.get('risk_level', 'unknown')} risk")
        
        # Return the risk analysis
        return jsonify({
            'status': 'success',
            'risk_analysis': risk_analysis,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error analyzing trade risk: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Error analyzing trade risk: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
