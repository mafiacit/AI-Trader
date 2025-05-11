import logging
import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import random
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MarketAnalysis')

def get_historical_data(currency_pair, timeframe='1d', periods=100):
    """
    Get historical data for the specified currency pair and timeframe.
    In a real application, this would call a market data API.
    """
    logger.info(f"Getting historical data for {currency_pair} on {timeframe} timeframe")
    
    # Simulated historical data generation
    end_date = datetime.datetime.now()
    
    # Calculate time delta based on timeframe
    if timeframe == '1h':
        delta = datetime.timedelta(hours=1)
    elif timeframe == '4h':
        delta = datetime.timedelta(hours=4)
    elif timeframe == '1d':
        delta = datetime.timedelta(days=1)
    else:
        delta = datetime.timedelta(days=1)  # Default to daily
        
    dates = [(end_date - i * delta).strftime('%Y-%m-%d %H:%M:%S') for i in range(periods, 0, -1)]
    
    # Generate simulated price data based on currency pair
    if currency_pair == 'EURUSD':
        # Start with a realistic base price
        base_price = 1.10
        volatility = 0.002
        volatility_multiplier = 0.01  # 1% daily volatility
    elif currency_pair == 'GBPUSD':
        base_price = 1.25
        volatility = 0.003
        volatility_multiplier = 0.01
    elif currency_pair == 'USDJPY':
        base_price = 150.0
        volatility = 0.2
        volatility_multiplier = 0.01
    elif currency_pair == 'AUDUSD':
        base_price = 0.75
        volatility = 0.003
        volatility_multiplier = 0.01
    elif currency_pair == 'USDCAD':
        base_price = 1.35
        volatility = 0.0025
        volatility_multiplier = 0.01
    elif currency_pair == 'XAUUSD':  # Gold
        base_price = 2300.0
        volatility = 20.0  # Fixed high volatility value
        volatility_multiplier = 0.015  # 1.5% daily volatility
    elif currency_pair == 'BTCUSD':  # Bitcoin
        base_price = 60000.0
        volatility = 500.0  # Fixed high volatility value
        volatility_multiplier = 0.03  # 3% daily volatility
    elif currency_pair == 'ETHUSD':  # Ethereum
        base_price = 3500.0
        volatility = 100.0  # Fixed high volatility value
        volatility_multiplier = 0.04  # 4% daily volatility
    else:
        base_price = 1.0
        volatility = 0.001
        volatility_multiplier = 0.01
    
    # Generate a random walk for the prices with controlled volatility
    prices = [base_price]
    
    for i in range(periods):
        # Normal daily percentage change with controlled volatility
        daily_change = np.random.normal(0, volatility_multiplier)
        # Cap the change to prevent extreme values
        daily_change = max(min(daily_change, volatility_multiplier*3), -volatility_multiplier*3)
        next_price = prices[-1] * (1 + daily_change)
        prices.append(next_price)
    
    prices = prices[1:]  # Remove the initial seed price
    
    # Create simulated OHLC data
    data = []
    for i in range(periods):
        open_price = prices[i]
        # Create realistic high/low range based on asset type
        high_price = open_price * (1 + abs(np.random.normal(0, volatility_multiplier/2)))
        low_price = open_price * (1 - abs(np.random.normal(0, volatility_multiplier/2)))
        close_price = prices[i]
        
        # Ensure high is the highest and low is the lowest
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Simulated volume
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'date': dates[i],
            'open': round(open_price, 5),
            'high': round(high_price, 5),
            'low': round(low_price, 5),
            'close': round(close_price, 5),
            'volume': volume
        })
    
    logger.info(f"Generated {periods} periods of simulated data for {currency_pair}")
    return data

def calculate_indicators(df):
    """Calculate technical indicators on the price data."""
    # Short and long moving averages
    df['sma_5'] = df['close'].rolling(window=5).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()
    
    # Relative Strength Index (RSI)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Moving Average Convergence Divergence (MACD)
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['std_20'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma_20'] + (df['std_20'] * 2)
    df['lower_band'] = df['sma_20'] - (df['std_20'] * 2)
    
    return df

def prepare_features(df):
    """Prepare features for the ML model."""
    # Calculate price changes
    df['price_change'] = df['close'].pct_change()
    df['price_change_1d'] = df['close'].pct_change(periods=1)
    df['price_change_5d'] = df['close'].pct_change(periods=5)
    
    # Calculate indicator-based features
    df['above_sma_20'] = (df['close'] > df['sma_20']).astype(int)
    df['sma_cross'] = ((df['sma_5'] > df['sma_20']) & 
                      (df['sma_5'].shift(1) <= df['sma_20'].shift(1))).astype(int)
    
    df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
    df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
    
    df['macd_cross_up'] = ((df['macd'] > df['macd_signal']) & 
                          (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
    df['macd_cross_down'] = ((df['macd'] < df['macd_signal']) & 
                            (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
    
    # Volatility features
    df['volatility'] = df['std_20'] / df['sma_20']
    
    # Clean up any NaN values
    df = df.dropna()
    
    return df

def predict_market_direction(df):
    """
    Use machine learning to predict market direction.
    In a real application, this would use a properly trained model.
    """
    # In this simplified version, we'll use a basic heuristic approach
    # based on the technical indicators
    
    # Get the latest data point
    latest = df.iloc[-1]
    
    # Calculate a market sentiment score based on indicators
    sentiment_score = 0
    
    # Moving average signals
    if latest['close'] > latest['sma_20']:
        sentiment_score += 1
    else:
        sentiment_score -= 1
        
    if latest['sma_5'] > latest['sma_20']:
        sentiment_score += 1
    else:
        sentiment_score -= 1
    
    # RSI signals
    if latest['rsi'] > 70:
        sentiment_score -= 1  # Overbought
    elif latest['rsi'] < 30:
        sentiment_score += 1  # Oversold
        
    # MACD signals
    if latest['macd'] > latest['macd_signal']:
        sentiment_score += 1
    else:
        sentiment_score -= 1
        
    # Bollinger Bands signals
    if latest['close'] > latest['upper_band']:
        sentiment_score -= 1  # Overbought
    elif latest['close'] < latest['lower_band']:
        sentiment_score += 1  # Oversold
    
    # Generate prediction
    if sentiment_score >= 2:
        prediction = 'buy'
        confidence = min(50 + 10 * sentiment_score, 95)
    elif sentiment_score <= -2:
        prediction = 'sell'
        confidence = min(50 + 10 * abs(sentiment_score), 95)
    else:
        prediction = 'hold'
        confidence = 50
        
    return prediction, confidence

def analyze_market(currency_pair, timeframe='1d', use_ai=True):
    """
    Analyze the market for the specified currency pair and timeframe.
    Returns a comprehensive analysis including trend, support/resistance, and recommendations.
    
    Args:
        currency_pair (str): The currency pair to analyze (e.g., 'EURUSD')
        timeframe (str): The timeframe for analysis (e.g., '1d', '4h', '1h')
        use_ai (bool): Whether to use Groq AI for enhanced analysis
        
    Returns:
        dict: A comprehensive market analysis
    """
    logger.info(f"Analyzing market for {currency_pair} on {timeframe} timeframe")
    
    try:
        # Get historical data
        historical_data = get_historical_data(currency_pair, timeframe)
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(historical_data)
        
        # Calculate technical indicators
        df = calculate_indicators(df)
        
        # Prepare features for prediction
        df = prepare_features(df)
        
        # Make prediction
        recommendation, confidence = predict_market_direction(df)
        
        # Latest price data
        latest = df.iloc[-1]
        current_price = latest['close']
        
        # Determine trend
        if latest['sma_5'] > latest['sma_20'] and latest['close'] > latest['sma_20']:
            trend = 'bullish'
            strength = min(50 + 10 * (latest['rsi'] - 50), 95) if latest['rsi'] > 50 else 50
        elif latest['sma_5'] < latest['sma_20'] and latest['close'] < latest['sma_20']:
            trend = 'bearish'
            strength = min(50 + 10 * (50 - latest['rsi']), 95) if latest['rsi'] < 50 else 50
        else:
            trend = 'neutral'
            strength = 50
            
        # Support and resistance levels
        # In a real system, these would be calculated using more sophisticated methods
        # For this demo, we'll use a simplified approach based on recent highs/lows
        recent_data = df.tail(20)
        
        # Support: a level where price has bounced up multiple times
        # We'll use a simple calculation based on recent lows
        support = recent_data['low'].min() * 0.998  # Slightly below recent lows
        
        # Resistance: a level where price has bounced down multiple times
        # We'll use a simple calculation based on recent highs
        resistance = recent_data['high'].max() * 1.002  # Slightly above recent highs
        
        # Compile indicators
        indicators_dict = {
            'rsi': round(latest['rsi'], 2),
            'macd': round(latest['macd'], 5),
            'macd_signal': round(latest['macd_signal'], 5),
            'sma_20': round(latest['sma_20'], 5),
            'upper_band': round(latest['upper_band'], 5),
            'lower_band': round(latest['lower_band'], 5)
        }
        
        # Try to enhance analysis with Groq AI if available and requested
        ai_analysis = None
        if use_ai:
            try:
                import groq_ai
                import os
                
                # Only proceed if we have a Groq API key
                if os.environ.get("GROQ_API_KEY"):
                    # Create initial analysis dict for AI
                    initial_analysis = {
                        'currency_pair': currency_pair,
                        'timeframe': timeframe,
                        'current_price': float(current_price),
                        'trend': trend,
                        'strength': float(strength),
                        'support': float(round(support, 5)),
                        'resistance': float(round(resistance, 5)),
                        'recommendation': recommendation,
                        'confidence': float(confidence),
                        'indicators': indicators_dict
                    }
                    
                    # Get AI analysis
                    ai_analysis = groq_ai.analyze_market_with_ai(initial_analysis, currency_pair)
                    
                    # Enhance our analysis with AI insights if available
                    if ai_analysis and not ai_analysis.get('ai_error', False):
                        # Update with AI recommendations if confidence is higher
                        if ai_analysis.get('confidence', 0) > confidence:
                            recommendation = ai_analysis.get('recommendation', recommendation)
                            confidence = ai_analysis.get('confidence', confidence)
                            trend = ai_analysis.get('trend', trend)
                            strength = ai_analysis.get('strength', strength)
                            
                        logger.info(f"Enhanced analysis with Groq AI: {recommendation} ({confidence}%)")
                
            except ImportError:
                logger.warning("Groq AI module not available")
            except Exception as ai_error:
                logger.error(f"Error using Groq AI for analysis: {str(ai_error)}")
        
        # Save analysis to database
        try:
            from app import db, with_app_context
            from models import MarketAnalysis
            
            # Ensure we have an app context for database operations
            @with_app_context
            def save_to_database():
                # Check if we have a recent analysis (less than 10 minutes old)
                now = datetime.datetime.utcnow()
                ten_minutes_ago = now - datetime.timedelta(minutes=10)
                
                # Try to find recent analysis
                existing_analysis = MarketAnalysis.query.filter_by(
                    currency_pair=currency_pair,
                    timeframe=timeframe
                ).filter(
                    MarketAnalysis.timestamp > ten_minutes_ago
                ).order_by(
                    MarketAnalysis.timestamp.desc()
                ).first()
                
                if existing_analysis:
                    # Update existing analysis
                    analysis_record = existing_analysis
                else:
                    # Create new analysis
                    analysis_record = MarketAnalysis(
                        currency_pair=currency_pair,
                        timeframe=timeframe
                    )
                
                # Update fields - convert any numpy types to native Python types
                analysis_record.trend = str(trend)
                analysis_record.strength = float(strength)
                analysis_record.support = float(round(support, 5))
                analysis_record.resistance = float(round(resistance, 5))
                analysis_record.recommendation = str(recommendation)
                analysis_record.confidence = float(confidence)
                analysis_record.current_price = float(current_price)
                analysis_record.timestamp = now
                
                # Convert any numpy values in indicators to native Python types
                clean_indicators = {}
                for key, value in indicators_dict.items():
                    if hasattr(value, 'item'):  # Check if it's a numpy type
                        clean_indicators[key] = value.item()  # Convert to native Python type
                    else:
                        clean_indicators[key] = value
                
                # Add AI insights to indicators if available
                if ai_analysis:
                    clean_indicators['ai_reasoning'] = ai_analysis.get('reasoning', '')
                    clean_indicators['ai_risk_assessment'] = ai_analysis.get('risk_assessment', '')
                    clean_indicators['ai_timeframe'] = ai_analysis.get('timeframe', '')
                    if 'key_factors' in ai_analysis:
                        clean_indicators['ai_key_factors'] = str(ai_analysis['key_factors'])
                        
                analysis_record.set_indicators(clean_indicators)
                
                # Save to database
                db.session.add(analysis_record)
                db.session.commit()
                
                logger.info("Analytics data saved successfully to database")
                return analysis_record, now, clean_indicators
            
            # Execute the database operation with proper context
            analysis_record, now, clean_indicators = save_to_database()
            
            # Compile analysis results for return
            analysis = {
                'id': analysis_record.id,
                'currency_pair': currency_pair,
                'timeframe': timeframe,
                'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                'current_price': float(current_price),
                'trend': trend,
                'strength': float(strength),
                'support': float(round(support, 5)),
                'resistance': float(round(resistance, 5)),
                'recommendation': recommendation,
                'confidence': float(confidence),
                'indicators': clean_indicators,
                'historical_data': [{
                    'date': row['date'],
                    'close': float(row['close'])
                } for _, row in df.tail(30).iterrows()]
            }
            
            # Add AI analysis if available
            if ai_analysis:
                analysis['ai_analysis'] = ai_analysis
            
        except Exception as e:
            logger.warning(f"Could not save analytics data to database: {str(e)}")
            
            # If database save fails, still return analysis
            analysis = {
                'currency_pair': currency_pair,
                'timeframe': timeframe,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'current_price': float(current_price),
                'trend': trend,
                'strength': float(strength),
                'support': float(round(support, 5)),
                'resistance': float(round(resistance, 5)),
                'recommendation': recommendation,
                'confidence': float(confidence),
                'indicators': indicators_dict,
                'historical_data': [{
                    'date': row['date'],
                    'close': float(row['close'])
                } for _, row in df.tail(30).iterrows()]
            }
            
            # Add AI analysis if available
            if ai_analysis:
                analysis['ai_analysis'] = ai_analysis
            
            # Also try to save to file as backup
            try:
                filename = f"analysis_{currency_pair}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(analysis, f, indent=2)
                logger.info("Analytics data saved to file as backup")
            except Exception as file_error:
                logger.warning(f"Could not save analytics data to file: {str(file_error)}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in market analysis: {str(e)}")
        raise Exception(f"Market analysis failed: {str(e)}")
