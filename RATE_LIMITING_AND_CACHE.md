# Sistema de Rate Limiting e Cache

Este documento descreve o sistema de rate limiting e cache implementado na aplicação de trading.

## Rate Limiting

### Configuração

O rate limiting é configurado através do arquivo `config.py` na seção `RATE_LIMITING`:

```python
RATE_LIMITING = {
    'ENABLED': True,
    'STORAGE_TYPE': 'redis',  # 'redis' ou 'memory'
    'REDIS_URL': 'redis://localhost:6379/1',
    'DEFAULT_LIMITS': {
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'requests_per_day': 10000
    },
    'API_LIMITS': {
        'requests_per_minute': 30,
        'requests_per_hour': 500,
        'requests_per_day': 5000
    },
    'BOT_CONTROL_LIMITS': {
        'requests_per_minute': 5,
        'requests_per_hour': 50,
        'requests_per_day': 200
    },
    'FORCE_TRADE_LIMITS': {
        'requests_per_minute': 2,
        'requests_per_hour': 20,
        'requests_per_day': 100
    }
}
```

### Decoradores Disponíveis

1. **@limit_requests** - Rate limiting geral
2. **@limit_api** - Rate limiting para APIs
3. **@limit_bot_control** - Rate limiting para controle do bot
4. **@limit_force_trade** - Rate limiting para trades forçadas

### Endpoints Protegidos

#### Controle do Bot
- `/bot/start` - @limit_bot_control
- `/bot/stop` - @limit_bot_control
- `/bot/status` - @limit_bot_control
- `/bot/force_trade` - @limit_force_trade

#### APIs Gerais
- `/auth/logout` - @limit_api
- `/user/profile` - @limit_api
- `/config` (GET) - @limit_api
- `/dashboard/stats` - @limit_api
- `/trades/history` - @limit_api
- `/ml/models` - @limit_api
- `/ml/retrain` - @limit_api
- `/ml/status` - @limit_api

#### Administração
- `/admin/rate-limiter/stats` - @limit_api
- `/admin/rate-limiter/cleanup` - @limit_api
- `/admin/cache/stats` - @limit_api
- `/admin/cache/clear` - @limit_api

### Monitoramento

#### Estatísticas do Rate Limiter
```bash
GET /admin/rate-limiter/stats
```

Retorna informações sobre:
- Número de chaves ativas
- Estatísticas de uso por endpoint
- Bloqueios recentes

#### Limpeza Manual
```bash
POST /admin/rate-limiter/cleanup
```

Executa limpeza manual dos dados expirados.

## Sistema de Cache

### Configuração

O cache é configurado através do arquivo `config.py` na seção `CACHE`:

```python
CACHE = {
    'TYPE': 'redis',  # 'redis' ou 'memory'
    'REDIS_URL': 'redis://localhost:6379/0',
    'DEFAULT_TIMEOUT': 300,  # 5 minutos
    'KEY_PREFIX': 'trading_app:',
    'SERIALIZER': 'json'  # 'json' ou 'pickle'
}
```

### Decoradores de Cache

1. **@cached(timeout, key_prefix)** - Cache geral para funções
2. **@cache_user_data(timeout)** - Cache específico para dados do usuário
3. **@cache_market_data(timeout)** - Cache para dados de mercado

### Endpoints com Cache

#### Dados do Usuário (5 minutos)
- `/user/profile` - @cached(timeout=300, key_prefix='user_profile:')
- `/config` (GET) - @cached(timeout=300, key_prefix='user_config:')

#### Dashboard (1 minuto)
- `/dashboard/stats` - @cached(timeout=60, key_prefix='dashboard_stats:')

#### Histórico de Trades (3 minutos)
- `/trades/history` - @cached(timeout=180, key_prefix='trade_history:')

### Invalidação de Cache

O cache é automaticamente invalidado quando:

1. **Configuração é salva** - `invalidate_user_cache(user_id)`
2. **Nova trade é criada** - `invalidate_user_cache(user_id)`
3. **Resultado de trade é atualizado** - `invalidate_user_cache(user_id)`

### Monitoramento do Cache

#### Estatísticas do Cache
```bash
GET /admin/cache/stats
```

Retorna informações sobre:
- Número de chaves ativas
- Taxa de hit/miss
- Uso de memória
- Estatísticas por tipo de cache

#### Limpeza do Cache
```bash
POST /admin/cache/clear
{
  "pattern": "user_profile:*"  // Opcional, padrão é "*" (limpar tudo)
}
```

Permite limpar:
- Todo o cache (`pattern: "*"`)
- Cache específico por padrão (`pattern: "user_profile:*"`)

## Integração com a Aplicação

### Inicialização

No arquivo `app.py`, os sistemas são inicializados:

```python
# Inicializar rate limiter
try:
    from config import Config
    from rate_limiter import initialize_rate_limiter
    initialize_rate_limiter(Config)
except ImportError:
    from rate_limiter import initialize_rate_limiter
    initialize_rate_limiter()

# Inicializar cache
try:
    from config import Config
    from cache import initialize_cache
    initialize_cache(Config)
except ImportError:
    from cache import initialize_cache
    initialize_cache()
```

### Uso em Rotas

```python
from rate_limiter import limit_api
from cache import cached, invalidate_user_cache

@api.route('/user/profile', methods=['GET'])
@jwt_required()
@limit_api
@cached(timeout=300, key_prefix='user_profile:')
def get_user_profile():
    # Lógica da função
    pass

@api.route('/config', methods=['POST'])
@jwt_required()
@limit_api
def save_config():
    # Salvar configuração
    # ...
    
    # Invalidar cache do usuário
    user_id = get_jwt_identity()
    invalidate_user_cache(user_id)
    
    return jsonify({'success': True})
```

## Fallbacks e Robustez

### Rate Limiter
- Se Redis não estiver disponível, usa cache em memória
- Se o sistema falhar, permite todas as requisições (fail-open)
- Limpeza automática periódica (1% de chance por requisição)

### Cache
- Se Redis não estiver disponível, usa cache em memória
- Se o cache falhar, executa a função normalmente
- Serialização automática de dados complexos

## Monitoramento e Logs

Todos os sistemas geram logs detalhados:

```python
import logging
logger = logging.getLogger(__name__)

# Rate limiting
logger.warning(f"Rate limit exceeded for {identifier}")
logger.info(f"Rate limiter initialized with {storage_type} storage")

# Cache
logger.info(f"Cache hit for key: {cache_key}")
logger.warning(f"Cache miss for key: {cache_key}")
logger.error(f"Cache error: {str(e)}")
```

## Configuração de Produção

### Redis
```bash
# Instalar Redis
sudo apt-get install redis-server

# Configurar Redis para produção
# /etc/redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Variáveis de Ambiente
```bash
REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1
```

### Monitoramento
- Use ferramentas como Redis Monitor para acompanhar o uso
- Configure alertas para alta taxa de rate limiting
- Monitore a taxa de hit do cache

## Troubleshooting

### Rate Limiting não funciona
1. Verificar se Redis está rodando
2. Verificar configuração de URL do Redis
3. Verificar logs para erros de conexão

### Cache não funciona
1. Verificar se Redis está rodando
2. Verificar se os decoradores estão aplicados corretamente
3. Verificar se a invalidação está sendo chamada

### Performance
1. Ajustar timeouts de cache conforme necessário
2. Monitorar uso de memória do Redis
3. Ajustar limites de rate limiting conforme tráfego