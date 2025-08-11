#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar o status do sistema de Machine Learning
"""

from app import create_app
from models import MLModel, TradeHistory, TradingConfig
from services.ml_service import MLService
from datetime import datetime, timedelta

def check_ml_status():
    """Verifica o status completo do sistema ML"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("STATUS DO SISTEMA DE MACHINE LEARNING")
        print("=" * 60)
        
        # 1. Verificar trades disponíveis
        print("\n1. TRADES DISPONÍVEIS:")
        total_trades = TradeHistory.query.count()
        print(f"   Total de trades no banco: {total_trades}")
        
        # Trades por usuário
        users_trades = {}
        for user_id in [1, 2, 3]:  # Verificar usuários comuns
            user_trades = TradeHistory.query.filter_by(user_id=user_id).count()
            if user_trades > 0:
                users_trades[user_id] = user_trades
                print(f"   Usuário {user_id}: {user_trades} trades")
        
        # 2. Verificar modelos ML
        print("\n2. MODELOS DE MACHINE LEARNING:")
        total_models = MLModel.query.count()
        active_models = MLModel.query.filter_by(is_active=True).count()
        print(f"   Total de modelos: {total_models}")
        print(f"   Modelos ativos: {active_models}")
        
        if total_models > 0:
            print("\n   Detalhes dos modelos:")
            models = MLModel.query.all()
            for model in models:
                status = "ATIVO" if model.is_active else "INATIVO"
                print(f"     - {model.model_name} ({model.asset}) - {status}")
                print(f"       Usuário: {model.user_id}, Precisão: {model.accuracy:.2f}%")
                print(f"       Trades ao vivo: {model.live_trades}, Última atualização: {model.last_retrained}")
        else:
            print("   ❌ Nenhum modelo encontrado no banco de dados")
        
        # 3. Verificar configuração ML por usuário
        print("\n3. CONFIGURAÇÃO DE ML POR USUÁRIO:")
        for user_id in users_trades.keys():
            config = TradingConfig.query.filter_by(user_id=user_id).first()
            if config:
                ml_enabled = "HABILITADO" if config.use_ml_signals else "DESABILITADO"
                print(f"   Usuário {user_id}: ML {ml_enabled}")
            else:
                print(f"   Usuário {user_id}: Sem configuração encontrada")
        
        # 4. Verificar dados de treinamento disponíveis
        print("\n4. DADOS DE TREINAMENTO DISPONÍVEIS:")
        for user_id in users_trades.keys():
            # Verificar trades dos últimos 90 dias
            start_date = datetime.now() - timedelta(days=90)
            recent_trades = TradeHistory.query.filter(
                TradeHistory.user_id == user_id,
                TradeHistory.timestamp >= start_date,
                TradeHistory.result.in_(['win', 'loss'])
            ).count()
            
            print(f"   Usuário {user_id}: {recent_trades} trades nos últimos 90 dias")
            
            # Verificar por asset
            assets = TradeHistory.query.filter(
                TradeHistory.user_id == user_id,
                TradeHistory.timestamp >= start_date
            ).with_entities(TradeHistory.asset).distinct().all()
            
            for (asset,) in assets:
                asset_trades = TradeHistory.query.filter(
                    TradeHistory.user_id == user_id,
                    TradeHistory.asset == asset,
                    TradeHistory.timestamp >= start_date,
                    TradeHistory.result.in_(['win', 'loss'])
                ).count()
                
                sufficient = "✅ SUFICIENTE" if asset_trades >= 100 else "❌ INSUFICIENTE"
                print(f"     {asset}: {asset_trades} trades - {sufficient}")
        
        # 5. Testar inicialização do MLService
        print("\n5. TESTE DE INICIALIZAÇÃO DO ML SERVICE:")
        for user_id in users_trades.keys():
            try:
                ml_service = MLService(user_id)
                print(f"   Usuário {user_id}: ✅ MLService inicializado com sucesso")
                
                # Verificar se há modelos carregados na memória
                loaded_models = len(ml_service.models)
                print(f"     Modelos carregados na memória: {loaded_models}")
                
            except Exception as e:
                print(f"   Usuário {user_id}: ❌ Erro ao inicializar MLService: {str(e)}")
        
        # 6. Verificar últimos trades
        print("\n6. ÚLTIMOS TRADES (AMOSTRA):")
        for user_id in users_trades.keys():
            recent_trades = TradeHistory.query.filter_by(user_id=user_id).order_by(
                TradeHistory.timestamp.desc()
            ).limit(3).all()
            
            print(f"   Usuário {user_id} - Últimos 3 trades:")
            for trade in recent_trades:
                print(f"     {trade.timestamp.strftime('%Y-%m-%d %H:%M')}: {trade.asset} - {trade.direction} - {trade.result}")
        
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO FINAL:")
        print("=" * 60)
        
        # Diagnóstico
        if total_models == 0:
            print("❌ PROBLEMA: Não há modelos ML no banco de dados")
            print("   CAUSA PROVÁVEL: Modelos nunca foram treinados")
            print("   SOLUÇÃO: Executar treinamento inicial dos modelos")
        elif active_models == 0:
            print("❌ PROBLEMA: Há modelos no banco, mas nenhum está ativo")
            print("   CAUSA PROVÁVEL: Modelos foram desativados por baixa performance")
            print("   SOLUÇÃO: Retreinar modelos ou reativar modelos existentes")
        else:
            print(f"✅ SISTEMA OK: {active_models} modelo(s) ativo(s) encontrado(s)")
        
        # Verificar se há dados suficientes para treinar
        for user_id in users_trades.keys():
            start_date = datetime.now() - timedelta(days=90)
            sufficient_data = TradeHistory.query.filter(
                TradeHistory.user_id == user_id,
                TradeHistory.timestamp >= start_date,
                TradeHistory.result.in_(['win', 'loss'])
            ).count() >= 100
            
            if sufficient_data:
                print(f"✅ Usuário {user_id}: Dados suficientes para treinamento ({users_trades[user_id]} trades)")
            else:
                print(f"⚠️  Usuário {user_id}: Dados insuficientes para treinamento automático")

if __name__ == "__main__":
    check_ml_status()