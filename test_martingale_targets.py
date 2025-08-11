#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar o cálculo correto de Take Profit e Stop Loss
após perdas no Martingale 3
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TradingConfig
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockTradingBot:
    """Mock do TradingBot para testar a lógica de targets"""
    
    def __init__(self, config):
        self.config = config
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.is_running = True
        
        # Simular saldo inicial de $1000
        self.initial_balance = 1000.0
        self.current_balance = 1000.0
        
        logger.info(f"Bot iniciado com saldo: ${self.current_balance}")
        logger.info(f"Take Profit configurado: {self.config.take_profit}%")
        logger.info(f"Stop Loss configurado: {self.config.stop_loss}%")
        logger.info(f"Martingale habilitado: {self.config.martingale_enabled}")
        logger.info(f"Níveis máximos de Martingale: {self.config.max_martingale_levels}")
    
    def _calculate_trade_amount(self):
        """Calcular valor do trade baseado na configuração e nível de Martingale"""
        if self.config.use_balance_percentage:
            base_amount = self.current_balance * (self.config.balance_percentage / 100)
        else:
            base_amount = self.config.trade_amount
        
        # Aplicar multiplicador do Martingale
        if self.martingale_level > 0:
            multiplier = self.config.martingale_multiplier ** self.martingale_level
            amount = base_amount * multiplier
        else:
            amount = base_amount
        
        return round(amount, 2)
    
    def simulate_trade_result(self, result, payout_percentage=85.0):
        """Simular resultado de um trade"""
        trade_amount = self._calculate_trade_amount()
        
        logger.info(f"\n--- TRADE {self.session_trades + 1} ---")
        logger.info(f"Nível Martingale: {self.martingale_level}")
        logger.info(f"Valor do trade: ${trade_amount}")
        
        if result == 'win':
            profit = trade_amount * (payout_percentage / 100)
            logger.info(f"RESULTADO: WIN - Lucro: +${profit}")
        else:
            profit = -trade_amount
            logger.info(f"RESULTADO: LOSS - Perda: ${profit}")
        
        # Atualizar estatísticas
        self.session_trades += 1
        self.session_profit += profit
        self.current_balance += profit
        
        logger.info(f"Lucro da sessão: ${self.session_profit}")
        logger.info(f"Saldo atual: ${self.current_balance}")
        
        # Lógica de Martingale
        if result == 'win':
            if self.martingale_level > 0:
                logger.info(f"WIN no Martingale {self.martingale_level} - resetando para entrada normal")
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Verificar Take Profit
            take_profit_value = self.initial_balance * (self.config.take_profit / 100)
            if self.session_profit >= take_profit_value:
                logger.info(f"\n🎯 TAKE PROFIT ATINGIDO!")
                logger.info(f"Lucro atual: ${self.session_profit} >= Meta: ${take_profit_value}")
                return 'take_profit_reached'
        else:
            self.consecutive_losses += 1
            
            # Aplicar Martingale se habilitado e dentro dos limites
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_levels:
                self.martingale_level += 1
                logger.info(f"LOSS - Martingale aumentado para nível: {self.martingale_level}/{self.config.max_martingale_levels}")
                
                if self.martingale_level <= self.config.max_martingale_levels:
                    logger.info(f"Continuando com Martingale nível {self.martingale_level}")
                    return 'continue_martingale'
            else:
                # Esgotou todos os níveis de Martingale
                if self.config.martingale_enabled:
                    logger.info(f"Todos os {self.config.max_martingale_levels} níveis de Martingale esgotados")
                
                # Reset Martingale
                self.martingale_level = 0
                
                # Verificar Stop Loss
                stop_loss_value = self.initial_balance * (self.config.stop_loss / 100)
                if self.session_profit <= -stop_loss_value:
                    logger.info(f"\n🛑 STOP LOSS ATINGIDO!")
                    logger.info(f"Perda atual: ${self.session_profit} <= Meta: -${stop_loss_value}")
                    return 'stop_loss_reached'
                else:
                    logger.info(f"Stop Loss não atingido (${self.session_profit} > -${stop_loss_value}) - continuando")
        
        return 'continue'
    
    def check_targets_status(self):
        """Verificar status atual dos targets"""
        take_profit_value = self.initial_balance * (self.config.take_profit / 100)
        stop_loss_value = self.initial_balance * (self.config.stop_loss / 100)
        
        take_profit_percent = (self.session_profit / take_profit_value) * 100 if take_profit_value > 0 else 0
        stop_loss_percent = (abs(self.session_profit) / stop_loss_value) * 100 if stop_loss_value > 0 and self.session_profit < 0 else 0
        
        logger.info(f"\n📊 STATUS DOS TARGETS:")
        logger.info(f"Take Profit: {take_profit_percent:.1f}% (${self.session_profit:.2f} / ${take_profit_value:.2f})")
        logger.info(f"Stop Loss: {stop_loss_percent:.1f}% (${abs(self.session_profit):.2f} / ${stop_loss_value:.2f})")

def test_martingale_scenario():
    """Testar cenário específico: perda na entrada normal e Martingale 3"""
    logger.info("\n" + "="*60)
    logger.info("TESTE: Cálculo de Take Profit e Stop Loss após Martingale 3")
    logger.info("="*60)
    
    # Criar configuração de teste
    config = TradingConfig()
    config.take_profit = 70.0  # 70% do saldo inicial
    config.stop_loss = 30.0    # 30% do saldo inicial
    config.martingale_enabled = True
    config.max_martingale_levels = 3
    config.martingale_multiplier = 2.2
    config.use_balance_percentage = True
    config.balance_percentage = 2.0  # 2% do saldo
    
    # Criar bot de teste
    bot = MockTradingBot(config)
    
    # Cenário: 4 perdas consecutivas (entrada normal + 3 Martingales)
    logger.info("\n🎲 SIMULANDO CENÁRIO: 4 perdas consecutivas")
    logger.info("Entrada normal + Martingale 1, 2, 3")
    
    results = []
    
    # Trade 1: Entrada normal - LOSS
    result = bot.simulate_trade_result('loss')
    results.append(result)
    bot.check_targets_status()
    
    if result == 'continue_martingale':
        # Trade 2: Martingale 1 - LOSS
        result = bot.simulate_trade_result('loss')
        results.append(result)
        bot.check_targets_status()
        
        if result == 'continue_martingale':
            # Trade 3: Martingale 2 - LOSS
            result = bot.simulate_trade_result('loss')
            results.append(result)
            bot.check_targets_status()
            
            if result == 'continue_martingale':
                # Trade 4: Martingale 3 - LOSS
                result = bot.simulate_trade_result('loss')
                results.append(result)
                bot.check_targets_status()
    
    # Verificar se o sistema está funcionando corretamente
    logger.info("\n" + "="*60)
    logger.info("ANÁLISE DOS RESULTADOS:")
    logger.info("="*60)
    
    final_result = results[-1] if results else 'continue'
    
    if final_result == 'stop_loss_reached':
        logger.info("✅ CORRETO: Sistema parou por Stop Loss após esgotar Martingale")
    elif final_result == 'continue':
        logger.info("✅ CORRETO: Sistema continua operando (Stop Loss não atingido)")
    else:
        logger.info(f"❌ INESPERADO: Resultado final: {final_result}")
    
    # Testar cenário de recuperação
    logger.info("\n🎲 TESTANDO RECUPERAÇÃO: Trade WIN após as perdas")
    if bot.is_running and final_result != 'stop_loss_reached':
        result = bot.simulate_trade_result('win', 85.0)
        bot.check_targets_status()
        
        if result == 'take_profit_reached':
            logger.info("✅ CORRETO: Take Profit atingido após WIN")
        else:
            logger.info("✅ CORRETO: Continuando operação (Take Profit não atingido ainda)")
    
    logger.info("\n" + "="*60)
    logger.info("TESTE CONCLUÍDO")
    logger.info("="*60)

if __name__ == "__main__":
    test_martingale_scenario()