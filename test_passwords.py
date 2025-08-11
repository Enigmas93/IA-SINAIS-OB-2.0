#!/usr/bin/env python3
"""
Script para testar senhas dos usuários
"""

from app import app, db
from models import User
from werkzeug.security import check_password_hash

def test_user_passwords():
    app.app_context().push()
    
    users = User.query.all()
    
    for user in users:
        print(f"\n=== Usuário: {user.email} ===")
        print(f"Hash da senha: {user.password_hash[:50]}...")
        
        # Testar senhas comuns
        passwords_to_test = ['123456', 'test', 'password', 'admin', '123', 'senha']
        
        for password in passwords_to_test:
            is_valid = check_password_hash(user.password_hash, password)
            status = "✅ VÁLIDA" if is_valid else "❌ Inválida"
            print(f"Senha '{password}': {status}")
            
            if is_valid:
                print(f"\n🎉 SENHA ENCONTRADA para {user.email}: '{password}'")
                break

if __name__ == "__main__":
    test_user_passwords()