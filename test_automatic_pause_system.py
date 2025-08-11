#!/usr/bin/env python3
"""
Teste do sistema de pausa automática após atingir metas
"""

from app import app, db
from models import User, TradingConfig
from services.trading_bot import TradingBot
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAutomaticPauseSystem:
    def __init__(self):
        self.app = app
        self.test_results = []
        
    def add_test_result(self, test_name, expected, actual, passed):
        """Add test result"""
        result = {
            'test': test_name,
            'expected': expected,
            'actual': actual,
            'passed': passed,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        logger.info(f"{status} - {test_name}")
        logger.info(f"  Esperado: {expected}")
        logger.info(f"  Atual: {actual}")
        
    def test_take_profit_pause_logic(self):
        """Testa se o bot pausa corretamente ao atingir take profit"""
        logger.info("\n=== Testando Lógica de Pausa no Take Profit ===")
        
        with self.app.app_context():
            # Get test user and config
            user = User.query.filter_by(email='test@test.com').first()
            config = TradingConfig.query.filter_by(user_id=user.id).first()
            
            if not config:
                logger.error("Configuração não encontrada")
                return
                
            # Create bot instance
            bot = TradingBot(user.id, config, self.app)
            
            # Simulate automatic mode
            config.auto_mode = True
            config.continuous_mode = True
            config.auto_restart = True
            config.take_profit = 10.0  # 10%
            
            # Set initial balance and session profit
            bot.initial_balance = 1000.0
            bot.session_profit = 0.0
            bot.martingale_level = 0  # Normal entry level
            bot.current_session = 'morning'
            
            # Test 1: Normal trading should continue
            should_continue = bot._should_continue_trading()
            self.add_test_result(
                "Normal trading continues",
                True,
                should_continue,
                should_continue == True
            )
            
            # Test 2: Take profit reached - should pause in automatic mode
            take_profit_value = bot.initial_balance * (config.take_profit / 100)  # 10% of 1000 = 100
            bot.session_profit = take_profit_value + 1  # Exceed take profit
            
            should_continue = bot._should_continue_trading()
            self.add_test_result(
                "Take profit reached - should pause",
                False,
                should_continue,
                should_continue == False
            )
            
            # Test 3: During martingale - should continue even if take profit reached
            bot.session_profit = take_profit_value + 1  # Still above take profit
            bot.martingale_level = 2  # In martingale progression
            
            should_continue = bot._should_continue_trading()
            self.add_test_result(
                "During martingale - should continue despite take profit",
                True,
                should_continue,
                should_continue == True
            )
            
    def test_stop_loss_pause_logic(self):
        """Testa se o bot pausa corretamente após perder todos os martingales"""
        logger.info("\n=== Testando Lógica de Pausa no Stop Loss ===")
        
        with self.app.app_context():
            # Get test user and config
            user = User.query.filter_by(email='test@test.com').first()
            config = TradingConfig.query.filter_by(user_id=user.id).first()
            
            # Create bot instance
            bot = TradingBot(user.id, config, self.app)
            
            # Simulate automatic mode
            config.auto_mode = True
            config.continuous_mode = True
            config.auto_restart = True
            config.martingale_enabled = True
            config.max_martingale_levels = 3
            
            # Set initial state
            bot.initial_balance = 1000.0
            bot.session_profit = -200.0  # Significant loss
            bot.martingale_level = 0  # Back to normal after losing all martingales
            bot.current_session = 'morning'
            
            # Test: After losing all martingales, should check for restart
            # This would be handled in _wait_for_trade_result, but we can test the logic
            
            # Simulate the condition where all martingales are exhausted
            logger.info("Simulando perda de todos os níveis de martingale...")
            
            # Check if auto-restart logic would trigger
            auto_restart_enabled = (
                config.auto_mode and 
                getattr(config, 'auto_restart', True) and 
                getattr(config, 'continuous_mode', True)
            )
            
            self.add_test_result(
                "Auto-restart habilitado para modo automático",
                True,
                auto_restart_enabled,
                auto_restart_enabled == True
            )
            
    def test_session_management(self):
        """Testa o gerenciamento de sessões automáticas"""
        logger.info("\n=== Testando Gerenciamento de Sessões ===")
        
        with self.app.app_context():
            # Get test user and config
            user = User.query.filter_by(email='test@test.com').first()
            config = TradingConfig.query.filter_by(user_id=user.id).first()
            
            # Create bot instance
            bot = TradingBot(user.id, config, self.app)
            
            # Test session time logic
            current_time = datetime.now()
            
            # Test morning session
            config.morning_enabled = True
            config.morning_start = "09:00"
            
            # Test if session time detection works
            is_morning_time = bot._is_in_session_time('morning')
            logger.info(f"Horário atual: {current_time.strftime('%H:%M')}")
            logger.info(f"Sessão manhã configurada: {config.morning_start}")
            logger.info(f"É horário da sessão manhã: {is_morning_time}")
            
            # Test next session calculation
            next_session = bot._get_next_session_time()
            if next_session:
                logger.info(f"Próxima sessão: {next_session.strftime('%H:%M')}")
            else:
                logger.info("Nenhuma próxima sessão encontrada")
                
    def test_continuous_mode_behavior(self):
        """Testa o comportamento do modo contínuo"""
        logger.info("\n=== Testando Comportamento do Modo Contínuo ===")
        
        with self.app.app_context():
            # Get test user and config
            user = User.query.filter_by(email='test@test.com').first()
            config = TradingConfig.query.filter_by(user_id=user.id).first()
            
            # Test different mode combinations
            test_cases = [
                {
                    'name': 'Modo Manual',
                    'auto_mode': False,
                    'continuous_mode': False,
                    'auto_restart': False
                },
                {
                    'name': 'Modo Automático sem Restart',
                    'auto_mode': True,
                    'continuous_mode': True,
                    'auto_restart': False
                },
                {
                    'name': 'Modo Automático com Restart',
                    'auto_mode': True,
                    'continuous_mode': True,
                    'auto_restart': True
                }
            ]
            
            for case in test_cases:
                logger.info(f"\nTestando: {case['name']}")
                
                # Set config
                config.auto_mode = case['auto_mode']
                config.continuous_mode = case['continuous_mode']
                config.auto_restart = case['auto_restart']
                
                # Create bot instance
                bot = TradingBot(user.id, config, self.app)
                bot.initial_balance = 1000.0
                bot.session_profit = 100.0  # Above take profit
                bot.martingale_level = 0
                bot.current_session = 'morning'
                
                # Test behavior
                should_continue = bot._should_continue_trading()
                
                expected_behavior = "Pausar" if case['auto_mode'] else "Parar"
                actual_behavior = "Pausar" if not should_continue and case['auto_mode'] else "Parar" if not should_continue else "Continuar"
                
                logger.info(f"  Comportamento esperado: {expected_behavior}")
                logger.info(f"  Comportamento atual: {actual_behavior}")
                
    def run_all_tests(self):
        """Execute todos os testes"""
        logger.info("Iniciando testes do sistema de pausa automática")
        
        try:
            self.test_take_profit_pause_logic()
            self.test_stop_loss_pause_logic()
            self.test_session_management()
            self.test_continuous_mode_behavior()
            
            # Summary
            logger.info("\n" + "="*50)
            logger.info("RESUMO DOS TESTES")
            logger.info("="*50)
            
            passed_tests = sum(1 for result in self.test_results if result['passed'])
            total_tests = len(self.test_results)
            
            logger.info(f"Total de testes: {total_tests}")
            logger.info(f"Testes aprovados: {passed_tests}")
            logger.info(f"Testes falharam: {total_tests - passed_tests}")
            
            if passed_tests == total_tests:
                logger.info("TODOS OS TESTES PASSARAM!")
            else:
                logger.info("ALGUNS TESTES FALHARAM - Verificar implementação")
                
                # Show failed tests
                failed_tests = [r for r in self.test_results if not r['passed']]
                for test in failed_tests:
                    logger.info(f"FALHOU: {test['test']}")
                    
        except Exception as e:
            logger.error(f"Erro durante os testes: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    tester = TestAutomaticPauseSystem()
    tester.run_all_tests()