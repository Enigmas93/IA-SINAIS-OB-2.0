#!/usr/bin/env python3
"""
Test script for ML Service functionality
"""

from services.ml_service import MLService
from models import db, MLModel, TradeHistory
from app import app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ml_service():
    """Test ML service functionality"""
    with app.app_context():
        try:
            # Initialize ML service for user 2
            ml_service = MLService(2)
            logger.info("ML Service initialized successfully")
            
            # Check existing models
            existing_models = MLModel.query.filter_by(user_id=2, is_active=True).all()
            logger.info(f"Found {len(existing_models)} existing ML models")
            
            for model in existing_models:
                logger.info(f"Model: {model.model_name}, Type: {model.model_type}, Asset: {model.asset}, Accuracy: {model.accuracy}")
            
            # Check training data availability
            trade_count = TradeHistory.query.filter_by(user_id=2).count()
            logger.info(f"Found {trade_count} historical trades for training")
            
            if trade_count < 100:
                logger.warning("Insufficient training data - need at least 100 trades")
                # Create some dummy training data for testing
                logger.info("Creating dummy training data for testing...")
                
                from datetime import datetime, timedelta
                import random
                
                for i in range(150):
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
                        timestamp=datetime.now() - timedelta(days=random.randint(1, 60))
                    )
                    db.session.add(trade)
                
                db.session.commit()
                logger.info("Created 150 dummy trades for testing")
            
            # Test model training
            logger.info("Testing model training...")
            result = ml_service.train_model('EURUSD', 'random_forest')
            logger.info(f"Training result: {result}")
            
            # Test model performance retrieval
            logger.info("Testing model performance retrieval...")
            performance = ml_service.get_model_performance()
            logger.info(f"Model performance data: {performance}")
            
            # Test retrain statistics
            logger.info("Testing retrain statistics...")
            retrain_stats = ml_service.get_retrain_statistics()
            logger.info(f"Retrain statistics: {retrain_stats}")
            
            # Test signal prediction (if model exists)
            if result:
                logger.info("Testing signal prediction...")
                dummy_candles = [
                    {'close': 1.1000, 'high': 1.1010, 'low': 1.0990, 'open': 1.0995, 'volume': 1000},
                    {'close': 1.1005, 'high': 1.1015, 'low': 1.0995, 'open': 1.1000, 'volume': 1100},
                    {'close': 1.1010, 'high': 1.1020, 'low': 1.1000, 'open': 1.1005, 'volume': 1200}
                ]
                
                dummy_analysis = {
                    'asset': 'EURUSD',
                    'signal': 'call',
                    'confidence': 0.7,
                    'strength': 0.8,
                    'rsi_value': 65,
                    'macd_value': 0.05,
                    'bb_position': 0.8,
                    'volume_ratio': 1.1,
                    'volatility': 0.02
                }
                
                prediction = ml_service.predict_signal(dummy_candles, dummy_analysis)
                logger.info(f"ML prediction: {prediction}")
            
            logger.info("ML Service test completed successfully")
            
        except Exception as e:
            logger.error(f"Error testing ML service: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_ml_service()