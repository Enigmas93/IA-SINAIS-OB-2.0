import redis
import json
import logging
import os
from typing import Any, Optional, Union, Dict
from datetime import datetime, timedelta
import pickle
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

class CacheManager:
    """Sistema de cache Redis com fallback para cache em memória"""
    
    def __init__(self, config=None):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_cache_expiry = {}
        self.config = config
        
        # Configurações de cache
        if config and hasattr(config, 'CACHE'):
            self.cache_config = config.CACHE
        else:
            # Configurações padrão
            self.cache_config = {
                'REDIS_URL': 'redis://localhost:6379/0',
                'DEFAULT_TIMEOUT': 300,  # 5 minutos
                'KEY_PREFIX': 'trading_bot:',
                'ENABLED': True,
                'FALLBACK_TO_MEMORY': True,
                'MAX_MEMORY_ITEMS': 1000
            }
        
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Inicializa conexão Redis"""
        if not self.cache_config.get('ENABLED', True):
            logger.info("Cache desabilitado por configuração")
            return
        
        # Verifica variável de ambiente USE_REDIS
        use_redis = os.getenv('USE_REDIS', 'true').lower() in ('true', '1', 'yes')
        if not use_redis:
            logger.info("Redis desabilitado por variável de ambiente USE_REDIS=false")
            logger.info("Usando cache em memória")
            self.redis_client = None
            return
        
        try:
            import redis
            self.redis_client = redis.from_url(
                self.cache_config.get('REDIS_URL', 'redis://localhost:6379/0'),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Testa conexão
            self.redis_client.ping()
            logger.info("Conexão Redis estabelecida com sucesso")
            
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis: {e}")
            fallback_enabled = os.getenv('CACHE_FALLBACK_TO_MEMORY', 'true').lower() in ('true', '1', 'yes')
            if fallback_enabled or self.cache_config.get('FALLBACK_TO_MEMORY', True):
                logger.info("Usando cache em memória como fallback")
                self.redis_client = None
            else:
                raise
    
    def _get_key(self, key: str) -> str:
        """Gera chave com prefixo"""
        prefix = self.cache_config.get('KEY_PREFIX', 'trading_bot:')
        return f"{prefix}{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serializa valor para armazenamento"""
        try:
            # Tenta JSON primeiro (mais rápido)
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            # Fallback para pickle
            return pickle.dumps(value).hex()
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserializa valor do cache"""
        try:
            # Tenta JSON primeiro
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            try:
                # Fallback para pickle
                return pickle.loads(bytes.fromhex(value))
            except Exception:
                # Se falhar, retorna string original
                return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor do cache"""
        cache_key = self._get_key(key)
        
        # Tenta Redis primeiro
        if self.redis_client:
            try:
                value = self.redis_client.get(cache_key)
                if value is not None:
                    return self._deserialize_value(value)
            except Exception as e:
                logger.warning(f"Erro ao ler do Redis: {e}")
        
        # Fallback para cache em memória
        if cache_key in self.memory_cache:
            # Verifica expiração
            if cache_key in self.memory_cache_expiry:
                if datetime.now() > self.memory_cache_expiry[cache_key]:
                    # Cache expirado
                    del self.memory_cache[cache_key]
                    del self.memory_cache_expiry[cache_key]
                    return default
            
            return self.memory_cache[cache_key]
        
        return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Define valor no cache"""
        cache_key = self._get_key(key)
        timeout = timeout or self.cache_config.get('DEFAULT_TIMEOUT', 300)
        
        # Tenta Redis primeiro
        if self.redis_client:
            try:
                serialized_value = self._serialize_value(value)
                self.redis_client.setex(cache_key, timeout, serialized_value)
                return True
            except Exception as e:
                logger.warning(f"Erro ao escrever no Redis: {e}")
        
        # Fallback para cache em memória
        self._cleanup_memory_cache()
        self.memory_cache[cache_key] = value
        self.memory_cache_expiry[cache_key] = datetime.now() + timedelta(seconds=timeout)
        return True
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        cache_key = self._get_key(key)
        
        # Remove do Redis
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Erro ao deletar do Redis: {e}")
        
        # Remove do cache em memória
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        if cache_key in self.memory_cache_expiry:
            del self.memory_cache_expiry[cache_key]
        
        return True
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        cache_key = self._get_key(key)
        
        # Verifica Redis primeiro
        if self.redis_client:
            try:
                return bool(self.redis_client.exists(cache_key))
            except Exception as e:
                logger.warning(f"Erro ao verificar existência no Redis: {e}")
        
        # Verifica cache em memória
        if cache_key in self.memory_cache:
            # Verifica expiração
            if cache_key in self.memory_cache_expiry:
                if datetime.now() > self.memory_cache_expiry[cache_key]:
                    # Cache expirado
                    del self.memory_cache[cache_key]
                    del self.memory_cache_expiry[cache_key]
                    return False
            return True
        
        return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Incrementa valor numérico no cache"""
        cache_key = self._get_key(key)
        
        # Tenta Redis primeiro
        if self.redis_client:
            try:
                return self.redis_client.incr(cache_key, amount)
            except Exception as e:
                logger.warning(f"Erro ao incrementar no Redis: {e}")
        
        # Fallback para cache em memória
        current_value = self.get(key, 0)
        if isinstance(current_value, (int, float)):
            new_value = current_value + amount
            self.set(key, new_value)
            return new_value
        else:
            self.set(key, amount)
            return amount
    
    def expire(self, key: str, timeout: int) -> bool:
        """Define tempo de expiração para uma chave"""
        cache_key = self._get_key(key)
        
        # Tenta Redis primeiro
        if self.redis_client:
            try:
                return bool(self.redis_client.expire(cache_key, timeout))
            except Exception as e:
                logger.warning(f"Erro ao definir expiração no Redis: {e}")
        
        # Fallback para cache em memória
        if cache_key in self.memory_cache:
            self.memory_cache_expiry[cache_key] = datetime.now() + timedelta(seconds=timeout)
            return True
        
        return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        count = 0
        
        # Redis
        if self.redis_client:
            try:
                keys = self.redis_client.keys(self._get_key(pattern))
                if keys:
                    count += self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Erro ao limpar padrão no Redis: {e}")
        
        # Cache em memória
        import fnmatch
        prefix = self._get_key('')
        pattern_with_prefix = self._get_key(pattern)
        keys_to_remove = []
        
        for key in list(self.memory_cache.keys()):
            # Remove prefix para comparar apenas a parte relevante
            key_without_prefix = key[len(prefix):] if key.startswith(prefix) else key
            pattern_without_prefix = pattern_with_prefix[len(prefix):] if pattern_with_prefix.startswith(prefix) else pattern
            
            # Usa fnmatch para suportar wildcards como *
            if fnmatch.fnmatch(key_without_prefix, pattern_without_prefix) or fnmatch.fnmatch(key, pattern_with_prefix):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.memory_cache_expiry:
                del self.memory_cache_expiry[key]
            count += 1
        
        logger.debug(f"Cleared {count} keys matching pattern '{pattern}'")
        return count
    
    def _cleanup_memory_cache(self):
        """Limpa cache em memória expirado e controla tamanho"""
        now = datetime.now()
        
        # Remove itens expirados
        expired_keys = []
        for key, expiry_time in self.memory_cache_expiry.items():
            if now > expiry_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self.memory_cache:
                del self.memory_cache[key]
            del self.memory_cache_expiry[key]
        
        # Controla tamanho máximo
        max_items = self.cache_config.get('MAX_MEMORY_ITEMS', 1000)
        if len(self.memory_cache) > max_items:
            # Remove os itens mais antigos
            items_to_remove = len(self.memory_cache) - max_items
            oldest_keys = sorted(
                self.memory_cache_expiry.keys(),
                key=lambda k: self.memory_cache_expiry.get(k, datetime.min)
            )[:items_to_remove]
            
            for key in oldest_keys:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.memory_cache_expiry:
                    del self.memory_cache_expiry[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        stats = {
            'redis_connected': self.redis_client is not None,
            'memory_cache_size': len(self.memory_cache),
            'memory_cache_max_size': self.cache_config.get('MAX_MEMORY_ITEMS', 1000)
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'N/A'),
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_total_commands': info.get('total_commands_processed', 0)
                })
            except Exception as e:
                logger.warning(f"Erro ao obter estatísticas do Redis: {e}")
                stats['redis_error'] = str(e)
        
        return stats

# Instância global do cache
cache_manager = None

def initialize_cache(config=None):
    """Inicializa o sistema de cache"""
    global cache_manager
    cache_manager = CacheManager(config)
    logger.info("Sistema de cache inicializado")
    return cache_manager

def get_cache():
    """Obtém a instância do cache manager"""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
        logger.warning("Cache manager inicializado sem configuração")
    return cache_manager

# Decorators para cache
def cached(timeout: int = 300, key_prefix: str = ''):
    """Decorator para cache de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Gera chave única baseada na função e argumentos
            func_name = f"{func.__module__}.{func.__name__}"
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}{func_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Tenta obter do cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit para {func_name}")
                return result
            
            # Executa função e armazena resultado
            logger.debug(f"Cache miss para {func_name}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

def cache_user_data(user_id: int, timeout: int = 600):
    """Decorator específico para cache de dados do usuário"""
    return cached(timeout=timeout, key_prefix=f'user:{user_id}:')

def cache_market_data(timeout: int = 60):
    """Decorator específico para cache de dados de mercado"""
    return cached(timeout=timeout, key_prefix='market:')

def invalidate_user_cache(user_id: int):
    """Invalida todo o cache de um usuário específico"""
    cache = get_cache()
    
    # Invalida cache com padrão user:{user_id}:*
    pattern1 = f'user:{user_id}:*'
    count1 = cache.clear_pattern(pattern1)
    
    # Invalida cache com padrão user_config: (usado pela rota GET /api/config)
    pattern2 = 'user_config:*'
    count2 = cache.clear_pattern(pattern2)
    
    total_count = count1 + count2
    logger.info(f"Invalidado {total_count} itens do cache para usuário {user_id} (user: {count1}, config: {count2})")
    return total_count