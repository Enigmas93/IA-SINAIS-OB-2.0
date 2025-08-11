#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORREÇÃO DO BUG IDENTIFICADO:

O problema está na comparação dos targets de Take Profit e Stop Loss.
O código está comparando session_profit (valor em dólares) diretamente com
config.take_profit e config.stop_loss (valores em porcentagem).

EXEMPLO DO PROBLEMA:
- session_profit = -373.76 (dólares)
- config.stop_loss = 30.0 (porcentagem)
- Comparação: -373.76 <= -30.0 = True (INCORRETO!)

DEVERIA SER:
- session_profit = -373.76 (dólares)
- stop_loss_value = 1000.0 * (30.0 / 100) = 300.0 (dólares)
- Comparação: -373.76 <= -300.0 = True (CORRETO!)
"""

import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def demonstrate_bug():
    """Demonstra o bug na comparação de targets"""
    logger.info("\n" + "=" * 80)
    logger.info("🐛 DEMONSTRAÇÃO DO BUG IDENTIFICADO")
    logger.info("=" * 80)
    
    # Valores típicos do cenário problemático
    initial_balance = 1000.0
    session_profit = -373.76  # Após 4 perdas consecutivas
    take_profit_config = 70.0  # 70% (porcentagem)
    stop_loss_config = 30.0    # 30% (porcentagem)
    
    logger.info(f"💰 Saldo inicial: ${initial_balance}")
    logger.info(f"📊 Lucro da sessão: ${session_profit}")
    logger.info(f"🎯 Take Profit configurado: {take_profit_config}% (interface)")
    logger.info(f"🛑 Stop Loss configurado: {stop_loss_config}% (interface)")
    
    # COMPARAÇÃO INCORRETA (como está no código atual)
    logger.info("\n❌ COMPARAÇÃO INCORRETA (código atual):")
    take_profit_reached_wrong = session_profit >= take_profit_config
    stop_loss_reached_wrong = session_profit <= -stop_loss_config
    
    logger.info(f"   Take Profit: {session_profit} >= {take_profit_config} = {take_profit_reached_wrong}")
    logger.info(f"   Stop Loss: {session_profit} <= -{stop_loss_config} = {stop_loss_reached_wrong}")
    
    if stop_loss_reached_wrong:
        logger.error(f"   🚨 BUG: Stop Loss atingido incorretamente!")
        logger.error(f"   🚨 Comparando ${session_profit} com -{stop_loss_config}% ao invés de valor em dólares")
    
    # COMPARAÇÃO CORRETA
    logger.info("\n✅ COMPARAÇÃO CORRETA (como deveria ser):")
    take_profit_value = initial_balance * (take_profit_config / 100)  # $700
    stop_loss_value = initial_balance * (stop_loss_config / 100)      # $300
    
    take_profit_reached_correct = session_profit >= take_profit_value
    stop_loss_reached_correct = session_profit <= -stop_loss_value
    
    logger.info(f"   Take Profit valor: ${take_profit_value} (70% de ${initial_balance})")
    logger.info(f"   Stop Loss valor: ${stop_loss_value} (30% de ${initial_balance})")
    logger.info(f"   Take Profit: {session_profit} >= {take_profit_value} = {take_profit_reached_correct}")
    logger.info(f"   Stop Loss: {session_profit} <= -{stop_loss_value} = {stop_loss_reached_correct}")
    
    if stop_loss_reached_correct:
        logger.info(f"   ✅ Stop Loss atingido corretamente!")
        logger.info(f"   ✅ Perda de ${abs(session_profit)} excedeu limite de ${stop_loss_value}")
    else:
        logger.info(f"   ✅ Stop Loss NÃO atingido - bot deve continuar")
        logger.info(f"   ✅ Perda de ${abs(session_profit)} ainda dentro do limite de ${stop_loss_value}")
    
    return {
        'bug_detected': stop_loss_reached_wrong and not stop_loss_reached_correct,
        'correct_take_profit': take_profit_reached_correct,
        'correct_stop_loss': stop_loss_reached_correct,
        'take_profit_value': take_profit_value,
        'stop_loss_value': stop_loss_value
    }

def test_various_scenarios():
    """Testa vários cenários para confirmar o bug"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTE DE VÁRIOS CENÁRIOS")
    logger.info("=" * 80)
    
    initial_balance = 1000.0
    take_profit_config = 70.0  # 70%
    stop_loss_config = 30.0    # 30%
    
    take_profit_value = initial_balance * (take_profit_config / 100)  # $700
    stop_loss_value = initial_balance * (stop_loss_config / 100)      # $300
    
    scenarios = [
        (-50.0, "Perda pequena"),
        (-150.0, "Perda moderada"),
        (-250.0, "Perda próxima ao limite"),
        (-300.0, "Perda exata no limite"),
        (-350.0, "Perda acima do limite"),
        (-373.76, "Cenário real do problema"),
        (100.0, "Lucro pequeno"),
        (500.0, "Lucro moderado"),
        (700.0, "Lucro no limite"),
        (800.0, "Lucro acima do limite")
    ]
    
    for session_profit, description in scenarios:
        logger.info(f"\n📊 {description}: ${session_profit}")
        
        # Comparação incorreta
        wrong_tp = session_profit >= take_profit_config
        wrong_sl = session_profit <= -stop_loss_config
        
        # Comparação correta
        correct_tp = session_profit >= take_profit_value
        correct_sl = session_profit <= -stop_loss_value
        
        logger.info(f"   Código atual: TP={wrong_tp}, SL={wrong_sl}")
        logger.info(f"   Código correto: TP={correct_tp}, SL={correct_sl}")
        
        if wrong_tp != correct_tp or wrong_sl != correct_sl:
            logger.error(f"   🚨 DISCREPÂNCIA DETECTADA!")
            if wrong_sl and not correct_sl:
                logger.error(f"   🚨 Stop Loss acionado incorretamente pelo código atual")
            elif not wrong_sl and correct_sl:
                logger.error(f"   🚨 Stop Loss NÃO acionado quando deveria pelo código atual")

def show_code_locations():
    """Mostra onde o bug está localizado no código"""
    logger.info("\n" + "=" * 80)
    logger.info("📍 LOCALIZAÇÃO DO BUG NO CÓDIGO")
    logger.info("=" * 80)
    
    locations = [
        {
            'file': 'services/trading_bot.py',
            'line': '558',
            'code': 'if self.session_profit >= self.config.take_profit:',
            'fix': 'if self.session_profit >= (self.initial_balance * (self.config.take_profit / 100)):'
        },
        {
            'file': 'services/trading_bot.py',
            'line': '574',
            'code': 'if self.session_profit <= -self.config.stop_loss:',
            'fix': 'if self.session_profit <= -(self.initial_balance * (self.config.stop_loss / 100)):'
        },
        {
            'file': 'services/trading_bot.py',
            'line': '948',
            'code': 'if self.session_profit >= self.config.take_profit:',
            'fix': 'if self.session_profit >= (self.initial_balance * (self.config.take_profit / 100)):'
        },
        {
            'file': 'services/trading_bot.py',
            'line': '978',
            'code': 'if self.session_profit <= -self.config.stop_loss:',
            'fix': 'if self.session_profit <= -(self.initial_balance * (self.config.stop_loss / 100)):'
        },
        {
            'file': 'services/trading_bot.py',
            'line': '1004-1005',
            'code': 'take_profit_reached = self.session_profit >= self.config.take_profit\nstop_loss_reached = self.session_profit <= -self.config.stop_loss',
            'fix': 'take_profit_reached = self.session_profit >= (self.initial_balance * (self.config.take_profit / 100))\nstop_loss_reached = self.session_profit <= -(self.initial_balance * (self.config.stop_loss / 100))'
        }
    ]
    
    for i, location in enumerate(locations, 1):
        logger.info(f"\n🔍 Localização {i}:")
        logger.info(f"   Arquivo: {location['file']}")
        logger.info(f"   Linha: {location['line']}")
        logger.info(f"   ❌ Código atual: {location['code']}")
        logger.info(f"   ✅ Correção: {location['fix']}")

def generate_fix_summary():
    """Gera um resumo da correção necessária"""
    logger.info("\n" + "=" * 80)
    logger.info("📋 RESUMO DA CORREÇÃO NECESSÁRIA")
    logger.info("=" * 80)
    
    logger.info("🐛 PROBLEMA IDENTIFICADO:")
    logger.info("   O código está comparando session_profit (valor em dólares) diretamente")
    logger.info("   com config.take_profit e config.stop_loss (valores em porcentagem).")
    logger.info("   Isso faz com que o bot pare prematuramente.")
    
    logger.info("\n✅ SOLUÇÃO:")
    logger.info("   Converter os valores de porcentagem para valores absolutos em dólares")
    logger.info("   antes de fazer a comparação.")
    
    logger.info("\n🔧 IMPLEMENTAÇÃO:")
    logger.info("   1. Calcular take_profit_value = initial_balance * (config.take_profit / 100)")
    logger.info("   2. Calcular stop_loss_value = initial_balance * (config.stop_loss / 100)")
    logger.info("   3. Comparar session_profit com esses valores calculados")
    
    logger.info("\n📊 EXEMPLO:")
    logger.info("   Saldo inicial: $1000")
    logger.info("   Take Profit: 70% = $700")
    logger.info("   Stop Loss: 30% = $300")
    logger.info("   Session profit: -$373.76")
    logger.info("   Resultado: Stop Loss atingido (-$373.76 <= -$300) ✅")
    
    logger.info("\n🎯 IMPACTO DA CORREÇÃO:")
    logger.info("   - Bot não irá mais parar prematuramente")
    logger.info("   - Targets serão respeitados corretamente")
    logger.info("   - Martingale funcionará até os limites reais")

if __name__ == "__main__":
    logger.info("🚀 Iniciando análise do bug de cálculo de targets...")
    
    # Demonstrar o bug
    bug_result = demonstrate_bug()
    
    # Testar vários cenários
    test_various_scenarios()
    
    # Mostrar localizações no código
    show_code_locations()
    
    # Gerar resumo da correção
    generate_fix_summary()
    
    logger.info("\n" + "=" * 80)
    logger.info("🎉 ANÁLISE CONCLUÍDA")
    logger.info("=" * 80)
    
    if bug_result['bug_detected']:
        logger.error("❌ BUG CONFIRMADO: Correção necessária no código")
    else:
        logger.info("✅ Nenhum bug detectado neste cenário específico")
    
    logger.info("\n📝 PRÓXIMOS PASSOS:")
    logger.info("   1. Aplicar as correções nos arquivos indicados")
    logger.info("   2. Testar com cenários reais")
    logger.info("   3. Verificar se o problema foi resolvido")