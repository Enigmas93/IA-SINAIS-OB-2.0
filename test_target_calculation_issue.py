#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste específico para investigar o problema relatado:
Sistema parando antes de atingir as metas configuradas
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

class DetailedMockTradingBot:
    """Mock detalhado do TradingBot para investigar o problema"""
    
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
        
        logger.info(f"\n🤖 BOT CONFIGURADO:")
        logger.info(f"Saldo inicial: ${self.initial_balance}")
        logger.info(f"Take Profit: {self.config.take_profit}% = ${self.initial_balance * (self.config.take_profit / 100)}")
        logger.info(f"Stop Loss: {self.config.stop_loss}% = ${self.initial_balance * (self.config.stop_loss / 100)}")
        logger.info(f"Martingale: {self.config.martingale_enabled} (Max: {self.config.max_martingale_levels})")
        logger.info(f"Multiplicador: {self.config.martingale_multiplier}x")
        logger.info(f"Valor base: {self.config.balance_percentage}% do saldo")
    
    def _calculate_trade_amount(self):
        """Calcular valor do trade baseado na configuração e nível de Martingale"""
        if self.config.use_balance_percentage:
            # Usar saldo ATUAL para calcular o valor base
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
    
    def _should_continue_trading_check(self):
        """Verificar se deve continuar trading (baseado na lógica real)"""
        # NUNCA parar durante progressão ativa do Martingale
        if self.martingale_level > 0:
            logger.info(f"🔄 Martingale nível {self.martingale_level} ativo - CONTINUANDO independente dos targets")
            return True, "martingale_active"
        
        # Verificar targets apenas quando martingale_level = 0
        take_profit_value = self.initial_balance * (self.config.take_profit / 100)
        stop_loss_value = self.initial_balance * (self.config.stop_loss / 100)
        
        # Check take profit
        if self.session_profit >= take_profit_value:
            logger.info(f"🎯 TAKE PROFIT ATINGIDO: ${self.session_profit} >= ${take_profit_value}")
            return False, "take_profit_reached"
        
        # Check stop loss
        if self.session_profit <= -stop_loss_value:
            logger.info(f"🛑 STOP LOSS ATINGIDO: ${self.session_profit} <= -${stop_loss_value}")
            return False, "stop_loss_reached"
        
        logger.info(f"✅ Targets não atingidos - CONTINUANDO")
        logger.info(f"   Take Profit: ${self.session_profit:.2f} / ${take_profit_value:.2f} ({(self.session_profit/take_profit_value)*100:.1f}%)")
        logger.info(f"   Stop Loss: ${abs(self.session_profit):.2f} / ${stop_loss_value:.2f} ({(abs(self.session_profit)/stop_loss_value)*100:.1f}%)")
        return True, "continue"
    
    def simulate_trade_result(self, result, payout_percentage=85.0):
        """Simular resultado de um trade com lógica detalhada"""
        trade_amount = self._calculate_trade_amount()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"📊 TRADE {self.session_trades + 1}")
        logger.info(f"{'='*50}")
        logger.info(f"Nível Martingale: {self.martingale_level}")
        logger.info(f"Valor do trade: ${trade_amount}")
        logger.info(f"Saldo antes: ${self.current_balance}")
        
        if result == 'win':
            profit = trade_amount * (payout_percentage / 100)
            logger.info(f"✅ RESULTADO: WIN - Lucro: +${profit}")
        else:
            profit = -trade_amount
            logger.info(f"❌ RESULTADO: LOSS - Perda: ${profit}")
        
        # Atualizar estatísticas
        self.session_trades += 1
        self.session_profit += profit
        self.current_balance += profit
        
        logger.info(f"Saldo após: ${self.current_balance}")
        logger.info(f"Lucro da sessão: ${self.session_profit}")
        
        # Lógica de Martingale (baseada no código real)
        if result == 'win':
            # WIN: Sempre resetar martingale para 0
            if self.martingale_level > 0:
                logger.info(f"🎉 WIN no Martingale {self.martingale_level} - resetando para entrada normal")
            
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Verificar targets após WIN
            should_continue, reason = self._should_continue_trading_check()
            return reason
            
        else:
            # LOSS: Aplicar progressão do Martingale
            self.consecutive_losses += 1
            
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_levels:
                self.martingale_level += 1
                logger.info(f"📈 LOSS - Martingale aumentado para: {self.martingale_level}/{self.config.max_martingale_levels}")
                
                if self.martingale_level <= self.config.max_martingale_levels:
                    logger.info(f"🔄 Continuando com Martingale nível {self.martingale_level}")
                    return 'continue_martingale'
            else:
                # Esgotou todos os níveis de Martingale OU Martingale desabilitado
                if self.config.martingale_enabled:
                    logger.info(f"⚠️ Todos os {self.config.max_martingale_levels} níveis de Martingale esgotados")
                else:
                    logger.info(f"⚠️ Martingale desabilitado - verificando targets após loss")
                
                # Reset martingale level
                self.martingale_level = 0
                
                # Verificar targets após esgotar Martingale
                should_continue, reason = self._should_continue_trading_check()
                return reason
        
        return 'continue'

def test_problematic_scenarios():
    """Testar cenários que podem causar parada prematura"""
    logger.info("\n" + "="*80)
    logger.info("🔍 INVESTIGAÇÃO: Parada prematura antes de atingir targets")
    logger.info("="*80)
    
    # Cenário 1: Perdas que não atingem Stop Loss
    logger.info("\n📋 CENÁRIO 1: Perdas moderadas (não deveria parar)")
    config = TradingConfig()
    config.take_profit = 70.0  # $700
    config.stop_loss = 30.0    # $300
    config.martingale_enabled = True
    config.max_martingale_levels = 3
    config.martingale_multiplier = 2.2
    config.use_balance_percentage = True
    config.balance_percentage = 2.0
    
    bot = DetailedMockTradingBot(config)
    
    # Simular algumas perdas que NÃO deveriam atingir stop loss
    trades = [
        ('loss', 'Entrada normal'),
        ('loss', 'Martingale 1'),
        ('loss', 'Martingale 2'),
        ('win', 'Martingale 3 - Recuperação'),  # Deveria resetar e continuar
        ('loss', 'Nova entrada normal'),
        ('win', 'Nova entrada normal - WIN')
    ]
    
    for i, (result, description) in enumerate(trades):
        logger.info(f"\n🎲 {description}")
        trade_result = bot.simulate_trade_result(result)
        
        logger.info(f"📊 Resultado da lógica: {trade_result}")
        
        if trade_result in ['take_profit_reached', 'stop_loss_reached']:
            logger.info(f"🛑 Bot pararia aqui: {trade_result}")
            break
        elif trade_result == 'continue_martingale':
            logger.info(f"🔄 Continuando com Martingale")
        else:
            logger.info(f"✅ Continuando operação normal")
    
    # Cenário 2: Verificar se há problema com cálculo de percentual
    logger.info("\n" + "="*80)
    logger.info("📋 CENÁRIO 2: Verificação de cálculos de percentual")
    logger.info("="*80)
    
    # Simular situação onde o usuário pode estar vendo valores incorretos
    initial_balance = 1000.0
    current_session_profit = -150.0  # Perda de $150
    
    take_profit_target = initial_balance * (70.0 / 100)  # $700
    stop_loss_target = initial_balance * (30.0 / 100)    # $300
    
    logger.info(f"\n💰 ANÁLISE DE CÁLCULOS:")
    logger.info(f"Saldo inicial: ${initial_balance}")
    logger.info(f"Lucro da sessão: ${current_session_profit}")
    logger.info(f"Take Profit target: ${take_profit_target} (70%)")
    logger.info(f"Stop Loss target: ${stop_loss_target} (30%)")
    
    # Verificar se está próximo do stop loss
    stop_loss_percentage = (abs(current_session_profit) / stop_loss_target) * 100
    logger.info(f"\n📊 Status do Stop Loss:")
    logger.info(f"Perda atual: ${abs(current_session_profit)}")
    logger.info(f"Meta Stop Loss: ${stop_loss_target}")
    logger.info(f"Progresso: {stop_loss_percentage:.1f}% do Stop Loss")
    
    if current_session_profit <= -stop_loss_target:
        logger.info(f"🛑 STOP LOSS ATINGIDO!")
    else:
        logger.info(f"✅ Stop Loss NÃO atingido - deveria continuar")
        logger.info(f"Faltam ${stop_loss_target - abs(current_session_profit):.2f} para atingir Stop Loss")
    
    # Cenário 3: Testar com valores reais da interface
    logger.info("\n" + "="*80)
    logger.info("📋 CENÁRIO 3: Teste com configurações típicas da interface")
    logger.info("="*80)
    
    # Configurações mais conservadoras
    config2 = TradingConfig()
    config2.take_profit = 50.0   # $500 (mais conservador)
    config2.stop_loss = 20.0     # $200 (mais conservador)
    config2.martingale_enabled = True
    config2.max_martingale_levels = 3
    config2.martingale_multiplier = 2.0  # Multiplicador menor
    config2.use_balance_percentage = True
    config2.balance_percentage = 1.5  # 1.5% do saldo
    
    bot2 = DetailedMockTradingBot(config2)
    
    # Simular sequência que pode estar causando problema
    problem_sequence = [
        ('loss', 'Entrada 1'),
        ('loss', 'Martingale 1'),
        ('loss', 'Martingale 2'),
        ('loss', 'Martingale 3'),  # Aqui deveria verificar stop loss
        ('loss', 'Nova entrada após reset'),  # Se não atingiu stop loss
    ]
    
    for result, description in problem_sequence:
        logger.info(f"\n🎲 {description}")
        trade_result = bot2.simulate_trade_result(result)
        
        if trade_result in ['take_profit_reached', 'stop_loss_reached']:
            logger.info(f"🛑 Sistema parou: {trade_result}")
            break
        elif trade_result == 'continue_martingale':
            logger.info(f"🔄 Continuando Martingale")
        else:
            logger.info(f"✅ Continuando operação")
    
    logger.info("\n" + "="*80)
    logger.info("🔍 INVESTIGAÇÃO CONCLUÍDA")
    logger.info("="*80)

if __name__ == "__main__":
    test_problematic_scenarios()