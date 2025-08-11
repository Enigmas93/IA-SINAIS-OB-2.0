#!/usr/bin/env python3
"""
Script para corrigir o problema de continuous_mode e auto_restart
que estava causando o bot a continuar operando após atingir stop loss.

Este script atualiza todas as configurações existentes no banco de dados
para desabilitar continuous_mode e auto_restart por padrão.
"""

import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, TradingConfig
from config import Config

def create_app():
    """Criar aplicação Flask para acesso ao banco de dados"""
    app = Flask(__name__)
    
    # Configurar banco de dados diretamente
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading_bot.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def fix_continuous_mode_settings():
    """Corrigir configurações de continuous_mode e auto_restart"""
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar todas as configurações que têm continuous_mode ou auto_restart ativados
            configs_to_update = TradingConfig.query.filter(
                (TradingConfig.continuous_mode == True) | 
                (TradingConfig.auto_restart == True)
            ).all()
            
            print(f"Encontradas {len(configs_to_update)} configurações para atualizar...")
            
            updated_count = 0
            for config in configs_to_update:
                print(f"Atualizando configuração do usuário {config.user_id}:")
                print(f"  - continuous_mode: {config.continuous_mode} -> False")
                print(f"  - auto_restart: {config.auto_restart} -> False")
                
                # Atualizar as configurações
                config.continuous_mode = False
                config.auto_restart = False
                updated_count += 1
            
            # Salvar as alterações
            if updated_count > 0:
                db.session.commit()
                print(f"\n✅ {updated_count} configurações atualizadas com sucesso!")
                print("\n🔧 CORREÇÃO APLICADA:")
                print("   - continuous_mode = False (bot para após atingir metas)")
                print("   - auto_restart = False (bot não reinicia automaticamente)")
                print("\n📋 COMPORTAMENTO ESPERADO:")
                print("   - Quando take profit for atingido: bot para")
                print("   - Quando stop loss for atingido (3º martingale): bot para")
                print("   - Bot não continua operando após atingir metas")
            else:
                print("\n✅ Nenhuma configuração precisava ser atualizada.")
                
        except Exception as e:
            print(f"\n❌ Erro ao atualizar configurações: {str(e)}")
            db.session.rollback()
            return False
            
    return True

def verify_fix():
    """Verificar se a correção foi aplicada corretamente"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se ainda há configurações com continuous_mode ou auto_restart ativados
            problematic_configs = TradingConfig.query.filter(
                (TradingConfig.continuous_mode == True) | 
                (TradingConfig.auto_restart == True)
            ).all()
            
            if len(problematic_configs) == 0:
                print("\n✅ VERIFICAÇÃO PASSOU: Todas as configurações estão corretas!")
                return True
            else:
                print(f"\n⚠️ VERIFICAÇÃO FALHOU: {len(problematic_configs)} configurações ainda têm problemas")
                for config in problematic_configs:
                    print(f"   Usuário {config.user_id}: continuous_mode={config.continuous_mode}, auto_restart={config.auto_restart}")
                return False
                
        except Exception as e:
            print(f"\n❌ Erro na verificação: {str(e)}")
            return False

if __name__ == '__main__':
    print("🔧 CORREÇÃO DO SISTEMA DE PAUSA")
    print("=" * 50)
    print("\n📋 PROBLEMA IDENTIFICADO:")
    print("   O bot continuava operando após atingir stop loss")
    print("   porque continuous_mode e auto_restart estavam ativados por padrão.")
    print("\n🔧 SOLUÇÃO:")
    print("   Desabilitar continuous_mode e auto_restart para todas as configurações.")
    print("\n" + "=" * 50)
    
    # Aplicar a correção
    if fix_continuous_mode_settings():
        print("\n" + "=" * 50)
        print("🔍 VERIFICANDO A CORREÇÃO...")
        verify_fix()
        print("\n" + "=" * 50)
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("   1. Reinicie o bot se estiver rodando")
        print("   2. Teste o comportamento com uma operação")
        print("   3. Verifique se o bot para após atingir take profit ou stop loss")
        print("\n✅ Correção concluída!")
    else:
        print("\n❌ Falha na aplicação da correção. Verifique os logs de erro acima.")