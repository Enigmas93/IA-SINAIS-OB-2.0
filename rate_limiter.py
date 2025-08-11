from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict, deque
from validators import create_api_response

logger = logging.getLogger(__name__)

class RateLimiter:
    """Sistema de rate limiting baseado em memória"""
    
    def __init__(self, config=None):
        # Armazena tentativas por IP/usuário
        self.attempts = defaultdict(deque)
        # Armazena bloqueios temporários
        self.blocked_ips = {}
        self.blocked_users = {}
        
        # Configurações de rate limiting (carregadas do config centralizado)
        if config and hasattr(config, 'RATE_LIMITING'):
            self.limits = config.RATE_LIMITING
            logger.info("Rate limiter configurado com configurações centralizadas")
        else:
            # Fallback para configurações padrão
            self.limits = {
                'login': {'requests': 5, 'window': 300, 'block_duration': 900},
                'register': {'requests': 3, 'window': 600, 'block_duration': 1800},
                'api_general': {'requests': 100, 'window': 60, 'block_duration': 300},
                'config_save': {'requests': 10, 'window': 60, 'block_duration': 300},
                'bot_control': {'requests': 20, 'window': 60, 'block_duration': 300},
                'force_trade': {'requests': 30, 'window': 60, 'block_duration': 600}
            }
            logger.warning("Rate limiter usando configurações padrão (config não fornecido)")
    
    def get_client_id(self, user_id=None):
        """Obtém identificador único do cliente (IP + User ID se disponível)"""
        ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if ip:
            ip = ip.split(',')[0].strip()
        else:
            ip = request.remote_addr or 'unknown'
        
        if user_id:
            return f"user_{user_id}_{ip}"
        return f"ip_{ip}"
    
    def is_blocked(self, client_id, limit_type):
        """Verifica se o cliente está bloqueado"""
        current_time = time.time()
        
        # Verifica bloqueio por IP
        if client_id in self.blocked_ips:
            if current_time < self.blocked_ips[client_id]:
                return True
            else:
                del self.blocked_ips[client_id]
        
        # Verifica bloqueio por usuário (se aplicável)
        if client_id.startswith('user_'):
            user_key = client_id.split('_')[1]
            if user_key in self.blocked_users:
                if current_time < self.blocked_users[user_key]:
                    return True
                else:
                    del self.blocked_users[user_key]
        
        return False
    
    def add_attempt(self, client_id, limit_type):
        """Adiciona uma tentativa e verifica se excedeu o limite"""
        current_time = time.time()
        limit_config = self.limits.get(limit_type, self.limits['api_general'])
        window = limit_config['window']
        max_requests = limit_config['requests']
        
        # Remove tentativas antigas
        attempts_queue = self.attempts[f"{client_id}_{limit_type}"]
        while attempts_queue and attempts_queue[0] < current_time - window:
            attempts_queue.popleft()
        
        # Adiciona nova tentativa
        attempts_queue.append(current_time)
        
        # Verifica se excedeu o limite
        if len(attempts_queue) > max_requests:
            self.block_client(client_id, limit_type)
            return False
        
        return True
    
    def block_client(self, client_id, limit_type):
        """Bloqueia um cliente temporariamente"""
        current_time = time.time()
        limit_config = self.limits.get(limit_type, self.limits['api_general'])
        block_duration = limit_config['block_duration']
        block_until = current_time + block_duration
        
        # Bloqueia por IP
        self.blocked_ips[client_id] = block_until
        
        # Se for usuário específico, bloqueia também por usuário
        if client_id.startswith('user_'):
            user_key = client_id.split('_')[1]
            self.blocked_users[user_key] = block_until
        
        logger.warning(f"Cliente {client_id} bloqueado por {block_duration}s devido a excesso de tentativas ({limit_type})")
    
    def get_remaining_attempts(self, client_id, limit_type):
        """Retorna o número de tentativas restantes"""
        current_time = time.time()
        limit_config = self.limits.get(limit_type, self.limits['api_general'])
        window = limit_config['window']
        max_requests = limit_config['requests']
        
        attempts_queue = self.attempts[f"{client_id}_{limit_type}"]
        # Remove tentativas antigas
        while attempts_queue and attempts_queue[0] < current_time - window:
            attempts_queue.popleft()
        
        return max(0, max_requests - len(attempts_queue))
    
    def get_block_time_remaining(self, client_id):
        """Retorna o tempo restante de bloqueio em segundos"""
        current_time = time.time()
        
        # Verifica bloqueio por IP
        if client_id in self.blocked_ips:
            remaining = self.blocked_ips[client_id] - current_time
            if remaining > 0:
                return remaining
        
        # Verifica bloqueio por usuário
        if client_id.startswith('user_'):
            user_key = client_id.split('_')[1]
            if user_key in self.blocked_users:
                remaining = self.blocked_users[user_key] - current_time
                if remaining > 0:
                    return remaining
        
        return 0
    
    def cleanup_old_data(self):
        """Remove dados antigos para economizar memória"""
        current_time = time.time()
        
        # Remove bloqueios expirados
        expired_ips = [ip for ip, block_time in self.blocked_ips.items() if current_time > block_time]
        for ip in expired_ips:
            del self.blocked_ips[ip]
        
        expired_users = [user for user, block_time in self.blocked_users.items() if current_time > block_time]
        for user in expired_users:
            del self.blocked_users[user]
        
        # Remove tentativas muito antigas (mais de 1 hora)
        old_threshold = current_time - 3600
        keys_to_remove = []
        
        for key, attempts_queue in self.attempts.items():
            while attempts_queue and attempts_queue[0] < old_threshold:
                attempts_queue.popleft()
            if not attempts_queue:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.attempts[key]
        
        logger.info(f"Rate limiter cleanup: removed {len(expired_ips)} expired IP blocks, {len(expired_users)} expired user blocks, {len(keys_to_remove)} empty attempt queues")

# Instância global do rate limiter (será inicializada com config)
rate_limiter = None

def initialize_rate_limiter(config=None):
    """Inicializa o rate limiter com configuração"""
    global rate_limiter
    rate_limiter = RateLimiter(config)
    logger.info("Rate limiter inicializado")
    return rate_limiter

def get_rate_limiter():
    """Obtém a instância do rate limiter (inicializa se necessário)"""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
        logger.warning("Rate limiter inicializado sem configuração")
    return rate_limiter

def limit_requests(limit_type='api_general', get_user_id=None):
    """Decorator para aplicar rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                limiter = get_rate_limiter()
                
                # Obtém ID do usuário se fornecido
                user_id = None
                if get_user_id:
                    try:
                        if callable(get_user_id):
                            user_id = get_user_id()
                        else:
                            user_id = get_user_id
                    except:
                        pass
                
                client_id = limiter.get_client_id(user_id)
                
                # Verifica se está bloqueado
                if limiter.is_blocked(client_id, limit_type):
                    remaining_time = limiter.get_block_time_remaining(client_id)
                    logger.warning(f"Request blocked for {client_id} - {remaining_time:.0f}s remaining")
                    
                    return jsonify(create_api_response(
                        success=False,
                        message=f'Muitas tentativas. Tente novamente em {remaining_time:.0f} segundos',
                        errors=[f'Rate limit exceeded. Try again in {remaining_time:.0f} seconds']
                    )), 429
                
                # Adiciona tentativa e verifica limite
                if not limiter.add_attempt(client_id, limit_type):
                    remaining_time = limiter.get_block_time_remaining(client_id)
                    
                    return jsonify(create_api_response(
                        success=False,
                        message=f'Limite de tentativas excedido. Bloqueado por {remaining_time:.0f} segundos',
                        errors=[f'Rate limit exceeded. Blocked for {remaining_time:.0f} seconds']
                    )), 429
                
                # Adiciona informações de rate limit aos headers da resposta
                response = f(*args, **kwargs)
                
                if hasattr(response, 'headers'):
                    remaining = limiter.get_remaining_attempts(client_id, limit_type)
                    limit_config = limiter.limits.get(limit_type, limiter.limits['api_general'])
                    
                    response.headers['X-RateLimit-Limit'] = str(limit_config['requests'])
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Window'] = str(limit_config['window'])
                
                return response
                
            except Exception as e:
                logger.error(f"Rate limiter error: {str(e)}")
                # Em caso de erro no rate limiter, permite a requisição
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def get_current_user_id():
    """Função auxiliar para obter ID do usuário atual do JWT"""
    try:
        from flask_jwt_extended import get_jwt_identity
        return get_jwt_identity()
    except:
        return None

def cleanup_rate_limiter():
    """Função para limpeza periódica do rate limiter"""
    limiter = get_rate_limiter()
    limiter.cleanup_old_data()

# Decorators específicos para diferentes tipos de endpoints
def limit_login(f):
    """Rate limiting específico para login"""
    return limit_requests('login')(f)

def limit_register(f):
    """Rate limiting específico para registro"""
    return limit_requests('register')(f)

def limit_api(f):
    """Rate limiting geral para APIs"""
    return limit_requests('api_general', get_current_user_id)(f)

def limit_config(f):
    """Rate limiting para salvamento de configurações"""
    return limit_requests('config_save', get_current_user_id)(f)

def limit_bot_control(f):
    """Rate limiting para controle do bot"""
    return limit_requests('bot_control', get_current_user_id)(f)

def limit_force_trade(f):
    """Rate limiting para trades forçados"""
    return limit_requests('force_trade', get_current_user_id)(f)

# Função para monitoramento
def get_rate_limiter_stats():
    """Retorna estatísticas do rate limiter"""
    limiter = get_rate_limiter()
    return {
        'blocked_ips': len(limiter.blocked_ips),
        'blocked_users': len(limiter.blocked_users),
        'active_attempts': len(limiter.attempts),
        'limits_config': limiter.limits
    }