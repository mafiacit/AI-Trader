from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Explicitly set table name since 'user' is a reserved keyword
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    telegram_id = db.Column(db.String(64), unique=True, nullable=True)
    account_balance = db.Column(db.Float, default=10000.0)  # Starting with $10,000 virtual balance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy='dynamic')
    settings = db.relationship('UserSettings', backref='user', uselist=False)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # Only set attributes that are defined columns
            if hasattr(self.__class__, key):
                setattr(self, key, value)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'telegram_id': self.telegram_id,
            'account_balance': self.account_balance,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    default_currency_pair = db.Column(db.String(10), default='EURUSD')  # Options include EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, XAUUSD, BTCUSD, ETHUSD
    default_trade_amount = db.Column(db.Float, default=1000.0)
    default_timeframe = db.Column(db.String(5), default='1d')
    auto_trade_enabled = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(10), default='medium')  # 'low', 'medium', 'high'
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.__class__, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f'<UserSettings for User {self.user_id}>'

class Trade(db.Model):
    __tablename__ = 'trade'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    currency_pair = db.Column(db.String(10), nullable=False)
    trade_type = db.Column(db.String(10), nullable=False)  # 'buy', 'sell', 'call', 'put'
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    profit_loss = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(10), default='open')  # 'open' or 'closed'
    leverage = db.Column(db.Integer, default=1)
    open_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    close_timestamp = db.Column(db.DateTime, nullable=True)
    close_price = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(20), default='web')  # 'web', 'telegram', 'auto'
    analysis_id = db.Column(db.Integer, db.ForeignKey('market_analysis.id'), nullable=True)
    pocket_option = db.Column(db.Boolean, default=False)  # Whether this is a pocket/binary option
    expiry_timestamp = db.Column(db.DateTime, nullable=True)  # Expiry time for pocket options
    
    # Relationships
    analysis = db.relationship('MarketAnalysis', backref='trades')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.__class__, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'currency_pair': self.currency_pair,
            'trade_type': self.trade_type,
            'amount': self.amount,
            'price': self.price,
            'profit_loss': self.profit_loss,
            'status': self.status,
            'leverage': self.leverage,
            'open_timestamp': self.open_timestamp,
            'close_timestamp': self.close_timestamp,
            'close_price': self.close_price,
            'source': self.source
        }
    
    def __repr__(self):
        return f'<Trade {self.id}: {self.trade_type} {self.currency_pair}>'

class MarketAnalysis(db.Model):
    __tablename__ = 'market_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    currency_pair = db.Column(db.String(10), nullable=False)
    timeframe = db.Column(db.String(5), nullable=False)
    trend = db.Column(db.String(10), nullable=False)  # 'bullish', 'bearish', or 'neutral'
    strength = db.Column(db.Float, nullable=False)  # 0-100
    support = db.Column(db.Float, nullable=False)
    resistance = db.Column(db.Float, nullable=False)
    recommendation = db.Column(db.String(10), nullable=False)  # 'buy', 'sell', or 'hold'
    confidence = db.Column(db.Float, nullable=False)  # 0-100
    current_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    indicators = db.Column(db.Text, nullable=True)  # JSON string of indicators
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.__class__, key):
                setattr(self, key, value)
    
    def set_indicators(self, indicators_dict):
        self.indicators = json.dumps(indicators_dict)
        
    def get_indicators(self):
        if self.indicators:
            return json.loads(self.indicators)
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency_pair': self.currency_pair,
            'timeframe': self.timeframe,
            'trend': self.trend,
            'strength': self.strength,
            'support': self.support,
            'resistance': self.resistance,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'current_price': self.current_price,
            'timestamp': self.timestamp,
            'indicators': self.get_indicators()
        }
    
    def __repr__(self):
        return f'<Analysis {self.currency_pair} {self.timeframe}: {self.recommendation}>'

class TelegramChat(db.Model):
    __tablename__ = 'telegram_chat'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(64), nullable=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.__class__, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f'<TelegramChat {self.chat_id}: {self.username}>'
