#!/usr/bin/env python3
"""
Teste forçado do ML Service - bypassa filtros de data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from models import TradeHistory, MLModel
from services.ml_service import MLService
from datetime import datetime, timedelta
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ml_service_forced():
    """Test ML service with forced training data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize ML Service
            ml_service = MLService(user_id=1)
            logger.info("ML Service initialized successfully")
            
            # Clear existing data for clean test
            TradeHistory.query.filter_by(user_id=1, asset='EURUSD').delete()
            MLModel.query.filter_by(user_id=1).delete()
            db.session.commit()
            
            # Create sufficient training data (200 samples)
            logger.info("Creating 200 training samples...")
            for i in range(200):
                trade = TradeHistory(
                    user_id=1,
                    asset='EURUSD',
                    direction='call' if random.random() > 0.5 else 'put',
                    amount=10.0,
                    result='win' if random.random() > 0.4 else 'loss',
                    profit=random.uniform(-10, 15),
                    expiration_time=60,
                    account_type='PRACTICE',
                    signal_strength=random.uniform(0.5, 1.0),
                    rsi_value=random.uniform(20, 80),
                    macd_value=random.uniform(-0.1, 0.1),
                    macd_signal_value=random.uniform(-0.1, 0.1),
                    ma_short_value=random.uniform(1.0, 1.2),
                    ma_long_value=random.uniform(1.0, 1.2),
                    aroon_up=random.uniform(0, 100),
                    aroon_down=random.uniform(0, 100),
                    volatility=random.uniform(0.01, 0.05),
                    trend_direction=random.choice(['up', 'down', 'sideways']),
                    timestamp=datetime.now() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(trade)
            
            db.session.commit()
            logger.info("Created 200 training samples")
            
            # Force training by modifying the minimum requirement temporarily
            original_min_samples = 100
            
            # Test training with sufficient data
            logger.info("Testing model training with sufficient data...")
            training_result = ml_service.train_model('EURUSD', 'random_forest')
            logger.info(f"Training result: {training_result}")
            
            if training_result:
                logger.info("✅ Model training successful!")
                
                # Test model performance retrieval
                performance = ml_service.get_model_performance()
                logger.info(f"Model performance: {performance}")
                
                # Test prediction
                dummy_analysis = {
                    'asset': 'EURUSD',
                    'signal': 'call',
                    'trend': {'direction': 'up'}
                }
                dummy_candles = [{
                    'open': 1.1000,
                    'high': 1.1010,
                    'low': 1.0990,
                    'close': 1.1005,
                    'volume': 1000
                }]
                
                prediction = ml_service.predict_signal(dummy_candles, dummy_analysis)
                logger.info(f"ML Prediction: {prediction}")
                
                if prediction:
                    logger.info("✅ ML prediction successful!")
                else:
                    logger.warning("❌ ML prediction failed")
            else:
                logger.error("❌ Model training failed")
            
            # Check if model files were created
            import os
            ml_models_dir = os.path.join(os.getcwd(), 'ml_models')
            if os.path.exists(ml_models_dir):
                files = os.listdir(ml_models_dir)
                logger.info(f"ML models directory contents: {files}")
            else:
                logger.info("ML models directory not found")
            
            logger.info("ML Service forced test completed")
            
        except Exception as e:
            logger.error(f"Error in ML service test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_ml_service_forced()