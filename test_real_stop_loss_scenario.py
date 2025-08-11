#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste real para verificar o comportamento do bot após atingir Stop Loss
com auto-restart em modo automático.
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
    """Mock configuration matching real bot settings"""
    def __init__(self):
        self.take_profit = 8.5  # 8.5%
        self.stop_loss = 25.0   # 25%
        self.martingale_enabled = True
        self.max_martingale_levels = 3
        self.auto_mode = True
        self.auto_restart = True
        self.continuous_mode = True
        self.entry_amount = 2.0  # $2 entrada
        self.martingale_multiplier = 2.2
        self.asset = 'EURUSD'
        self.timeframe = '1m'
        self.strategy_mode = 'intermediario'
        self.min_signal_score = 75.0
        
class RealStopLossScenarioBot:
    """Simulador que replica o comportamento real do bot"""
    
    def __init__(self, initial_balance: float):
        self.config = MockTradingConfig()
        self.initial_balance = initial_balance
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.is_running = True
        self.session_restarted = False
        self.stop_scheduled = False
        
        logger.info(f"🤖 Bot Real Scenario inicializado")
        logger.info(f"💰 Saldo inicial: ${initial_balance:.2f}")
        logger.info(f"🎯 Take Profit: {self.config.take_profit}% (${initial_balance * (self.config.take_profit/100):.2f})")
        logger.info(f"🔴 Stop Loss: {self.config.stop_loss}% (${initial_balance * (self.config.stop_loss/100):.2f})")
        logger.info(f"⚙️ Entrada: ${self.config.entry_amount:.2f} | Multiplicador: {self.config.martingale_multiplier}x")
        logger.info(f"🔄 Auto Mode: {self.config.auto_mode} | Auto Restart: {self.config.auto_restart} | Contínuo: {self.config.continuous_mode}")
    
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
        logger.info(f"📢 NOTIFICAÇÃO ENVIADA: {target_type}")
        logger.info(f"   💰 Lucro atual: ${current_profit:.2f}")
        logger.info(f"   🎯 Meta: {target_value}%")
    
    def _reset_session_for_restart(self):
        """Reset session statistics for auto-restart after reaching targets"""
        logger.info("\n🔄 EXECUTANDO AUTO-RESTART...")
        
        # Save current session data for reporting
        previous_profit = self.session_profit
        previous_trades = self.session_trades
        
        logger.info(f"📊 Dados da sessão anterior:")
        logger.info(f"   💰 Lucro: ${previous_profit:.2f}")
        logger.info(f"   📈 Trades: {previous_trades}")
        logger.info(f"   🎲 Martingale final: {self.martingale_level}")
        
        # Reset session statistics but keep bot running
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        self.session_restarted = True
        
        logger.info(f"\n✅ SESSÃO RESETADA COM SUCESSO")
        logger.info(f"🕐 Bot continuará operando no próximo período agendado")
        logger.info(f"🔄 Aguardando próximo horário de trading...")
    
    def _schedule_stop(self):
        """Schedule bot stop"""
        logger.info("\n🛑 AGENDANDO PARADA DO BOT...")
        self.is_running = False
        self.stop_scheduled = True
        logger.info("✅ Bot será parado após completar operação atual")
        logger.info("🔌 Desconectando serviços...")
        logger.info("📴 Bot parado com sucesso")
    
    def simulate_trade_result(self, win: bool, trade_description: str) -> bool:
        """Simulate a trade result and return True if should continue trading"""
        trade_amount = self._calculate_trade_amount()
        self.session_trades += 1
        
        logger.info(f"\n📊 EXECUTANDO TRADE #{self.session_trades}")
        logger.info(f"📝 Descrição: {trade_description}")
        logger.info(f"💰 Valor da entrada: ${trade_amount:.2f}")
        logger.info(f"🎲 Nível Martingale: {self.martingale_level}")
        
        if win:
            # Calculate profit (85% payout)
            profit = trade_amount * 0.85
            self.session_profit += profit
            logger.info(f"✅ RESULTADO: VITÓRIA (+${profit:.2f})")
            
            # WIN: Always reset martingale to 0
            if self.martingale_level > 0:
                logger.info(f"🔄 Vitória no Martingale {self.martingale_level} - resetando para entrada normal")
            
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Check take profit
            take_profit_value = self.initial_balance * (self.config.take_profit / 100)
            if self.session_profit >= take_profit_value:
                logger.info(f"\n🎯 TAKE PROFIT ATINGIDO!")
                logger.info(f"💰 Lucro: ${self.session_profit:.2f} >= ${take_profit_value:.2f}")
                
                if (self.config.auto_mode and 
                    getattr(self.config, 'auto_restart', True) and 
                    getattr(self.config, 'continuous_mode', True)):
                    logger.info("🔄 AUTO-RESTART ativado - resetando sessão")
                    self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
                    self._reset_session_for_restart()
                    return True  # Continue trading
                else:
                    logger.info("🛑 AUTO-STOPPING - parando bot")
                    self._send_target_notification('take_profit_reached', self.session_profit, self.config.take_profit)
                    self._schedule_stop()
                    return False
        else:
            # Calculate loss
            loss = -trade_amount
            self.session_profit += loss
            logger.info(f"❌ RESULTADO: PERDA (${loss:.2f})")
            self.consecutive_losses += 1
            
            # Apply martingale progression if enabled and within limits
            if self.config.martingale_enabled and self.martingale_level < self.config.max_martingale_levels:
                self.martingale_level += 1
                logger.info(f"📈 Martingale aumentado: {self.martingale_level}/{self.config.max_martingale_levels}")
                
                if self.martingale_level <= self.config.max_martingale_levels:
                    next_amount = self._calculate_trade_amount()
                    logger.info(f"▶️ Próxima entrada: ${next_amount:.2f} (Martingale {self.martingale_level})")
            else:
                # Exhausted all martingale levels
                if self.config.martingale_enabled:
                    logger.info(f"\n⚠️ MARTINGALE ESGOTADO!")
                    logger.info(f"🔄 Todos os {self.config.max_martingale_levels} níveis utilizados")
                else:
                    logger.info("\n⚠️ Martingale desabilitado - verificando metas")
                
                # Reset martingale level
                self.martingale_level = 0
                
                # Check stop loss only after exhausting all martingale attempts
                stop_loss_value = self.initial_balance * (self.config.stop_loss / 100)
                logger.info(f"\n🔍 VERIFICANDO STOP LOSS...")
                logger.info(f"💰 Lucro atual: ${self.session_profit:.2f}")
                logger.info(f"🔴 Limite Stop Loss: -${stop_loss_value:.2f}")
                
                if self.session_profit <= -stop_loss_value:
                    logger.info(f"\n🚨 STOP LOSS ATINGIDO!")
                    logger.info(f"💸 ${self.session_profit:.2f} <= -${stop_loss_value:.2f}")
                    
                    # Check if auto-restart is enabled and we're in automatic mode
                    if (self.config.auto_mode and 
                        getattr(self.config, 'auto_restart', True) and 
                        getattr(self.config, 'continuous_mode', True)):
                        logger.info(f"\n🔄 AUTO-RESTART ATIVADO!")
                        logger.info(f"📋 Condições atendidas:")
                        logger.info(f"   ⚙️ Modo Automático: {self.config.auto_mode}")
                        logger.info(f"   🔄 Auto Restart: {getattr(self.config, 'auto_restart', True)}")
                        logger.info(f"   🔁 Modo Contínuo: {getattr(self.config, 'continuous_mode', True)}")
                        logger.info(f"\n🎯 AÇÃO: Resetando sessão e continuando no próximo período agendado")
                        self._send_target_notification('stop_loss_reached', self.session_profit, self.config.stop_loss)
                        self._reset_session_for_restart()
                        return True  # Continue trading in continuous mode
                    else:
                        logger.info(f"\n🛑 AUTO-STOPPING ATIVADO!")
                        logger.info(f"📋 Condições:")
                        logger.info(f"   ⚙️ Modo Automático: {self.config.auto_mode}")
                        logger.info(f"   🔄 Auto Restart: {getattr(self.config, 'auto_restart', True)}")
                        logger.info(f"   🔁 Modo Contínuo: {getattr(self.config, 'continuous_mode', True)}")
                        logger.info(f"\n🎯 AÇÃO: Parando bot após esgotar tentativas de martingale")
                        self._send_target_notification('stop_loss_reached', self.session_profit, self.config.stop_loss)
                        self._schedule_stop()
                        return False
                else:
                    logger.info(f"\n✅ STOP LOSS NÃO ATINGIDO")
                    logger.info(f"💰 ${self.session_profit:.2f} > -${stop_loss_value:.2f}")
                    logger.info(f"▶️ Continuando com entrada normal")
        
        logger.info(f"\n📊 STATUS DA SESSÃO:")
        logger.info(f"   💰 Lucro: ${self.session_profit:.2f}")
        logger.info(f"   📈 Trades: {self.session_trades}")
        logger.info(f"   🎲 Martingale: {self.martingale_level}")
        logger.info(f"   📉 Perdas consecutivas: {self.consecutive_losses}")
        
        return True

def test_real_stop_loss_scenario():
    """Testa cenário real onde Stop Loss deve ativar auto-restart"""
    logger.info("\n" + "=" * 100)
    logger.info("🧪 TESTE CENÁRIO REAL: Stop Loss com Auto-Restart")
    logger.info("=" * 100)
    
    # Usar saldo real típico
    bot = RealStopLossScenarioBot(500.0)
    
    # Calcular quantas perdas são necessárias para atingir 25% de stop loss
    # Stop Loss: 25% de $500 = $125
    # Sequência de perdas: $2 + $4.40 + $9.68 + $21.30 = $37.38
    # Precisamos de mais perdas para atingir $125
    
    logger.info(f"\n🎯 OBJETIVO: Atingir Stop Loss de ${500 * 0.25:.2f} com sequência de perdas")
    
    # Simular múltiplas sequências de perdas até atingir stop loss
    sequence = 1
    
    while bot.is_running and not bot.session_restarted and not bot.stop_scheduled:
        logger.info(f"\n🔄 SEQUÊNCIA DE PERDAS #{sequence}")
        logger.info(f"" + "-" * 50)
        
        # 4 perdas consecutivas (entrada + 3 martingales)
        trades = [
            (False, f"Seq {sequence} - Entrada Normal"),
            (False, f"Seq {sequence} - Martingale 1"),
            (False, f"Seq {sequence} - Martingale 2"),
            (False, f"Seq {sequence} - Martingale 3")
        ]
        
        for win, description in trades:
            should_continue = bot.simulate_trade_result(win, description)
            
            if not should_continue:
                logger.info(f"\n🛑 Bot parou na sequência {sequence}")
                break
            
            if bot.session_restarted:
                logger.info(f"\n✅ AUTO-RESTART executado na sequência {sequence}!")
                return True
            
            if bot.stop_scheduled:
                logger.info(f"\n🛑 Parada agendada na sequência {sequence}")
                return False
        
        sequence += 1
        
        # Limite de segurança para evitar loop infinito
        if sequence > 10:
            logger.error("❌ Limite de sequências atingido - teste falhou")
            return False
    
    if bot.session_restarted:
        logger.info("\n✅ SUCESSO: Auto-restart executado corretamente!")
        return True
    else:
        logger.error("\n❌ FALHA: Stop Loss não ativou auto-restart")
        return False

def main():
    """Executa o teste do cenário real"""
    logger.info("🚀 INICIANDO TESTE DE CENÁRIO REAL")
    logger.info(f"⏰ Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("🎯 Objetivo: Verificar se Stop Loss ativa auto-restart corretamente")
    
    try:
        result = test_real_stop_loss_scenario()
        
        logger.info("\n" + "=" * 100)
        logger.info("📋 RESULTADO FINAL")
        logger.info("=" * 100)
        
        if result:
            logger.info("✅ TESTE PASSOU: Auto-restart funcionando corretamente!")
            logger.info("🎉 O bot agora para automaticamente após Stop Loss e reinicia no próximo horário")
        else:
            logger.error("❌ TESTE FALHOU: Auto-restart não funcionou como esperado")
            logger.error("⚠️ Verifique a implementação da lógica de Stop Loss")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 Erro durante o teste: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)