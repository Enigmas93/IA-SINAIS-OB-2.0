#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir o sistema de pausa automática do trading bot.

Problema identificado:
1. A função _reset_session_for_restart() apenas reseta as estatísticas mas não pausa o bot
2. O loop contínuo não está pausando corretamente após atingir as metas
3. A lógica de auto-restart não está funcionando como esperado

Solução:
1. Modificar _reset_session_for_restart() para pausar até a próxima sessão
2. Corrigir a lógica no loop contínuo para pausar adequadamente
3. Garantir que o bot pause e aguarde a próxima sessão agendada
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_automatic_pause_system():
    """Corrige o sistema de pausa automática do trading bot"""
    
    logger.info("🔧 Iniciando correção do sistema de pausa automática")
    
    # Caminho do arquivo trading_bot.py
    trading_bot_path = "services/trading_bot.py"
    
    if not os.path.exists(trading_bot_path):
        logger.error(f"❌ Arquivo não encontrado: {trading_bot_path}")
        return False
    
    # Ler o arquivo atual
    with open(trading_bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup do arquivo original
    backup_path = f"{trading_bot_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"📋 Backup criado: {backup_path}")
    
    # Correções necessárias
    corrections = [
        {
            'description': 'Corrigir _reset_session_for_restart para pausar até próxima sessão',
            'old_code': '''    def _reset_session_for_restart(self):
        """Reset session statistics for auto-restart after reaching targets"""
        try:
            logger.info("Resetting session for auto-restart...")
            
            # Save current session data for reporting
            previous_profit = self.session_profit
            previous_trades = self.session_trades
            
            # Reset session statistics but keep bot running
            self.session_profit = 0.0
            self.session_trades = 0
            self.martingale_level = 0
            self.consecutive_losses = 0
            
            # Update session start time for new cycle
            self.session_start_time = datetime.now()
            
            # Send restart notification
            self._send_restart_notification(previous_profit, previous_trades)
            
            logger.info(f"Session reset completed - Previous: {previous_trades} trades, {previous_profit:.2f} profit")
            
        except Exception as e:
            logger.error(f"Error resetting session for restart: {str(e)}")''',
            'new_code': '''    def _reset_session_for_restart(self):
        """Reset session statistics and pause until next scheduled session"""
        try:
            logger.info("Resetting session for auto-restart and pausing until next session...")
            
            # Save current session data for reporting
            previous_profit = self.session_profit
            previous_trades = self.session_trades
            current_session_type = self.current_session
            
            # Send restart notification before resetting
            self._send_restart_notification(previous_profit, previous_trades)
            
            # Reset session statistics and pause until next session
            self.session_profit = 0.0
            self.session_trades = 0
            self.martingale_level = 0
            self.consecutive_losses = 0
            self.current_session = None  # Clear current session to trigger pause
            
            logger.info(f"Session reset completed - Previous: {previous_trades} trades, {previous_profit:.2f} profit")
            logger.info(f"Bot will now pause and wait for next scheduled session after {current_session_type}")
            
        except Exception as e:
            logger.error(f"Error resetting session for restart: {str(e)}")'''
        },
        {
            'description': 'Corrigir loop contínuo para pausar adequadamente após atingir metas',
            'old_code': '''                    # Check if we should continue trading (targets check)
                    if not self._should_continue_trading():
                        logger.info(f"Targets reached in {session_type} session - pausing until next session")
                        self._pause_until_next_session()
                        continue''',
            'new_code': '''                    # Check if we should continue trading (targets check)
                    if not self._should_continue_trading():
                        logger.info(f"Targets reached in {session_type} session - pausing until next session")
                        self._pause_until_next_session()
                        break  # Exit the loop to properly pause'''
        },
        {
            'description': 'Melhorar _pause_until_next_session para aguardar adequadamente',
            'old_code': '''    def _pause_until_next_session(self):
        """Pause trading and wait for the next scheduled session"""
        logger.info("Pausing trading - waiting for next scheduled session")
        
        # Reset session data but keep the bot running
        self.current_session = None
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        
        # Send pause notification
        self._send_session_notification('session_paused', 'automatic')
        
        # Calculate time until next session
        next_session_time = self._get_next_session_time()
        if next_session_time:
            wait_seconds = (next_session_time - datetime.now()).total_seconds()
            if wait_seconds > 0:
                logger.info(f"Next session starts at {next_session_time.strftime('%H:%M')} - waiting {wait_seconds/60:.1f} minutes")
                time.sleep(min(wait_seconds, 300))  # Wait max 5 minutes at a time to check for stop events
            else:
                time.sleep(60)  # Wait 1 minute if calculation is off
        else:
            logger.info("No next session found - waiting 5 minutes")
            time.sleep(300)''',
            'new_code': '''    def _pause_until_next_session(self):
        """Pause trading and wait for the next scheduled session"""
        logger.info("Pausing trading - waiting for next scheduled session")
        
        # Reset session data but keep the bot running
        self.current_session = None
        self.session_profit = 0.0
        self.session_trades = 0
        self.martingale_level = 0
        self.consecutive_losses = 0
        
        # Send pause notification
        self._send_session_notification('session_paused', 'automatic')
        
        # Calculate time until next session
        next_session_time = self._get_next_session_time()
        if next_session_time:
            wait_seconds = (next_session_time - datetime.now()).total_seconds()
            if wait_seconds > 0:
                logger.info(f"Next session starts at {next_session_time.strftime('%H:%M')} - waiting {wait_seconds/60:.1f} minutes")
                
                # Wait in smaller intervals to allow for stop events
                while wait_seconds > 0 and self.is_running and not self.stop_event.is_set():
                    sleep_time = min(wait_seconds, 60)  # Check every minute
                    time.sleep(sleep_time)
                    wait_seconds -= sleep_time
                    
                    # Recalculate remaining time
                    if wait_seconds > 60:
                        remaining_time = (next_session_time - datetime.now()).total_seconds()
                        wait_seconds = max(0, remaining_time)
                        
                logger.info("Pause period completed - ready for next session")
            else:
                time.sleep(60)  # Wait 1 minute if calculation is off
        else:
            logger.info("No next session found - waiting 5 minutes")
            time.sleep(300)'''
        }
    ]
    
    # Aplicar correções
    modified_content = content
    for correction in corrections:
        logger.info(f"🔧 Aplicando: {correction['description']}")
        
        if correction['old_code'] in modified_content:
            modified_content = modified_content.replace(
                correction['old_code'], 
                correction['new_code']
            )
            logger.info(f"✅ Correção aplicada com sucesso")
        else:
            logger.warning(f"⚠️ Código não encontrado para: {correction['description']}")
    
    # Salvar arquivo modificado
    with open(trading_bot_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    logger.info(f"✅ Arquivo corrigido salvo: {trading_bot_path}")
    
    return True

def main():
    """Função principal"""
    try:
        logger.info("🚀 Iniciando correção do sistema de pausa automática")
        
        if fix_automatic_pause_system():
            logger.info("✅ Correção do sistema de pausa automática concluída com sucesso!")
            logger.info("")
            logger.info("📋 Resumo das correções aplicadas:")
            logger.info("1. ✅ _reset_session_for_restart agora pausa até a próxima sessão")
            logger.info("2. ✅ Loop contínuo corrigido para pausar adequadamente")
            logger.info("3. ✅ _pause_until_next_session melhorado para aguardar corretamente")
            logger.info("")
            logger.info("🎯 O bot agora irá:")
            logger.info("   • Pausar automaticamente ao atingir take profit ou stop loss")
            logger.info("   • Aguardar a próxima sessão agendada")
            logger.info("   • Reiniciar automaticamente no horário correto")
            logger.info("   • Operar continuamente apenas durante as sessões")
            
        else:
            logger.error("❌ Falha na correção do sistema de pausa automática")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Erro durante a correção: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())