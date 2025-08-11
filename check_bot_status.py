#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import trading_bot
from services.trading_bot import TradingBot
from datetime import datetime

print("=== VERIFICAÇÃO DO STATUS DO BOT ===")
print(f"Timestamp: {datetime.now()}")
print()

# Check if there's a trading bot instance
print(f"Trading bot global variable: {trading_bot}")
print(f"Type: {type(trading_bot)}")

if trading_bot:
    print(f"Is TradingBot instance: {isinstance(trading_bot, TradingBot)}")
    
    if isinstance(trading_bot, TradingBot):
        print("\n=== BOT REAL DETECTADO ===")
        print(f"Bot running: {getattr(trading_bot, 'running', False)}")
        print(f"Current session: {getattr(trading_bot, 'current_session', None)}")
        print(f"Auto mode: {getattr(trading_bot, 'auto_mode', False)}")
        print(f"Continuous mode: {getattr(trading_bot.config, 'continuous_mode', False) if hasattr(trading_bot, 'config') else 'N/A'}")
        print(f"Afternoon enabled: {getattr(trading_bot.config, 'afternoon_enabled', False) if hasattr(trading_bot, 'config') else 'N/A'}")
        print(f"Afternoon start: {getattr(trading_bot.config, 'afternoon_start', None) if hasattr(trading_bot, 'config') else 'N/A'}")
        
        # Check scheduler status
        if hasattr(trading_bot, 'scheduler'):
            print(f"\nScheduler running: {trading_bot.scheduler.running if trading_bot.scheduler else False}")
            if trading_bot.scheduler and trading_bot.scheduler.running:
                jobs = trading_bot.scheduler.get_jobs()
                print(f"Active jobs: {len(jobs)}")
                for job in jobs:
                    print(f"  - {job.id}: {job.next_run_time}")
    else:
        print("\n=== BOT DUMMY DETECTADO ===")
        print("Nenhuma instância real do bot está ativa")
else:
    print("\n=== NENHUM BOT DETECTADO ===")
    print("Variável trading_bot é None")