#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste real do comportamento do bot em modo automático
"""

import sys
import os
import requests
import json
import time
from datetime import datetime

# Configuração da API
API_BASE = "http://localhost:5000/api"

def get_auth_token():
    """Obter token de autenticação"""
    login_data = {
        "email": "sk8gabriel77@hotmail.com",
        "password": "123456"
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        
        print(f"Status do login: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                token = data.get('data', {}).get('token')
                if token:
                    print(f"✓ Login realizado com sucesso!")
                    return token
                else:
                    print(f"Token não encontrado na resposta")
                    return None
        else:
            print(f"Erro no login: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exceção durante login: {e}")
        return None

def get_bot_status(token):
    """Verificar status do bot"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{API_BASE}/bot/status", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao verificar status: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao verificar status: {e}")
        return None

def start_bot(token):
    """Iniciar o bot"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{API_BASE}/bot/start", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao iniciar bot: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao iniciar bot: {e}")
        return None

def stop_bot(token):
    """Parar o bot"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{API_BASE}/bot/stop", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao parar bot: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao parar bot: {e}")
        return None

def get_user_config(headers):
    """Obter configuração do usuário"""
    try:
        response = requests.get(f"{API_BASE}/config", headers=headers)
        
        if response.status_code == 200:
            return response.json().get('data', {})
        else:
            print(f"Erro ao obter config: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao obter configuração: {e}")
        return None

def update_config_to_auto_mode(headers):
    """Atualizar configuração para modo automático"""
    config_data = {
        "operation_mode": "auto",
        "auto_mode": True,
        "continuous_mode": True,
        "auto_restart": True,
        "morning_enabled": True,
        "morning_start": "08:30",
        "afternoon_enabled": True,
        "afternoon_start": "14:30",
        "night_enabled": True,
        "night_start": "19:30"
    }
    
    try:
        response = requests.post(f"{API_BASE}/config", json=config_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ Configuração atualizada para modo automático!")
                return True
            else:
                print(f"Erro ao atualizar configuração: {data.get('message', 'Erro desconhecido')}")
                return False
        else:
            print(f"Erro HTTP ao atualizar configuração: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exceção ao atualizar configuração: {e}")
        return False

def main():
    print("=" * 80)
    print("TESTE REAL: Comportamento do Bot em Modo Automático")
    print("=" * 80)
    print(f"Horário atual: {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. Fazer login
    print("\n1. Fazendo login...")
    token = get_auth_token()
    if not token:
        print("Falha no login. Encerrando teste.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Atualizar configuração para modo automático
    print("\n2. Ativando modo automático...")
    if not update_config_to_auto_mode(headers):
        print("Falha ao ativar modo automático. Encerrando teste.")
        return
    
    # 3. Verificar configuração do usuário
    print("\n3. Verificando configuração do usuário...")
    config = get_user_config(headers)
    if config:
        print(f"Modo automático: {config.get('auto_mode', False)}")
        print(f"Sessão manhã: {config.get('morning_enabled', False)} - {config.get('morning_start', 'N/A')}")
        print(f"Sessão tarde: {config.get('afternoon_enabled', False)} - {config.get('afternoon_start', 'N/A')}")
        print(f"Sessão noite: {config.get('night_enabled', False)} - {config.get('night_start', 'N/A')}")
    
    # 4. Verificar status inicial do bot
    print("\n4. Verificando status inicial do bot...")
    status = get_bot_status(token)
    if status:
        print(f"Bot está rodando: {status.get('is_running', False)}")
        print(f"Sessão atual: {status.get('current_session', 'Nenhuma')}")
    
    # 5. Iniciar o bot
    print("\n5. Iniciando o bot...")
    start_result = start_bot(token)
    if start_result:
        print("Bot iniciado com sucesso!")
        print(f"Mensagem: {start_result.get('message', '')}")
    else:
        print("Falha ao iniciar bot. Encerrando teste.")
        return
    
    # 6. Aguardar um pouco e verificar status
    print("\n6. Aguardando 3 segundos e verificando status...")
    time.sleep(3)
    
    status = get_bot_status(token)
    if status:
        print(f"Bot está rodando: {status.get('is_running', False)}")
        print(f"Sessão atual: {status.get('current_session', 'Nenhuma')}")
        print(f"Modo automático: {status.get('auto_mode', False)}")
        print(f"Próxima sessão: {status.get('next_session_time', 'N/A')}")
        
        # Verificar se o bot NÃO iniciou trading imediatamente em modo automático
        if config and config.get('auto_mode', False):
            if status.get('current_session') is None:
                print("✓ SUCESSO: Bot em modo automático não iniciou trading imediatamente!")
                print("✓ Bot está aguardando o próximo horário de sessão programado.")
            else:
                print("✗ PROBLEMA: Bot iniciou trading imediatamente mesmo em modo automático.")
        else:
            print("ℹ Bot não está em modo automático.")
    
    # 7. Parar o bot
    print("\n7. Parando o bot...")
    stop_result = stop_bot(token)
    if stop_result:
        print("Bot parado com sucesso!")
        print(f"Mensagem: {stop_result.get('message', '')}")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    main()