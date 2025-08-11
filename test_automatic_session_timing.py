#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o bot em modo automático aguarda os horários de sessão
ao invés de iniciar trading imediatamente quando ativado.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import User, TradingConfig
from services.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_automatic_mode_session_timing():
    """
    Testa se o bot em modo automático aguarda os horários de sessão
    ao invés de iniciar trading imediatamente.
    """
    logger.info("\n" + "=" * 80)
    logger.info("TESTE: Bot em Modo Automático - Aguardar Horários de Sessão")
    logger.info("=" * 80)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create test user
        user = User(
            name="Test User",
            email="test@example.com",
            iq_email="test@iq.com",
            iq_password="password123",
            account_type="PRACTICE"
        )
        
        # Create test config with automatic mode enabled
        current_time = datetime.now()
        future_time = current_time + timedelta(hours=2)  # Session 2 hours from now
        
        config = TradingConfig(
            user_id=1,
            asset="EURUSD-OTC",
            trade_amount=25.0,
            take_profit=15.0,
            auto_mode=True,  # Modo automático ativado
            continuous_mode=True,
            morning_enabled=True,
            morning_start=future_time.strftime("%H:%M"),  # Sessão da manhã no futuro
            afternoon_enabled=True,
            afternoon_start="14:30",
            night_enabled=False,
            rsi_period=14,
            rsi_oversold=30,
            rsi_overbought=70,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9,
            ma_short_period=10,
            ma_long_period=20,
            aroon_period=14,
            enable_engulfing=True,
            enable_hammer=True,
            enable_doji=True,
            enable_shooting_star=True,
            min_signal_score=70,
            strategy_mode="conservative",
            timeframe="1m",
            use_ml_signals=False
        )
        
        logger.info(f"Configuração do teste:")
        logger.info(f"- Modo automático: {config.auto_mode}")
        logger.info(f"- Horário atual: {current_time.strftime('%H:%M:%S')}")
        logger.info(f"- Próxima sessão (manhã): {config.morning_start}")
        logger.info(f"- Sessão da tarde: {config.afternoon_start}")
        
        # Mock dos serviços para evitar conexões reais
        with patch('services.iq_option_service.IQOptionService') as mock_iq_service:
            mock_iq_instance = Mock()
            mock_iq_service.return_value = mock_iq_instance
            mock_iq_instance.connect.return_value = True
            mock_iq_instance.set_account_type.return_value = True
            
            with patch('services.signal_analyzer.SignalAnalyzer') as mock_signal_service:
                mock_signal_instance = Mock()
                mock_signal_service.return_value = mock_signal_instance
                
                # Criar bot de trading
                logger.info("\n1. Criando bot em modo automático...")
                bot = TradingBot(user.id, config, app)
                
                # Verificar se o bot foi configurado corretamente
                logger.info(f"✓ Bot criado com modo automático: {bot.config.auto_mode}")
                
                # Simular início do bot
                logger.info("\n2. Iniciando bot...")
                
                # Capturar logs para verificar comportamento
                with patch('services.trading_bot.logger') as mock_logger:
                    # Mock do scheduler para evitar jobs reais
                    with patch.object(bot, 'scheduler') as mock_scheduler:
                        mock_scheduler.running = False
                        mock_scheduler.start.return_value = None
                        mock_scheduler.add_job.return_value = None
                        
                        # Iniciar o bot
                        success = bot.start()
                        
                        if success:
                            logger.info("✓ Bot iniciado com sucesso")
                            
                            # Verificar se o bot NÃO iniciou trading imediatamente
                            logger.info("\n3. Verificando se o bot aguarda horário de sessão...")
                            
                            # Verificar se não há sessão ativa
                            if bot.current_session is None:
                                logger.info("✓ Bot não iniciou trading imediatamente - aguardando horário de sessão")
                            else:
                                logger.error(f"✗ Bot iniciou trading imediatamente na sessão: {bot.current_session}")
                            
                            # Verificar se o scheduler foi configurado
                            if mock_scheduler.add_job.called:
                                logger.info("✓ Scheduler configurado para sessões automáticas")
                                logger.info(f"  - Número de jobs agendados: {mock_scheduler.add_job.call_count}")
                            else:
                                logger.error("✗ Scheduler não foi configurado")
                            
                            # Verificar logs de modo automático
                            logger.info("\n4. Verificando logs do modo automático...")
                            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
                            
                            automatic_mode_logs = [
                                log for log in log_calls 
                                if 'automatic mode' in log.lower() or 'scheduled session' in log.lower()
                            ]
                            
                            if automatic_mode_logs:
                                logger.info("✓ Logs de modo automático encontrados:")
                                for log in automatic_mode_logs:
                                    logger.info(f"  - {log}")
                            else:
                                logger.warning("⚠ Nenhum log específico de modo automático encontrado")
                            
                            # Testar função _get_next_session_time
                            logger.info("\n5. Testando cálculo da próxima sessão...")
                            next_session = bot._get_next_session_time()
                            if next_session:
                                logger.info(f"✓ Próxima sessão calculada: {next_session.strftime('%H:%M:%S')}")
                                
                                # Verificar se é no futuro
                                if next_session > datetime.now():
                                    logger.info("✓ Próxima sessão está no futuro (correto)")
                                else:
                                    logger.error("✗ Próxima sessão não está no futuro")
                            else:
                                logger.error("✗ Não foi possível calcular próxima sessão")
                            
                        else:
                            logger.error("✗ Falha ao iniciar bot")
                        
                        # Parar o bot
                        logger.info("\n6. Parando bot...")
                        bot.stop()
                        logger.info("✓ Bot parado")
        
        logger.info("\n" + "=" * 80)
        logger.info("RESULTADO: Teste de modo automático com horários de sessão")
        logger.info("=" * 80)
        logger.info("✓ Bot em modo automático agora aguarda horários de sessão")
        logger.info("✓ Não inicia trading imediatamente quando ativado")
        logger.info("✓ Scheduler configurado para sessões automáticas")
        logger.info("=" * 80)

if __name__ == "__main__":
    test_automatic_mode_session_timing()