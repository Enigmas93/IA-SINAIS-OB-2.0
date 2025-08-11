import os
from datetime import timedelta
from typing import Dict, Any, Optional
import logging

class Config:
    """Configuração base do sistema"""
    
    # Configurações básicas do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Configurações JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = 'HS256'
    
    # Configurações de Rate Limiting
    RATE_LIMITING = {
        'login': {
            'requests': int(os.environ.get('RATE_LIMIT_LOGIN_REQUESTS', 5)),
            'window': int(os.environ.get('RATE_LIMIT_LOGIN_WINDOW', 300)),  # 5 minutos
            'block_duration': int(os.environ.get('RATE_LIMIT_LOGIN_BLOCK', 900))  # 15 minutos
        },
        'register': {
            'requests': int(os.environ.get('RATE_LIMIT_REGISTER_REQUESTS', 3)),
            'window': int(os.environ.get('RATE_LIMIT_REGISTER_WINDOW', 600)),  # 10 minutos
            'block_duration': int(os.environ.get('RATE_LIMIT_REGISTER_BLOCK', 1800))  # 30 minutos
        },
        'api_general': {
            'requests': int(os.environ.get('RATE_LIMIT_API_REQUESTS', 100)),
            'window': int(os.environ.get('RATE_LIMIT_API_WINDOW', 60)),  # 1 minuto
            'block_duration': int(os.environ.get('RATE_LIMIT_API_BLOCK', 300))  # 5 minutos
        },
        'config_save': {
            'requests': int(os.environ.get('RATE_LIMIT_CONFIG_REQUESTS', 10)),
            'window': int(os.environ.get('RATE_LIMIT_CONFIG_WINDOW', 60)),
            'block_duration': int(os.environ.get('RATE_LIMIT_CONFIG_BLOCK', 300))
        },
        'bot_control': {
            'requests': int(os.environ.get('RATE_LIMIT_BOT_REQUESTS', 20)),
            'window': int(os.environ.get('RATE_LIMIT_BOT_WINDOW', 60)),
            'block_duration': int(os.environ.get('RATE_LIMIT_BOT_BLOCK', 300))
        },
        'force_trade': {
            'requests': int(os.environ.get('RATE_LIMIT_TRADE_REQUESTS', 30)),
            'window': int(os.environ.get('RATE_LIMIT_TRADE_WINDOW', 60)),
            'block_duration': int(os.environ.get('RATE_LIMIT_TRADE_BLOCK', 600))  # 10 minutos
        }
    }
    
    # Configurações de Cache
    CACHE_CONFIG = {
        'balance_cache_duration': int(os.environ.get('BALANCE_CACHE_DURATION', 300)),  # 5 minutos
        'signal_cache_duration': int(os.environ.get('SIGNAL_CACHE_DURATION', 60)),  # 1 minuto
        'market_data_cache_duration': int(os.environ.get('MARKET_DATA_CACHE_DURATION', 30))  # 30 segundos
    }
    
    # Configurações de Conexão IQ Option
    IQ_OPTION_CONFIG = {
        'connection_timeout': int(os.environ.get('IQ_CONNECTION_TIMEOUT', 30)),
        'max_connection_retries': int(os.environ.get('IQ_MAX_RETRIES', 3)),
        'retry_delay': int(os.environ.get('IQ_RETRY_DELAY', 5)),
        'heartbeat_interval': int(os.environ.get('IQ_HEARTBEAT_INTERVAL', 30)),
        'max_failures_before_cooldown': int(os.environ.get('IQ_MAX_FAILURES', 3)),
        'failure_cooldown_duration': int(os.environ.get('IQ_FAILURE_COOLDOWN', 600))  # 10 minutos
    }
    
    # Configurações de Trading
    TRADING_CONFIG = {
        'default_trade_amount': float(os.environ.get('DEFAULT_TRADE_AMOUNT', 10.0)),
        'min_trade_amount': float(os.environ.get('MIN_TRADE_AMOUNT', 1.0)),
        'max_trade_amount': float(os.environ.get('MAX_TRADE_AMOUNT', 1000.0)),
        'default_take_profit': float(os.environ.get('DEFAULT_TAKE_PROFIT', 70.0)),
        'min_take_profit': float(os.environ.get('MIN_TAKE_PROFIT', 10.0)),
        'max_take_profit': float(os.environ.get('MAX_TAKE_PROFIT', 500.0)),
        'max_martingale_levels': int(os.environ.get('MAX_MARTINGALE_LEVELS', 3)),
        'min_signal_score': int(os.environ.get('MIN_SIGNAL_SCORE', 60)),
        'max_signal_score': int(os.environ.get('MAX_SIGNAL_SCORE', 100)),
        'supported_assets': os.environ.get('SUPPORTED_ASSETS', 'EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,EURGBP,EURJPY,GBPJPY').split(','),
        'supported_timeframes': os.environ.get('SUPPORTED_TIMEFRAMES', '1m,5m,15m,30m,1h').split(','),
        'strategy_modes': os.environ.get('STRATEGY_MODES', 'conservador,intermediario,agressivo').split(','),
        'advance_signal_minutes': int(os.environ.get('ADVANCE_SIGNAL_MINUTES', 2)),
        'min_advance_signal_minutes': int(os.environ.get('MIN_ADVANCE_SIGNAL_MINUTES', 1)),
        'max_advance_signal_minutes': int(os.environ.get('MAX_ADVANCE_SIGNAL_MINUTES', 10))
    }
    
    # Configurações de Machine Learning
    ML_CONFIG = {
        'enabled': os.environ.get('ML_ENABLED', 'true').lower() == 'true',
        'model_retrain_interval_days': int(os.environ.get('ML_RETRAIN_INTERVAL', 7)),
        'model_retrain_trade_threshold': int(os.environ.get('ML_RETRAIN_TRADES', 50)),
        'min_accuracy_threshold': float(os.environ.get('ML_MIN_ACCURACY', 0.6)),
        'feature_window_size': int(os.environ.get('ML_FEATURE_WINDOW', 20)),
        'prediction_confidence_threshold': float(os.environ.get('ML_CONFIDENCE_THRESHOLD', 0.7))
    }
    
    # Configurações de Logging
    LOGGING_CONFIG = {
        'level': os.environ.get('LOG_LEVEL', 'INFO').upper(),
        'format': os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        'file_path': os.environ.get('LOG_FILE_PATH', 'logs/app.log'),
        'max_file_size': int(os.environ.get('LOG_MAX_SIZE', 10485760)),  # 10MB
        'backup_count': int(os.environ.get('LOG_BACKUP_COUNT', 5)),
        'enable_file_logging': os.environ.get('LOG_TO_FILE', 'true').lower() == 'true'
    }
    
    # Configurações de Segurança
    SECURITY_CONFIG = {
        'password_min_length': int(os.environ.get('PASSWORD_MIN_LENGTH', 6)),
        'password_require_uppercase': os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'false').lower() == 'true',
        'password_require_lowercase': os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'false').lower() == 'true',
        'password_require_numbers': os.environ.get('PASSWORD_REQUIRE_NUMBERS', 'false').lower() == 'true',
        'password_require_symbols': os.environ.get('PASSWORD_REQUIRE_SYMBOLS', 'false').lower() == 'true',
        'session_timeout_minutes': int(os.environ.get('SESSION_TIMEOUT', 480)),  # 8 horas
        'max_login_attempts': int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5)),
        'account_lockout_duration': int(os.environ.get('ACCOUNT_LOCKOUT_DURATION', 900))  # 15 minutos
    }
    
    # Configurações de Performance
    PERFORMANCE_CONFIG = {
        'enable_query_optimization': os.environ.get('ENABLE_QUERY_OPTIMIZATION', 'true').lower() == 'true',
        'database_pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'database_max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
        'enable_compression': os.environ.get('ENABLE_COMPRESSION', 'true').lower() == 'true',
        'static_file_cache_timeout': int(os.environ.get('STATIC_CACHE_TIMEOUT', 3600))  # 1 hora
    }
    
    # Configurações de WebSocket
    WEBSOCKET_CONFIG = {
        'enabled': os.environ.get('WEBSOCKET_ENABLED', 'true').lower() == 'true',
        'heartbeat_interval': int(os.environ.get('WS_HEARTBEAT_INTERVAL', 30)),
        'connection_timeout': int(os.environ.get('WS_CONNECTION_TIMEOUT', 60)),
        'max_connections_per_user': int(os.environ.get('WS_MAX_CONNECTIONS', 3)),
        'message_queue_size': int(os.environ.get('WS_QUEUE_SIZE', 100))
    }
    
    # Configurações de Monitoramento
    MONITORING_CONFIG = {
        'enable_health_checks': os.environ.get('ENABLE_HEALTH_CHECKS', 'true').lower() == 'true',
        'health_check_interval': int(os.environ.get('HEALTH_CHECK_INTERVAL', 60)),
        'enable_metrics': os.environ.get('ENABLE_METRICS', 'true').lower() == 'true',
        'metrics_retention_days': int(os.environ.get('METRICS_RETENTION_DAYS', 30)),
        'alert_thresholds': {
            'error_rate': float(os.environ.get('ALERT_ERROR_RATE', 0.05)),  # 5%
            'response_time': float(os.environ.get('ALERT_RESPONSE_TIME', 2.0)),  # 2 segundos
            'memory_usage': float(os.environ.get('ALERT_MEMORY_USAGE', 0.8))  # 80%
        }
    }
    
    @classmethod
    def get_config_value(cls, section: str, key: str, default: Any = None) -> Any:
        """Obtém um valor de configuração específico"""
        section_config = getattr(cls, section.upper() + '_CONFIG', {})
        return section_config.get(key, default)
    
    @classmethod
    def update_config_value(cls, section: str, key: str, value: Any) -> bool:
        """Atualiza um valor de configuração (apenas em memória)"""
        try:
            section_config = getattr(cls, section.upper() + '_CONFIG', {})
            section_config[key] = value
            return True
        except Exception:
            return False
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Valida todas as configurações e retorna erros encontrados"""
        errors = []
        warnings = []
        
        # Validar configurações críticas
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            if os.environ.get('FLASK_ENV') == 'production':
                errors.append('SECRET_KEY deve ser alterada em produção')
            else:
                warnings.append('Usando SECRET_KEY padrão (apenas desenvolvimento)')
        
        # Validar configurações de rate limiting
        for limit_type, config in cls.RATE_LIMITING.items():
            if config['requests'] <= 0:
                errors.append(f'Rate limiting {limit_type}: requests deve ser > 0')
            if config['window'] <= 0:
                errors.append(f'Rate limiting {limit_type}: window deve ser > 0')
            if config['block_duration'] <= 0:
                errors.append(f'Rate limiting {limit_type}: block_duration deve ser > 0')
        
        # Validar configurações de trading
        if cls.TRADING_CONFIG['min_trade_amount'] >= cls.TRADING_CONFIG['max_trade_amount']:
            errors.append('min_trade_amount deve ser menor que max_trade_amount')
        
        if cls.TRADING_CONFIG['min_take_profit'] >= cls.TRADING_CONFIG['max_take_profit']:
            errors.append('min_take_profit deve ser menor que max_take_profit')
        
        # Validar configurações de ML
        if cls.ML_CONFIG['min_accuracy_threshold'] <= 0 or cls.ML_CONFIG['min_accuracy_threshold'] > 1:
            errors.append('min_accuracy_threshold deve estar entre 0 e 1')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @classmethod
    def get_environment_info(cls) -> Dict[str, Any]:
        """Retorna informações sobre o ambiente atual"""
        return {
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'debug': os.environ.get('FLASK_DEBUG', 'false').lower() == 'true',
            'python_version': os.sys.version,
            'config_source': 'environment_variables' if any(key.startswith(('RATE_LIMIT_', 'ML_', 'LOG_')) for key in os.environ) else 'defaults'
        }

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///trading_bot_dev.db'
    
    # Rate limiting mais permissivo em desenvolvimento
    RATE_LIMITING = {
        'login': {'requests': 10, 'window': 300, 'block_duration': 300},
        'register': {'requests': 5, 'window': 600, 'block_duration': 600},
        'api_general': {'requests': 200, 'window': 60, 'block_duration': 60},
        'config_save': {'requests': 20, 'window': 60, 'block_duration': 60},
        'bot_control': {'requests': 50, 'window': 60, 'block_duration': 60},
        'force_trade': {'requests': 100, 'window': 60, 'block_duration': 60}
    }
    
    # Logging mais verboso
    LOGGING_CONFIG = {
        **Config.LOGGING_CONFIG,
        'level': 'DEBUG'
    }

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///trading_bot.db'
    
    # Configurações de segurança mais rigorosas
    SECURITY_CONFIG = {
        **Config.SECURITY_CONFIG,
        'password_min_length': 8,
        'password_require_uppercase': True,
        'password_require_lowercase': True,
        'password_require_numbers': True,
        'max_login_attempts': 3,
        'account_lockout_duration': 1800  # 30 minutos
    }
    
    # Rate limiting mais restritivo
    RATE_LIMITING = {
        'login': {'requests': 3, 'window': 300, 'block_duration': 1800},
        'register': {'requests': 2, 'window': 600, 'block_duration': 3600},
        'api_general': {'requests': 60, 'window': 60, 'block_duration': 600},
        'config_save': {'requests': 5, 'window': 60, 'block_duration': 600},
        'bot_control': {'requests': 10, 'window': 60, 'block_duration': 600},
        'force_trade': {'requests': 20, 'window': 60, 'block_duration': 1200}
    }

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Desabilitar rate limiting em testes
    RATE_LIMITING = {
        'login': {'requests': 1000, 'window': 1, 'block_duration': 1},
        'register': {'requests': 1000, 'window': 1, 'block_duration': 1},
        'api_general': {'requests': 1000, 'window': 1, 'block_duration': 1},
        'config_save': {'requests': 1000, 'window': 1, 'block_duration': 1},
        'bot_control': {'requests': 1000, 'window': 1, 'block_duration': 1},
        'force_trade': {'requests': 1000, 'window': 1, 'block_duration': 1}
    }
    
    # Cache desabilitado
    CACHE_CONFIG = {
        'balance_cache_duration': 0,
        'signal_cache_duration': 0,
        'market_data_cache_duration': 0
    }

# Mapeamento de configurações por ambiente
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(environment: Optional[str] = None) -> Config:
    """Retorna a configuração apropriada para o ambiente"""
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config_by_name.get(environment, DevelopmentConfig)
    return config_class()

def setup_logging(config: Config) -> None:
    """Configura o sistema de logging baseado na configuração"""
    log_config = config.LOGGING_CONFIG
    
    # Configurar nível de log
    log_level = getattr(logging, log_config['level'], logging.INFO)
    
    # Configurar formatação
    formatter = logging.Formatter(log_config['format'])
    
    # Configurar handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configurar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Configurar handler para arquivo se habilitado
    if log_config['enable_file_logging']:
        try:
            from logging.handlers import RotatingFileHandler
            import os
            
            # Criar diretório de logs se não existir
            log_dir = os.path.dirname(log_config['file_path'])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = RotatingFileHandler(
                log_config['file_path'],
                maxBytes=log_config['max_file_size'],
                backupCount=log_config['backup_count']
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            logging.warning(f"Não foi possível configurar logging para arquivo: {e}")

# Função para validar configuração na inicialização
def validate_and_setup_config(environment: Optional[str] = None) -> Config:
    """Valida e configura o sistema baseado no ambiente"""
    config = get_config(environment)
    
    # Validar configuração
    validation_result = config.validate_config()
    
    if not validation_result['valid']:
        print("ERRO: Configuração inválida encontrada:")
        for error in validation_result['errors']:
            print(f"  - {error}")
        raise ValueError("Configuração inválida")
    
    if validation_result['warnings']:
        print("AVISO: Problemas de configuração encontrados:")
        for warning in validation_result['warnings']:
            print(f"  - {warning}")
    
    # Configurar logging
    setup_logging(config)
    
    # Log informações do ambiente
    env_info = config.get_environment_info()
    logging.info(f"Sistema iniciado - Ambiente: {env_info['environment']}, Debug: {env_info['debug']}")
    
    return config