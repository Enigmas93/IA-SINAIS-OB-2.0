#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, TradingConfig
from datetime import datetime

print("=== VERIFICAÇÃO DA CONFIGURAÇÃO DO USUÁRIO ===")
print(f"Timestamp: {datetime.now()}")
print()

with app.app_context():
    # Get all users
    users = User.query.all()
    print(f"Total de usuários: {len(users)}")
    
    for user in users:
        print(f"\n--- Usuário: {user.name} (ID: {user.id}) ---")
        print(f"Email: {user.email}")
        
        # Get user config
        config = TradingConfig.query.filter_by(user_id=user.id).first()
        
        if config:
            print("\n=== CONFIGURAÇÃO ENCONTRADA ===")
            print(f"Auto mode: {getattr(config, 'auto_mode', False)}")
            print(f"Continuous mode: {getattr(config, 'continuous_mode', False)}")
            print(f"\nSessões habilitadas:")
            print(f"  - Manhã: {getattr(config, 'morning_enabled', False)} ({getattr(config, 'morning_start', 'N/A')})")
            print(f"  - Tarde: {getattr(config, 'afternoon_enabled', False)} ({getattr(config, 'afternoon_start', 'N/A')})")
            print(f"  - Noite: {getattr(config, 'night_enabled', False)} ({getattr(config, 'night_start', 'N/A')})")
            print(f"\nOutras configurações:")
            print(f"  - Asset: {config.asset}")
            print(f"  - Trade amount: {config.trade_amount}")
            print(f"  - Take profit: {config.take_profit}%")
            print(f"  - Stop loss: Martingale 3 levels (sem percentual)")
            print(f"  - Auto restart: {getattr(config, 'auto_restart', False)}")
        else:
            print("\n=== NENHUMA CONFIGURAÇÃO ENCONTRADA ===")
            print("Usuário não possui configuração de trading")
    
    if not users:
        print("\n=== NENHUM USUÁRIO ENCONTRADO ===")
        print("Banco de dados não possui usuários cadastrados")