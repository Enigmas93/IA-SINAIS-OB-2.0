from functools import wraps
from flask import request, jsonify
from pydantic import ValidationError
from schemas import (
    TradingConfigSchema, UserCredentialsSchema, TradeSignalSchema,
    TradeExecutionSchema, BotStatusSchema, APIResponseSchema, PaginationSchema
)
import logging

logger = logging.getLogger(__name__)

def validate_json(schema_class):
    """Decorator para validar dados JSON usando schemas Pydantic"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verifica se há dados JSON na requisição
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'message': 'Content-Type deve ser application/json',
                        'errors': ['Dados JSON são obrigatórios']
                    }), 400
                
                # Obtém os dados JSON
                json_data = request.get_json()
                if json_data is None:
                    return jsonify({
                        'success': False,
                        'message': 'Dados JSON inválidos ou vazios',
                        'errors': ['JSON malformado ou vazio']
                    }), 400
                
                # Valida os dados usando o schema
                try:
                    validated_data = schema_class(**json_data)
                    # Adiciona os dados validados ao request para uso na função
                    request.validated_data = validated_data
                    return f(*args, **kwargs)
                    
                except ValidationError as e:
                    # Formata os erros de validação
                    errors = []
                    for error in e.errors():
                        field = ' -> '.join(str(loc) for loc in error['loc'])
                        message = error['msg']
                        errors.append(f"{field}: {message}")
                    
                    logger.warning(f"Erro de validação na rota {request.endpoint}: {errors}")
                    
                    return jsonify({
                        'success': False,
                        'message': 'Dados de entrada inválidos',
                        'errors': errors
                    }), 400
                    
            except Exception as e:
                logger.error(f"Erro inesperado na validação: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': 'Erro interno do servidor',
                    'errors': ['Erro na validação dos dados']
                }), 500
                
        return decorated_function
    return decorator

def validate_query_params(schema_class):
    """Decorator para validar parâmetros de query usando schemas Pydantic"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Obtém os parâmetros de query
                query_params = request.args.to_dict()
                
                # Converte strings para tipos apropriados
                converted_params = {}
                for key, value in query_params.items():
                    # Tenta converter valores numéricos
                    if value.isdigit():
                        converted_params[key] = int(value)
                    elif value.replace('.', '', 1).isdigit():
                        converted_params[key] = float(value)
                    elif value.lower() in ['true', 'false']:
                        converted_params[key] = value.lower() == 'true'
                    else:
                        converted_params[key] = value
                
                # Valida os parâmetros usando o schema
                try:
                    validated_params = schema_class(**converted_params)
                    request.validated_params = validated_params
                    return f(*args, **kwargs)
                    
                except ValidationError as e:
                    errors = []
                    for error in e.errors():
                        field = ' -> '.join(str(loc) for loc in error['loc'])
                        message = error['msg']
                        errors.append(f"{field}: {message}")
                    
                    logger.warning(f"Erro de validação de parâmetros na rota {request.endpoint}: {errors}")
                    
                    return jsonify({
                        'success': False,
                        'message': 'Parâmetros de consulta inválidos',
                        'errors': errors
                    }), 400
                    
            except Exception as e:
                logger.error(f"Erro inesperado na validação de parâmetros: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': 'Erro interno do servidor',
                    'errors': ['Erro na validação dos parâmetros']
                }), 500
                
        return decorated_function
    return decorator

def sanitize_input(data):
    """Sanitiza dados de entrada removendo caracteres perigosos"""
    if isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        # Remove caracteres potencialmente perigosos
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        sanitized = data
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized.strip()
    else:
        return data

def validate_trading_config(data):
    """Validação específica para configurações de trading"""
    try:
        # Sanitiza os dados primeiro
        sanitized_data = sanitize_input(data)
        
        # Valida usando o schema
        config = TradingConfigSchema(**sanitized_data)
        
        # Validações adicionais de negócio
        if config.use_balance_percentage and config.balance_percentage is None:
            raise ValueError("Porcentagem do saldo é obrigatória quando habilitada")
        
        if config.martingale_enabled and config.max_martingale_levels < 1:
            raise ValueError("Níveis de martingale devem ser pelo menos 1 quando habilitado")
        
        # Verifica se pelo menos uma sessão está habilitada
        sessions_enabled = [
            config.morning_enabled,
            config.afternoon_enabled,
            config.night_enabled,
            config.continuous_mode
        ]
        
        if not any(sessions_enabled):
            raise ValueError("Pelo menos uma sessão ou modo contínuo deve estar habilitado")
        
        # Valida horários das sessões habilitadas
        if config.morning_enabled and not config.morning_start:
            raise ValueError("Horário de início da manhã é obrigatório quando sessão está habilitada")
        
        if config.afternoon_enabled and not config.afternoon_start:
            raise ValueError("Horário de início da tarde é obrigatório quando sessão está habilitada")
        
        if config.night_enabled and not config.night_start:
            raise ValueError("Horário de início da noite é obrigatório quando sessão está habilitada")
        
        return config
        
    except ValidationError as e:
        raise ValueError(f"Dados de configuração inválidos: {e}")
    except Exception as e:
        raise ValueError(f"Erro na validação: {str(e)}")

def validate_credentials(data):
    """Validação específica para credenciais"""
    try:
        sanitized_data = sanitize_input(data)
        credentials = UserCredentialsSchema(**sanitized_data)
        
        # Validações adicionais de segurança
        if len(credentials.iq_password) > 100:
            raise ValueError("Senha muito longa")
        
        if '@' not in credentials.iq_email:
            raise ValueError("Email inválido")
        
        return credentials
        
    except ValidationError as e:
        raise ValueError(f"Credenciais inválidas: {e}")
    except Exception as e:
        raise ValueError(f"Erro na validação: {str(e)}")

def validate_trade_signal(data):
    """Validação específica para sinais de trading"""
    try:
        signal = TradeSignalSchema(**data)
        
        # Validações de negócio
        if signal.direction != 'none' and signal.confidence < 0.5:
            logger.warning(f"Sinal com baixa confiança: {signal.confidence}")
        
        if signal.score_percentage < 50:
            logger.warning(f"Sinal com score baixo: {signal.score_percentage}%")
        
        return signal
        
    except ValidationError as e:
        raise ValueError(f"Sinal inválido: {e}")
    except Exception as e:
        raise ValueError(f"Erro na validação: {str(e)}")

def create_api_response(success=True, message=None, data=None, errors=None):
    """Cria uma resposta padronizada da API"""
    try:
        response_data = {
            'success': success,
            'message': message,
            'data': data,
            'errors': errors
        }
        
        # Valida a resposta usando o schema
        validated_response = APIResponseSchema(**response_data)
        return validated_response.dict()
        
    except Exception as e:
        logger.error(f"Erro ao criar resposta da API: {str(e)}")
        # Retorna resposta de erro padrão
        return {
            'success': False,
            'message': 'Erro interno do servidor',
            'errors': ['Erro na formatação da resposta'],
            'timestamp': None
        }

def validate_pagination_params(page=1, per_page=20):
    """Valida parâmetros de paginação"""
    try:
        pagination = PaginationSchema(
            page=page,
            per_page=per_page,
            total_pages=0,
            total_items=0
        )
        return pagination
        
    except ValidationError as e:
        raise ValueError(f"Parâmetros de paginação inválidos: {e}")
    except Exception as e:
        raise ValueError(f"Erro na validação: {str(e)}")

# Funções auxiliares para validação de tipos específicos
def is_valid_asset(asset):
    """Verifica se o asset é válido"""
    valid_assets = [
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
        'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP', 'AUDCAD', 'CADJPY',
        'EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC', 'AUDUSD-OTC'
    ]
    return asset.upper() in [a.upper() for a in valid_assets]

def is_valid_timeframe(timeframe):
    """Verifica se o timeframe é válido"""
    valid_timeframes = ['1m', '5m']
    return timeframe in valid_timeframes

def is_valid_direction(direction):
    """Verifica se a direção é válida"""
    valid_directions = ['call', 'put', 'none']
    return direction in valid_directions

def is_valid_strategy_mode(mode):
    """Verifica se o modo de estratégia é válido"""
    valid_modes = ['conservador', 'intermediario', 'agressivo']
    return mode in valid_modes