#!/usr/bin/env python3
"""
Script para testar o login e verificar se os dados de ML estão sendo carregados corretamente
"""

import requests
import json
from datetime import datetime

def test_login_and_ml():
    base_url = "http://localhost:5000"
    
    # Dados de login (usando um usuário existente)
    login_data = {
        "email": "test@test.com",
        "password": "123456",
        "account_type": "PRACTICE"
    }
    
    print("=== Testando Login ===")
    
    # Fazer login
    login_response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    print(f"Status do login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Erro no login: {login_response.text}")
        return
    
    login_result = login_response.json()
    token = login_result.get('token')
    
    if not token:
        print("Token não encontrado na resposta do login")
        return
    
    print(f"Login bem-sucedido! Token: {token[:50]}...")
    
    # Headers para as próximas requisições
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("\n=== Testando API ML Status ===")
    
    # Testar ML Status
    status_response = requests.get(f"{base_url}/api/ml/status", headers=headers)
    print(f"Status ML Status: {status_response.status_code}")
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"ML Status: {json.dumps(status_data, indent=2)}")
    else:
        print(f"Erro ML Status: {status_response.text}")
    
    print("\n=== Testando API ML Models ===")
    
    # Testar ML Models
    models_response = requests.get(f"{base_url}/api/ml/models", headers=headers)
    print(f"Status ML Models: {models_response.status_code}")
    
    if models_response.status_code == 200:
        models_data = models_response.json()
        print(f"ML Models: {json.dumps(models_data, indent=2)}")
        
        # Verificar se há modelos
        models = models_data.get('models', [])
        if models:
            print(f"\n✅ Encontrados {len(models)} modelo(s) ML:")
            for model in models:
                print(f"  - {model['asset']}: {model['accuracy']*100:.1f}% acurácia")
        else:
            print("\n❌ Nenhum modelo ML encontrado")
    else:
        print(f"Erro ML Models: {models_response.text}")
    
    print("\n=== Testando Dashboard ===")
    
    # Testar se o dashboard carrega
    dashboard_response = requests.get(f"{base_url}/dashboard")
    print(f"Status Dashboard: {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 200:
        print("✅ Dashboard carregou com sucesso")
    else:
        print(f"❌ Erro no Dashboard: {dashboard_response.text}")

if __name__ == "__main__":
    test_login_and_ml()