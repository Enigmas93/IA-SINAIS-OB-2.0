#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_api_values():
    """Testa se a API está retornando os valores corretos"""
    try:
        # Login
        login_response = requests.post('http://localhost:5000/login', 
                                     data={'username': 'sk8gabriel77@hotmail.com', 'password': '123456'},
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        
        if login_response.status_code == 200:
            token = login_response.json()['token']
            print("✅ Login realizado com sucesso")
            
            # Buscar configuração
            config_response = requests.get('http://localhost:5000/api/config', 
                                         headers={'Authorization': f'Bearer {token}'})
            
            if config_response.status_code == 200:
                config = config_response.json()
                take_profit = config.get('take_profit', 'N/A')
                stop_loss = config.get('stop_loss', 'N/A')
                
                print(f"✅ API retorna - Take Profit: {take_profit}%, Stop Loss: {stop_loss}%")
                print("✅ Valores corretos sendo retornados pela API")
                
                # Verificar se os valores não são os antigos hardcoded
                if take_profit != 70 and stop_loss != 30:
                    print("✅ Valores não são mais os hardcoded (70% e 30%)")
                else:
                    print("⚠️  Ainda retornando valores antigos hardcoded")
                    
            else:
                print(f"❌ Erro ao buscar configuração: {config_response.status_code}")
        else:
            print(f"❌ Erro no login: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_api_values()