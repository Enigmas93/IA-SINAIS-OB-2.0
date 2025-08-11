from pydantic import BaseModel, validator, Field
from typing import Optional, Literal
from datetime import datetime

class TradingConfigSchema(BaseModel):
    """Schema de validação para configurações de trading"""
    asset: str = Field(..., min_length=1, max_length=20, description="Asset para trading")
    trade_amount: float = Field(..., gt=0, le=10000, description="Valor do trade")
    balance_percentage: Optional[float] = Field(None, ge=1, le=100, description="Porcentagem do saldo")
    use_balance_percentage: bool = Field(False, description="Usar porcentagem do saldo")
    take_profit: float = Field(..., ge=1, le=1000, description="Take profit em porcentagem")
    martingale_enabled: bool = Field(False, description="Habilitar martingale")
    max_martingale_levels: int = Field(3, ge=1, le=5, description="Níveis máximos de martingale")
    min_signal_score: int = Field(70, ge=50, le=100, description="Score mínimo do sinal")
    strategy_mode: Literal['conservador', 'intermediario', 'agressivo'] = Field('intermediario', description="Modo da estratégia")
    timeframe: Literal['1m', '5m'] = Field('1m', description="Timeframe para análise")
    
    # Configurações de sessão
    morning_enabled: bool = Field(False, description="Sessão matutina habilitada")
    morning_start: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Horário início manhã")
    afternoon_enabled: bool = Field(False, description="Sessão vespertina habilitada")
    afternoon_start: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Horário início tarde")
    night_enabled: bool = Field(False, description="Sessão noturna habilitada")
    night_start: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Horário início noite")
    
    # Configurações avançadas
    continuous_mode: bool = Field(False, description="Modo contínuo")
    auto_restart: bool = Field(False, description="Reinício automático")
    keep_connection: bool = Field(True, description="Manter conexão")
    use_ml_signals: bool = Field(False, description="Usar sinais de ML")
    
    # Configurações de sinais antecipados
    advance_signal_minutes: int = Field(2, ge=1, le=10, description="Minutos de antecedência para sinais")
    
    @validator('trade_amount')
    def validate_trade_amount(cls, v, values):
        """Valida o valor do trade"""
        if v <= 0:
            raise ValueError('Valor do trade deve ser positivo')
        if v > 10000:
            raise ValueError('Valor do trade muito alto (máximo: $10,000)')
        return v
    
    @validator('balance_percentage')
    def validate_balance_percentage(cls, v, values):
        """Valida a porcentagem do saldo"""
        if v is not None:
            if v < 1 or v > 100:
                raise ValueError('Porcentagem do saldo deve estar entre 1% e 100%')
        return v
    
    @validator('take_profit')
    def validate_take_profit(cls, v):
        """Valida o take profit"""
        if v < 1:
            raise ValueError('Take profit deve ser pelo menos 1%')
        if v > 1000:
            raise ValueError('Take profit muito alto (máximo: 1000%)')
        return v
    
    @validator('morning_start', 'afternoon_start', 'night_start')
    def validate_time_format(cls, v):
        """Valida formato de horário"""
        if v is not None:
            try:
                hour, minute = map(int, v.split(':'))
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    raise ValueError('Horário inválido')
            except ValueError:
                raise ValueError('Formato de horário deve ser HH:MM')
        return v
    
    @validator('asset')
    def validate_asset(cls, v):
        """Valida o asset"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Asset é obrigatório')
        # Lista de assets válidos (pode ser expandida)
        valid_assets = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
            'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP', 'AUDCAD', 'CADJPY', 'EURAUD',
            'GBPCAD', 'AUDNZD', 'CADCHF', 'CHFJPY', 'EURNZD', 'GBPAUD', 'GBPCHF',
            'EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC', 'AUDUSD-OTC', 'EURAUD-OTC',
            'GBPCAD-OTC', 'AUDNZD-OTC', 'CADCHF-OTC', 'CHFJPY-OTC', 'EURNZD-OTC'
        ]
        if v.upper() not in [asset.upper() for asset in valid_assets]:
            raise ValueError(f'Asset inválido. Assets válidos: {", ".join(valid_assets)}')
        return v.upper()

class UserCredentialsSchema(BaseModel):
    """Schema de validação para credenciais do usuário"""
    iq_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$', description="Email da IQ Option")
    iq_password: str = Field(..., min_length=6, max_length=100, description="Senha da IQ Option")
    
    @validator('iq_email')
    def validate_email(cls, v):
        """Valida o formato do email"""
        if '@' not in v or '.' not in v:
            raise ValueError('Email inválido')
        return v.lower().strip()
    
    @validator('iq_password')
    def validate_password(cls, v):
        """Valida a senha"""
        if len(v) < 6:
            raise ValueError('Senha deve ter pelo menos 6 caracteres')
        return v

class TradeSignalSchema(BaseModel):
    """Schema de validação para sinais de trading"""
    direction: Literal['call', 'put', 'none'] = Field(..., description="Direção do sinal")
    confidence: float = Field(..., ge=0, le=1, description="Confiança do sinal")
    strength: float = Field(..., ge=0, le=1, description="Força do sinal")
    score_percentage: float = Field(..., ge=0, le=100, description="Score em porcentagem")
    asset: str = Field(..., min_length=1, description="Asset do sinal")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp do sinal")
    manual_only: bool = Field(False, description="Apenas sinal manual")
    
    @validator('confidence', 'strength')
    def validate_percentage_values(cls, v):
        """Valida valores de porcentagem"""
        if v < 0 or v > 1:
            raise ValueError('Valores devem estar entre 0 e 1')
        return v

class TradeExecutionSchema(BaseModel):
    """Schema de validação para execução de trades"""
    asset: str = Field(..., min_length=1, description="Asset do trade")
    direction: Literal['call', 'put'] = Field(..., description="Direção do trade")
    amount: float = Field(..., gt=0, le=10000, description="Valor do trade")
    duration: int = Field(60, ge=60, le=300, description="Duração em segundos")
    martingale_level: int = Field(0, ge=0, le=5, description="Nível do martingale")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Valida o valor do trade"""
        if v <= 0:
            raise ValueError('Valor deve ser positivo')
        if v > 10000:
            raise ValueError('Valor muito alto')
        return v

class BotStatusSchema(BaseModel):
    """Schema de validação para status do bot"""
    running: bool = Field(..., description="Bot está rodando")
    current_session: Optional[Literal['morning', 'afternoon', 'night', 'manual']] = Field(None, description="Sessão atual")
    session_start_time: Optional[datetime] = Field(None, description="Início da sessão")
    trades_today: int = Field(0, ge=0, description="Trades hoje")
    profit_today: float = Field(0, description="Lucro hoje")
    session_trades: int = Field(0, ge=0, description="Trades da sessão")
    session_profit: float = Field(0, description="Lucro da sessão")
    martingale_level: int = Field(0, ge=0, le=5, description="Nível atual do martingale")
    consecutive_losses: int = Field(0, ge=0, description="Perdas consecutivas")
    balance: float = Field(0, ge=0, description="Saldo atual")
    take_profit_target: float = Field(0, ge=0, description="Meta de take profit")
    take_profit_reached: bool = Field(False, description="Take profit atingido")
    stop_loss_reached: bool = Field(False, description="Stop loss atingido")

class APIResponseSchema(BaseModel):
    """Schema padrão para respostas da API"""
    success: bool = Field(..., description="Sucesso da operação")
    message: Optional[str] = Field(None, description="Mensagem de retorno")
    data: Optional[dict] = Field(None, description="Dados de retorno")
    errors: Optional[list] = Field(None, description="Lista de erros")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp da resposta")

class PaginationSchema(BaseModel):
    """Schema para paginação"""
    page: int = Field(1, ge=1, description="Página atual")
    per_page: int = Field(20, ge=1, le=100, description="Itens por página")
    total_pages: int = Field(0, ge=0, description="Total de páginas")
    total_items: int = Field(0, ge=0, description="Total de itens")
    
    @validator('per_page')
    def validate_per_page(cls, v):
        """Valida itens por página"""
        if v > 100:
            raise ValueError('Máximo 100 itens por página')
        return v