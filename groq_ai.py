import os
import logging
import json
import time
from datetime import datetime
import groq
import threading
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rate limiting settings
API_CALLS = {}  # Store API call timestamps
RATE_LIMIT = 5  # Max calls per minute
RATE_WINDOW = 60  # Time window in seconds
RATE_LOCK = threading.Lock()  # Lock for thread safety

# Initialize Groq client
client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Rate limiting decorator
def rate_limited(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with RATE_LOCK:
            current_time = time.time()
            # Clean up old timestamps
            global API_CALLS
            API_CALLS = {k: v for k, v in API_CALLS.items() if current_time - v < RATE_WINDOW}
            
            # Check if we've hit the rate limit
            if len(API_CALLS) >= RATE_LIMIT:
                oldest_call = min(API_CALLS.values())
                sleep_time = RATE_WINDOW - (current_time - oldest_call)
                if sleep_time > 0:
                    logger.warning(f"Rate limit hit. Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
            
            # Register this call
            call_id = id(threading.current_thread())
            API_CALLS[call_id] = time.time()
        
        # Execute the function
        return func(*args, **kwargs)
    return wrapper

@rate_limited
def analyze_market_with_ai(market_data, currency_pair):
    """
    Use Groq AI to analyze market data and provide trading recommendations.
    
    Args:
        market_data (dict): Historical market data and technical indicators
        currency_pair (str): The currency pair being analyzed (e.g., 'EURUSD')
        
    Returns:
        dict: AI-generated market analysis including trend prediction and trade recommendation
    """
    try:
        # Format market data for the AI prompt
        indicators = market_data.get('indicators', {})
        
        # Determine the asset class based on currency pair
        asset_class = "forex"  # Default
        
        if currency_pair in ["BTCUSD", "ETHUSD"]:
            asset_class = "crypto"
        elif currency_pair == "XAUUSD":
            asset_class = "commodity"
            
        # Create a detailed prompt with market information, customized by asset class
        if asset_class == "forex":
            prompt = f"""
As a forex trading expert, analyze the following market data for {currency_pair} and provide a detailed trading recommendation.

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- SMA 20: {indicators.get('sma_20', 'N/A')}
- Bollinger Bands:
  - Upper: {indicators.get('upper_band', 'N/A')}
  - Lower: {indicators.get('lower_band', 'N/A')}

CURRENT PRICE: {market_data.get('current_price', 'N/A')}
SUPPORT LEVEL: {market_data.get('support', 'N/A')}
RESISTANCE LEVEL: {market_data.get('resistance', 'N/A')}

Consider relevant forex factors like interest rate differentials, economic data releases, central bank policies, and geopolitical events.

Based on this data, provide your analysis in the following JSON format:
{{
  "trend": "bullish|bearish|neutral",
  "strength": "value between 0-100",
  "recommendation": "buy|sell|hold",
  "confidence": "value between 0-100",
  "reasoning": "brief explanation",
  "key_factors": ["factor1", "factor2"],
  "risk_assessment": "brief risk analysis",
  "timeframe": "short_term|medium_term|long_term"
}}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "crypto":
            prompt = f"""
As a cryptocurrency trading expert, analyze the following market data for {currency_pair} and provide a detailed trading recommendation.

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- SMA 20: {indicators.get('sma_20', 'N/A')}
- Bollinger Bands:
  - Upper: {indicators.get('upper_band', 'N/A')}
  - Lower: {indicators.get('lower_band', 'N/A')}

CURRENT PRICE: {market_data.get('current_price', 'N/A')}
SUPPORT LEVEL: {market_data.get('support', 'N/A')}
RESISTANCE LEVEL: {market_data.get('resistance', 'N/A')}

Consider relevant crypto factors like market sentiment, adoption trends, regulation news, technological developments, and network metrics.

Based on this data, provide your analysis in the following JSON format:
{{
  "trend": "bullish|bearish|neutral",
  "strength": "value between 0-100",
  "recommendation": "buy|sell|hold",
  "confidence": "value between 0-100",
  "reasoning": "brief explanation focused on crypto-specific factors",
  "key_factors": ["factor1", "factor2"],
  "risk_assessment": "brief risk analysis including volatility considerations",
  "timeframe": "short_term|medium_term|long_term",
  "volatility_risk": "low|medium|high"
}}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "commodity":
            prompt = f"""
As a commodities trading expert, analyze the following market data for Gold (XAUUSD) and provide a detailed trading recommendation.

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- SMA 20: {indicators.get('sma_20', 'N/A')}
- Bollinger Bands:
  - Upper: {indicators.get('upper_band', 'N/A')}
  - Lower: {indicators.get('lower_band', 'N/A')}

CURRENT PRICE: {market_data.get('current_price', 'N/A')}
SUPPORT LEVEL: {market_data.get('support', 'N/A')}
RESISTANCE LEVEL: {market_data.get('resistance', 'N/A')}

Consider relevant gold factors like inflation expectations, US dollar strength, interest rates, market uncertainty, geopolitical risks, and physical demand.

Based on this data, provide your analysis in the following JSON format:
{{
  "trend": "bullish|bearish|neutral",
  "strength": "value between 0-100",
  "recommendation": "buy|sell|hold",
  "confidence": "value between 0-100",
  "reasoning": "brief explanation focused on gold-specific factors",
  "key_factors": ["factor1", "factor2"],
  "risk_assessment": "brief risk analysis",
  "timeframe": "short_term|medium_term|long_term",
  "correlation_to_market_uncertainty": "strong_positive|positive|neutral|negative"
}}
Only respond with the JSON object, no other text.
"""
        else:
            # Generic fallback
            prompt = f"""
As a financial trading expert, analyze the following market data for {currency_pair} and provide a detailed trading recommendation.

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- SMA 20: {indicators.get('sma_20', 'N/A')}
- Bollinger Bands:
  - Upper: {indicators.get('upper_band', 'N/A')}
  - Lower: {indicators.get('lower_band', 'N/A')}

CURRENT PRICE: {market_data.get('current_price', 'N/A')}
SUPPORT LEVEL: {market_data.get('support', 'N/A')}
RESISTANCE LEVEL: {market_data.get('resistance', 'N/A')}

Based on this data, provide your analysis in the following JSON format:
{{
  "trend": "bullish|bearish|neutral",
  "strength": "value between 0-100",
  "recommendation": "buy|sell|hold",
  "confidence": "value between 0-100",
  "reasoning": "brief explanation",
  "key_factors": ["factor1", "factor2"],
  "risk_assessment": "brief risk analysis",
  "timeframe": "short_term|medium_term|long_term"
}}
Only respond with the JSON object, no other text.
"""

        # Call Groq API
        logger.info(f"Calling Groq AI for market analysis of {currency_pair}")
        # Set the appropriate system message based on asset class
        if asset_class == "forex":
            system_message = "You are a financial expert specializing in forex trading and technical analysis with deep knowledge of currency markets, central bank policies, and macroeconomic factors."
        elif asset_class == "crypto":
            system_message = "You are a cryptocurrency trading expert with deep knowledge of blockchain technology, market cycles, on-chain metrics, and crypto-specific technical analysis."
        elif asset_class == "commodity":
            system_message = "You are a commodities trading expert specializing in gold markets with knowledge of inflation impacts, monetary policy, geopolitical factors, and precious metals market dynamics."
        else:
            system_message = "You are a financial expert specializing in trading and technical analysis."
            
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Or "mixtral-8x7b-32768" for more advanced analysis
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Low temperature for more consistent responses
            max_tokens=1024
        )
        
        # Extract the response content
        ai_response = response.choices[0].message.content
        if ai_response:
            ai_response = ai_response.strip()
        else:
            ai_response = "{}"
        
        # Parse JSON response
        try:
            analysis = json.loads(ai_response)
            
            # Validate required fields
            required_fields = ['trend', 'strength', 'recommendation', 'confidence']
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"AI analysis missing required field: {field}")
                    analysis[field] = "neutral" if field == 'trend' else (
                                     "hold" if field == 'recommendation' else 50)
            
            # Log successful analysis
            logger.info(f"Groq AI analysis complete for {currency_pair}: {analysis['recommendation']} ({analysis['confidence']}%)")
            return analysis
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON: {ai_response[:100]}...")
            # Return default analysis
            return {
                "trend": "neutral",
                "strength": 50,
                "recommendation": "hold",
                "confidence": 50,
                "reasoning": "Error parsing AI response",
                "ai_error": True
            }
            
    except Exception as e:
        logger.error(f"Error in Groq AI market analysis: {str(e)}")
        # Return default conservative recommendation
        return {
            "trend": "neutral",
            "strength": 50,
            "recommendation": "hold",
            "confidence": 50,
            "reasoning": f"Error in AI analysis: {str(e)}",
            "ai_error": True
        }

@rate_limited
def evaluate_trade_opportunity(market_data, currency_pair, risk_level="medium"):
    """
    Use Groq AI to evaluate a specific trading opportunity and provide execution details.
    
    Args:
        market_data (dict): Current market data and technical indicators
        currency_pair (str): The currency pair to trade
        risk_level (str): User's risk tolerance (low, medium, high)
        
    Returns:
        dict: Trade execution details including entry, stop loss, and take profit levels
    """
    try:
        # Format market data for the AI prompt
        current_price = market_data.get('current_price', 0)
        support = market_data.get('support', 0)
        resistance = market_data.get('resistance', 0)
        
        # Determine the asset class based on currency pair
        asset_class = "forex"  # Default
        
        if currency_pair in ["BTCUSD", "ETHUSD"]:
            asset_class = "crypto"
        elif currency_pair == "XAUUSD":
            asset_class = "commodity"
        
        # Create detailed prompt based on asset class
        if asset_class == "forex":
            prompt = f"""
As a professional forex trader, evaluate this trading opportunity for {currency_pair} with a {risk_level} risk tolerance.

MARKET DATA:
- Current price: {current_price}
- Support level: {support}
- Resistance level: {resistance}
- Market trend: {market_data.get('trend', 'unknown')}
- Recommendation: {market_data.get('recommendation', 'unknown')}

Consider interest rate differentials, economic calendar events, and forex-specific volatility patterns.

Provide specific trade execution details in the following JSON format:
{{
  "execute_trade": true|false,
  "trade_type": "buy"|"sell",
  "entry_price": "recommended entry price",
  "stop_loss": "stop loss price",
  "take_profit": "take profit price",
  "leverage": "recommended leverage 1-3",
  "position_size_percentage": "percentage of available capital to risk",
  "expected_risk_reward": "calculated risk-reward ratio",
  "reasoning": "brief explanation",
  "confidence": "value between 0-100"
}}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "crypto":
            prompt = f"""
As a professional cryptocurrency trader, evaluate this trading opportunity for {currency_pair} with a {risk_level} risk tolerance.

MARKET DATA:
- Current price: {current_price}
- Support level: {support}
- Resistance level: {resistance}
- Market trend: {market_data.get('trend', 'unknown')}
- Recommendation: {market_data.get('recommendation', 'unknown')}

Consider network metrics, market sentiment, upcoming protocol changes, and crypto-specific volatility patterns.

Provide specific trade execution details in the following JSON format:
{{
  "execute_trade": true|false,
  "trade_type": "buy"|"sell",
  "entry_price": "recommended entry price",
  "stop_loss": "stop loss price with extra margin for crypto volatility",
  "take_profit": "take profit price",
  "leverage": "recommended leverage 1-5",
  "position_size_percentage": "percentage of available capital to risk",
  "expected_risk_reward": "calculated risk-reward ratio",
  "reasoning": "brief explanation",
  "confidence": "value between 0-100",
  "hold_duration": "expected holding period"
}}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "commodity":
            prompt = f"""
As a professional gold trader, evaluate this trading opportunity for Gold (XAUUSD) with a {risk_level} risk tolerance.

MARKET DATA:
- Current price: {current_price}
- Support level: {support}
- Resistance level: {resistance}
- Market trend: {market_data.get('trend', 'unknown')}
- Recommendation: {market_data.get('recommendation', 'unknown')}

Consider inflation data, USD strength, geopolitical events, central bank gold purchases, and seasonal patterns.

Provide specific trade execution details in the following JSON format:
{{
  "execute_trade": true|false,
  "trade_type": "buy"|"sell",
  "entry_price": "recommended entry price",
  "stop_loss": "stop loss price",
  "take_profit": "take profit price",
  "leverage": "recommended leverage 1-3",
  "position_size_percentage": "percentage of available capital to risk",
  "expected_risk_reward": "calculated risk-reward ratio",
  "reasoning": "brief explanation with focus on gold market factors",
  "confidence": "value between 0-100",
  "portfolio_hedging_value": "value as a portfolio hedge (high|medium|low)"
}}
Only respond with the JSON object, no other text.
"""
        else:
            # Generic fallback
            prompt = f"""
As a professional trader, evaluate this trading opportunity for {currency_pair} with a {risk_level} risk tolerance.

MARKET DATA:
- Current price: {current_price}
- Support level: {support}
- Resistance level: {resistance}
- Market trend: {market_data.get('trend', 'unknown')}
- Recommendation: {market_data.get('recommendation', 'unknown')}

Provide specific trade execution details in the following JSON format:
{{
  "execute_trade": true|false,
  "trade_type": "buy"|"sell",
  "entry_price": "recommended entry price",
  "stop_loss": "stop loss price",
  "take_profit": "take profit price",
  "leverage": "recommended leverage 1-3",
  "position_size_percentage": "percentage of available capital to risk",
  "expected_risk_reward": "calculated risk-reward ratio",
  "reasoning": "brief explanation",
  "confidence": "value between 0-100"
}}
Only respond with the JSON object, no other text.
"""

        # Call Groq API
        logger.info(f"Calling Groq AI for trade opportunity evaluation on {currency_pair}")
        
        # Set the appropriate system message based on asset class
        if asset_class == "forex":
            system_message = "You are a professional forex trader with expertise in risk management, trade execution, and deep knowledge of currency market dynamics and central bank policies."
        elif asset_class == "crypto":
            system_message = "You are a professional cryptocurrency trader with expertise in volatility management, blockchain technology, and crypto-specific trading strategies including leverage considerations."
        elif asset_class == "commodity":
            system_message = "You are a professional gold trader with expertise in precious metals markets, macro-economic factors affecting gold, and safe-haven asset trading strategies."
        else:
            system_message = "You are a professional trader with expertise in risk management and trade execution."
            
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024
        )
        
        # Extract the response content
        ai_response = response.choices[0].message.content
        if ai_response:
            ai_response = ai_response.strip()
        else:
            ai_response = "{}"
        
        # Parse JSON response
        try:
            trade_plan = json.loads(ai_response)
            
            # Validate required fields
            required_fields = ['execute_trade', 'trade_type', 'entry_price', 'stop_loss', 'take_profit']
            for field in required_fields:
                if field not in trade_plan:
                    logger.warning(f"AI trade plan missing required field: {field}")
                    if field == 'execute_trade':
                        trade_plan[field] = False
                    elif field == 'trade_type':
                        trade_plan[field] = market_data.get('recommendation', 'hold')
                    else:
                        trade_plan[field] = current_price
            
            # Log successful analysis
            if trade_plan['execute_trade']:
                logger.info(f"Groq AI recommends {trade_plan['trade_type']} trade for {currency_pair}")
            else:
                logger.info(f"Groq AI does not recommend trading {currency_pair} at this time")
                
            return trade_plan
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI trade plan as JSON: {ai_response[:100]}...")
            # Return default trade plan (don't execute)
            return {
                "execute_trade": False,
                "trade_type": "hold",
                "reasoning": "Error parsing AI response",
                "ai_error": True
            }
            
    except Exception as e:
        logger.error(f"Error in Groq AI trade evaluation: {str(e)}")
        # Return default conservative recommendation
        return {
            "execute_trade": False,
            "trade_type": "hold",
            "reasoning": f"Error in AI analysis: {str(e)}",
            "ai_error": True
        }

@rate_limited
def analyze_trade_risk(trade_details, market_data, currency_pair, portfolio_info=None):
    """
    Use Groq AI to analyze the risk profile of a specific trade and provide a comprehensive risk assessment.
    
    Args:
        trade_details (dict): Details of the proposed trade (type, amount, entry price, etc.)
        market_data (dict): Current market data and technical indicators
        currency_pair (str): The currency pair being traded
        portfolio_info (dict): Optional information about the user's current portfolio
        
    Returns:
        dict: Comprehensive risk analysis including risk score, potential downside, and risk factors
    """
    try:
        # Format trade details for the AI prompt
        trade_type = trade_details.get('trade_type', 'buy')
        entry_price = trade_details.get('entry_price', market_data.get('current_price', 0))
        amount = trade_details.get('amount', 1000)
        leverage = trade_details.get('leverage', 1)
        stop_loss = trade_details.get('stop_loss', 0)
        take_profit = trade_details.get('take_profit', 0)
        
        # Calculate notional value and max risk if provided
        notional_value = amount * leverage
        max_risk_amount = "Not specified" if not stop_loss else f"${(entry_price - stop_loss) * amount * leverage if trade_type.lower() == 'buy' else (stop_loss - entry_price) * amount * leverage}"
        
        # Extract market data for the AI prompt
        current_price = market_data.get('current_price', 0)
        market_volatility = market_data.get('volatility', 'medium')
        market_trend = market_data.get('trend', 'neutral')
        
        # Determine if portfolio info is available
        has_portfolio_info = portfolio_info is not None
        portfolio_balance = portfolio_info.get('balance', 0) if has_portfolio_info else "Not provided"
        open_trades = portfolio_info.get('open_trades', []) if has_portfolio_info else []
        
        # Determine the asset class based on currency pair
        asset_class = "forex"  # Default
        
        if currency_pair in ["BTCUSD", "ETHUSD"]:
            asset_class = "crypto"
        elif currency_pair == "XAUUSD":
            asset_class = "commodity"
        
        # Create detailed prompt based on asset class
        if asset_class == "forex":
            prompt = f"""
As a risk management specialist in forex trading, analyze the following trade for {currency_pair} and provide a comprehensive risk assessment.

TRADE DETAILS:
- Trade type: {trade_type.upper()}
- Entry price: {entry_price}
- Trade amount: ${amount}
- Leverage: {leverage}x
- Notional value: ${notional_value}
- Stop loss: {stop_loss if stop_loss else "Not specified"}
- Take profit: {take_profit if take_profit else "Not specified"}
- Maximum risk amount: {max_risk_amount}

MARKET CONDITIONS:
- Current price: {current_price}
- Market trend: {market_trend}
- Support level: {market_data.get('support', 'N/A')}
- Resistance level: {market_data.get('resistance', 'N/A')}
- Market volatility: {market_volatility}

{"PORTFOLIO INFORMATION:" if has_portfolio_info else ""}
{"- Account balance: $" + str(portfolio_balance) if has_portfolio_info else ""}
{"- Number of open trades: " + str(len(open_trades)) if has_portfolio_info else ""}

Consider forex-specific risks including spread costs, overnight financing, slippage during high volatility, weekend gaps, and central bank announcements.

Analyze both macro and micro risk factors and provide a comprehensive risk assessment in the following JSON format:
{
  "risk_score": "value between 1-100, higher means riskier",
  "risk_level": "low|moderate|high|extreme",
  "maximum_drawdown_percent": "estimated maximum drawdown as percentage",
  "maximum_loss_amount": "estimated maximum loss in dollars",
  "probability_of_stop_loss_hit": "percentage chance of hitting stop loss",
  "probability_of_take_profit_hit": "percentage chance of hitting take profit",
  "risk_reward_ratio": "calculated risk:reward ratio",
  "risk_factors": [
    {"factor": "name of risk factor", "impact": "high|medium|low", "description": "brief description"}
  ],
  "position_sizing_recommendation": "recommendation on appropriate position size",
  "leverage_recommendation": "recommendation on appropriate leverage",
  "missing_risk_controls": ["stop loss", "take profit", etc.] (if any),
  "market_specific_risks": ["spread widening", "interest rate announcement", etc.],
  "protective_measures": ["recommended actions to reduce risk"],
  "overall_assessment": "brief overall risk assessment",
  "confidence_level": "confidence in this risk assessment (0-100)"
}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "crypto":
            prompt = f"""
As a risk management specialist in cryptocurrency trading, analyze the following trade for {currency_pair} and provide a comprehensive risk assessment.

TRADE DETAILS:
- Trade type: {trade_type.upper()}
- Entry price: {entry_price}
- Trade amount: ${amount}
- Leverage: {leverage}x
- Notional value: ${notional_value}
- Stop loss: {stop_loss if stop_loss else "Not specified"}
- Take profit: {take_profit if take_profit else "Not specified"}
- Maximum risk amount: {max_risk_amount}

MARKET CONDITIONS:
- Current price: {current_price}
- Market trend: {market_trend}
- Support level: {market_data.get('support', 'N/A')}
- Resistance level: {market_data.get('resistance', 'N/A')}
- Market volatility: {market_volatility}

{"PORTFOLIO INFORMATION:" if has_portfolio_info else ""}
{"- Account balance: $" + str(portfolio_balance) if has_portfolio_info else ""}
{"- Number of open trades: " + str(len(open_trades)) if has_portfolio_info else ""}

Consider crypto-specific risks including extreme volatility, flash crashes, regulatory announcements, security breaches, fork events, and liquidity issues.

Analyze both macro and micro risk factors and provide a comprehensive risk assessment in the following JSON format:
{
  "risk_score": "value between 1-100, higher means riskier",
  "risk_level": "low|moderate|high|extreme",
  "maximum_drawdown_percent": "estimated maximum drawdown as percentage",
  "maximum_loss_amount": "estimated maximum loss in dollars",
  "probability_of_stop_loss_hit": "percentage chance of hitting stop loss",
  "probability_of_take_profit_hit": "percentage chance of hitting take profit",
  "risk_reward_ratio": "calculated risk:reward ratio",
  "risk_factors": [
    {"factor": "name of risk factor", "impact": "high|medium|low", "description": "brief description"}
  ],
  "position_sizing_recommendation": "recommendation on appropriate position size",
  "leverage_recommendation": "recommendation on appropriate leverage",
  "missing_risk_controls": ["stop loss", "take profit", etc.] (if any),
  "market_specific_risks": ["high volatility", "liquidity issues", "regulatory announcements", etc.],
  "protective_measures": ["recommended actions to reduce risk"],
  "overall_assessment": "brief overall risk assessment",
  "confidence_level": "confidence in this risk assessment (0-100)",
  "volatility_adjustment": "percentage to widen stop loss to account for crypto volatility"
}
Only respond with the JSON object, no other text.
"""
        elif asset_class == "commodity":
            prompt = f"""
As a risk management specialist in commodity trading, analyze the following Gold (XAUUSD) trade and provide a comprehensive risk assessment.

TRADE DETAILS:
- Trade type: {trade_type.upper()}
- Entry price: {entry_price}
- Trade amount: ${amount}
- Leverage: {leverage}x
- Notional value: ${notional_value}
- Stop loss: {stop_loss if stop_loss else "Not specified"}
- Take profit: {take_profit if take_profit else "Not specified"}
- Maximum risk amount: {max_risk_amount}

MARKET CONDITIONS:
- Current price: {current_price}
- Market trend: {market_trend}
- Support level: {market_data.get('support', 'N/A')}
- Resistance level: {market_data.get('resistance', 'N/A')}
- Market volatility: {market_volatility}

{"PORTFOLIO INFORMATION:" if has_portfolio_info else ""}
{"- Account balance: $" + str(portfolio_balance) if has_portfolio_info else ""}
{"- Number of open trades: " + str(len(open_trades)) if has_portfolio_info else ""}

Consider gold-specific risks including inflation reports, Fed interest rate decisions, USD strength, geopolitical events, and changes in physical demand.

Analyze both macro and micro risk factors and provide a comprehensive risk assessment in the following JSON format:
{
  "risk_score": "value between 1-100, higher means riskier",
  "risk_level": "low|moderate|high|extreme",
  "maximum_drawdown_percent": "estimated maximum drawdown as percentage",
  "maximum_loss_amount": "estimated maximum loss in dollars",
  "probability_of_stop_loss_hit": "percentage chance of hitting stop loss",
  "probability_of_take_profit_hit": "percentage chance of hitting take profit",
  "risk_reward_ratio": "calculated risk:reward ratio",
  "risk_factors": [
    {"factor": "name of risk factor", "impact": "high|medium|low", "description": "brief description"}
  ],
  "position_sizing_recommendation": "recommendation on appropriate position size",
  "leverage_recommendation": "recommendation on appropriate leverage",
  "missing_risk_controls": ["stop loss", "take profit", etc.] (if any),
  "market_specific_risks": ["Fed announcements", "inflation data", "geopolitical events", etc.],
  "protective_measures": ["recommended actions to reduce risk"],
  "portfolio_diversification_effect": "effect on portfolio diversification",
  "overall_assessment": "brief overall risk assessment",
  "confidence_level": "confidence in this risk assessment (0-100)"
}
Only respond with the JSON object, no other text.
"""
        else:
            # Generic fallback
            prompt = f"""
As a risk management specialist in financial trading, analyze the following trade for {currency_pair} and provide a comprehensive risk assessment.

TRADE DETAILS:
- Trade type: {trade_type.upper()}
- Entry price: {entry_price}
- Trade amount: ${amount}
- Leverage: {leverage}x
- Notional value: ${notional_value}
- Stop loss: {stop_loss if stop_loss else "Not specified"}
- Take profit: {take_profit if take_profit else "Not specified"}
- Maximum risk amount: {max_risk_amount}

MARKET CONDITIONS:
- Current price: {current_price}
- Market trend: {market_trend}
- Support level: {market_data.get('support', 'N/A')}
- Resistance level: {market_data.get('resistance', 'N/A')}
- Market volatility: {market_volatility}

{"PORTFOLIO INFORMATION:" if has_portfolio_info else ""}
{"- Account balance: $" + str(portfolio_balance) if has_portfolio_info else ""}
{"- Number of open trades: " + str(len(open_trades)) if has_portfolio_info else ""}

Analyze both macro and micro risk factors and provide a comprehensive risk assessment in the following JSON format:
{
  "risk_score": "value between 1-100, higher means riskier",
  "risk_level": "low|moderate|high|extreme",
  "maximum_drawdown_percent": "estimated maximum drawdown as percentage",
  "maximum_loss_amount": "estimated maximum loss in dollars",
  "probability_of_stop_loss_hit": "percentage chance of hitting stop loss",
  "probability_of_take_profit_hit": "percentage chance of hitting take profit",
  "risk_reward_ratio": "calculated risk:reward ratio",
  "risk_factors": [
    {"factor": "name of risk factor", "impact": "high|medium|low", "description": "brief description"}
  ],
  "position_sizing_recommendation": "recommendation on appropriate position size",
  "leverage_recommendation": "recommendation on appropriate leverage",
  "missing_risk_controls": ["stop loss", "take profit", etc.] (if any),
  "protective_measures": ["recommended actions to reduce risk"],
  "overall_assessment": "brief overall risk assessment",
  "confidence_level": "confidence in this risk assessment (0-100)"
}
Only respond with the JSON object, no other text.
"""

        # Call Groq API
        logger.info(f"Calling Groq AI for trade risk analysis on {currency_pair}")
        
        # Set the appropriate system message based on asset class
        if asset_class == "forex":
            system_message = "You are a risk management expert specializing in forex markets with deep understanding of technical and fundamental risk factors, position sizing, and risk-reward optimization."
        elif asset_class == "crypto":
            system_message = "You are a risk management expert specializing in cryptocurrency markets with understanding of the unique volatility patterns, liquidity risks, and regulatory impacts on digital assets."
        elif asset_class == "commodity":
            system_message = "You are a risk management expert specializing in gold and commodity markets with understanding of how macroeconomic factors, inflation, and geopolitical events impact risk profiles."
        else:
            system_message = "You are a risk management expert specializing in financial markets."
            
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Or "mixtral-8x7b-32768" for more advanced analysis
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Low temperature for more consistent responses
            max_tokens=1024
        )
        
        # Extract the response content
        ai_response = response.choices[0].message.content
        if ai_response:
            ai_response = ai_response.strip()
        else:
            ai_response = "{}"
        
        # Parse JSON response
        try:
            risk_analysis = json.loads(ai_response)
            
            # Validate required fields
            required_fields = ['risk_score', 'risk_level', 'risk_factors', 'overall_assessment']
            for field in required_fields:
                if field not in risk_analysis:
                    logger.warning(f"AI risk analysis missing required field: {field}")
                    if field == 'risk_score':
                        risk_analysis[field] = 50
                    elif field == 'risk_level':
                        risk_analysis[field] = 'moderate'
                    elif field == 'risk_factors':
                        risk_analysis[field] = [{"factor": "Unknown", "impact": "medium", "description": "Risk factors could not be determined"}]
                    elif field == 'overall_assessment':
                        risk_analysis[field] = "Insufficient data for complete risk assessment"
            
            # Log successful analysis
            logger.info(f"Groq AI risk analysis complete for {currency_pair} trade: {risk_analysis['risk_level']} risk (score: {risk_analysis['risk_score']})")
            return risk_analysis
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI risk analysis as JSON: {ai_response[:100]}...")
            # Return default risk analysis
            return {
                "risk_score": 75,  # Conservative high risk score by default
                "risk_level": "high",
                "risk_factors": [
                    {"factor": "Analysis Error", "impact": "high", "description": "Unable to properly analyze risk due to parsing error"}
                ],
                "overall_assessment": "Unable to properly analyze risk. Consider this a high-risk trade until proper assessment is completed.",
                "ai_error": True
            }
            
    except Exception as e:
        logger.error(f"Error in Groq AI risk analysis: {str(e)}")
        # Return default conservative risk assessment
        return {
            "risk_score": 80,  # Highest risk due to error
            "risk_level": "extreme",
            "risk_factors": [
                {"factor": "Analysis Failure", "impact": "high", "description": f"Error in risk analysis: {str(e)}"}
            ],
            "overall_assessment": "Risk analysis failed. Consider this an extremely high-risk trade until proper assessment is completed.",
            "ai_error": True
        }