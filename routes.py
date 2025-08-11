from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc
import logging
import json
import time
import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.orm import joinedload
from database import db

# Import validation schemas and validators
from validators import (
    validate_json, validate_query_params, validate_trading_config,
    validate_credentials, create_api_response, validate_pagination_params,
    sanitize_input
)
from schemas import (
    TradingConfigSchema, UserCredentialsSchema, APIResponseSchema,
    PaginationSchema
)

# Import rate limiting
from rate_limiter import (
    limit_login, limit_register, limit_api, limit_config,
    limit_bot_control, limit_force_trade, cleanup_rate_limiter,
    get_rate_limiter_stats
)

# Import cache system
from cache import get_cache, cached, cache_user_data, invalidate_user_cache

# Import models
try:
    from models import User, TradingConfig, TradeHistory, MLModel, SystemLog, SessionTargets, MarketData
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

def convert_numpy_to_json_serializable(obj):
    """Convert numpy arrays and other non-serializable objects to JSON-serializable types"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_json_serializable(item) for item in obj]
    elif hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    else:
        return obj

# Connection failures tracking
connection_failures = {}  # Track connection failures
FAILURE_COOLDOWN = 600  # 10 minutos de cooldown após falha
MAX_FAILURES = 3  # Máximo de falhas antes do cooldown

def get_cached_balance(user_id: int, account_type: str = 'PRACTICE') -> Optional[float]:
    """Get balance from cache using new cache system"""
    cache = get_cache()
    cache_key = f"balance:{user_id}:{account_type}"
    balance = cache.get(cache_key)
    
    if balance is not None:
        logger.info(f"Using cached balance for user {user_id} ({account_type}): ${balance}")
        return balance
    
    return None

def set_cached_balance(user_id: int, balance: float, account_type: str = 'PRACTICE'):
    """Set balance in cache using new cache system"""
    cache = get_cache()
    cache_key = f"balance:{user_id}:{account_type}"
    # Cache balance for 5 minutes
    cache.set(cache_key, balance, timeout=300)
    logger.info(f"Cached balance for user {user_id} ({account_type}): ${balance}")

def should_skip_connection(user_id: int) -> bool:
    """Check if we should skip connection due to recent failures"""
    if user_id in connection_failures:
        failure_data = connection_failures[user_id]
        if failure_data['count'] >= MAX_FAILURES:
            time_since_last_failure = time.time() - failure_data['last_failure']
            if time_since_last_failure < FAILURE_COOLDOWN:
                logger.warning(f"Skipping IQ Option connection for user {user_id} due to recent failures (cooldown: {FAILURE_COOLDOWN - time_since_last_failure:.0f}s remaining)")
                return True
            else:
                # Reset failures after cooldown
                del connection_failures[user_id]
    return False

def record_connection_failure(user_id: int):
    """Record a connection failure"""
    if user_id not in connection_failures:
        connection_failures[user_id] = {'count': 0, 'last_failure': 0}
    
    connection_failures[user_id]['count'] += 1
    connection_failures[user_id]['last_failure'] = time.time()
    logger.warning(f"Recorded connection failure for user {user_id} (total: {connection_failures[user_id]['count']})")

def record_connection_success(user_id: int):
    """Record a successful connection (reset failures)"""
    if user_id in connection_failures:
        del connection_failures[user_id]
        logger.info(f"Reset connection failures for user {user_id}")

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
@limit_register
def register():
    """Register a new user with validation"""
    try:
        data = request.get_json()
        
        # Debug: Log received data (without sensitive info)
        debug_data = {k: v if k not in ['password', 'password_confirm', 'iq_password'] else '***' for k, v in (data or {}).items()}
        logger.info(f"Registration attempt with data: {debug_data}")
        
        if not data:
            logger.warning("No JSON data received in registration request")
            return jsonify(create_api_response(
                success=False,
                message='Dados não fornecidos',
                errors=['JSON data is required']
            )), 400
        
        # Sanitize input data
        sanitized_data = sanitize_input(data)
        
        # Validate required fields
        required_fields = ['name', 'email', 'password', 'iq_email', 'iq_password']
        missing_fields = [field for field in required_fields if not sanitized_data.get(field)]
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return jsonify(create_api_response(
                success=False,
                message='Campos obrigatórios não fornecidos',
                errors=[f'Campo {field} é obrigatório' for field in missing_fields]
            )), 400
        
        # Validate password confirmation if provided
        if 'password_confirm' in sanitized_data and sanitized_data['password'] != sanitized_data['password_confirm']:
            logger.warning(f"Password confirmation mismatch for email: {sanitized_data.get('email')}")
            return jsonify(create_api_response(
                success=False,
                message='As senhas não coincidem',
                errors=['Password confirmation does not match']
            )), 400
        
        # Validate credentials using schema
        try:
            credentials = validate_credentials({
                'iq_email': sanitized_data['iq_email'],
                'iq_password': sanitized_data['iq_password']
            })
        except ValueError as e:
            logger.warning(f"Credential validation failed: {str(e)}")
            return jsonify(create_api_response(
                success=False,
                message='Credenciais inválidas',
                errors=[str(e)]
            )), 400
        
        # Additional validations
        if len(sanitized_data['name']) < 2:
            return jsonify(create_api_response(
                success=False,
                message='Nome deve ter pelo menos 2 caracteres',
                errors=['Name too short']
            )), 400
        
        if len(sanitized_data['password']) < 6:
            return jsonify(create_api_response(
                success=False,
                message='Senha deve ter pelo menos 6 caracteres',
                errors=['Password too short']
            )), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=sanitized_data['email']).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {sanitized_data.get('email')}")
            return jsonify(create_api_response(
                success=False,
                message='Email já cadastrado',
                errors=['Email already exists']
            )), 400
        
        logger.info(f"All validations passed, creating user: {sanitized_data.get('email')}")
        
        # Create new user (always starts with PRACTICE account)
        user = User(
            name=sanitized_data['name'],
            email=sanitized_data['email'],
            password_hash=generate_password_hash(sanitized_data['password']),
            iq_email=credentials.iq_email,
            iq_password=credentials.iq_password,  # This should be encrypted in production
            account_type='PRACTICE'  # Always start with demo account
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create default trading configuration with validation
        default_config_data = {
            'asset': 'EURUSD',
            'trade_amount': 10.0,
            'use_balance_percentage': True,
            'balance_percentage': 2.0,
            'take_profit': 70.0,
            'martingale_enabled': True,
            'max_martingale_levels': 3,
            'morning_start': '10:00',
            'afternoon_start': '14:00',
            'morning_enabled': True,
            'afternoon_enabled': True,
            'night_enabled': False,
            'continuous_mode': False,
            'strategy_mode': 'intermediario',
            'min_signal_score': 70,
            'timeframe': '1m'
        }
        
        try:
            validated_config = validate_trading_config(default_config_data)
            config = TradingConfig(
                user_id=user.id,
                asset=validated_config.asset,
                trade_amount=validated_config.trade_amount,
                use_balance_percentage=validated_config.use_balance_percentage,
                balance_percentage=validated_config.balance_percentage,
                take_profit=validated_config.take_profit,
                martingale_enabled=validated_config.martingale_enabled,
                max_martingale_levels=validated_config.max_martingale_levels,
                morning_start=validated_config.morning_start,
                afternoon_start=validated_config.afternoon_start,
                operation_mode='manual',
                strategy_mode=validated_config.strategy_mode,
                min_signal_score=validated_config.min_signal_score,
                timeframe=validated_config.timeframe
            )
            
            db.session.add(config)
            db.session.commit()
        except ValueError as e:
            logger.error(f"Error creating default config: {str(e)}")
            # Continue without failing registration
        
        logger.info(f"New user registered: {user.email}")
        
        return jsonify(create_api_response(
            success=True,
            message='Usuário criado com sucesso',
            data={'user_id': user.id}
        )), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify(create_api_response(
            success=False,
            message='Erro interno do servidor',
            errors=[str(e)]
        )), 500

@api.route('/auth/login', methods=['POST'])
@limit_login
def login_api():
    """Authenticate user and return JWT token with validation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(create_api_response(
                success=False,
                message='Dados de login não fornecidos',
                errors=['Login data is required']
            )), 400
        
        # Sanitize input data
        sanitized_data = sanitize_input(data)
        
        if not sanitized_data.get('email') or not sanitized_data.get('password'):
            return jsonify(create_api_response(
                success=False,
                message='Email e senha são obrigatórios',
                errors=['Email and password are required']
            )), 400
        
        # Validate email format
        email = sanitized_data['email'].lower().strip()
        if '@' not in email or '.' not in email:
            return jsonify(create_api_response(
                success=False,
                message='Formato de email inválido',
                errors=['Invalid email format']
            )), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, sanitized_data['password']):
            logger.warning(f"Failed login attempt for email: {email}")
            return jsonify(create_api_response(
                success=False,
                message='Credenciais inválidas',
                errors=['Invalid credentials']
            )), 401
        
        # Update account type if provided and valid
        account_type = sanitized_data.get('account_type')
        if account_type and account_type in ['PRACTICE', 'REAL'] and user.account_type != account_type:
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
        
        return jsonify(create_api_response(
            success=True,
            message='Login realizado com sucesso',
            data={
                'token': access_token,
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'account_type': user.account_type
                }
            }
        )), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify(create_api_response(
            success=False,
            message='Erro interno do servidor',
            errors=[str(e)]
        )), 500

@api.route('/auth/logout', methods=['POST'])
@jwt_required()
@limit_api
def logout_api():
    """Logout user and blacklist token"""
    try:
        jti = get_jwt()['jti']
        blacklisted_tokens.add(jti)
        
        logger.info(f"User logged out: {get_jwt_identity()}")
        
        return jsonify(create_api_response(
            success=True,
            message='Logout realizado com sucesso'
        )), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify(create_api_response(
            success=False,
            message='Erro interno do servidor',
            errors=[str(e)]
        )), 500

# User routes
@api.route('/user/profile', methods=['GET'])
@jwt_required()
@limit_api
@cached(timeout=300, key_prefix='user_profile:')
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
@limit_api
@cached(timeout=300, key_prefix='user_config:')
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
            # Stop loss is now based on losing all 3 martingale levels (no percentage)
            'martingale_enabled': config.martingale_enabled,
            'max_martingale_levels': config.max_martingale_levels,
            'morning_start': config.morning_start,
            'afternoon_start': config.afternoon_start,
            'night_start': config.night_start,
            'morning_enabled': getattr(config, 'morning_enabled', True),
            'afternoon_enabled': getattr(config, 'afternoon_enabled', True),
            'night_enabled': getattr(config, 'night_enabled', False),
            'continuous_mode': getattr(config, 'continuous_mode', False),
            'auto_restart': getattr(config, 'auto_restart', True),
            'keep_connection': getattr(config, 'keep_connection', True),
            'operation_mode': config.operation_mode,
            'strategy_mode': config.strategy_mode,
            'min_signal_score': config.min_signal_score,
            'timeframe': config.timeframe,
            'advance_signal_minutes': getattr(config, 'advance_signal_minutes', 2)
        }), 200
        
    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

@api.route('/config', methods=['POST'])
@jwt_required()
@limit_config
def save_config():
    """Save user's trading configuration with validation"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Debug: Log received configuration data
        logger.info(f"[DEBUG] Received config data: {data}")
        logger.info(f"[DEBUG] Night fields: night_start={data.get('night_start')}, night_enabled={data.get('night_enabled')}, continuous_mode={data.get('continuous_mode')}")
        
        if not data:
            return jsonify(create_api_response(
                success=False,
                message='Dados de configuração não fornecidos',
                errors=['Configuration data is required']
            )), 400
        
        # Sanitize input data
        sanitized_data = sanitize_input(data)
        
        # Get existing configuration
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        
        # Prepare data for validation with defaults from existing config
        config_data = {
            'asset': sanitized_data.get('asset', config.asset if config else 'EURUSD'),
            'trade_amount': sanitized_data.get('trade_amount', config.trade_amount if config else 10.0),
            'use_balance_percentage': sanitized_data.get('use_balance_percentage', config.use_balance_percentage if config else False),
            'balance_percentage': sanitized_data.get('balance_percentage', config.balance_percentage if config else None),
            'take_profit': sanitized_data.get('take_profit', config.take_profit if config else 70.0),
            'martingale_enabled': sanitized_data.get('martingale_enabled', config.martingale_enabled if config else True),
            'max_martingale_levels': sanitized_data.get('max_martingale_levels', config.max_martingale_levels if config else 3),
            'morning_start': sanitized_data.get('morning_start', config.morning_start if config else '10:00'),
            'afternoon_start': sanitized_data.get('afternoon_start', config.afternoon_start if config else '14:00'),
            'night_start': sanitized_data.get('night_start', config.night_start if config else None),
            'morning_enabled': sanitized_data.get('morning_enabled', getattr(config, 'morning_enabled', True) if config else True),
            'afternoon_enabled': sanitized_data.get('afternoon_enabled', getattr(config, 'afternoon_enabled', True) if config else True),
            'night_enabled': sanitized_data.get('night_enabled', getattr(config, 'night_enabled', False) if config else False),
            'continuous_mode': sanitized_data.get('continuous_mode', getattr(config, 'continuous_mode', False) if config else False),
            'auto_restart': sanitized_data.get('auto_restart', getattr(config, 'auto_restart', True) if config else True),
            'keep_connection': sanitized_data.get('keep_connection', getattr(config, 'keep_connection', True) if config else True),
            'strategy_mode': sanitized_data.get('strategy_mode', config.strategy_mode if config else 'intermediario'),
            'min_signal_score': sanitized_data.get('min_signal_score', config.min_signal_score if config else 70),
            'timeframe': sanitized_data.get('timeframe', config.timeframe if config else '1m'),
            'advance_signal_minutes': sanitized_data.get('advance_signal_minutes', getattr(config, 'advance_signal_minutes', 2) if config else 2),
            'use_ml_signals': sanitized_data.get('use_ml_signals', False)
        }
        
        # Validate configuration using schema
        try:
            validated_config = validate_trading_config(config_data)
        except ValueError as e:
            logger.warning(f"Configuration validation failed for user {user_id}: {str(e)}")
            return jsonify(create_api_response(
                success=False,
                message='Configuração inválida',
                errors=[str(e)]
            )), 400
        
        # Create or update configuration
        if not config:
            config = TradingConfig(user_id=user_id)
        
        # Update configuration with validated data
        config.asset = validated_config.asset
        config.trade_amount = validated_config.trade_amount
        config.use_balance_percentage = validated_config.use_balance_percentage
        config.balance_percentage = validated_config.balance_percentage
        config.take_profit = validated_config.take_profit
        config.martingale_enabled = validated_config.martingale_enabled
        config.max_martingale_levels = validated_config.max_martingale_levels
        config.morning_start = validated_config.morning_start
        config.afternoon_start = validated_config.afternoon_start
        config.night_start = validated_config.night_start
        config.morning_enabled = validated_config.morning_enabled
        config.afternoon_enabled = validated_config.afternoon_enabled
        config.night_enabled = validated_config.night_enabled
        config.continuous_mode = validated_config.continuous_mode
        config.auto_restart = validated_config.auto_restart
        config.keep_connection = validated_config.keep_connection
        config.strategy_mode = validated_config.strategy_mode
        config.min_signal_score = validated_config.min_signal_score
        config.timeframe = validated_config.timeframe
        config.advance_signal_minutes = validated_config.advance_signal_minutes
        config.updated_at = datetime.utcnow()
        
        # Handle operation mode (not in schema but needed for compatibility)
        operation_mode = sanitized_data.get('operation_mode', config.operation_mode if config else 'manual')
        if operation_mode in ['auto', 'manual']:
            config.operation_mode = operation_mode
        
        # Synchronize auto_mode with operation_mode
        if config.operation_mode == 'auto':
            config.auto_mode = True
        elif config.operation_mode == 'manual':
            config.auto_mode = False
        
        db.session.add(config)
        db.session.commit()
        
        # Invalidate user cache after configuration update
        invalidate_user_cache(user_id)
        
        # Update running bot configuration if bot is active
        import app as app_module
        if app_module.trading_bot is not None and app_module.trading_bot.user_id == user_id:
            try:
                app_module.trading_bot.update_config(config)
                logger.info(f"Updated running bot configuration for user: {user_id}")
            except Exception as e:
                logger.error(f"Error updating running bot configuration: {str(e)}")
        
        logger.info(f"Configuration updated for user: {user_id}")
        
        return jsonify(create_api_response(
            success=True,
            message='Configuração salva com sucesso',
            data={
                'asset': config.asset,
                'trade_amount': config.trade_amount,
                'strategy_mode': config.strategy_mode,
                'timeframe': config.timeframe
            }
        )), 200
        
    except Exception as e:
        logger.error(f"Save config error: {str(e)}")
        db.session.rollback()
        return jsonify(create_api_response(
            success=False,
            message='Erro interno do servidor',
            errors=[str(e)]
        )), 500

# Bot control routes
@api.route('/bot/start', methods=['POST'])
@jwt_required()
@limit_bot_control
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
@limit_bot_control
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
@limit_api
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
@limit_force_trade
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

# Stop loss test route removed - stop loss is now based on losing all 3 martingale levels

# Dashboard routes
@api.route('/dashboard/stats', methods=['GET'])
@jwt_required()
@limit_api
@cached(timeout=60, key_prefix='dashboard_stats:')
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
            # Record successful connection since bot is working
            record_connection_success(user_id)
        else:
            # Try to get from cache first
            cached_balance = get_cached_balance(user_id, account_type)
            if cached_balance is not None:
                balance = cached_balance
            else:
                # Check if we should skip connection due to recent failures
                if should_skip_connection(user_id):
                    logger.info(f"Using fallback balance ${balance} due to connection cooldown")
                else:
                    # If no cache, connect temporarily to get real balance
                    try:
                        if user and user.iq_email and user.iq_password:
                            from services.iq_option_service import IQOptionService
                            temp_service = IQOptionService(user.iq_email, user.iq_password)
                            logger.info(f"Connecting to IQ Option to get {account_type} balance...")
                            
                            # Set a shorter timeout for dashboard requests
                            connection_success = False
                            try:
                                connection_success = temp_service.connect(timeout=10)  # 10 second timeout
                            except Exception as conn_e:
                                logger.error(f"Connection timeout/error: {str(conn_e)}")
                                record_connection_failure(user_id)
                                connection_success = False
                            
                            if connection_success:
                                # Set account type before getting balance
                                if temp_service.set_account_type(account_type):
                                    real_balance = temp_service.update_balance()
                                    if real_balance > 0:
                                        balance = real_balance
                                        logger.info(f"Retrieved {account_type} balance from IQ Option: ${balance}")
                                        # Cache the balance
                                        set_cached_balance(user_id, balance, account_type)
                                        # Record successful connection
                                        record_connection_success(user_id)
                                    else:
                                        logger.warning(f"IQ Option returned 0 balance for {account_type}")
                                        record_connection_failure(user_id)
                                else:
                                    logger.warning(f"Failed to set account type to {account_type}")
                                    record_connection_failure(user_id)
                                temp_service.disconnect()
                                logger.info("Disconnected from IQ Option")
                            else:
                                logger.error("Failed to connect to IQ Option for balance")
                                record_connection_failure(user_id)
                        else:
                            logger.warning("No IQ Option credentials found for user")
                    except Exception as e:
                        logger.error(f"Error getting {account_type} balance: {str(e)}")
                        record_connection_failure(user_id)
        
        # Get today's session targets
        session_targets = get_today_session_targets(user_id)
        
        # Include Take Profit and Stop Loss information from bot status
        response_data = {
            'balance': balance,
            'today_profit': today_profit,
            'win_rate': win_rate,
            'bot_status': bot_status,  # Return the full bot status object instead of string
            'total_trades': total_trades,
            'win_trades': win_trades,
            'loss_trades': loss_trades,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'best_streak': best_streak,
            'recent_trades': recent_trades_data,
            'profit_history': profit_history,
            'last_trade': recent_trades_data[0] if recent_trades_data else None,
            'next_schedule': get_next_schedule(user_id),
            'session_targets': session_targets
        }
        
        # Add Take Profit and Stop Loss information if bot is running
        if bot_status.get('running', False) and app_module.trading_bot is not None:
            full_status = app_module.trading_bot.get_status()
            # Convert last_signal to JSON-serializable format
            last_signal = full_status.get('last_signal', None)
            if last_signal:
                last_signal = convert_numpy_to_json_serializable(last_signal)
            
            response_data.update({
                'session_profit': full_status.get('session_profit', 0),
                'take_profit_target': full_status.get('take_profit_target', 0),
                'stop_loss_method': full_status.get('stop_loss_method', 'Martingale 3 levels'),
                'take_profit_reached': full_status.get('take_profit_reached', False),
                'stop_loss_reached': full_status.get('stop_loss_reached', False),
                'last_signal': last_signal
            })
        else:
            # Default values when bot is not running
            response_data.update({
                'session_profit': 0,
                'take_profit_target': 0,
                'stop_loss_method': 'Martingale 3 levels',
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
@limit_api
@cached(timeout=180, key_prefix='trade_history:')
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

def get_today_session_targets(user_id):
    """Get today's session targets status"""
    try:
        today = datetime.now().date()
        
        # Get all session targets for today
        session_targets = SessionTargets.query.filter(
            SessionTargets.user_id == user_id,
            SessionTargets.date == today
        ).all()
        
        # Create a dictionary with session status
        targets_data = {
            'morning': {
                'take_profit_reached': False,
                'stop_loss_reached': False,
                'session_profit': 0.0,
                'total_trades': 0,
                'target_reached_at': None
            },
            'afternoon': {
                'take_profit_reached': False,
                'stop_loss_reached': False,
                'session_profit': 0.0,
                'total_trades': 0,
                'target_reached_at': None
            },
            'night': {
                'take_profit_reached': False,
                'stop_loss_reached': False,
                'session_profit': 0.0,
                'total_trades': 0,
                'target_reached_at': None
            }
        }
        
        # Update with actual data
        for target in session_targets:
            if target.session_type in targets_data:
                targets_data[target.session_type] = {
                    'take_profit_reached': target.take_profit_reached,
                    'stop_loss_reached': target.stop_loss_reached,
                    'session_profit': target.session_profit,
                    'total_trades': target.total_trades,
                    'target_reached_at': target.target_reached_at.strftime('%H:%M:%S') if target.target_reached_at else None
                }
        
        return targets_data
        
    except Exception as e:
        logger.error(f"Error getting session targets: {e}")
        return {
            'morning': {'take_profit_reached': False, 'stop_loss_reached': False, 'session_profit': 0.0, 'total_trades': 0, 'target_reached_at': None},
            'afternoon': {'take_profit_reached': False, 'stop_loss_reached': False, 'session_profit': 0.0, 'total_trades': 0, 'target_reached_at': None},
            'night': {'take_profit_reached': False, 'stop_loss_reached': False, 'session_profit': 0.0, 'total_trades': 0, 'target_reached_at': None}
        }

def get_next_schedule(user_id):
    """Get next scheduled trading session"""
    try:
        config = TradingConfig.query.filter_by(user_id=user_id).first()
        if not config or config.operation_mode != 'auto':
            return "Não Programado"
        
        now = datetime.now()
        current_time = now.time()
        
        # List of all sessions with their times
        sessions = []
        
        if config.morning_start and getattr(config, 'morning_enabled', True):
            morning_start = datetime.strptime(config.morning_start, '%H:%M').time()
            sessions.append(('morning', morning_start, config.morning_start))
        
        if config.afternoon_start and getattr(config, 'afternoon_enabled', True):
            afternoon_start = datetime.strptime(config.afternoon_start, '%H:%M').time()
            sessions.append(('afternoon', afternoon_start, config.afternoon_start))
        
        if config.night_start and getattr(config, 'night_enabled', False):
            night_start = datetime.strptime(config.night_start, '%H:%M').time()
            sessions.append(('night', night_start, config.night_start))
        
        # Sort sessions by time
        sessions.sort(key=lambda x: x[1])
        
        # Find next session today
        for session_name, session_time, session_str in sessions:
            if current_time < session_time:
                return f"Hoje {session_str}"
        
        # If all sessions passed today, get first session tomorrow
        if sessions:
            return f"Amanhã {sessions[0][2]}"
        
        return "Não Programado"
        
    except Exception as e:
        logger.error(f"Error getting next schedule: {e}")
        return "Erro"

# Machine Learning routes
@api.route('/ml/models', methods=['GET'])
@jwt_required()
@limit_api
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
@limit_api
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
@limit_api
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

# Rate Limiter monitoring endpoint
@api.route('/admin/rate-limiter/stats', methods=['GET'])
@jwt_required()
@limit_api
def get_rate_limiter_stats_endpoint():
    """Get rate limiter statistics (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is admin (you can implement your own admin check logic)
        # For now, we'll allow any authenticated user to see stats
        
        stats = get_rate_limiter_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'Estatísticas do rate limiter obtidas com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Get rate limiter stats error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao obter estatísticas do rate limiter'
        }), 500

# Rate limiter cleanup endpoint
@api.route('/admin/rate-limiter/cleanup', methods=['POST'])
@jwt_required()
@limit_api
def cleanup_rate_limiter_endpoint():
    """Manually trigger rate limiter cleanup"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is admin (you can implement your own admin check logic)
        # For now, we'll allow any authenticated user to trigger cleanup
        
        cleanup_rate_limiter()
        
        return jsonify({
            'success': True,
            'message': 'Limpeza do rate limiter executada com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Rate limiter cleanup error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao executar limpeza do rate limiter'
        }), 500

# Cache monitoring endpoint
@api.route('/admin/cache/stats', methods=['GET'])
@jwt_required()
@limit_api
def get_cache_stats_endpoint():
    """Get cache system statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is admin (you can implement your own admin check logic)
        # For now, we'll allow any authenticated user to see cache stats
        
        cache = get_cache()
        stats = cache.get_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'Estatísticas do cache obtidas com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Get cache stats error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao obter estatísticas do cache'
        }), 500

# Cache cleanup endpoint
@api.route('/admin/cache/clear', methods=['POST'])
@jwt_required()
@limit_api
def clear_cache_endpoint():
    """Clear cache data"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is admin (you can implement your own admin check logic)
        # For now, we'll allow any authenticated user to clear cache
        
        data = request.get_json() or {}
        pattern = data.get('pattern', '*')  # Default to clear all
        
        cache = get_cache()
        
        if pattern == '*':
            # Clear all cache
            cache.clear_all()
            message = 'Todo o cache foi limpo com sucesso'
        else:
            # Clear specific pattern
            cache.clear_pattern(pattern)
            message = f'Cache com padrão "{pattern}" foi limpo com sucesso'
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao limpar cache'
        }), 500

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

# Periodic cleanup task (should be called by a scheduler)
@api.before_request
def periodic_rate_limiter_cleanup():
    """Periodic cleanup of rate limiter data"""
    import random
    # Only run cleanup randomly (1% chance per request) to avoid overhead
    if random.random() < 0.01:
        try:
            cleanup_rate_limiter()
        except Exception as e:
            logger.error(f"Periodic rate limiter cleanup error: {str(e)}")

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint não encontrado'}), 404

@api.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'message': 'Erro interno do servidor'}), 500