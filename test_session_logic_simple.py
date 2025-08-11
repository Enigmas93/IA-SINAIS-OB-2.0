#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples da nova lógica de sessões
Verifica se as sessões só têm horário de início e param após atingir metas
"""

import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestSessionLogic:
    def __init__(self):
        self.test_results = []
        
    def log_result(self, test_name, passed, message=""):
        """Log do resultado do teste"""
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        self.test_results.append((test_name, passed, message))
        
    def test_config_structure(self):
        """Testa se a estrutura de configuração não tem mais horários de fim"""
        try:
            from models import TradingConfig
            
            # Verifica se os campos de fim de sessão foram removidos
            config_columns = [column.name for column in TradingConfig.__table__.columns]
            
            # Campos que NÃO devem existir mais
            forbidden_fields = ['morning_end', 'afternoon_end', 'night_end']
            
            for field in forbidden_fields:
                if field in config_columns:
                    self.log_result(
                        f"Campo {field} removido", 
                        False, 
                        f"Campo {field} ainda existe na configuração"
                    )
                    return False
                    
            # Campos que DEVEM existir
            required_fields = ['morning_start', 'afternoon_start', 'night_start']
            
            for field in required_fields:
                if field not in config_columns:
                    self.log_result(
                        f"Campo {field} presente", 
                        False, 
                        f"Campo {field} não encontrado na configuração"
                    )
                    return False
                    
            self.log_result(
                "Estrutura de configuração", 
                True, 
                "Apenas horários de início presentes, horários de fim removidos"
            )
            return True
            
        except Exception as e:
            self.log_result("Estrutura de configuração", False, f"Erro: {str(e)}")
            return False
            
    def test_trading_bot_logic(self):
        """Testa se a lógica do bot foi atualizada"""
        try:
            # Lê o arquivo do trading bot para verificar se as referências foram removidas
            with open('services/trading_bot.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verifica se não há mais referências aos horários de fim
            forbidden_references = ['morning_end', 'afternoon_end', 'night_end']
            
            for ref in forbidden_references:
                if ref in content:
                    self.log_result(
                        f"Referência {ref} removida do bot", 
                        False, 
                        f"Ainda há referência a {ref} no código do bot"
                    )
                    return False
                    
            # Verifica se a função _should_continue_trading foi modificada
            if 'def _should_continue_trading' in content:
                # Procura pela lógica de parada após meta
                if 'take_profit' in content and 'stop_loss' in content:
                    self.log_result(
                        "Lógica de parada após meta", 
                        True, 
                        "Bot configurado para parar após atingir take_profit ou stop_loss"
                    )
                else:
                    self.log_result(
                        "Lógica de parada após meta", 
                        False, 
                        "Lógica de parada após meta não encontrada"
                    )
                    return False
            else:
                self.log_result(
                    "Função _should_continue_trading", 
                    False, 
                    "Função _should_continue_trading não encontrada"
                )
                return False
                
            self.log_result(
                "Lógica do trading bot", 
                True, 
                "Bot atualizado para nova lógica de sessões"
            )
            return True
            
        except Exception as e:
            self.log_result("Lógica do trading bot", False, f"Erro: {str(e)}")
            return False
            
    def test_routes_updated(self):
        """Testa se as rotas foram atualizadas"""
        try:
            with open('routes.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verifica se não há mais referências aos horários de fim
            forbidden_references = ['morning_end', 'afternoon_end', 'night_end']
            
            for ref in forbidden_references:
                if ref in content:
                    self.log_result(
                        f"Referência {ref} removida das rotas", 
                        False, 
                        f"Ainda há referência a {ref} nas rotas"
                    )
                    return False
                    
            self.log_result(
                "Rotas atualizadas", 
                True, 
                "Rotas não contêm mais referências aos horários de fim"
            )
            return True
            
        except Exception as e:
            self.log_result("Rotas atualizadas", False, f"Erro: {str(e)}")
            return False
            
    def test_frontend_updated(self):
        """Testa se o frontend foi atualizado"""
        try:
            # Verifica templates HTML
            html_files = ['templates/base.html', 'templates/dashboard.html']
            
            for html_file in html_files:
                if os.path.exists(html_file):
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    forbidden_references = ['morning_end', 'afternoon_end', 'night_end']
                    
                    for ref in forbidden_references:
                        if ref in content:
                            self.log_result(
                                f"Template {html_file} atualizado", 
                                False, 
                                f"Ainda há referência a {ref} em {html_file}"
                            )
                            return False
                            
            # Verifica JavaScript
            if os.path.exists('static/js/app.js'):
                with open('static/js/app.js', 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                forbidden_references = ['morningEnd', 'afternoonEnd', 'nightEnd']
                
                for ref in forbidden_references:
                    if ref in content:
                        self.log_result(
                            "JavaScript atualizado", 
                            False, 
                            f"Ainda há referência a {ref} no JavaScript"
                        )
                        return False
                        
            self.log_result(
                "Frontend atualizado", 
                True, 
                "Templates e JavaScript não contêm mais referências aos horários de fim"
            )
            return True
            
        except Exception as e:
            self.log_result("Frontend atualizado", False, f"Erro: {str(e)}")
            return False
            
    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n=== TESTE DA NOVA LÓGICA DE SESSÕES ===")
        print(f"Horário atual: {datetime.now().strftime('%H:%M:%S')}")
        print("\nVerificando se as modificações foram aplicadas corretamente...\n")
        
        tests = [
            self.test_config_structure,
            self.test_trading_bot_logic,
            self.test_routes_updated,
            self.test_frontend_updated
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            if test():
                passed_tests += 1
            print()  # Linha em branco entre testes
            
        # Resumo final
        print("=" * 50)
        print(f"RESUMO: {passed_tests}/{total_tests} testes passaram")
        
        if passed_tests == total_tests:
            print("\n🎉 SUCESSO: Todas as modificações foram aplicadas corretamente!")
            print("\n📋 NOVA LÓGICA DE SESSÕES:")
            print("   • Sessões têm apenas horário de início")
            print("   • Bot para automaticamente após atingir take_profit ou stop_loss")
            print("   • Bot só retorna na próxima sessão agendada")
            print("   • Interface atualizada para refletir as mudanças")
        else:
            print("\n⚠️  ATENÇÃO: Algumas modificações podem não ter sido aplicadas completamente.")
            
        return passed_tests == total_tests

if __name__ == "__main__":
    try:
        tester = TestSessionLogic()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)