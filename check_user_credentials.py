#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar as credenciais do usuário no banco de dados
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import User, TradingConfig

def check_user_credentials():
    """Verificar credenciais dos usuários"""
    app = create_app()
    
    with app.app_context():
        print("=== VERIFICAÇÃO DAS CREDENCIAIS DOS USUÁRIOS ===")
        print(f"Timestamp: {datetime.now()}")
        
        users = User.query.all()
        print(f"\nTotal de usuários: {len(users)}")
        
        for user in users:
            print(f"\n--- Usuário: {user.name} (ID: {user.id}) ---")
            print(f"Email: {user.email}")
            print(f"Password hash: {user.password_hash[:20]}...")
            print(f"IQ Email: {user.iq_email}")
            print(f"IQ Password: {user.iq_password}")
            print(f"Account Type: {user.account_type}")
            
            # Para teste, vamos tentar algumas senhas comuns
            from werkzeug.security import check_password_hash
            
            common_passwords = ['123456', 'password', 'admin', 'gabriel', 'test']
            
            print("\nTestando senhas comuns:")
            for pwd in common_passwords:
                if check_password_hash(user.password_hash, pwd):
                    print(f"✓ Senha encontrada: {pwd}")
                    break
            else:
                print("✗ Nenhuma senha comum funcionou")
                print("Sugestão: Use a interface web para redefinir a senha")

if __name__ == "__main__":
    check_user_credentials()