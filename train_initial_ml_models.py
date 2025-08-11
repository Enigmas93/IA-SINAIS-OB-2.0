#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para treinar os modelos ML iniciais
"""

from app import create_app
from models import TradeHistory, TradingConfig
from services.ml_service import MLService
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_initial_models():
    """Treina os modelos ML iniciais para usuários com dados suficientes"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("TREINAMENTO INICIAL DOS MODELOS DE MACHINE LEARNING")
        print("=" * 60)
        
        # Verificar usuários com dados suficientes
        users_to_train = []
        
        for user_id in [1, 2, 3]:  # Verificar usuários comuns
            # Verificar se usuário tem configuração e ML habilitado
            config = TradingConfig.query.filter_by(user_id=user_id).first()
            if not config or not config.use_ml_signals:
                continue
            
            # Verificar se há dados suficientes
            start_date = datetime.now() - timedelta(days=90)
            trade_count = TradeHistory.query.filter(
                TradeHistory.user_id == user_id,
                TradeHistory.timestamp >= start_date,
                TradeHistory.result.in_(['win', 'loss'])
            ).count()
            
            if trade_count >= 100:
                users_to_train.append((user_id, trade_count))
                print(f"✅ Usuário {user_id}: {trade_count} trades disponíveis - QUALIFICADO para treinamento")
            else:
                print(f"❌ Usuário {user_id}: {trade_count} trades disponíveis - INSUFICIENTE para treinamento")
        
        if not users_to_train:
            print("\n❌ Nenhum usuário qualificado para treinamento encontrado")
            return
        
        print(f"\n🎯 Iniciando treinamento para {len(users_to_train)} usuário(s)...")
        
        # Treinar modelos para cada usuário qualificado
        for user_id, trade_count in users_to_train:
            print(f"\n{'='*40}")
            print(f"TREINANDO MODELOS PARA USUÁRIO {user_id}")
            print(f"{'='*40}")
            
            try:
                # Inicializar MLService
                ml_service = MLService(user_id)
                print(f"✅ MLService inicializado para usuário {user_id}")
                
                # Obter assets únicos dos trades do usuário
                start_date = datetime.now() - timedelta(days=90)
                assets = TradeHistory.query.filter(
                    TradeHistory.user_id == user_id,
                    TradeHistory.timestamp >= start_date
                ).with_entities(TradeHistory.asset).distinct().all()
                
                assets_list = [asset[0] for asset in assets]
                print(f"📊 Assets encontrados: {assets_list}")
                
                # Treinar modelos para cada asset
                trained_models = []
                failed_models = []
                
                for asset in assets_list:
                    # Verificar se há dados suficientes para este asset
                    asset_trades = TradeHistory.query.filter(
                        TradeHistory.user_id == user_id,
                        TradeHistory.asset == asset,
                        TradeHistory.timestamp >= start_date,
                        TradeHistory.result.in_(['win', 'loss'])
                    ).count()
                    
                    print(f"\n🔄 Processando {asset}: {asset_trades} trades")
                    
                    if asset_trades < 100:
                        print(f"   ⚠️  Pulando {asset} - dados insuficientes ({asset_trades} < 100)")
                        continue
                    
                    # Treinar diferentes tipos de modelo
                    model_types = ['random_forest', 'gradient_boost']
                    
                    for model_type in model_types:
                        print(f"   🤖 Treinando modelo {model_type} para {asset}...")
                        
                        try:
                            success = ml_service.train_model(asset, model_type, retrain=False)
                            
                            if success:
                                model_name = f"{asset}_{model_type}"
                                trained_models.append(model_name)
                                print(f"   ✅ Modelo {model_name} treinado com sucesso")
                            else:
                                failed_models.append(f"{asset}_{model_type}")
                                print(f"   ❌ Falha ao treinar modelo {asset}_{model_type}")
                                
                        except Exception as e:
                            failed_models.append(f"{asset}_{model_type}")
                            print(f"   ❌ Erro ao treinar {asset}_{model_type}: {str(e)}")
                
                # Resumo do treinamento para este usuário
                print(f"\n📋 RESUMO DO TREINAMENTO - USUÁRIO {user_id}:")
                print(f"   ✅ Modelos treinados com sucesso: {len(trained_models)}")
                for model in trained_models:
                    print(f"     - {model}")
                
                if failed_models:
                    print(f"   ❌ Modelos que falharam: {len(failed_models)}")
                    for model in failed_models:
                        print(f"     - {model}")
                
                if trained_models:
                    print(f"   🎉 Usuário {user_id}: Treinamento concluído com sucesso!")
                else:
                    print(f"   😞 Usuário {user_id}: Nenhum modelo foi treinado com sucesso")
                    
            except Exception as e:
                print(f"❌ Erro geral no treinamento para usuário {user_id}: {str(e)}")
                logger.error(f"Training error for user {user_id}: {str(e)}")
        
        print(f"\n{'='*60}")
        print("TREINAMENTO INICIAL CONCLUÍDO")
        print(f"{'='*60}")
        
        # Verificação final
        print("\n🔍 VERIFICAÇÃO FINAL:")
        from models import MLModel
        
        for user_id, _ in users_to_train:
            active_models = MLModel.query.filter_by(
                user_id=user_id,
                is_active=True
            ).count()
            
            if active_models > 0:
                print(f"✅ Usuário {user_id}: {active_models} modelo(s) ativo(s) criado(s)")
            else:
                print(f"❌ Usuário {user_id}: Nenhum modelo ativo encontrado")
        
        print("\n💡 PRÓXIMOS PASSOS:")
        print("   1. Verificar o dashboard para confirmar que os modelos aparecem")
        print("   2. Os modelos serão retreinados automaticamente a cada 50 trades")
        print("   3. Modelos com precisão < 60% serão retreinados automaticamente")
        print("   4. Retreinamento automático também ocorre a cada 7 dias")

if __name__ == "__main__":
    train_initial_models()