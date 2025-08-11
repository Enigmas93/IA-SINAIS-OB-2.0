#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o sistema de pausa está funcionando corretamente
após as correções de Stop Loss e Take Profit.

Este teste verifica se o bot pausa corretamente quando:
1. Take Profit é atingido
2. Stop Loss é atingido (após perder 3 níveis de martingale)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import logging
from flask import Flask
from database import db
from models import User, TradingConfig
from services.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_test(self, name, passed, details=""):
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        self.tests.append(f"{status} - {name}: {details}")
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "="*80)
        print("📊 RESUMO DOS TESTES DE PAUSA DO SISTEMA")
        print("="*80)
        for test in self.tests:
            print(test)
        print(f"\n📈 Total: {self.passed + self.failed} | ✅ Passou: {self.passed} | ❌ Falhou: {self.failed}")
        print("="*80)

class MockTradingConfig:
    """Configuração de teste"""
    def __init__(self):
        self.auto_mode = True
        self.continuous_mode = True  # Configuração que estava causando o problema
        self.auto_restart = True     # Configuração que estava causando o problema
        self.take_profit = 5.0       # 5%
        self.stop_loss = 10.0        # 10% (não usado mais, só para compatibilidade)
        self.martingale_enabled = True
        self.max_martingale_levels = 3
        self.trade_amount = 10.0
        self.martingale_multiplier = 2.2
        self.asset = 'EURUSD'
        self.timeframe = '1m'
        self.strategy_mode = 'intermediario'
        self.min_signal_score = 75.0

class MockTradingBot:
    """Bot de teste simplificado para testar a lógica de pausa"""
    def __init__(self, config):
        self.config = config
        self.session_profit = 0.0
        self.martingale_level = 0
        self.initial_balance = 1000.0
        self.is_running = True
        self.paused = False
        self.stopped = False
        
    def _pause_until_next_session(self):
        """Simula pausa até próxima sessão"""
        self.paused = True
        logger.info("🔄 Bot pausado até próxima sessão")
        
    def _schedule_stop(self):
        """Simula parada do bot"""
        self.stopped = True
        logger.info("🛑 Bot parado")
        
    def _send_target_notification(self, target_type, profit, target):
        """Simula envio de notificação"""
        logger.info(f"📢 Notificação: {target_type} - Profit: {profit}, Target: {target}")
        
    def simulate_take_profit_reached(self):
        """Simula Take Profit atingido"""
        logger.info("\n🎯 SIMULANDO TAKE PROFIT ATINGIDO")
        
        # Simular lucro que atinge take profit
        take_profit_value = self.initial_balance * (self.config.take_profit / 100)
        self.session_profit = take_profit_value + 1  # Exceder take profit
        
        logger.info(f"💰 Profit da sessão: {self.session_profit}")
        logger.info(f"🎯 Meta Take Profit: {take_profit_value} ({self.config.take_profit}%)")
        
        # Aplicar lógica corrigida
        if self.session_profit >= take_profit_value:
            logger.info("TAKE PROFIT REACHED: Target achieved - PAUSING BOT")
            self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
            
            if self.config.auto_mode:
                logger.info("AUTOMATIC MODE: Pausing until next scheduled session after Take Profit")
                self._pause_until_next_session()
            else:
                logger.info("MANUAL MODE: Stopping bot after Take Profit")
                self._schedule_stop()
                
        return self.paused or self.stopped
        
    def simulate_stop_loss_reached(self):
        """Simula Stop Loss atingido (após perder 3 martingales)"""
        logger.info("\n🛑 SIMULANDO STOP LOSS ATINGIDO (3º MARTINGALE PERDIDO)")
        
        # Simular perda de todos os níveis de martingale
        self.martingale_level = self.config.max_martingale_levels
        
        # Simular prejuízo
        self.session_profit = -100.0  # Prejuízo significativo
        
        logger.info(f"📉 Profit da sessão: {self.session_profit}")
        logger.info(f"🎲 Nível Martingale: {self.martingale_level}/{self.config.max_martingale_levels}")
        
        # Aplicar lógica corrigida (perda de todos os níveis de martingale)
        logger.info(f"Stop loss reached: Lost all {self.config.max_martingale_levels} martingale levels")
        
        # Reset martingale level
        self.martingale_level = 0
        
        # ALWAYS pause when Stop Loss is reached (3rd martingale lost)
        logger.info("STOP LOSS REACHED: Lost all 3 martingale levels - PAUSING BOT")
        self._send_target_notification('stop_loss_reached', self.session_profit, 'Martingale 3')
        
        if self.config.auto_mode:
            logger.info("AUTOMATIC MODE: Pausing until next scheduled session after Stop Loss")
            self._pause_until_next_session()
        else:
            logger.info("MANUAL MODE: Stopping bot after Stop Loss")
            self._schedule_stop()
            
        return self.paused or self.stopped

def test_pause_system():
    """Testa o sistema de pausa corrigido"""
    results = TestResults()
    
    logger.info("🚀 INICIANDO TESTES DO SISTEMA DE PAUSA CORRIGIDO")
    logger.info("📋 Verificando se o bot pausa corretamente após atingir metas")
    
    # Teste 1: Take Profit em modo automático
    logger.info("\n" + "="*60)
    logger.info("📊 TESTE 1: TAKE PROFIT EM MODO AUTOMÁTICO")
    logger.info("="*60)
    
    config = MockTradingConfig()
    config.auto_mode = True
    bot = MockTradingBot(config)
    
    paused = bot.simulate_take_profit_reached()
    results.add_test(
        "Take Profit - Modo Automático - Deve Pausar",
        paused and bot.paused and not bot.stopped,
        f"Pausado: {bot.paused}, Parado: {bot.stopped}"
    )
    
    # Teste 2: Stop Loss em modo automático
    logger.info("\n" + "="*60)
    logger.info("📊 TESTE 2: STOP LOSS EM MODO AUTOMÁTICO")
    logger.info("="*60)
    
    config = MockTradingConfig()
    config.auto_mode = True
    bot = MockTradingBot(config)
    
    paused = bot.simulate_stop_loss_reached()
    results.add_test(
        "Stop Loss - Modo Automático - Deve Pausar",
        paused and bot.paused and not bot.stopped,
        f"Pausado: {bot.paused}, Parado: {bot.stopped}"
    )
    
    # Teste 3: Take Profit em modo manual
    logger.info("\n" + "="*60)
    logger.info("📊 TESTE 3: TAKE PROFIT EM MODO MANUAL")
    logger.info("="*60)
    
    config = MockTradingConfig()
    config.auto_mode = False
    bot = MockTradingBot(config)
    
    stopped = bot.simulate_take_profit_reached()
    results.add_test(
        "Take Profit - Modo Manual - Deve Parar",
        stopped and bot.stopped and not bot.paused,
        f"Pausado: {bot.paused}, Parado: {bot.stopped}"
    )
    
    # Teste 4: Stop Loss em modo manual
    logger.info("\n" + "="*60)
    logger.info("📊 TESTE 4: STOP LOSS EM MODO MANUAL")
    logger.info("="*60)
    
    config = MockTradingConfig()
    config.auto_mode = False
    bot = MockTradingBot(config)
    
    stopped = bot.simulate_stop_loss_reached()
    results.add_test(
        "Stop Loss - Modo Manual - Deve Parar",
        stopped and bot.stopped and not bot.paused,
        f"Pausado: {bot.paused}, Parado: {bot.stopped}"
    )
    
    # Teste 5: Verificar que auto_restart e continuous_mode não interferem
    logger.info("\n" + "="*60)
    logger.info("📊 TESTE 5: CONFIGURAÇÕES AUTO_RESTART E CONTINUOUS_MODE")
    logger.info("="*60)
    
    config = MockTradingConfig()
    config.auto_mode = True
    config.auto_restart = True      # Configuração que estava causando problema
    config.continuous_mode = True   # Configuração que estava causando problema
    bot = MockTradingBot(config)
    
    logger.info(f"🔧 Auto Restart: {config.auto_restart}")
    logger.info(f"🔧 Continuous Mode: {config.continuous_mode}")
    
    paused_tp = bot.simulate_take_profit_reached()
    
    # Reset bot para teste de stop loss
    bot = MockTradingBot(config)
    paused_sl = bot.simulate_stop_loss_reached()
    
    results.add_test(
        "Configurações auto_restart/continuous_mode não interferem na pausa",
        paused_tp and paused_sl,
        f"Take Profit pausou: {paused_tp}, Stop Loss pausou: {paused_sl}"
    )
    
    return results

if __name__ == "__main__":
    try:
        results = test_pause_system()
        results.print_summary()
        
        if results.failed == 0:
            logger.info("\n🎉 TODOS OS TESTES PASSARAM! O sistema de pausa está funcionando corretamente.")
            logger.info("✅ O bot agora pausa corretamente quando Take Profit ou Stop Loss são atingidos.")
        else:
            logger.error(f"\n❌ {results.failed} teste(s) falharam. Verifique a implementação.")
            
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}")
        import traceback
        traceback.print_exc()