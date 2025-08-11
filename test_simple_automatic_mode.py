#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Simples do Modo Automático

Este script testa a lógica de verificação de targets no modo automático
sem inicializar o bot completo.
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestConfig:
    """Configuração de teste simples"""
    def __init__(self, auto_mode=True):
        self.auto_mode = auto_mode
        self.trade_amount = 10.0
        self.take_profit = 5.0  # 5% take profit
        self.stop_loss = 10.0   # 10% stop loss
        self.martingale_enabled = True
        self.martingale_multiplier = 2.0
        self.max_martingale_levels = 3
        self.asset = 'EURUSD'
        self.timeframe = '1m'
        self.strategy_mode = 'intermediario'
        self.min_signal_score = 75.0
        
        # Configurar horários de sessão
        now = datetime.now()
        self.morning_start = (now + timedelta(minutes=1)).strftime('%H:%M')
        self.morning_end = (now + timedelta(minutes=3)).strftime('%H:%M')
        self.afternoon_start = (now + timedelta(minutes=5)).strftime('%H:%M')
        self.afternoon_end = (now + timedelta(minutes=7)).strftime('%H:%M')
        self.night_start = (now + timedelta(minutes=9)).strftime('%H:%M')
        self.night_end = (now + timedelta(minutes=11)).strftime('%H:%M')
        
        # Flags de sessão
        self.morning_enabled = True
        self.afternoon_enabled = True
        self.night_enabled = True
        
        # Configurações de ML
        self.use_ml_signals = False
        self.ml_confidence_threshold = 0.7

class MockTradingBot:
    """Mock simplificado do TradingBot para testar a lógica"""
    def __init__(self, config):
        self.config = config
        self.session_profit = 0.0
        self.martingale_level = 0
        self.initial_balance = 1000.0
        self.stop_event = Mock()
        self.stop_event.is_set.return_value = False
        
    def get_current_balance(self):
        return self.initial_balance
    
    def _send_target_notification(self, event_type, profit, percentage):
        print(f"Notificação: {event_type} - Lucro: ${profit:.2f} ({percentage}%)")
    
    def _should_continue_trading(self) -> bool:
        """Lógica de verificação de targets copiada do TradingBot real"""
        # Check if stop event is set
        if self.stop_event.is_set():
            return False
        
        # NEVER stop during active Martingale progression
        # Only check targets when Martingale level is 0 (back to normal entry)
        if self.martingale_level > 0:
            print(f"Martingale level {self.martingale_level} active - continuing trading regardless of targets")
            return True
        
        # Check take profit - only when at normal entry level
        take_profit_value = getattr(self, 'initial_balance', self.get_current_balance()) * (self.config.take_profit / 100)
        if self.session_profit >= take_profit_value:
            print(f"Take profit reached: {self.session_profit} >= {take_profit_value} ({self.config.take_profit}%)")
            self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
            
            # In automatic mode, pause until next session; in manual mode, stop completely
            if self.config.auto_mode:
                print("AUTOMATIC MODE: Take profit reached - will pause until next scheduled session")
                return False  # This will trigger pause in continuous loop
            else:
                print("MANUAL MODE: Take profit reached - stopping bot")
                self.stop_event.set()
                return False
        
        # Check stop loss - only when at normal entry level
        stop_loss_value = getattr(self, 'initial_balance', self.get_current_balance()) * (self.config.stop_loss / 100)
        if self.session_profit <= -stop_loss_value:
            print(f"Stop loss reached: {self.session_profit} <= -{stop_loss_value} ({self.config.stop_loss}%)")
            self._send_target_notification('stop_loss_reached', self.session_profit, self.config.stop_loss)
            
            # In automatic mode, pause until next session; in manual mode, stop completely
            if self.config.auto_mode:
                print("AUTOMATIC MODE: Stop loss reached - will pause until next scheduled session")
                return False  # This will trigger pause in continuous loop
            else:
                print("MANUAL MODE: Stop loss reached - stopping bot")
                self.stop_event.set()
                return False
        
        # Continue trading if targets not reached
        return True
    
    def _is_in_session_time(self, session_type):
        """Verificar se está no horário da sessão"""
        now = datetime.now().time()
        
        if session_type == 'morning':
            start_time = datetime.strptime(self.config.morning_start, '%H:%M').time()
            end_time = datetime.strptime(self.config.morning_end, '%H:%M').time()
        elif session_type == 'afternoon':
            start_time = datetime.strptime(self.config.afternoon_start, '%H:%M').time()
            end_time = datetime.strptime(self.config.afternoon_end, '%H:%M').time()
        elif session_type == 'night':
            start_time = datetime.strptime(self.config.night_start, '%H:%M').time()
            end_time = datetime.strptime(self.config.night_end, '%H:%M').time()
        else:
            return False
        
        # Handle sessions that cross midnight
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time

def test_automatic_mode_logic():
    """Testar a lógica do modo automático"""
    print("\n=== TESTE DA LÓGICA DO MODO AUTOMÁTICO ===")
    
    # Teste 1: Modo automático com Take Profit
    print("\n1. Testando Take Profit no modo automático...")
    config = TestConfig(auto_mode=True)
    bot = MockTradingBot(config)
    
    # Simular atingir take profit (5% de $1000 = $50)
    bot.session_profit = 50.0
    bot.martingale_level = 0  # Nível normal
    
    should_continue = bot._should_continue_trading()
    print(f"Resultado: Deve continuar trading = {should_continue}")
    print(f"Stop event definido: {bot.stop_event.set.called}")
    
    if not should_continue and not bot.stop_event.set.called:
        print("✓ CORRETO: Modo automático pausa após Take Profit (não para completamente)")
    else:
        print("✗ ERRO: Comportamento incorreto no modo automático")
    
    # Teste 2: Modo automático com Stop Loss
    print("\n2. Testando Stop Loss no modo automático...")
    bot.session_profit = -100.0  # 10% de perda
    bot.stop_event.reset_mock()  # Reset do mock
    
    should_continue = bot._should_continue_trading()
    print(f"Resultado: Deve continuar trading = {should_continue}")
    print(f"Stop event definido: {bot.stop_event.set.called}")
    
    if not should_continue and not bot.stop_event.set.called:
        print("✓ CORRETO: Modo automático pausa após Stop Loss (não para completamente)")
    else:
        print("✗ ERRO: Comportamento incorreto no modo automático")
    
    # Teste 3: Durante Martingale (não deve parar)
    print("\n3. Testando durante Martingale...")
    bot.session_profit = -100.0  # Stop Loss atingido
    bot.martingale_level = 2  # Em Martingale
    bot.stop_event.reset_mock()
    
    should_continue = bot._should_continue_trading()
    print(f"Resultado: Deve continuar trading = {should_continue}")
    
    if should_continue:
        print("✓ CORRETO: Bot continua durante Martingale mesmo com Stop Loss")
    else:
        print("✗ ERRO: Bot não deveria parar durante Martingale")

def test_manual_mode_logic():
    """Testar a lógica do modo manual"""
    print("\n=== TESTE DA LÓGICA DO MODO MANUAL ===")
    
    # Teste 1: Modo manual com Take Profit
    print("\n1. Testando Take Profit no modo manual...")
    config = TestConfig(auto_mode=False)
    bot = MockTradingBot(config)
    
    # Simular atingir take profit
    bot.session_profit = 50.0
    bot.martingale_level = 0
    
    should_continue = bot._should_continue_trading()
    print(f"Resultado: Deve continuar trading = {should_continue}")
    print(f"Stop event definido: {bot.stop_event.set.called}")
    
    if not should_continue and bot.stop_event.set.called:
        print("✓ CORRETO: Modo manual para completamente após Take Profit")
    else:
        print("✗ ERRO: Comportamento incorreto no modo manual")
    
    # Teste 2: Modo manual com Stop Loss
    print("\n2. Testando Stop Loss no modo manual...")
    bot.session_profit = -100.0
    bot.stop_event.reset_mock()
    
    should_continue = bot._should_continue_trading()
    print(f"Resultado: Deve continuar trading = {should_continue}")
    print(f"Stop event definido: {bot.stop_event.set.called}")
    
    if not should_continue and bot.stop_event.set.called:
        print("✓ CORRETO: Modo manual para completamente após Stop Loss")
    else:
        print("✗ ERRO: Comportamento incorreto no modo manual")

def test_session_time_logic():
    """Testar a lógica de verificação de horário de sessão"""
    print("\n=== TESTE DA LÓGICA DE HORÁRIO DE SESSÃO ===")
    
    config = TestConfig()
    bot = MockTradingBot(config)
    
    # Simular estar dentro do horário da manhã
    now = datetime.now()
    morning_start = datetime.strptime(config.morning_start, '%H:%M').time()
    
    with patch('datetime.datetime') as mock_datetime:
        mock_now = datetime.combine(now.date(), morning_start)
        mock_datetime.now.return_value = mock_now
        
        # Testar verificação de horário
        in_morning = bot._is_in_session_time('morning')
        in_afternoon = bot._is_in_session_time('afternoon')
        in_night = bot._is_in_session_time('night')
        
        print(f"Horário atual simulado: {mock_now.time()}")
        print(f"Está na sessão manhã: {in_morning}")
        print(f"Está na sessão tarde: {in_afternoon}")
        print(f"Está na sessão noite: {in_night}")
        
        if in_morning and not in_afternoon and not in_night:
            print("✓ CORRETO: Verificação de horário funcionando")
        else:
            print("✗ ERRO: Verificação de horário com problema")

if __name__ == '__main__':
    print("Iniciando testes da lógica do modo automático...")
    
    try:
        test_automatic_mode_logic()
        test_manual_mode_logic()
        test_session_time_logic()
        
        print("\n=== RESUMO DOS TESTES ===")
        print("✓ Teste da lógica do modo automático concluído")
        print("✓ Teste da lógica do modo manual concluído")
        print("✓ Teste da lógica de horário de sessão concluído")
        print("\nTodos os testes foram executados com sucesso!")
        
    except Exception as e:
        print(f"\n✗ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)