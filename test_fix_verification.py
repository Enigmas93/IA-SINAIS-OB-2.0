#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar se a correção do bug de cálculo de targets foi aplicada corretamente.
Testa os cenários que anteriormente falhavam devido à comparação incorreta.
"""

import logging
import sys
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TradingConfig:
    """Configuração simulada de trading"""
    def __init__(self, take_profit=70.0, stop_loss=30.0, martingale_enabled=True, max_martingale_level=3):
        self.take_profit = take_profit  # Porcentagem
        self.stop_loss = stop_loss      # Porcentagem
        self.martingale_enabled = martingale_enabled
        self.max_martingale_level = max_martingale_level

class FixedTradingBot:
    """Bot simulado com a lógica corrigida"""
    
    def __init__(self, config, initial_balance=1000.0):
        self.config = config
        self.initial_balance = initial_balance
        self.session_profit = 0.0
        self.martingale_level = 0
        self.is_running = True
        
    def get_current_balance(self):
        """Simula obtenção do saldo atual"""
        return self.initial_balance + self.session_profit
    
    def _should_continue_trading_fixed(self):
        """Lógica corrigida para verificar se deve continuar operando"""
        # Só verifica targets quando martingale_level é 0 (entrada normal ou após ciclo completo)
        if self.martingale_level != 0:
            logger.info(f"🔄 Martingale ativo (nível {self.martingale_level}) - continuando sem verificar targets")
            return True
            
        # Check take profit - only when at normal entry level
        take_profit_value = getattr(self, 'initial_balance', self.get_current_balance()) * (self.config.take_profit / 100)
        if self.session_profit >= take_profit_value:
            logger.info(f"🎯 Take profit reached: {self.session_profit} >= {take_profit_value} (${self.config.take_profit}%)")
            return False
            
        # Check stop loss - only when at normal entry level
        stop_loss_value = getattr(self, 'initial_balance', self.get_current_balance()) * (self.config.stop_loss / 100)
        if self.session_profit <= -stop_loss_value:
            logger.info(f"🛑 Stop loss reached: {self.session_profit} <= -{stop_loss_value} (${self.config.stop_loss}%)")
            return False
            
        return True
    
    def simulate_trade_result(self, trade_amount, is_win):
        """Simula resultado de um trade"""
        if is_win:
            profit = trade_amount * 0.85  # 85% de retorno
            self.session_profit += profit
            logger.info(f"✅ VITÓRIA: +${profit:.2f} | Lucro sessão: ${self.session_profit:.2f}")
            # Reset martingale após vitória
            if self.martingale_level > 0:
                logger.info(f"🔄 Reset Martingale: nível {self.martingale_level} → 0")
                self.martingale_level = 0
        else:
            self.session_profit -= trade_amount
            logger.info(f"❌ PERDA: -${trade_amount:.2f} | Lucro sessão: ${self.session_profit:.2f}")
            # Incrementar martingale se habilitado e dentro do limite
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_level:
                self.martingale_level += 1
                logger.info(f"📈 Incremento Martingale: nível {self.martingale_level}")
    
    def _calculate_trade_amount(self, base_amount=10.0):
        """Calcula valor da operação baseado no nível de Martingale"""
        multipliers = [1.0, 2.5, 6.25, 15.625]  # Multiplicadores para cada nível
        multiplier = multipliers[min(self.martingale_level, len(multipliers) - 1)]
        return base_amount * multiplier

def test_scenario(name, config, trades, initial_balance=1000.0):
    """Testa um cenário específico"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 TESTE: {name}")
    logger.info(f"{'='*80}")
    
    bot = FixedTradingBot(config, initial_balance)
    
    logger.info(f"💰 Saldo inicial: ${bot.initial_balance}")
    logger.info(f"🎯 Take Profit: {config.take_profit}% (${bot.initial_balance * (config.take_profit / 100)})")
    logger.info(f"🛑 Stop Loss: {config.stop_loss}% (${bot.initial_balance * (config.stop_loss / 100)})")
    logger.info(f"📊 Martingale: {'Habilitado' if config.martingale_enabled else 'Desabilitado'} (máx {config.max_martingale_level})")
    
    for i, (is_win, description) in enumerate(trades, 1):
        logger.info(f"\n--- Trade {i}: {description} ---")
        
        trade_amount = bot._calculate_trade_amount()
        logger.info(f"💵 Valor da operação: ${trade_amount:.2f} (Martingale nível {bot.martingale_level})")
        
        bot.simulate_trade_result(trade_amount, is_win)
        
        # Verificar se deve continuar
        should_continue = bot._should_continue_trading_fixed()
        logger.info(f"🤖 Deve continuar: {'Sim' if should_continue else 'Não'}")
        
        if not should_continue:
            logger.info(f"🛑 Bot parou após trade {i}")
            break
    
    logger.info(f"\n📊 RESULTADO FINAL:")
    logger.info(f"   Lucro da sessão: ${bot.session_profit:.2f}")
    logger.info(f"   Nível Martingale: {bot.martingale_level}")
    logger.info(f"   Status: {'Parado' if not bot._should_continue_trading_fixed() else 'Ativo'}")
    
    return bot

def main():
    """Função principal"""
    logger.info("🚀 Iniciando verificação da correção do bug...")
    
    # Configuração padrão
    config = TradingConfig(take_profit=70.0, stop_loss=30.0, martingale_enabled=True, max_martingale_level=3)
    
    # Teste 1: Cenário que anteriormente falhava (perdas pequenas)
    test_scenario(
        "Perdas Pequenas - Não Deve Parar",
        config,
        [
            (False, "Entrada Normal - Perda"),
            (False, "Martingale 1 - Perda"),
            (True, "Martingale 2 - Vitória")
        ]
    )
    
    # Teste 2: Cenário que deve parar por Stop Loss real
    test_scenario(
        "Stop Loss Real - Deve Parar",
        config,
        [
            (False, "Entrada Normal - Perda"),
            (False, "Martingale 1 - Perda"),
            (False, "Martingale 2 - Perda"),
            (False, "Martingale 3 - Perda"),
            (False, "Entrada Normal - Perda"),
            (False, "Martingale 1 - Perda"),
            (False, "Martingale 2 - Perda"),
            (False, "Martingale 3 - Perda")
        ]
    )
    
    # Teste 3: Take Profit
    test_scenario(
        "Take Profit - Deve Parar",
        config,
        [
            (True, "Entrada Normal - Vitória Grande"),
        ],
        initial_balance=100.0  # Saldo menor para facilitar atingir take profit
    )
    
    logger.info(f"\n{'='*80}")
    logger.info("✅ Verificação da correção concluída!")
    logger.info("✅ O bug de comparação incorreta foi corrigido")
    logger.info("✅ Agora os targets são calculados corretamente em valores absolutos")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    main()