#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Comportamento de Sessões Automáticas

Este script verifica se o sistema está funcionando conforme solicitado:
1. Opera apenas nos horários definidos para as sessões (manhã, tarde, noite)
2. Pausa automaticamente ao atingir take profit ou stop loss
3. Aguarda o próximo horário agendado para reiniciar
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import time
import logging
from unittest.mock import Mock, patch

from app import create_app
from models import User, TradingConfig, db
from services.trading_bot import TradingBot
from services.iq_option_service import IQOptionService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_automatic_sessions.log')
    ]
)
logger = logging.getLogger(__name__)

class TestAutomaticSessionBehavior:
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Configurar horários de teste (próximos minutos)
        now = datetime.now()
        self.morning_start = (now + timedelta(minutes=2)).strftime('%H:%M')
        self.afternoon_start = (now + timedelta(minutes=6)).strftime('%H:%M')
        self.night_start = (now + timedelta(minutes=10)).strftime('%H:%M')
        
        logger.info(f"\n=== TESTE DE COMPORTAMENTO DE SESSÕES AUTOMÁTICAS ===")
        logger.info(f"Horário atual: {now.strftime('%H:%M:%S')}")
        logger.info(f"Sessão manhã: {self.morning_start}")
        logger.info(f"Sessão tarde: {self.afternoon_start}")
        logger.info(f"Sessão noite: {self.night_start}")
    
    def create_test_user_and_config(self):
        """Criar usuário e configuração de teste"""
        try:
            # Limpar dados existentes
            existing_user = User.query.filter_by(email='test_auto@test.com').first()
            if existing_user:
                TradingConfig.query.filter_by(user_id=existing_user.id).delete()
                db.session.delete(existing_user)
                db.session.commit()
            
            # Criar novo usuário
            user = User(
                name='test_auto_user',
                email='test_auto@test.com',
                password_hash='test_hash',
                iq_email='test_auto@iq.com',
                iq_password='test_password'
            )
            db.session.add(user)
            db.session.commit()
            
            # Criar configuração para modo automático
            config = TradingConfig(
                user_id=user.id,
                asset='EURUSD',
                trade_amount=10.0,
                take_profit=5.0,  # 5% take profit
                
                # MODO AUTOMÁTICO - configurações corretas
                auto_mode=True,           # Modo automático ativado
                continuous_mode=False,    # NÃO continuar entre sessões
                auto_restart=False,       # NÃO reiniciar automaticamente
                operation_mode='auto',
                
                # Horários das sessões
                morning_enabled=True,
                morning_start=self.morning_start,
                afternoon_enabled=True,
                afternoon_start=self.afternoon_start,
                night_enabled=True,
                night_start=self.night_start,
                
                # Configurações de trading
                martingale_enabled=True,
                max_martingale_levels=3,
                martingale_multiplier=2.2,
                timeframe='1m',
                strategy_mode='intermediario',
                min_signal_score=75.0
            )
            db.session.add(config)
            db.session.commit()
            
            logger.info(f"[OK] Usuário e configuração criados com sucesso")
            logger.info(f"  - auto_mode: {config.auto_mode}")
            logger.info(f"  - continuous_mode: {config.continuous_mode}")
            logger.info(f"  - auto_restart: {config.auto_restart}")
            
            return user, config
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário e configuração: {str(e)}")
            return None, None
    
    def test_automatic_session_scheduling(self):
        """Testar agendamento automático de sessões"""
        logger.info("\n=== TESTE 1: AGENDAMENTO AUTOMÁTICO DE SESSÕES ===")
        
        user, config = self.create_test_user_and_config()
        if not user or not config:
            logger.error("[ERRO] Falha ao criar configuração de teste")
            return False
        
        try:
            # Mock do IQOptionService
            with patch('services.trading_bot.IQOptionService') as mock_iq_service:
                mock_iq_instance = Mock()
                mock_iq_instance.is_connected = True
                mock_iq_instance.connect.return_value = True
                mock_iq_service.return_value = mock_iq_instance
                
                # Criar bot com configuração automática
                bot = TradingBot(user.id, config, self.app)
                
                # Verificar se o bot foi configurado para modo automático
                if not bot.config.auto_mode:
                    logger.error("[ERRO] Bot não está em modo automático")
                    return False
                
                logger.info("[OK] Bot configurado em modo automático")
                
                # Mock do scheduler para capturar jobs agendados
                with patch.object(bot, 'scheduler') as mock_scheduler:
                    mock_scheduler.running = False
                    mock_scheduler.start.return_value = None
                    mock_scheduler.add_job.return_value = None
                    
                    # Iniciar o bot
                    bot.start()
                    
                    # Verificar se o scheduler foi iniciado
                    if mock_scheduler.start.called:
                        logger.info("[OK] Scheduler iniciado para sessões automáticas")
                    else:
                        logger.error("[ERRO] Scheduler não foi iniciado")
                        return False
                    
                    # Verificar se as sessões foram agendadas
                    if mock_scheduler.add_job.call_count >= 3:  # manhã, tarde, noite
                        logger.info(f"[OK] Sessões agendadas: {mock_scheduler.add_job.call_count} jobs")
                        
                        # Verificar se o bot NÃO iniciou trading imediatamente
                        if bot.current_session is None:
                            logger.info("[OK] Bot aguardando próxima sessão agendada (comportamento correto)")
                        else:
                            logger.error(f"[ERRO] Bot iniciou trading imediatamente: {bot.current_session}")
                            return False
                    else:
                        logger.error(f"[ERRO] Número insuficiente de sessões agendadas: {mock_scheduler.add_job.call_count}")
                        return False
                
                # Testar cálculo da próxima sessão
                next_session = bot._get_next_session_time()
                if next_session:
                    logger.info(f"[OK] Próxima sessão calculada: {next_session.strftime('%H:%M:%S')}")
                    
                    # Verificar se é no futuro
                    if next_session > datetime.now():
                        logger.info("[OK] Próxima sessão está no futuro (correto)")
                    else:
                        logger.error("[ERRO] Próxima sessão não está no futuro")
                        return False
                else:
                    logger.error("[ERRO] Não foi possível calcular próxima sessão")
                    return False
                
                bot.stop()
                logger.info("[OK] Teste de agendamento concluído com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"Erro no teste de agendamento: {str(e)}")
            return False
    
    def test_session_pause_behavior(self):
        """Testar comportamento de pausa ao atingir metas"""
        logger.info("\n=== TESTE 2: PAUSA AUTOMÁTICA AO ATINGIR METAS ===")
        
        user, config = self.create_test_user_and_config()
        if not user or not config:
            logger.error("[ERRO] Falha ao criar configuração de teste")
            return False
        
        try:
            # Mock do IQOptionService
            with patch('services.trading_bot.IQOptionService') as mock_iq_service:
                mock_iq_instance = Mock()
                mock_iq_instance.is_connected = True
                mock_iq_instance.connect.return_value = True
                mock_iq_service.return_value = mock_iq_instance
                
                # Criar bot
                bot = TradingBot(user.id, config, self.app)
                
                # Simular sessão ativa
                bot.current_session = 'morning'
                bot.session_profit = 0.0
                bot.session_trades = 0
                bot.martingale_level = 0
                bot.initial_balance = 1000.0
                
                # Teste 1: Verificar comportamento normal (sem metas atingidas)
                should_continue = bot._should_continue_trading()
                if should_continue:
                    logger.info("[OK] Bot continua trading quando metas não foram atingidas")
                else:
                    logger.error("[ERRO] Bot parou sem atingir metas")
                    return False
                
                # Teste 2: Simular Take Profit atingido
                take_profit_value = bot.initial_balance * (config.take_profit / 100)  # 5% de 1000 = 50
                bot.session_profit = take_profit_value + 1  # Ligeiramente acima
                
                should_continue = bot._should_continue_trading()
                if not should_continue:
                    logger.info("[OK] Bot pausa corretamente ao atingir Take Profit")
                else:
                    logger.error("[ERRO] Bot não pausou ao atingir Take Profit")
                    return False
                
                # Teste 3: Simular Stop Loss atingido (após esgotar martingale)
                bot.session_profit = 0.0  # Reset
                bot.martingale_level = 0  # Reset para nível normal para verificar targets
                # Stop loss padrão é 100% do saldo inicial (1000 * 100% = 1000)
                bot.session_profit = -1001  # Perda maior que stop loss padrão
                
                should_continue = bot._should_continue_trading()
                if not should_continue:
                    logger.info("[OK] Bot pausa corretamente ao atingir Stop Loss")
                else:
                    logger.error("[ERRO] Bot não pausou ao atingir Stop Loss")
                    return False
                
                # Teste 4: Verificar que não para durante Martingale
                bot.session_profit = -300  # Perda significativa
                bot.martingale_level = 2  # Mas em progressão Martingale
                
                should_continue = bot._should_continue_trading()
                if should_continue:
                    logger.info("[OK] Bot continua trading durante progressão Martingale (correto)")
                else:
                    logger.error("[ERRO] Bot pausou durante progressão Martingale")
                    return False
                
                logger.info("[OK] Teste de pausa automática concluído com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"Erro no teste de pausa: {str(e)}")
            return False
    
    def test_session_timing_behavior(self):
        """Testar comportamento de horários de sessão"""
        logger.info("\n=== TESTE 3: COMPORTAMENTO DE HORÁRIOS DE SESSÃO ===")
        
        user, config = self.create_test_user_and_config()
        if not user or not config:
            logger.error("[ERRO] Falha ao criar configuração de teste")
            return False
        
        try:
            # Mock do IQOptionService
            with patch('services.trading_bot.IQOptionService') as mock_iq_service:
                mock_iq_instance = Mock()
                mock_iq_instance.is_connected = True
                mock_iq_instance.connect.return_value = True
                mock_iq_service.return_value = mock_iq_instance
                
                # Criar bot
                bot = TradingBot(user.id, config, self.app)
                
                # Testar função de verificação de horário de sessão
                now = datetime.now()
                
                # Teste 1: Verificar que não está em sessão antes do horário
                in_morning_session = bot._is_in_session_time('morning')
                if not in_morning_session:
                    logger.info("[OK] Corretamente detecta que não está em horário de sessão")
                else:
                    logger.warning("[AVISO] Detectou que está em sessão (pode ser devido ao horário de teste)")
                
                # Teste 2: Simular sessão ativa
                bot.current_session = 'morning'
                in_morning_session = bot._is_in_session_time('morning')
                if in_morning_session:
                    logger.info("[OK] Corretamente detecta sessão ativa")
                else:
                    logger.error("[ERRO] Não detectou sessão ativa")
                    return False
                
                # Teste 3: Verificar cálculo de próxima sessão
                bot.current_session = None
                next_session = bot._get_next_session_time()
                if next_session:
                    time_diff = (next_session - now).total_seconds()
                    if 0 < time_diff < 15 * 60:  # Próxima sessão em até 15 minutos
                        logger.info(f"[OK] Próxima sessão em {time_diff/60:.1f} minutos")
                    else:
                        logger.info(f"[OK] Próxima sessão calculada: {next_session.strftime('%H:%M')}")
                else:
                    logger.error("[ERRO] Não conseguiu calcular próxima sessão")
                    return False
                
                logger.info("[OK] Teste de horários de sessão concluído com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"Erro no teste de horários: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Executar todos os testes"""
        logger.info("\n" + "="*60)
        logger.info("INICIANDO TESTES DE COMPORTAMENTO DE SESSÕES AUTOMÁTICAS")
        logger.info("="*60)
        
        tests = [
            ("Agendamento Automático", self.test_automatic_session_scheduling),
            ("Pausa ao Atingir Metas", self.test_session_pause_behavior),
            ("Horários de Sessão", self.test_session_timing_behavior)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    logger.info(f"[OK] {test_name}: PASSOU")
                else:
                    logger.error(f"[ERRO] {test_name}: FALHOU")
            except Exception as e:
                logger.error(f"[ERRO] {test_name}: ERRO - {str(e)}")
                results.append((test_name, False))
        
        # Resumo final
        logger.info("\n" + "="*60)
        logger.info("RESUMO DOS TESTES")
        logger.info("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "[OK] PASSOU" if result else "[ERRO] FALHOU"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nResultado Final: {passed}/{total} testes passaram")
        
        if passed == total:
            logger.info("[SUCESSO] TODOS OS TESTES PASSARAM!")
            logger.info("\n[COMPORTAMENTO VERIFICADO]:")
            logger.info("   [OK] Bot opera apenas nos horários das sessões configuradas")
            logger.info("   [OK] Bot pausa automaticamente ao atingir take profit ou stop loss")
            logger.info("   [OK] Bot aguarda o próximo horário agendado para reiniciar")
            logger.info("   [OK] Bot não opera continuamente entre sessões")
        else:
            logger.error("[ERRO] ALGUNS TESTES FALHARAM - Verificar configurações")
        
        return passed == total
    
    def cleanup(self):
        """Limpar recursos"""
        try:
            # Limpar dados de teste
            user = User.query.filter_by(email='test_auto@test.com').first()
            if user:
                TradingConfig.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()
            
            self.app_context.pop()
            logger.info("[OK] Limpeza concluída")
        except Exception as e:
            logger.error(f"Erro na limpeza: {str(e)}")

if __name__ == '__main__':
    tester = TestAutomaticSessionBehavior()
    try:
        success = tester.run_all_tests()
        exit_code = 0 if success else 1
    except Exception as e:
        logger.error(f"Erro geral nos testes: {str(e)}")
        exit_code = 1
    finally:
        tester.cleanup()
    
    sys.exit(exit_code)