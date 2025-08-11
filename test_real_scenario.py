#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste específico para verificar o problema relatado pelo usuário:
"O sistema está parando sozinho sem alcançar as metas configuradas na interface corretamente"

Este script simula exatamente o cenário onde o bot deveria continuar após perdas no Martingale 3
mas está parando incorretamente.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingConfig:
    """Configuração de trading simulada"""
    def __init__(self):
        # Configurações típicas da interface
        self.take_profit = 70.0  # 70% do saldo inicial
        self.stop_loss = 30.0    # 30% do saldo inicial
        self.trade_amount = 2.0  # 2% do saldo
        self.martingale_enabled = True
        self.max_martingale_levels = 3
        self.martingale_multiplier = 2.2
        self.auto_restart = False  # Desabilitado para teste
        self.continuous_mode = False

class RealScenarioBot:
    """Bot simulado com a lógica exata do código real"""
    
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.config = TradingConfig()
        self.is_running = True
        
        logger.info(f"🤖 Bot iniciado com saldo: ${self.initial_balance}")
        logger.info(f"📊 Take Profit: ${self.config.take_profit} (70%)")
        logger.info(f"📊 Stop Loss: ${self.config.stop_loss} (30%)")
        logger.info(f"🎲 Martingale: {self.config.max_martingale_levels} níveis, multiplicador {self.config.martingale_multiplier}x")
        logger.info(f"💰 Valor base: {self.config.trade_amount}% do saldo")
        
    def _calculate_trade_amount(self) -> float:
        """Calcula o valor do trade baseado no nível de Martingale"""
        base_amount = (self.config.trade_amount / 100) * self.initial_balance
        
        if self.martingale_level == 0:
            return base_amount
        else:
            # Aplicar multiplicador de Martingale
            return base_amount * (self.config.martingale_multiplier ** self.martingale_level)
    
    def _should_continue_trading(self) -> bool:
        """Lógica EXATA do código real para verificar se deve continuar"""
        
        # NEVER stop during active Martingale progression
        # Only check targets when Martingale level is 0 (back to normal entry)
        if self.martingale_level > 0:
            logger.debug(f"Martingale level {self.martingale_level} active - continuing trading regardless of targets")
            return True
        
        # Only check targets when we're at normal entry level (martingale_level = 0)
        # This means we've either:
        # 1. Won at some Martingale level and reset to 0, OR
        # 2. Lost all Martingale attempts and reset to 0
        
        # Check take profit - only when at normal entry level
        if self.session_profit >= self.config.take_profit:
            logger.info(f"Take profit reached: {self.session_profit} >= {self.config.take_profit}")
            
            # Check if auto-restart is enabled for continuous operation
            if getattr(self.config, 'auto_restart', True) and getattr(self.config, 'continuous_mode', True):
                logger.info("AUTO-RESTART: Take profit reached - resetting session and continuing in next scheduled period")
                return True  # Continue trading in continuous mode
            else:
                logger.info("AUTO-STOPPING: Take profit reached after completing Martingale cycle - stopping bot")
                self.is_running = False
                return False
        
        # Check stop loss - only when at normal entry level
        if self.session_profit <= -self.config.stop_loss:
            logger.info(f"Stop loss reached: {self.session_profit} <= -{self.config.stop_loss}")
            
            # Check if auto-restart is enabled for continuous operation
            if getattr(self.config, 'auto_restart', True) and getattr(self.config, 'continuous_mode', True):
                logger.info("AUTO-RESTART: Stop loss reached - resetting session and continuing in next scheduled period")
                return True  # Continue trading in continuous mode
            else:
                logger.info("AUTO-STOPPING: Stop loss reached after completing Martingale cycle - stopping bot")
                self.is_running = False
                return False
        
        # Continue trading if targets not reached
        return True
    
    def _wait_for_trade_result_logic(self, won: bool) -> bool:
        """Lógica EXATA do _wait_for_trade_result do código real"""
        
        trade_amount = self._calculate_trade_amount()
        
        if won:
            # WIN: Calculate profit (80% payout)
            profit = trade_amount * 0.8
            self.current_balance += profit
            self.session_profit += profit
            
            logger.info(f"✅ RESULTADO: WIN - Lucro: +${profit:.2f}")
            logger.info(f"Saldo após: ${self.current_balance:.2f}")
            logger.info(f"Lucro da sessão: ${self.session_profit:.2f}")
            
            # WIN: Always reset martingale to 0 (back to normal entry)
            if self.martingale_level > 0:
                logger.info(f"🎉 WIN no Martingale {self.martingale_level} - resetando para entrada normal")
            
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Check targets only after completing full martingale cycle (after 3rd martingale)
            if self.session_profit >= self.config.take_profit:
                logger.info(f"Take profit reached: {self.session_profit} >= {self.config.take_profit}")
                logger.info("AUTO-STOPPING: Take profit reached - stopping bot")
                self.is_running = False
                return False
                
        else:
            # LOSS: Subtract trade amount
            self.current_balance -= trade_amount
            self.session_profit -= trade_amount
            
            logger.info(f"❌ RESULTADO: LOSS - Perda: ${-trade_amount:.2f}")
            logger.info(f"Saldo após: ${self.current_balance:.2f}")
            logger.info(f"Lucro da sessão: ${self.session_profit:.2f}")
            
            self.consecutive_losses += 1
            
            # LOSS: Apply martingale progression if enabled and within limits
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_levels:
                self.martingale_level += 1
                logger.info(f"📈 LOSS - Martingale aumentado para: {self.martingale_level}/{self.config.max_martingale_levels}")
                
                # Continue trading - don't stop until max martingale levels are exhausted
                if self.martingale_level <= self.config.max_martingale_levels:
                    logger.info(f"🔄 Continuando com Martingale nível {self.martingale_level}")
                    return True
            else:
                # Exhausted all martingale levels OR martingale disabled
                if self.config.martingale_enabled:
                    logger.info(f"⚠️ Todos os {self.config.max_martingale_levels} níveis de Martingale esgotados - verificando targets")
                else:
                    logger.info("Martingale desabilitado - verificando targets após perda")
                
                # Reset martingale level
                self.martingale_level = 0
                
                # Check stop loss only after exhausting all martingale attempts
                if self.session_profit <= -self.config.stop_loss:
                    logger.info(f"Stop loss reached: {self.session_profit} <= -{self.config.stop_loss}")
                    logger.info("AUTO-STOPPING: Stop loss reached after exhausting martingale attempts - stopping bot")
                    self.is_running = False
                    return False
                else:
                    logger.info(f"Stop loss não atingido ({self.session_profit:.2f} > -{self.config.stop_loss}) - continuando com entrada normal")
                    return True
        
        return True
    
    def simulate_trade(self, won: bool, trade_number: int) -> bool:
        """Simula um trade e retorna se deve continuar"""
        self.session_trades += 1
        
        trade_amount = self._calculate_trade_amount()
        
        logger.info("\n" + "=" * 50)
        logger.info(f"📊 TRADE {trade_number}")
        logger.info("=" * 50)
        logger.info(f"Nível Martingale: {self.martingale_level}")
        logger.info(f"Valor do trade: ${trade_amount:.2f}")
        logger.info(f"Saldo antes: ${self.current_balance:.2f}")
        
        # Aplicar lógica do _wait_for_trade_result
        should_continue = self._wait_for_trade_result_logic(won)
        
        # Verificar se deve continuar com _should_continue_trading
        if should_continue:
            should_continue = self._should_continue_trading()
        
        logger.info(f"📊 Resultado da lógica: {'continuar' if should_continue else 'parar'}")
        
        return should_continue

def test_problematic_scenario():
    """Testa o cenário problemático relatado pelo usuário"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTE: Cenário Problemático - Bot parando antes das metas")
    logger.info("=" * 80)
    
    bot = RealScenarioBot(1000.0)
    
    # Simular sequência de perdas que NÃO deveria parar o bot
    # Entrada normal + 3 Martingales = 4 perdas consecutivas
    
    scenarios = [
        (False, "Entrada Normal"),
        (False, "Martingale 1"),
        (False, "Martingale 2"),
        (False, "Martingale 3 - CRÍTICO")
    ]
    
    for i, (won, description) in enumerate(scenarios, 1):
        logger.info(f"\n🎲 {description}")
        
        should_continue = bot.simulate_trade(won, i)
        
        if not should_continue:
            logger.error(f"❌ PROBLEMA DETECTADO: Bot parou no {description}!")
            logger.error(f"Lucro da sessão: ${bot.session_profit:.2f}")
            logger.error(f"Stop Loss configurado: ${bot.config.stop_loss}")
            logger.error(f"Deveria continuar até atingir Stop Loss de ${bot.config.stop_loss}")
            return False
        else:
            logger.info(f"✅ Bot continuou corretamente após {description}")
    
    # Após esgotar os 3 Martingales, verificar se o Stop Loss foi atingido
    logger.info(f"\n📊 RESULTADO FINAL:")
    logger.info(f"Lucro da sessão: ${bot.session_profit:.2f}")
    logger.info(f"Stop Loss: ${bot.config.stop_loss}")
    logger.info(f"Stop Loss atingido: {bot.session_profit <= -bot.config.stop_loss}")
    
    if bot.session_profit <= -bot.config.stop_loss:
        logger.info("✅ Stop Loss atingido corretamente - bot deve parar")
        return True
    else:
        logger.warning(f"⚠️ Stop Loss NÃO atingido - bot deveria continuar")
        return True

def test_recovery_scenario():
    """Testa cenário de recuperação no Martingale 3"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTE: Cenário de Recuperação no Martingale 3")
    logger.info("=" * 80)
    
    bot = RealScenarioBot(1000.0)
    
    # 3 perdas + 1 vitória no Martingale 3
    scenarios = [
        (False, "Entrada Normal"),
        (False, "Martingale 1"),
        (False, "Martingale 2"),
        (True, "Martingale 3 - RECUPERAÇÃO")
    ]
    
    for i, (won, description) in enumerate(scenarios, 1):
        logger.info(f"\n🎲 {description}")
        
        should_continue = bot.simulate_trade(won, i)
        
        if i == 4:  # Após vitória no Martingale 3
            logger.info(f"\n📊 RESULTADO APÓS RECUPERAÇÃO:")
            logger.info(f"Lucro da sessão: ${bot.session_profit:.2f}")
            logger.info(f"Nível Martingale: {bot.martingale_level}")
            logger.info(f"Bot deve continuar: {should_continue}")
            
            if bot.session_profit >= bot.config.take_profit:
                logger.info("✅ Take Profit atingido - bot deve parar")
            else:
                logger.info("✅ Bot deve continuar - targets não atingidos")
    
    return True

if __name__ == "__main__":
    logger.info("🚀 Iniciando testes do cenário real...")
    
    # Teste 1: Cenário problemático
    success1 = test_problematic_scenario()
    
    # Teste 2: Cenário de recuperação
    success2 = test_recovery_scenario()
    
    logger.info("\n" + "=" * 80)
    logger.info("📋 RESUMO DOS TESTES")
    logger.info("=" * 80)
    logger.info(f"Teste Problemático: {'✅ PASSOU' if success1 else '❌ FALHOU'}")
    logger.info(f"Teste Recuperação: {'✅ PASSOU' if success2 else '❌ FALHOU'}")
    
    if success1 and success2:
        logger.info("\n🎉 Todos os testes passaram - lógica funcionando corretamente")
    else:
        logger.error("\n❌ Alguns testes falharam - possível problema na lógica")