#!/usr/bin/env python3
"""
Teste para verificar se o stop loss está sendo gravado corretamente na sessão da noite
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stop_loss_night_session_saving():
    """Teste para verificar se o stop loss da sessão da noite é salvo corretamente"""
    
    print("\n" + "="*80)
    print("    TESTE: GRAVAÇÃO DE STOP LOSS NA SESSÃO DA NOITE")
    print("="*80)
    
    try:
        # Import Flask app and models
        from app import app, db
        from models import TradingConfig, SessionTargets
        from services.trading_bot import TradingBot
        
        with app.app_context():
            # Create test configuration for night session
            config = TradingConfig(
                user_id=999,  # Test user ID
                asset='EURUSD',
                timeframe='1m',
                trade_amount=10.0,
                use_balance_percentage=False,
                balance_percentage=2.0,
                take_profit=50.0,
                stop_loss=30.0,
                martingale_enabled=True,
                max_martingale_levels=3,
                morning_start="09:00",
                morning_end="12:00",
                afternoon_start="14:00",
                afternoon_end="17:00",
                night_start="19:00",
                night_end="22:00",
                morning_enabled=True,
                afternoon_enabled=True,
                night_enabled=True,  # Enable night session
                continuous_mode=True,
                auto_restart=True,
                auto_mode=True
            )
            
            # Create trading bot instance
            bot = TradingBot(user_id=999, config=config)
            
            # Mock IQ Option service
            bot.iq_service = Mock()
            bot.iq_service.connect.return_value = True
            bot.iq_service.is_connected.return_value = True
            bot.iq_service.get_balance.return_value = 1000.0
            
            print("\n1. ✅ Bot configurado para sessão da noite")
            print(f"   • Sessão da noite: {config.night_start} - {config.night_end}")
            print(f"   • Stop Loss: {config.stop_loss}%")
            print(f"   • Usuário: {config.user_id}")
            
            # Simulate night session
            bot.current_session = 'night'
            bot.session_start_time = datetime.now()
            bot.session_profit = -350.0  # Simulate stop loss reached (-35% of $1000)
            bot.session_trades = 5
            bot.initial_balance = 1000.0
            
            print("\n2. ✅ Simulando atingir Stop Loss na sessão da noite")
            print(f"   • Sessão atual: {bot.current_session}")
            print(f"   • Lucro da sessão: ${bot.session_profit}")
            print(f"   • Total de trades: {bot.session_trades}")
            print(f"   • Saldo inicial: ${bot.initial_balance}")
            
            # Clear any existing session targets for today
            today = datetime.now().date()
            existing_targets = SessionTargets.query.filter_by(
                user_id=999,
                date=today,
                session_type='night'
            ).all()
            
            for target in existing_targets:
                db.session.delete(target)
            db.session.commit()
            
            print("\n3. ✅ Limpeza de dados de teste anteriores")
            
            # Test the _send_target_notification function
            print("\n4. 🧪 Testando gravação do stop loss...")
            
            try:
                bot._send_target_notification('stop_loss_reached', bot.session_profit, config.stop_loss)
                print("   ✅ Função _send_target_notification executada sem erro")
            except Exception as e:
                print(f"   ❌ Erro na função _send_target_notification: {e}")
                return False
            
            # Verify data was saved to database
            print("\n5. 🔍 Verificando dados salvos no banco...")
            
            session_target = SessionTargets.query.filter_by(
                user_id=999,
                date=today,
                session_type='night'
            ).first()
            
            if session_target:
                print("   ✅ Registro encontrado no banco de dados:")
                print(f"      • ID: {session_target.id}")
                print(f"      • Usuário: {session_target.user_id}")
                print(f"      • Data: {session_target.date}")
                print(f"      • Tipo de sessão: {session_target.session_type}")
                print(f"      • Take Profit atingido: {session_target.take_profit_reached}")
                print(f"      • Stop Loss atingido: {session_target.stop_loss_reached}")
                print(f"      • Lucro da sessão: ${session_target.session_profit}")
                print(f"      • Total de trades: {session_target.total_trades}")
                print(f"      • Meta atingida em: {session_target.target_reached_at}")
                print(f"      • Início da sessão: {session_target.session_start}")
                print(f"      • Fim da sessão: {session_target.session_end}")
                
                # Verify stop loss was correctly recorded
                if session_target.stop_loss_reached:
                    print("\n   ✅ STOP LOSS GRAVADO CORRETAMENTE!")
                    success = True
                else:
                    print("\n   ❌ Stop Loss NÃO foi marcado como atingido")
                    success = False
                    
                # Verify session type is 'night'
                if session_target.session_type == 'night':
                    print("   ✅ Tipo de sessão 'night' gravado corretamente")
                else:
                    print(f"   ❌ Tipo de sessão incorreto: {session_target.session_type}")
                    success = False
                    
                # Verify profit value
                if abs(session_target.session_profit - bot.session_profit) < 0.01:
                    print("   ✅ Valor do lucro gravado corretamente")
                else:
                    print(f"   ❌ Valor do lucro incorreto: esperado {bot.session_profit}, obtido {session_target.session_profit}")
                    success = False
                    
            else:
                print("   ❌ NENHUM REGISTRO ENCONTRADO NO BANCO DE DADOS")
                success = False
            
            # Clean up test data
            if session_target:
                db.session.delete(session_target)
                db.session.commit()
                print("\n6. 🧹 Dados de teste removidos")
            
            return success
            
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_night_session_detection():
    """Teste para verificar se a sessão da noite é detectada corretamente"""
    
    print("\n" + "="*80)
    print("    TESTE: DETECÇÃO DE SESSÃO DA NOITE")
    print("="*80)
    
    try:
        from app import app
        from models import TradingConfig
        from services.trading_bot import TradingBot
        
        with app.app_context():
            config = TradingConfig(
                user_id=999,
                night_start="19:00",
                night_end="22:00",
                night_enabled=True
            )
            
            bot = TradingBot(user_id=999, config=config)
            
            # Test different times
            test_times = [
                ("18:30", False, "Antes da sessão da noite"),
                ("19:00", True, "Início da sessão da noite"),
                ("20:30", True, "Durante a sessão da noite"),
                ("22:00", False, "Fim da sessão da noite"),
                ("23:00", False, "Após a sessão da noite")
            ]
            
            print("\n🕐 Testando detecção de horário da sessão da noite:")
            
            all_passed = True
            for time_str, expected, description in test_times:
                with patch('services.trading_bot.datetime') as mock_datetime:
                    # Create a mock datetime for the test time
                    test_hour, test_minute = map(int, time_str.split(':'))
                    mock_now = datetime.now().replace(hour=test_hour, minute=test_minute)
                    mock_datetime.now.return_value = mock_now
                    
                    result = bot._is_in_session_time('night')
                    status = "✅" if result == expected else "❌"
                    print(f"   {status} {time_str} - {description}: {result} (esperado: {expected})")
                    
                    if result != expected:
                        all_passed = False
            
            return all_passed
            
    except Exception as e:
        logger.error(f"Erro no teste de detecção: {e}")
        return False

def main():
    """Função principal do teste"""
    print("\n🚀 INICIANDO TESTES DE STOP LOSS NA SESSÃO DA NOITE")
    print("="*80)
    
    # Test 1: Night session detection
    test1_passed = test_night_session_detection()
    
    # Test 2: Stop loss saving in night session
    test2_passed = test_stop_loss_night_session_saving()
    
    print("\n" + "="*80)
    print("    RESUMO DOS TESTES")
    print("="*80)
    
    print(f"\n1. Detecção de sessão da noite: {'✅ PASSOU' if test1_passed else '❌ FALHOU'}")
    print(f"2. Gravação de stop loss na noite: {'✅ PASSOU' if test2_passed else '❌ FALHOU'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ O stop loss está sendo gravado corretamente na sessão da noite")
        return True
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        print("⚠️  Verifique os logs acima para mais detalhes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)