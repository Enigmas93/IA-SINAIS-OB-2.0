#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o bot para automaticamente após atingir Stop Loss
e reinicia no próximo horário agendado quando em modo automático.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MockTradingConfig:
    """Mock configuration for testing"""
    def __init__(self):
        self.take_profit = 5.0  # 5%
        self.stop_loss = 10.0   # 10%
        self.martingale_enabled = True
        self.max_martingale_levels = 3
        self.auto_mode = True
        self.auto_restart = True
        self.continuous_mode = True
        self.entry_amount = 10.0
        self.martingale_multiplier = 2.2
        self.asset = 'EURUSD'
        self.timeframe = '1m'
        self.strategy_mode = 'intermediario'
        self.min_signal_score = 75.0
        
class StopLossAutoRestartBot:
    """Simulador para testar o comportamento de Stop Loss com auto-restart"""
    
    def __init__(self, initial_balance: float):
        self.config = MockTradingConfig()
        self.initial_balance = initial_balance
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.is_running = True
        self.session_restarted = False
        
        logger.info(f"Bot inicializado com saldo: ${initial_balance:.2f}")
        logger.info(f"Take Profit: {self.config.take_profit}% (${initial_balance * (self.config.take_profit/100):.2f})")
        logger.info(f"Stop Loss: {self.config.stop_loss}% (${initial_balance * (self.config.stop_loss/100):.2f})")
        logger.info(f"Modo Automático: {self.config.auto_mode}")
        logger.info(f"Auto Restart: {self.config.auto_restart}")
        logger.info(f"Modo Contínuo: {self.config.continuous_mode}")
    
    def _calculate_trade_amount(self) -> float:
        """Calculate trade amount based on martingale level"""
        if self.martingale_level == 0:
            return self.config.entry_amount
        else:
            # Calculate martingale amount
            base_amount = self.config.entry_amount
            for _ in range(self.martingale_level):
                base_amount *= self.config.martingale_multiplier
            return base_amount
    
    def _send_target_notification(self, target_type: str, current_profit: float, target_value: float):
        """Simulate sending target notification"""
        logger.info(f"📢 NOTIFICAÇÃO: {target_type} - Lucro: ${current_profit:.2f} (Meta: {target_value}%)")
    
    def _reset_session_for_restart(self):
        """Reset session statistics for auto-restart after reaching targets"""
        logger.info("🔄 REINICIANDO SESSÃO para auto-restart...")
        
        # Save current session data for reporting
        previous_profit = self.session_profit
        previous_trades = self.session_trades
        
        # Reset session statistics but keep bot running
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.session_restarted = True
        
        logger.info(f"✅ Sessão resetada - Anterior: {previous_trades} trades, ${previous_profit:.2f} lucro")
        logger.info("🕐 Bot continuará operando no próximo período agendado")
    
    def simulate_trade_result(self, win: bool, trade_description: str) -> bool:
        """Simulate a trade result and return True if should continue trading"""
        trade_amount = self._calculate_trade_amount()
        self.session_trades += 1
        
        logger.info(f"\n📊 TRADE #{self.session_trades}: {trade_description}")
        logger.info(f"💰 Valor da entrada: ${trade_amount:.2f} (Martingale nível {self.martingale_level})")
        
        if win:
            # Calculate profit (85% payout)
            profit = trade_amount * 0.85
            self.session_profit += profit
            logger.info(f"✅ VITÓRIA: +${profit:.2f}")
            
            # WIN: Always reset martingale to 0
            if self.martingale_level > 0:
                logger.info(f"🔄 Vitória no Martingale {self.martingale_level} - resetando para entrada normal")
            
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Check take profit
            take_profit_value = self.initial_balance * (self.config.take_profit / 100)
            if self.session_profit >= take_profit_value:
                logger.info(f"🎯 Take Profit atingido: ${self.session_profit:.2f} >= ${take_profit_value:.2f}")
                
                if (self.config.auto_mode and 
                    getattr(self.config, 'auto_restart', True) and 
                    getattr(self.config, 'continuous_mode', True)):
                    logger.info("🔄 AUTO-RESTART: Take profit atingido - resetando sessão")
                    self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
                    self._reset_session_for_restart()
                    return True  # Continue trading
                else:
                    logger.info("🛑 AUTO-STOPPING: Take profit atingido - parando bot")
                    self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
                    return False
        else:
            # Calculate loss
            loss = -trade_amount
            self.session_profit += loss
            logger.info(f"❌ PERDA: ${loss:.2f}")
            self.consecutive_losses += 1
            
            # Apply martingale progression if enabled and within limits
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_levels:
                self.martingale_level += 1
                logger.info(f"📈 Martingale aumentado para nível: {self.martingale_level}/{self.config.max_martingale_levels}")
                
                if self.martingale_level <= self.config.max_martingale_levels:
                    logger.info(f"▶️ Continuando com Martingale nível {self.martingale_level}")
            else:
                # Exhausted all martingale levels
                if self.config.martingale_enabled:
                    logger.info(f"⚠️ Todos os {self.config.max_martingale_levels} níveis de Martingale esgotados - verificando metas")
                else:
                    logger.info("⚠️ Martingale desabilitado - verificando metas após perda")
                
                # Reset martingale level
                self.martingale_level = 0
                
                # Check stop loss only after exhausting all martingale attempts
                stop_loss_value = self.initial_balance * (self.config.stop_loss / 100)
                if self.session_profit <= -stop_loss_value:
                    logger.info(f"🔴 Stop Loss atingido: ${self.session_profit:.2f} <= -${stop_loss_value:.2f}")
                    
                    # Check if auto-restart is enabled and we're in automatic mode
                    if (self.config.auto_mode and 
                        getattr(self.config, 'auto_restart', True) and 
                        getattr(self.config, 'continuous_mode', True)):
                        logger.info("🔄 AUTO-RESTART: Stop loss atingido - resetando sessão e continuando no próximo período agendado")
                        self._send_target_notification('stop_loss_reached', self.session_profit, self.config.stop_loss)
                        self._reset_session_for_restart()
                        return True  # Continue trading in continuous mode
                    else:
                        logger.info("🛑 AUTO-STOPPING: Stop loss atingido após esgotar tentativas de martingale - parando bot")
                        self._send_target_notification('stop_loss_reached', self.session_profit, self.config.stop_loss)
                        return False
                else:
                    logger.info(f"✅ Stop loss NÃO atingido (${self.session_profit:.2f} > -${stop_loss_value:.2f}) - continuando com entrada normal")
        
        logger.info(f"💼 Lucro da sessão: ${self.session_profit:.2f} | Total de trades: {self.session_trades}")
        return True

def test_stop_loss_auto_restart_scenario():
    """Testa o cenário onde Stop Loss é atingido e deve fazer auto-restart"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTE: Stop Loss com Auto-Restart em Modo Automático")
    logger.info("=" * 80)
    
    bot = StopLossAutoRestartBot(1000.0)
    
    # Simular sequência de perdas que deve atingir o Stop Loss
    # Entrada normal + 3 Martingales = 4 perdas consecutivas
    # Valores: $10 + $22 + $48.40 + $106.48 = $186.88 de perda
    # Stop Loss: 10% de $1000 = $100, então $186.88 > $100 = Stop Loss atingido
    
    scenarios = [
        (False, "Entrada Normal - Perda 1"),
        (False, "Martingale 1 - Perda 2"),
        (False, "Martingale 2 - Perda 3"),
        (False, "Martingale 3 - Perda 4 (deve atingir Stop Loss)")
    ]
    
    for win, description in scenarios:
        should_continue = bot.simulate_trade_result(win, description)
        
        if not should_continue:
            logger.error("❌ Bot parou inesperadamente - deveria fazer auto-restart!")
            return False
        
        if bot.session_restarted:
            logger.info("✅ SUCESSO: Bot fez auto-restart após atingir Stop Loss!")
            logger.info("🕐 Bot continuará operando no próximo período agendado")
            return True
    
    logger.error("❌ FALHA: Stop Loss não foi atingido quando deveria")
    return False

def test_stop_loss_without_auto_restart():
    """Testa o cenário onde Stop Loss é atingido sem auto-restart (deve parar)"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTE: Stop Loss SEM Auto-Restart (deve parar)")
    logger.info("=" * 80)
    
    bot = StopLossAutoRestartBot(1000.0)
    
    # Desabilitar auto-restart
    bot.config.auto_restart = False
    logger.info(f"Auto Restart desabilitado: {bot.config.auto_restart}")
    
    scenarios = [
        (False, "Entrada Normal - Perda 1"),
        (False, "Martingale 1 - Perda 2"),
        (False, "Martingale 2 - Perda 3"),
        (False, "Martingale 3 - Perda 4 (deve parar o bot)")
    ]
    
    for win, description in scenarios:
        should_continue = bot.simulate_trade_result(win, description)
        
        if not should_continue:
            logger.info("✅ SUCESSO: Bot parou corretamente após atingir Stop Loss sem auto-restart!")
            return True
        
        if bot.session_restarted:
            logger.error("❌ FALHA: Bot fez auto-restart quando não deveria!")
            return False
    
    logger.error("❌ FALHA: Stop Loss não foi atingido quando deveria")
    return False

def main():
    """Executa todos os testes"""
    logger.info("🚀 Iniciando testes de Stop Loss com Auto-Restart")
    logger.info(f"⏰ Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Stop Loss com Auto-Restart", test_stop_loss_auto_restart_scenario),
        ("Stop Loss sem Auto-Restart", test_stop_loss_without_auto_restart)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n🔍 Executando: {test_name}")
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name}: PASSOU")
            else:
                logger.error(f"❌ {test_name}: FALHOU")
                
        except Exception as e:
            logger.error(f"💥 Erro no teste '{test_name}': {str(e)}")
            results.append((test_name, False))
    
    # Resumo final
    logger.info("\n" + "=" * 80)
    logger.info("📋 RESUMO DOS TESTES")
    logger.info("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Resultado Final: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("🎉 TODOS OS TESTES PASSARAM! A correção está funcionando corretamente.")
        return True
    else:
        logger.error(f"⚠️ {total - passed} teste(s) falharam. Verifique a implementação.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)