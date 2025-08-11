#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o salvamento de configurações
"""

import requests
import json
from datetime import datetime

def register_test_user(base_url):
    """Registra um usuário de teste"""
    register_data = {
        "name": "Usuário Teste",
        "email": "teste@teste.com",
        "password": "teste123",
        "password_confirm": "teste123",
        "iq_email": "teste@iq.com",
        "iq_password": "senha_iq"
    }
    
    print("Registrando usuário de teste...")
    try:
        register_response = requests.post(f"{base_url}/api/auth/register", json=register_data)
        print(f"Status do registro: {register_response.status_code}")
        
        if register_response.status_code in [200, 201]:
            print("✅ Usuário registrado com sucesso!")
            return True
        elif register_response.status_code == 400:
            response_data = register_response.json()
            if "já cadastrado" in response_data.get('message', ''):
                print("ℹ️ Usuário já existe, continuando...")
                return True
            else:
                print(f"❌ Erro no registro: {response_data}")
                return False
        else:
            print(f"❌ Erro no registro: {register_response.text}")
            return False
    except Exception as e:
        print(f"Erro na requisição de registro: {e}")
        return False

def test_save_config():
    """Testa o salvamento de configurações"""
    
    # URL base da aplicação
    base_url = "http://localhost:5000"
    
    # Primeiro, registrar usuário de teste
    if not register_test_user(base_url):
        print("❌ Falha ao registrar usuário de teste")
        return
    
    # Fazer login para obter o token
    login_data = {
        "email": "teste@teste.com",
        "password": "teste123"
    }
    
    print("\n1. Fazendo login...")
    try:
        login_response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        print(f"Status do login: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get('token') or login_result.get('access_token')
            print(f"Token obtido: {token[:20] if token else 'None'}...")
            
            if not token:
                print("❌ Token não encontrado na resposta")
                print(f"Resposta completa: {login_result}")
                return
        else:
            print(f"❌ Erro no login: {login_response.text}")
            return
    except Exception as e:
        print(f"Erro na requisição de login: {e}")
        return
    
    # Configuração de teste
    config_data = {
        "asset": "EURUSD",
        "trade_amount": 10.0,
        "use_balance_percentage": True,
        "balance_percentage": 2.0,
        "take_profit": 70.0,
        "stop_loss": 30.0,
        "martingale_enabled": True,
        "max_martingale_levels": 3,
        "morning_start": "10:00",
        "morning_end": "12:00",
        "afternoon_start": "14:00",
        "afternoon_end": "17:00",
        "night_start": "19:00",
        "night_end": "22:00",
        "morning_enabled": True,
        "afternoon_enabled": True,
        "night_enabled": False,
        "continuous_mode": True,
        "auto_restart": True,
        "keep_connection": True,
        "operation_mode": "manual",
        "strategy_mode": "intermediario",
        "min_signal_score": 75.0,
        "timeframe": "1m"
    }
    
    # Headers com autorização
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    print("\n2. Testando salvamento de configurações...")
    print(f"Dados a serem enviados: {json.dumps(config_data, indent=2)}")
    
    try:
        # Fazer requisição POST para salvar configurações
        save_response = requests.post(f"{base_url}/api/config", json=config_data, headers=headers)
        print(f"\nStatus da resposta: {save_response.status_code}")
        print(f"Headers da resposta: {dict(save_response.headers)}")
        
        try:
            response_data = save_response.json()
            print(f"Resposta JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Resposta não é JSON: {save_response.text}")
        
        if save_response.status_code == 200:
            print("✅ Configurações salvas com sucesso!")
        else:
            print(f"❌ Erro ao salvar configurações: {save_response.status_code}")
            return
            
    except Exception as e:
        print(f"Erro na requisição de salvamento: {e}")
        return
    
    # Verificar se as configurações foram salvas corretamente
    print("\n3. Verificando configurações salvas...")
    try:
        get_response = requests.get(f"{base_url}/api/config", headers=headers)
        print(f"Status da verificação: {get_response.status_code}")
        
        if get_response.status_code == 200:
            saved_config = get_response.json()
            print(f"Configurações recuperadas: {json.dumps(saved_config, indent=2)}")
            print("✅ Configurações verificadas com sucesso!")
            
            # Verificar se os valores foram salvos corretamente
            print("\n4. Validando valores salvos...")
            validation_errors = []
            
            for key, expected_value in config_data.items():
                if key in saved_config:
                    saved_value = saved_config[key]
                    if saved_value != expected_value:
                        validation_errors.append(f"{key}: esperado {expected_value}, obtido {saved_value}")
                else:
                    validation_errors.append(f"{key}: campo não encontrado na resposta")
            
            if validation_errors:
                print("❌ Erros de validação encontrados:")
                for error in validation_errors:
                    print(f"  - {error}")
            else:
                print("✅ Todos os valores foram salvos corretamente!")
                
        else:
            print(f"❌ Erro ao recuperar configurações: {get_response.status_code}")
            print(f"Resposta: {get_response.text}")
            
    except Exception as e:
        print(f"Erro na verificação: {e}")

if __name__ == "__main__":
    print("=== TESTE DE SALVAMENTO DE CONFIGURAÇÕES ===")
    print(f"Iniciado em: {datetime.now()}")
    print("="*50)
    
    test_save_config()
    
    print("\n" + "="*50)
    print("Teste concluído!")