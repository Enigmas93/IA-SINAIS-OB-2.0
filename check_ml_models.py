#!/usr/bin/env python3
"""
Script para verificar modelos ML no banco de dados
"""

from app import app, db
from models import MLModel, User

def check_ml_models():
    app.app_context().push()
    
    print("=== Verificando Modelos ML ===")
    models = MLModel.query.all()
    print(f"Total de modelos ML: {len(models)}")
    
    if models:
        for model in models:
            print(f"\n--- Modelo: {model.model_name} ---")
            print(f"ID: {model.id}")
            print(f"User ID: {getattr(model, 'user_id', 'N/A')}")
            print(f"Ativo: {getattr(model, 'is_active', 'N/A')}")
            print(f"Símbolo: {getattr(model, 'symbol', 'N/A')}")
            print(f"Tipo: {getattr(model, 'model_type', 'N/A')}")
            print(f"Criado em: {getattr(model, 'created_at', 'N/A')}")
    else:
        print("\n❌ Nenhum modelo ML encontrado no banco de dados")
        
    print("\n=== Verificando Usuários ===")
    users = User.query.all()
    for user in users:
        print(f"User ID: {user.id}, Email: {user.email}")

if __name__ == "__main__":
    check_ml_models()