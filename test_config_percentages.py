#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se as porcentagens de Take Profit e Stop Loss
estão sendo carregadas e salvas corretamente
"""

import requests
import json

def test_config_percentages():
    """Testa se as porcentagens estão funcionando corretamente"""
    
    print("\n" + "="*60)
    print("    TESTE DE PORCENTAGENS TAKE PROFIT E STOP LOSS")
    print("="*60)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. Fazer login
        print("\n1. Fazendo login...")
        login_data = {"email": "sk8gabriel77@hotmail.com", "password": "123456"}
        
        login_response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.status_code}")
            return False
            
        token = login_response.json().get('token')
        if not token:
            print("❌ Token não encontrado na resposta")
            return False
            
        print("✅ Login realizado com sucesso")
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Obter configuração atual
        print("\n2. Obtendo configuração atual...")
        config_response = requests.get(f"{base_url}/api/config", headers=headers)
        
        if config_response.status_code != 200:
            print(f"❌ Erro ao obter configuração: {config_response.status_code}")
            print(f"Resposta: {config_response.text}")
            return False
            
        current_config = config_response.json()
        print("✅ Configuração obtida com sucesso")
        print(f"Take Profit atual: {current_config.get('take_profit', 'N/A')}%")
        print(f"Stop Loss atual: {current_config.get('stop_loss', 'N/A')}%")
        
        # 3. Testar salvamento de novas porcentagens
        print("\n3. Testando salvamento de novas porcentagens...")
        
        # Usar a configuração atual como base e modificar apenas as porcentagens
        test_config = current_config.copy()
        test_config['take_profit'] = 85.0  # Teste com 85%
        test_config['stop_loss'] = 25.0    # Teste com 25%
        
        save_response = requests.post(f"{base_url}/api/config", 
                                    json=test_config, 
                                    headers=headers)
        
        if save_response.status_code != 200:
            print(f"❌ Erro ao salvar configuração: {save_response.status_code}")
            print(f"Resposta: {save_response.text}")
            return False
            
        print("✅ Configuração salva com sucesso")
        
        # 4. Verificar se as porcentagens foram salvas corretamente
        print("\n4. Verificando se as porcentagens foram salvas...")
        
        verify_response = requests.get(f"{base_url}/api/config", headers=headers)
        
        if verify_response.status_code != 200:
            print(f"❌ Erro ao verificar configuração: {verify_response.status_code}")
            return False
            
        saved_config = verify_response.json()
        
        saved_take_profit = saved_config.get('take_profit')
        saved_stop_loss = saved_config.get('stop_loss')
        
        print(f"Take Profit salvo: {saved_take_profit}%")
        print(f"Stop Loss salvo: {saved_stop_loss}%")
        
        # 5. Validar se os valores estão corretos
        success = True
        
        if saved_take_profit != 85.0:
            print(f"❌ Take Profit incorreto! Esperado: 85.0, Obtido: {saved_take_profit}")
            success = False
        else:
            print("✅ Take Profit correto (85.0%)")
            
        if saved_stop_loss != 25.0:
            print(f"❌ Stop Loss incorreto! Esperado: 25.0, Obtido: {saved_stop_loss}")
            success = False
        else:
            print("✅ Stop Loss correto (25.0%)")
            
        # 6. Testar com outros valores
        print("\n5. Testando com outros valores...")
        
        test_config2 = saved_config.copy()
        test_config2['take_profit'] = 90.0
        test_config2['stop_loss'] = 15.0
        
        save_response2 = requests.post(f"{base_url}/api/config", 
                                     json=test_config2, 
                                     headers=headers)
        
        if save_response2.status_code == 200:
            verify_response2 = requests.get(f"{base_url}/api/config", headers=headers)
            if verify_response2.status_code == 200:
                saved_config2 = verify_response2.json()
                
                if (saved_config2.get('take_profit') == 90.0 and 
                    saved_config2.get('stop_loss') == 15.0):
                    print("✅ Segundo teste de porcentagens passou")
                else:
                    print(f"❌ Segundo teste falhou: TP={saved_config2.get('take_profit')}, SL={saved_config2.get('stop_loss')}")
                    success = False
            else:
                print("❌ Erro ao verificar segunda configuração")
                success = False
        else:
            print("❌ Erro ao salvar segunda configuração")
            success = False
            
        print("\n" + "="*60)
        if success:
            print("✅ TODOS OS TESTES PASSARAM - PORCENTAGENS FUNCIONANDO CORRETAMENTE")
        else:
            print("❌ ALGUNS TESTES FALHARAM - PROBLEMA COM PORCENTAGENS DETECTADO")
        print("="*60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {str(e)}")
        return False

if __name__ == "__main__":
    test_config_percentages()