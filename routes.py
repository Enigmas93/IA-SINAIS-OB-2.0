from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc
import logging
import json
import time
from typing import Dict, List, Optional
from sqlalchemy.orm import joinedload

# Import models
try:
    from models import db, User, TradingConfig, TradeHistory, MLModel, SystemLog, MarketData
except ImportError as e:
    logging.error(f"Error importing models in routes: {e}")
    raise

# Import services with robust fallback system
try:
    from services import TradingBot, IQOptionService, SignalAnalyzer, MLService
    logging.info("Services imported successfully in routes")
except ImportError as e:
    logging.error(f"Error importing services in routes: {e}")
    # Create dummy classes to prevent import errors
    class TradingBot:
        def __init__(self, *args, **kwargs):
            self.is_running = False
        def start(self):
            return False
        def stop(self):
            return True
    class IQOptionService:
        def __init__(self, *args, **kwargs):
            self.is_connected = False
            self.balance = 0.0
        def connect(self):
            return False
    class SignalAnalyzer:
        def __init__(self, *args, **kwargs):
            pass
        def analyze(self, *args, **kwargs):
            return {'signal': 'HOLD', 'confidence': 0.0}
    class MLService:
        def __init__(self, *args, **kwargs):
            pass
        def predict(self, *args, **kwargs):
            return {'prediction': 'HOLD', 'confidence': 0.0}

# Create blueprints
api = Blueprint('api', __name__, url_prefix='/api')
main = Blueprint('main', __name__)

# Initialize services
logger = logging.getLogger(__name__)

# Cache global para saldos dos usuários
balance_cache = {}
CACHE_DURATION = 300  # 5 minutos em segundos

def get_cached_balance(user_id: int, account_type: str = 'PRACTICE') -> float:
    """Get balance from cache if available and not expired"""
    cache_key = f"{user_id}_{account_type}"
    if cache_key in balance_cache:
        cached_data = balance_cache[cache_key]
        if time.time() - cached_data['timestamp'] < CACHE_DURATION:
            logger.info(f"Using cached balance for user {user_id} ({account_type}): ${cached_data['balance']}")
            return cached_data['balance']
        else:
            # Cache expired, remove it
            del balance_cache[cache_key]
            logger.info(f"Cache expired for user {user_id} ({account_type})")
    return None

def set_cached_balance(user_id: int, balance: float, account_type: str = 'PRACTICE'):
    """Set balance in cache with current timestamp"""
    cache_key = f"{user_id}_{account_type}"
    balance_cache[cache_key] = {
        'balance': balance,
        'timestamp': time.time()
    }
    logger.info(f"Cached balance for user {user_id} ({account_type}): ${balance}")

# Blacklist for JWT tokens
blacklisted_tokens = set()

# Main routes
@main.route('/')
def index():
    """Home page - show presentation page"""
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST - Handle login form submission
    data = request.get_json() or request.form.to_dict()
    email = data.get('email')
    password = data.get('password')
    account_type = data.get('account_type', 'PRACTICE')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email e senha são obrigatórios'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401
    
    # Update account type if different
    if user.account_type != account_type:
        user.account_type = account_type
        logger.info(f"Updated account type for user {user.email} to {account_type}")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(
        identity=user.id,
        expires_delta=timedelta(days=7)
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return jsonify({
        'success': True,
        'token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'account_type': user.account_type
        }
    }), 200

@main.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@main.route('/register', methods=['POST'])
def register_redirect():
    """Redirect register POST to API endpoint"""
    from flask import request
    # Forward the request to the API endpoint
    data = request.get_json()
    
    # Call the API register function directly
    return register()

# Authentication routes
@api.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Debug: Log received data (without sensitive info)
        debug_data = {k: v if k not in ['password', 'password_confirm', 'iq_password'] else '***' for k, v in (data or {}).items()}
        logger.info(f"Registration attempt with data: {debug_data}")
        
        if not data:
            logger.warning("No JSON data received in registration request")
            return jsonify({'message': 'Dados não fornecidos'}), 400
        
        # Validate required fields
        required_fields = ['name', 'email', 'password', 'iq_email', 'iq_password']
        for field in required_fields:
            if not data.get(field):
                logger.warning(f"Missing required field: {field}")
                return jsonify({'message': f'Campo {field} é obrigatório'}), 400
        
        # Validate password confirmation if provided
        if 'password_confirm' in data and data['password'] != data['password_confirm']:
            logger.warning(f"Password confirmation mismatch for email: {data.get('email')}")
            return jsonify({'message': 'As senhas não coincidem'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {data.get('email')}")
            return jsonify({'message': 'Email já cadastrado'}), 400
        
        logger.info(f"All validations passed, creating user: {data.get('email')}")
        
        # Create new user (always starts with PRACTICE account)
        user = User(
            name=data['name'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            iq_email=data['iq_email'],
            iq_password=data['iq_password'],  # This should be encrypted in production
            account_type='PRACTICE'  # Always start with demo account
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create default trading configuration
        config = TradingConfig(
            user_id=user.id,
            asset='EURUSD',
            trade_amount=10.0,
            use_balance_percentage=True,
            balance_percentage=2.0,
            take_profit=70.0,
            stop_loss=30.0,
            martingale_enabled=True,
            max_martingale_levels=3,
            morning_start='10:00',
            afternoon_start='14:00',
            operation_mode='manual'
        )
        
        db.session.add(config)
        db.session.commit()
        
        logger.info(f"New user registered: {user.email}")
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'user_id': user.id
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/auth/login', methods=['POST'])
def login_api():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Email e senha são obrigatórios'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'message': 'Credenciais inválidas'}), 401
        
        # Update account type if provided
        account_type = data.get('account_type')
        if account_type and user.account_type != account_type:
            user.account_type = account_type
            logger.info(f"Updated account type for user {user.email} to {account_type}")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7)
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return jsonify({
            'token': access_token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'account_type': user.account_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout_api():
    """Logout user and blacklist token"""
    try:
        jti = get_jwt()['jti']
        blacklisted_tokens.add(jti)
        
        logger.info(f"User logged out: {get_jwt_identity()}")
        
        return jsonify({'message': 'Logout realizado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# User routes
@api.route('/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get user profile information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'account_type': user.account_type,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Configuration routes
@api.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get user's trading configuration"""
    try:
        user_id = get_jwt_identity()
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        
        if not config:
            return jsonify({'message': 'Configuração não encontrada'}), 404
        
        return jsonify({
            'asset': config.asset,
            'trade_amount': config.trade_amount,
            'use_balance_percentage': config.use_balance_percentage,
            'balance_percentage': config.balance_percentage,
            'take_profit': config.take_profit,
            'stop_loss': config.stop_loss,
            'martingale_enabled': config.martingale_enabled,
            'max_martingale_levels': config.max_martingale_levels,
            'morning_start': config.morning_start,
            'morning_end': config.morning_end,
            'afternoon_start': config.afternoon_start,
            'afternoon_end': config.afternoon_end,
            'operation_mode': config.operation_mode,
            'strategy_mode': config.strategy_mode,
            'min_signal_score': config.min_signal_score,
            'timeframe': config.timeframe
        }), 200
        
    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/config', methods=['POST'])
@jwt_required()
def save_config():
    """Save user's trading configuration"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        
        if not config:
            config = TradingConfig(user_id=user_id)
        
        # Update configuration
        config.asset = data.get('asset', config.asset)
        config.trade_amount = data.get('trade_amount', config.trade_amount)
        config.use_balance_percentage = data.get('use_balance_percentage', config.use_balance_percentage)
        config.balance_percentage = data.get('balance_percentage', config.balance_percentage)
        config.take_profit = data.get('take_profit', config.take_profit)
        config.stop_loss = data.get('stop_loss', config.stop_loss)
        config.martingale_enabled = data.get('martingale_enabled', config.martingale_enabled)
        config.max_martingale_levels = data.get('max_martingale_levels', config.max_martingale_levels)
        config.morning_start = data.get('morning_start', config.morning_start)
        config.morning_end = data.get('morning_end', config.morning_end)
        config.afternoon_start = data.get('afternoon_start', config.afternoon_start)
        config.afternoon_end = data.get('afternoon_end', config.afternoon_end)
        config.operation_mode = data.get('operation_mode', config.operation_mode)
        config.strategy_mode = data.get('strategy_mode', config.strategy_mode)
        config.min_signal_score = data.get('min_signal_score', config.min_signal_score)
        config.timeframe = data.get('timeframe', config.timeframe)
        config.updated_at = datetime.utcnow()
        
        # Synchronize auto_mode with operation_mode
        if config.operation_mode == 'auto':
            config.auto_mode = True
        elif config.operation_mode == 'manual':
            config.auto_mode = False
        
        db.session.add(config)
        db.session.commit()
        
        logger.info(f"Configuration updated for user: {user_id}")
        
        return jsonify({'message': 'Configuração salva com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Save config error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Bot control routes
@api.route('/bot/start', methods=['POST'])
@jwt_required()
def start_bot():
    """Start the trading bot"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        
        if not user or not config:
            return jsonify({'message': 'Usuário ou configuração não encontrados'}), 404
        
        # Ensure auto_mode is synchronized with operation_mode
        if config.operation_mode == 'auto' and not config.auto_mode:
            config.auto_mode = True
            db.session.commit()
            logger.info(f"Synchronized auto_mode=True for user {user_id} (operation_mode=auto)")
        elif config.operation_mode == 'manual' and config.auto_mode:
            config.auto_mode = False
            db.session.commit()
            logger.info(f"Synchronized auto_mode=False for user {user_id} (operation_mode=manual)")
        
        # Check if bot is already running
        from services.trading_bot import TradingBot
        from flask import current_app
        import app as app_module
        
        # If there's already a bot running, stop it first
        if app_module.trading_bot is not None:
            try:
                logger.info(f"Stopping existing bot before starting new one for user: {user_id}")
                app_module.trading_bot.stop()
                app_module.trading_bot = None
            except Exception as e:
                logger.error(f"Error stopping existing bot: {str(e)}")
        
        # Create new bot instance and start it
        new_trading_bot = TradingBot(user_id, config, app=current_app._get_current_object())
        success = new_trading_bot.start()
        
        if success:
            # Store the bot instance globally so it can be accessed by other endpoints
            app_module.trading_bot = new_trading_bot
            logger.info(f"Bot started for user: {user_id}")
            return jsonify({'message': 'Bot iniciado com sucesso'}), 200
        else:
            return jsonify({'message': 'Erro ao iniciar bot'}), 500
        
    except Exception as e:
        logger.error(f"Start bot error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/bot/stop', methods=['POST'])
@jwt_required()
def stop_bot():
    """Stop the trading bot"""
    try:
        from app import get_or_create_trading_bot
        import app as app_module
        
        user_id = get_jwt_identity()
        trading_bot = get_or_create_trading_bot()
        
        # Check if bot has stop method
        if not hasattr(trading_bot, 'stop'):
            logger.warning(f"Bot instance does not have stop method for user: {user_id}")
            # Clear the global bot instance anyway
            app_module.trading_bot = None
            return jsonify({'message': 'Bot parado com sucesso'}), 200
        
        # Stop the bot
        try:
            success = trading_bot.stop()
            if success:
                # Clear the global bot instance
                app_module.trading_bot = None
                logger.info(f"Bot stopped successfully for user: {user_id}")
                return jsonify({'message': 'Bot parado com sucesso'}), 200
            else:
                logger.error(f"Bot stop method returned False for user: {user_id}")
                return jsonify({'message': 'Erro ao parar bot'}), 500
        except Exception as stop_error:
            logger.error(f"Error calling bot stop method for user {user_id}: {str(stop_error)}")
            # Clear the global bot instance anyway
            app_module.trading_bot = None
            return jsonify({'message': 'Bot parado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Stop bot error for user {get_jwt_identity()}: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/bot/status', methods=['GET'])
@jwt_required()
def get_bot_status():
    """Get bot status"""
    try:
        import app as app_module
        
        user_id = get_jwt_identity()
        
        # Check if there's a real bot instance running
        if app_module.trading_bot is not None:
            status = app_module.trading_bot.get_bot_status(user_id)
        else:
            # No bot running, return default status
            status = {'running': False, 'balance': 0}
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Get bot status error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/bot/force_trade', methods=['POST'])
@jwt_required()
def force_trade():
    """Force a trade in manual mode"""
    try:
        import app as app_module
        
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'direction' not in data:
            return jsonify({'message': 'Direção do trade é obrigatória'}), 400
        
        direction = data['direction'].lower()
        if direction not in ['call', 'put']:
            return jsonify({'message': 'Direção deve ser call ou put'}), 400
        
        # Check if bot is running and in manual mode
        if app_module.trading_bot is None:
            return jsonify({'message': 'Bot não está rodando'}), 400
        
        bot_status = app_module.trading_bot.get_status()
        if not bot_status.get('running', False):
            return jsonify({'message': 'Bot não está rodando'}), 400
        
        if bot_status.get('current_session') != 'manual':
            return jsonify({'message': 'Bot deve estar em modo manual para forçar trades'}), 400
        
        # Execute the trade
        success = app_module.trading_bot.force_trade(direction)
        
        if success:
            return jsonify({'message': f'Trade {direction} executado com sucesso'}), 200
        else:
            return jsonify({'message': 'Erro ao executar trade'}), 500
        
    except Exception as e:
        logger.error(f"Force trade error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/bot/test_stop_loss', methods=['POST'])
@jwt_required()
def test_stop_loss():
    """Test Stop Loss notification"""
    try:
        import app as app_module
        
        user_id = get_jwt_identity()
        
        if app_module.trading_bot is None:
            return jsonify({'message': 'Bot não está rodando'}), 400
        
        success = app_module.trading_bot.test_stop_loss_notification()
        
        if success:
            return jsonify({'message': 'Notificação de Stop Loss enviada com sucesso'}), 200
        else:
            return jsonify({'message': 'Erro ao enviar notificação de teste'}), 500
            
    except Exception as e:
        logger.error(f"Test stop loss error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Dashboard routes
@api.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        user_id = get_jwt_identity()
        
        # Get user account type
        user = User.query.get(user_id)
        account_type = user.account_type if user else 'PRACTICE'
        
        # Get basic stats filtered by account type
        total_trades = TradeHistory.query.filter_by(user_id=user_id, account_type=account_type).count()
        win_trades = TradeHistory.query.filter_by(user_id=user_id, account_type=account_type, result='win').count()
        loss_trades = total_trades - win_trades
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Get profit stats filtered by account type
        trades = TradeHistory.query.filter_by(user_id=user_id, account_type=account_type).all()
        total_profit = sum(trade.profit for trade in trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # Get today's profit filtered by account type
        today = datetime.utcnow().date()
        today_trades = TradeHistory.query.filter(
            and_(
                TradeHistory.user_id == user_id,
                TradeHistory.account_type == account_type,
                TradeHistory.timestamp >= today
            )
        ).all()
        today_profit = sum(trade.profit for trade in today_trades)
        
        # Get best streak filtered by account type
        best_streak = calculate_best_streak(trades)
        
        # Get recent trades filtered by account type
        recent_trades = TradeHistory.query.filter_by(user_id=user_id, account_type=account_type)\
            .order_by(desc(TradeHistory.timestamp))\
            .limit(5).all()
        
        recent_trades_data = [{
            'asset': trade.asset,
            'direction': trade.direction,
            'result': trade.result,
            'profit': trade.profit,
            'timestamp': trade.timestamp.isoformat()
        } for trade in recent_trades]
        
        # Get profit history for chart (last 7 days) filtered by account type
        profit_history = get_profit_history(user_id, days=7, account_type=account_type)
        
        # Get bot status and real balance
        import app as app_module
        
        # Check if there's a real bot instance running
        if app_module.trading_bot is not None:
            bot_status = app_module.trading_bot.get_bot_status(user_id)
        else:
            # No bot running, return default status
            bot_status = {'running': False, 'balance': 0}
        
        # Get user account type
        user = User.query.get(user_id)
        account_type = user.account_type if user else 'PRACTICE'
        
        # Get real balance from IQ Option efficiently with cache
        balance = 1000.0  # Default fallback
        
        # First try to get from running bot (most efficient)
        bot_balance = bot_status.get('balance', 0)
        if bot_balance > 0 and bot_status.get('running', False):
            balance = bot_balance
            logger.info(f"Got balance from running bot: ${balance}")
            # Update cache with bot balance
            set_cached_balance(user_id, balance, account_type)
        else:
            # Try to get from cache first
            cached_balance = get_cached_balance(user_id, account_type)
            if cached_balance is not None:
                balance = cached_balance
            else:
                # If no cache, connect temporarily to get real balance
                try:
                    if user and user.iq_email and user.iq_password:
                        from services.iq_option_service import IQOptionService
                        temp_service = IQOptionService(user.iq_email, user.iq_password)
                        logger.info(f"Connecting to IQ Option to get {account_type} balance...")
                        if temp_service.connect():
                            # Set account type before getting balance
                            if temp_service.set_account_type(account_type):
                                real_balance = temp_service.update_balance()
                                if real_balance > 0:
                                    balance = real_balance
                                    logger.info(f"Retrieved {account_type} balance from IQ Option: ${balance}")
                                    # Cache the balance
                                    set_cached_balance(user_id, balance, account_type)
                                else:
                                    logger.warning(f"IQ Option returned 0 balance for {account_type}")
                            else:
                                logger.warning(f"Failed to set account type to {account_type}")
                            temp_service.disconnect()
                            logger.info("Disconnected from IQ Option")
                        else:
                            logger.error("Failed to connect to IQ Option for balance")
                    else:
                        logger.warning("No IQ Option credentials found for user")
                except Exception as e:
                    logger.error(f"Error getting {account_type} balance: {str(e)}")
        
        # Include Take Profit and Stop Loss information from bot status
        response_data = {
            'balance': balance,
            'today_profit': today_profit,
            'win_rate': win_rate,
            'bot_status': 'running' if bot_status.get('running', False) else 'stopped',
            'total_trades': total_trades,
            'win_trades': win_trades,
            'loss_trades': loss_trades,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'best_streak': best_streak,
            'recent_trades': recent_trades_data,
            'profit_history': profit_history,
            'last_trade': recent_trades_data[0] if recent_trades_data else None,
            'next_schedule': get_next_schedule(user_id)
        }
        
        # Add Take Profit and Stop Loss information if bot is running
        if bot_status.get('running', False) and app_module.trading_bot is not None:
            full_status = app_module.trading_bot.get_status()
            response_data.update({
                'session_profit': full_status.get('session_profit', 0),
                'take_profit_target': full_status.get('take_profit_target', 0),
                'stop_loss_target': full_status.get('stop_loss_target', 0),
                'take_profit_reached': full_status.get('take_profit_reached', False),
                'stop_loss_reached': full_status.get('stop_loss_reached', False)
            })
        else:
            # Default values when bot is not running
            response_data.update({
                'session_profit': 0,
                'take_profit_target': 0,
                'stop_loss_target': 0,
                'take_profit_reached': False,
                'stop_loss_reached': False
            })
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get dashboard stats error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Trade history routes
@api.route('/trades/history', methods=['GET'])
@jwt_required()
def get_trade_history():
    """Get trade history with pagination and filters"""
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get user account type
        user = User.query.get(user_id)
        account_type = user.account_type if user else 'PRACTICE'
        
        # Build query filtered by account type
        query = TradeHistory.query.filter_by(user_id=user_id, account_type=account_type)
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(TradeHistory.timestamp >= start_datetime)
            except ValueError:
                return jsonify({'message': 'Formato de data inválido para start_date'}), 422
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
                query = query.filter(TradeHistory.timestamp < end_datetime)
            except ValueError:
                return jsonify({'message': 'Formato de data inválido para end_date'}), 422
        
        # Execute paginated query
        pagination = query.order_by(desc(TradeHistory.timestamp)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        trades_data = [{
            'id': trade.id,
            'timestamp': trade.timestamp.isoformat(),
            'asset': trade.asset or 'N/A',
            'direction': trade.direction or 'N/A',
            'amount': trade.amount or 0,
            'result': trade.result or 'pending',
            'profit': trade.profit or 0,
            'martingale_level': trade.martingale_level or 0,
            'signal_strength': trade.signal_strength or 0
        } for trade in pagination.items]
        
        return jsonify({
            'trades': trades_data,
            'pagination': {
                'current_page': pagination.page,
                'total_pages': pagination.pages,
                'total_items': pagination.total,
                'per_page': per_page
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get trade history error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Helper functions
def calculate_best_streak(trades):
    """Calculate the best winning streak"""
    if not trades:
        return 0
    
    current_streak = 0
    best_streak = 0
    
    for trade in sorted(trades, key=lambda x: x.timestamp):
        if trade.result == 'win':
            current_streak += 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 0
    
    return best_streak

def get_profit_history(user_id, days=7, account_type='PRACTICE'):
    """Get profit history for the last N days filtered by account type"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days-1)
    
    labels = []
    data = []
    cumulative_profit = 0
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        labels.append(current_date.strftime('%d/%m'))
        
        # Get trades for this date filtered by account type
        day_trades = TradeHistory.query.filter(
            and_(
                TradeHistory.user_id == user_id,
                TradeHistory.account_type == account_type,
                TradeHistory.timestamp >= current_date,
                TradeHistory.timestamp < current_date + timedelta(days=1)
            )
        ).all()
        
        day_profit = sum(trade.profit for trade in day_trades)
        cumulative_profit += day_profit
        data.append(cumulative_profit)
    
    return {
        'labels': labels,
        'data': data
    }

def get_next_schedule(user_id):
    """Get next scheduled trading session"""
    config = TradingConfig.query.filter_by(user_id=user_id).first()
    if not config:
        return "Não Programado"
    
    # If operation mode is manual, return "Não Programado"
    if config.operation_mode != 'auto':
        return "Não Programado"
    
    now = datetime.now()
    morning_time = datetime.strptime(config.morning_start, '%H:%M').time()
    afternoon_time = datetime.strptime(config.afternoon_start, '%H:%M').time()
    
    # Check if we're before morning session
    if now.time() < morning_time:
        return config.morning_start
    # Check if we're before afternoon session
    elif now.time() < afternoon_time:
        return config.afternoon_start
    # Next session is tomorrow morning
    else:
        return f"Amanhã {config.morning_start}"

# Machine Learning routes
@api.route('/ml/models', methods=['GET'])
@jwt_required()
def get_ml_models():
    """Get ML model performance and statistics"""
    try:
        user_id = get_jwt_identity()
        
        # Get ML service instance
        ml_service = MLService(user_id)
        
        # Get model performance
        models_performance = ml_service.get_model_performance()
        
        # Get retrain statistics
        retrain_stats = ml_service.get_retrain_statistics()
        
        return jsonify({
            'models': models_performance,
            'retrain_statistics': retrain_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get ML models error: {str(e)}")
        return jsonify({'message': 'Erro ao obter informações dos modelos ML'}), 500

@api.route('/ml/retrain', methods=['POST'])
@jwt_required()
def manual_retrain():
    """Manually trigger model retraining"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        asset = data.get('asset')  # Optional: specific asset
        
        # Get ML service instance
        ml_service = MLService(user_id)
        
        # Trigger retrain
        success = ml_service.retrain_models(asset)
        
        if success:
            # Log manual retrain event
            ml_service._log_retrain_event(
                asset or 'all_assets', 
                'manual_trigger', 
                True
            )
            
            asset_text = f'do ativo {asset}' if asset else 'de todos os modelos'
            return jsonify({
                'success': True,
                'message': f'Retreinamento {asset_text} iniciado com sucesso'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Falha no retreinamento dos modelos'
            }), 500
            
    except Exception as e:
        logger.error(f"Manual retrain error: {str(e)}")
        return jsonify({'message': 'Erro ao iniciar retreinamento manual'}), 500

@api.route('/ml/status', methods=['GET'])
@jwt_required()
def get_ml_status():
    """Get ML system status and configuration"""
    try:
        user_id = get_jwt_identity()
        
        # Get user config
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        
        if not config:
            return jsonify({'message': 'Configuração não encontrada'}), 404
        
        # Get ML service instance
        ml_service = MLService(user_id)
        
        # Get model count
        active_models = MLModel.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).count()
        
        # Get recent retrain activity
        retrain_stats = ml_service.get_retrain_statistics()
        
        return jsonify({
            'ml_enabled': config.use_ml_signals,
            'active_models': active_models,
            'retrain_statistics': retrain_stats,
            'automatic_retrain_triggers': {
                'trade_count': 'A cada 50 operações',
                'time_based': 'A cada 7 dias',
                'performance_drop': 'Quando precisão < 60%'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get ML status error: {str(e)}")
        return jsonify({'message': 'Erro ao obter status do ML'}), 500

# JWT token blacklist check
@api.before_request
def check_if_token_revoked():
    """Check if JWT token is blacklisted"""
    if request.endpoint and 'auth' not in request.endpoint:
        try:
            jti = get_jwt()['jti']
            if jti in blacklisted_tokens:
                return jsonify({'message': 'Token inválido'}), 401
        except:
            pass  # No JWT token present

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint não encontrado'}), 404

@api.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'message': 'Erro interno do servidor'}), 500