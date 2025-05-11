import logging
import datetime
import random
import numpy as np
import pandas as pd
from market_analysis import analyze_market
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TradingBot')

class TradingBot:
    def __init__(self):
        self.logger = logger
        self.current_prices = {
            'EURUSD': 1.1053,  # Starting with a realistic initial price
            'GBPUSD': 1.2534,
            'USDJPY': 150.25,
            'AUDUSD': 0.6543,
            'USDCAD': 1.3456
        }
        self.volatility = {
            'EURUSD': 0.0015,  # Daily volatility for simulation
            'GBPUSD': 0.0018,
            'USDJPY': 0.0020,
            'AUDUSD': 0.0025,
            'USDCAD': 0.0016
        }
        self.last_analysis = {}
        self.logger.info("Trading bot initialized")
        
    def get_current_price(self, currency_pair):
        """Simulate getting current price for the currency pair."""
        # In a real system, this would call an API to get the actual price
        if currency_pair not in self.current_prices:
            # Default value for pairs we don't track
            self.current_prices[currency_pair] = 1.0
            self.volatility[currency_pair] = 0.001
            
        # Simulate small price movement
        price_change = np.random.normal(0, self.volatility[currency_pair])
        self.current_prices[currency_pair] *= (1 + price_change)
        
        # Round to 5 decimal places for FX pairs
        return round(self.current_prices[currency_pair], 5)
    
    def execute_trade(self, currency_pair, trade_type, amount, user_id=None, source='web', leverage=1, expiry_minutes=None, pocket_option=False):
        """Execute a trade based on user input.
        
        Args:
            currency_pair (str): The currency pair to trade (e.g., 'EURUSD')
            trade_type (str): 'buy' or 'sell'
            amount (float): Trade amount in USD
            user_id (int, optional): User ID for the trade
            source (str, optional): Source of the trade (web, telegram, auto)
            leverage (int, optional): Leverage multiplier
            expiry_minutes (int, optional): For pocket options, the expiry time in minutes
            pocket_option (bool, optional): Whether this is a pocket/binary option trade
            
        Returns:
            dict: Trade information
        """
        try:
            allowed_types = ['buy', 'sell']
            if pocket_option:
                allowed_types.extend(['call', 'put'])  # Binary options use call/put terminology
                
            if trade_type not in allowed_types:
                raise ValueError(f"Trade type must be one of {', '.join(allowed_types)}")
                
            current_price = self.get_current_price(currency_pair)
            
            # Save trade to database
            try:
                from app import db
                from models import Trade, User
                
                # Create new trade record
                trade = Trade(
                    user_id=user_id,
                    currency_pair=currency_pair,
                    trade_type=trade_type,
                    amount=amount,
                    price=current_price,
                    status='open',
                    leverage=leverage,
                    source=source
                )
                
                # For pocket options, set an expiry time
                if pocket_option and expiry_minutes:
                    from datetime import datetime, timedelta
                    trade.pocket_option = True
                    trade.expiry_timestamp = datetime.utcnow() + timedelta(minutes=expiry_minutes)
                
                # Update user balance if user_id is provided
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        # For simplicity, we'll just check if the user has enough balance
                        if user.account_balance >= amount:
                            # No need to deduct from balance as we're using virtual currency
                            # but in a real system we would update the available balance
                            pass
                        else:
                            raise ValueError(f"Insufficient balance: {user.account_balance} < {amount}")
                
                # Save trade to database
                db.session.add(trade)
                db.session.commit()
                
                self.logger.info(f"Trade executed and saved to database: {trade}")
                
                # Return trade dict for API
                return {
                    'status': 'success',
                    'trade_id': trade.id,
                    'currency_pair': currency_pair,
                    'type': trade_type,
                    'amount': amount,
                    'price': current_price,
                    'timestamp': trade.open_timestamp
                }
            
            except Exception as db_error:
                self.logger.error(f"Database error when executing trade: {str(db_error)}")
                
                # If database save fails, return trade as dictionary with fallback ID
                return {
                    'status': 'success',
                    'trade_id': 0,  # Placeholder ID
                    'currency_pair': currency_pair,
                    'type': trade_type,
                    'amount': amount,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'error': str(db_error)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def auto_trade(self, currency_pair, amount, user_id=None, analysis=None):
        """Execute a trade based on AI analysis."""
        try:
            if not analysis:
                # Get market analysis if not provided
                analysis = analyze_market(currency_pair, '1d')
                
            self.last_analysis[currency_pair] = analysis
            
            # Determine trade action based on analysis
            recommendation = analysis['recommendation']
            confidence = analysis['confidence']
            
            # Only trade if confidence is high enough
            if confidence < 70:
                self.logger.info(f"Not trading {currency_pair} - confidence too low ({confidence}%)")
                return {
                    'status': 'skipped',
                    'reason': f'Confidence too low ({confidence}%)',
                    'recommendation': recommendation
                }
                
            # Execute the recommended trade
            if recommendation == 'buy':
                result = self.execute_trade(currency_pair, 'buy', amount, user_id, 'auto')
                
                # Try to update the trade with analysis_id if available
                if result['status'] == 'success' and 'id' in analysis and result['trade_id'] > 0:
                    try:
                        from app import db
                        from models import Trade
                        
                        trade = Trade.query.get(result['trade_id'])
                        if trade:
                            trade.analysis_id = analysis['id']
                            db.session.commit()
                    except Exception as e:
                        self.logger.error(f"Error linking trade to analysis: {str(e)}")
                
                return result
                
            elif recommendation == 'sell':
                result = self.execute_trade(currency_pair, 'sell', amount, user_id, 'auto')
                
                # Try to update the trade with analysis_id if available
                if result['status'] == 'success' and 'id' in analysis and result['trade_id'] > 0:
                    try:
                        from app import db
                        from models import Trade
                        
                        trade = Trade.query.get(result['trade_id'])
                        if trade:
                            trade.analysis_id = analysis['id']
                            db.session.commit()
                    except Exception as e:
                        self.logger.error(f"Error linking trade to analysis: {str(e)}")
                
                return result
                
            else:
                # Hold recommendation
                self.logger.info(f"Not trading {currency_pair} - recommendation is to hold")
                return {
                    'status': 'skipped',
                    'reason': 'Analysis recommends holding',
                    'recommendation': recommendation
                }
        except Exception as e:
            self.logger.error(f"Error in auto-trade: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def close_trade(self, trade_id):
        """Close an open trade."""
        try:
            # Try to find and close trade in database
            from app import db
            from models import Trade, User
            
            trade = Trade.query.get(trade_id)
            if not trade or trade.status != 'open':
                self.logger.error(f"Invalid trade ID: {trade_id} or trade already closed")
                return {'status': 'error', 'message': 'Invalid trade ID or trade already closed'}
                
            # Get current price to calculate profit/loss
            current_price = self.get_current_price(trade.currency_pair)
            
            # Calculate profit/loss
            if trade.trade_type == 'buy':
                profit_loss = (current_price - trade.price) * trade.amount * trade.leverage
            else:  # sell
                profit_loss = (trade.price - current_price) * trade.amount * trade.leverage
                
            # Update trade record
            trade.status = 'closed'
            trade.close_price = current_price
            trade.close_timestamp = datetime.now()
            trade.profit_loss = round(profit_loss, 2)
            
            # Update user balance if applicable
            if trade.user_id:
                user = User.query.get(trade.user_id)
                if user:
                    user.account_balance += profit_loss
            
            db.session.commit()
            
            self.logger.info(f"Closed trade {trade_id} with P/L: {profit_loss:.2f}")
            
            return {
                'status': 'success',
                'trade_id': trade_id,
                'profit_loss': profit_loss,
                'close_price': current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error closing trade: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
        
    def get_open_trades(self, user_id=None, limit=20):
        """Get all open trades."""
        try:
            from models import Trade
            
            query = Trade.query.filter_by(status='open')
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            # Order by most recent first and limit
            query = query.order_by(Trade.open_timestamp.desc()).limit(limit)
            
            # Get results as list of dictionaries
            open_trades = []
            for trade in query.all():
                trade_dict = {
                    'id': trade.id,
                    'currency_pair': trade.currency_pair,
                    'type': trade.trade_type,
                    'amount': trade.amount,
                    'price': trade.price,
                    'timestamp': trade.open_timestamp,
                    'status': trade.status,
                    'leverage': trade.leverage,
                    'user_id': trade.user_id,
                    'source': trade.source
                }
                open_trades.append(trade_dict)
                
            return open_trades
            
        except Exception as e:
            self.logger.error(f"Error getting open trades: {str(e)}")
            return []  # Return empty list on error
    
    def get_trade_history(self, user_id=None, limit=20):
        """Get all trades, including closed ones."""
        try:
            from models import Trade
            
            query = Trade.query
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            # Order by most recent first and limit
            query = query.order_by(Trade.open_timestamp.desc()).limit(limit)
            
            # Get results as list of dictionaries
            trades = []
            for trade in query.all():
                trade_dict = {
                    'id': trade.id,
                    'currency_pair': trade.currency_pair,
                    'type': trade.trade_type,
                    'amount': trade.amount,
                    'price': trade.price,
                    'open_timestamp': trade.open_timestamp,
                    'close_timestamp': trade.close_timestamp,
                    'close_price': trade.close_price,
                    'status': trade.status,
                    'profit_loss': trade.profit_loss,
                    'leverage': trade.leverage,
                    'user_id': trade.user_id,
                    'source': trade.source
                }
                trades.append(trade_dict)
                
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting trade history: {str(e)}")
            return []  # Return empty list on error
