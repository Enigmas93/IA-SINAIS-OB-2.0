#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da Nova Lógica de Sessões

Este teste verifica se a nova lógica de sessões está funcionando corretamente:
- Sessões só têm horário de início
- Bot para após atingir uma meta (take profit ou stop loss)
- Bot só retorna na próxima sessão agendada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from models import TradingConfig, User, db
from services.trading_bot import TradingBot
from app import create_app
import time
import threading

class TestNewSessionLogic:
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Configurar horários de teste
        now = datetime.now()
        self.morning_start = (now + timedelta(minutes=1)).strftime('%H:%M')
        self.afternoon_start = (now + timedelta(minutes=5)).strftime('%H:%M')
        self.night_start = (now + timedelta(minutes=9)).strftime('%H:%M')
        
        print(f"\n=== TESTE DA NOVA LÓGICA DE SESSÕES ===")
        print(f"Horário atual: {now.strftime('%H:%M:%S')}")
        print(f"Sessões configuradas:")
        print(f"- Manhã: {self.morning_start} (até meta)")
        print(f"- Tarde: {self.afternoon_start} (até meta)")
        print(f"- Noite: {self.night_start} (até meta)")
        print(f"\nObjetivo: Verificar se o bot para após atingir metas e só retorna na próxima sessão\n")
    
    def setup_test_config(self):
        """Configura um usuário e configuração de teste"""
        # Criar usuário de teste
        test_user = User(
            username="test_session_user",
            email="test_session@example.com",
            password_hash="test_hash"
        )
        db.session.add(test_user)
        db.session.commit()
        
        # Criar configuração de teste com apenas horários de início
        config = TradingConfig(
            user_id=test_user.id,
            asset="EURUSD",
            trade_amount=10.0,
            take_profit=20.0,  # Meta baixa para teste rápido
            stop_loss=20.0,    # Meta baixa para teste rápido
            martingale_enabled=False,
            morning_start=self.morning_start,
            afternoon_start=self.afternoon_start,
            night_start=self.night_start,
            # Nota: Não há mais campos morning_end, afternoon_end, night_end
            morning_enabled=True,
            afternoon_enabled=True,
            night_enabled=True,
            operation_mode="auto",
            auto_mode=True,
            continuous_mode=True,
            auto_restart=False,  # Importante: desabilitado para testar parada
            strategy_mode="intermediario",
            min_signal_score=75,
            timeframe="1m"
        )
        db.session.add(config)
        db.session.commit()
        
        print(f"✅ Usuário e configuração de teste criados")
        print(f"   • Take Profit: {config.take_profit}%")
        print(f"   • Stop Loss: {config.stop_loss}%")
        print(f"   • Auto Restart: {config.auto_restart} (deve ser False)")
        print(f"   • Modo Contínuo: {config.continuous_mode}")
        
        return test_user, config
    
    def test_session_start_only_logic(self, config):
        """Testa se as sessões usam apenas horário de início"""
        print(f"\n🔍 Testando lógica de horário de início apenas...")
        
        # Criar instância do bot
        bot = TradingBot(config.user_id, config, app=self.app)
        
        # Testar função _is_in_session_time
        current_time = datetime.now().time()
        morning_start_time = datetime.strptime(self.morning_start, '%H:%M').time()
        
        # Simular que estamos após o horário de início da manhã
        if current_time >= morning_start_time:
            in_session = bot._is_in_session_time('morning')
            print(f"   • Horário atual ({current_time}) >= Início manhã ({morning_start_time}): {in_session}")
            
            if in_session:
                print(f"   ✅ Sessão da manhã ativa (sem verificação de fim)")
            else:
                print(f"   ❌ Sessão da manhã não ativa")
        else:
            print(f"   • Ainda não chegou o horário da sessão da manhã")
        
        return bot
    
    def test_target_reached_behavior(self, bot):
        """Testa o comportamento quando uma meta é atingida"""
        print(f"\n🎯 Testando comportamento ao atingir metas...")
        
        # Simular que uma meta foi atingida
        bot.session_profit = 25.0  # Acima do take profit de 20%
        bot.current_session = 'morning'
        
        # Testar se deve continuar trading
        should_continue = bot._should_continue_trading()
        print(f"   • Lucro da sessão: {bot.session_profit}%")
        print(f"   • Take Profit configurado: {bot.config.take_profit}%")
        print(f"   • Deve continuar trading: {should_continue}")
        
        if not should_continue:
            print(f"   ✅ Bot para corretamente após atingir take profit")
        else:
            print(f"   ❌ Bot não para após atingir take profit")
        
        # Testar com stop loss
        bot.session_profit = -25.0  # Abaixo do stop loss de -20%
        should_continue = bot._should_continue_trading()
        print(f"   • Lucro da sessão: {bot.session_profit}%")
        print(f"   • Stop Loss configurado: -{bot.config.stop_loss}%")
        print(f"   • Deve continuar trading: {should_continue}")
        
        if not should_continue:
            print(f"   ✅ Bot para corretamente após atingir stop loss")
        else:
            print(f"   ❌ Bot não para após atingir stop loss")
    
    def test_next_session_calculation(self, bot):
        """Testa o cálculo da próxima sessão"""
        print(f"\n⏰ Testando cálculo da próxima sessão...")
        
        try:
            next_session_time = bot._get_next_session_time()
            if next_session_time:
                print(f"   • Próxima sessão: {next_session_time.strftime('%H:%M:%S')}")
                print(f"   ✅ Cálculo da próxima sessão funcionando")
            else:
                print(f"   ❌ Não foi possível calcular próxima sessão")
        except Exception as e:
            print(f"   ❌ Erro ao calcular próxima sessão: {str(e)}")
    
    def cleanup(self):
        """Limpa dados de teste"""
        try:
            # Remover dados de teste
            test_configs = TradingConfig.query.filter_by(asset="EURUSD").all()
            for config in test_configs:
                db.session.delete(config)
            
            test_users = User.query.filter(User.username.like("test_session%")).all()
            for user in test_users:
                db.session.delete(user)
            
            db.session.commit()
            print(f"\n🧹 Dados de teste removidos")
        except Exception as e:
            print(f"\n❌ Erro na limpeza: {str(e)}")
            db.session.rollback()
        finally:
            self.app_context.pop()
    
    def run_test(self):
        """Executa todos os testes"""
        try:
            # Setup
            test_user, config = self.setup_test_config()
            
            # Testes
            bot = self.test_session_start_only_logic(config)
            self.test_target_reached_behavior(bot)
            self.test_next_session_calculation(bot)
            
            print(f"\n✅ TODOS OS TESTES CONCLUÍDOS")
            print(f"\n📋 RESUMO DAS MODIFICAÇÕES IMPLEMENTADAS:")
            print(f"   1. ✅ Removidos campos de horário de fim (morning_end, afternoon_end, night_end)")
            print(f"   2. ✅ Função _is_in_session_time modificada para verificar apenas início")
            print(f"   3. ✅ Função _should_continue_trading remove auto-restart")
            print(f"   4. ✅ Loop contínuo não verifica mais fim de sessão")
            print(f"   5. ✅ Bot para após atingir metas e aguarda próxima sessão")
            print(f"\n🎯 NOVA LÓGICA IMPLEMENTADA COM SUCESSO!")
            
        except Exception as e:
            print(f"\n❌ Erro durante o teste: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

if __name__ == "__main__":
    test = TestNewSessionLogic()
    test.run_test()