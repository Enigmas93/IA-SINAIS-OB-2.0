#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Modo Automático Contínuo

Este script testa se o sistema opera automaticamente nos horários configurados
e pausa após atingir Take Profit ou Stop Loss, aguardando o próximo horário agendado.
"""

import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.trading_bot import TradingBot
from models import TradingConfig, User

class TestConfig:
    """Configuração de teste simples"""
    def __init__(self):
        self.auto_mode = True  # Modo automático
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
        
        # Configurar horários de sessão (próximos minutos para teste)
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

def create_test_config():
    """Criar configuração de teste para modo automático"""
    return TestConfig()

def create_test_user():
    """Criar usuário de teste"""
    class TestUser:
        def __init__(self):
            self.id = 1
            self.email = 'test@example.com'
            self.iq_email = 'test@iq.com'
            self.iq_password = 'test_password'
            self.account_type = 'PRACTICE'
    
    return TestUser()

def test_automatic_continuous_mode():
    """Testar o modo automático contínuo"""
    print("\n=== TESTE DO MODO AUTOMÁTICO CONTÍNUO ===")
    
    # Criar configuração e usuário de teste
    config = create_test_config()
    user = create_test_user()
    
    print(f"Configuração de teste:")
    print(f"- Modo automático: {config.auto_mode}")
    print(f"- Take Profit: {config.take_profit}%")
    print(f"- Stop Loss: {config.stop_loss}%")
    print(f"- Sessão manhã: {config.morning_start} - {config.morning_end}")
    print(f"- Sessão tarde: {config.afternoon_start} - {config.afternoon_end}")
    print(f"- Sessão noite: {config.night_start} - {config.night_end}")
    
    # Mock da conexão IQ Option
    with patch('services.iq_option_service.IQOptionService') as mock_iq_service:
        # Configurar mocks
        mock_iq_instance = Mock()
        mock_iq_service.return_value = mock_iq_instance
        mock_iq_instance.connect.return_value = True
        mock_iq_instance.is_connected.return_value = True
        mock_iq_instance.get_balance.return_value = 1000.0
        mock_iq_instance.check_asset_availability.return_value = True
        mock_iq_instance.get_candles.return_value = [
            {'open': 100, 'close': 101, 'high': 102, 'low': 99, 'volume': 1000}
        ]
        
        # Mock do serviço de análise de sinal
        with patch('services.signal_analyzer.SignalAnalyzer') as mock_signal_service:
            mock_signal_instance = Mock()
            mock_signal_service.return_value = mock_signal_instance
            mock_signal_instance.analyze_signal.return_value = {
                'direction': 'call',
                'confidence': 0.8,
                'score': 85
            }
            
            # Mock do serviço ML
            with patch('services.ml_service.MLService') as mock_ml_service:
                mock_ml_instance = Mock()
                mock_ml_service.return_value = mock_ml_instance
                mock_ml_instance.predict.return_value = {'direction': 'call', 'confidence': 0.75}
                
                # Criar bot de trading
                bot = TradingBot(user.id, config)
                
                # Mock das funções de notificação
                bot._send_notification = Mock()
                bot._send_target_notification = Mock()
                
                print("\n1. Iniciando bot em modo automático...")
                
                # Simular início do bot
                try:
                    bot.start()
                    print("✓ Bot iniciado com sucesso")
                    
                    # Aguardar um pouco para o bot processar
                    time.sleep(2)
                    
                    print("\n2. Verificando se o bot está operando...")
                    print(f"- Bot rodando: {bot.is_running}")
                    print(f"- Thread de trading ativa: {bot.trading_thread and bot.trading_thread.is_alive()}")
                    
                    # Simular atingir take profit
                    print("\n3. Simulando atingir Take Profit...")
                    bot.session_profit = 50.0  # Simular lucro de $50 (5% de $1000)
                    bot.initial_balance = 1000.0
                    
                    # Verificar se deve continuar trading
                    should_continue = bot._should_continue_trading()
                    print(f"- Deve continuar trading após Take Profit: {should_continue}")
                    
                    if not should_continue:
                        print("✓ Bot pausou corretamente após atingir Take Profit")
                    else:
                        print("✗ Bot não pausou após atingir Take Profit")
                    
                    # Resetar para testar stop loss
                    bot.session_profit = 0
                    
                    print("\n4. Simulando atingir Stop Loss...")
                    bot.session_profit = -100.0  # Simular perda de $100 (10% de $1000)
                    
                    # Verificar se deve continuar trading
                    should_continue = bot._should_continue_trading()
                    print(f"- Deve continuar trading após Stop Loss: {should_continue}")
                    
                    if not should_continue:
                        print("✓ Bot pausou corretamente após atingir Stop Loss")
                    else:
                        print("✗ Bot não pausou após atingir Stop Loss")
                    
                    print("\n5. Testando verificação de horário de sessão...")
                    
                    # Testar função de verificação de horário
                    now = datetime.now()
                    morning_start = datetime.strptime(config.morning_start, '%H:%M').time()
                    morning_end = datetime.strptime(config.morning_end, '%H:%M').time()
                    
                    # Simular estar dentro do horário da manhã
                    with patch('datetime.datetime') as mock_datetime:
                        mock_now = datetime.combine(now.date(), morning_start)
                        mock_datetime.now.return_value = mock_now
                        
                        in_session = bot._is_in_session_time('morning')
                        print(f"- Está no horário da sessão manhã: {in_session}")
                    
                    print("\n6. Parando bot...")
                    bot.stop()
                    print("✓ Bot parado com sucesso")
                    
                except Exception as e:
                    print(f"✗ Erro durante o teste: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Garantir que o bot seja parado
                    try:
                        bot.stop()
                    except:
                        pass

def test_manual_mode_compatibility():
    """Testar se o modo manual ainda funciona corretamente"""
    print("\n=== TESTE DE COMPATIBILIDADE COM MODO MANUAL ===")
    
    # Criar configuração para modo manual
    config = create_test_config()
    config.auto_mode = False  # Modo manual
    user = create_test_user()
    
    print(f"Configuração de teste:")
    print(f"- Modo automático: {config.auto_mode}")
    print(f"- Take Profit: {config.take_profit}%")
    print(f"- Stop Loss: {config.stop_loss}%")
    
    # Mock da conexão IQ Option
    with patch('services.iq_option_service.IQOptionService') as mock_iq_service:
        mock_iq_instance = Mock()
        mock_iq_service.return_value = mock_iq_instance
        mock_iq_instance.connect.return_value = True
        mock_iq_instance.is_connected.return_value = True
        mock_iq_instance.get_balance.return_value = 1000.0
        
        # Criar bot de trading
        bot = TradingBot(user.id, config)
        bot._send_notification = Mock()
        bot._send_target_notification = Mock()
        
        print("\n1. Testando comportamento no modo manual...")
        
        # Simular atingir take profit no modo manual
        bot.session_profit = 50.0  # 5% de $1000
        bot.initial_balance = 1000.0
        
        should_continue = bot._should_continue_trading()
        print(f"- Deve continuar trading após Take Profit (manual): {should_continue}")
        print(f"- Stop event definido: {bot.stop_event.is_set()}")
        
        if not should_continue and bot.stop_event.is_set():
            print("✓ Modo manual para corretamente após atingir targets")
        else:
            print("✗ Modo manual não está funcionando corretamente")

if __name__ == '__main__':
    print("Iniciando testes do modo automático contínuo...")
    
    try:
        test_automatic_continuous_mode()
        test_manual_mode_compatibility()
        
        print("\n=== RESUMO DOS TESTES ===")
        print("✓ Teste do modo automático contínuo concluído")
        print("✓ Teste de compatibilidade com modo manual concluído")
        print("\nTodos os testes foram executados com sucesso!")
        
    except Exception as e:
        print(f"\n✗ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)