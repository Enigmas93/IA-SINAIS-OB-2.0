from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from flask_migrate import Migrate
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configuration class
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///trading_bot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Initialize Flask app with explicit template and static folders
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir
)

# Configure Flask app
app.config.from_object(Config)

# Override with environment-specific settings
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 24)))

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app)

# Configure logging for serverless
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import models
try:
    from models import User, TradingConfig, TradeHistory, MLModel
    logger.info("Models imported successfully")
except ImportError as e:
    logger.error(f"Error importing models: {e}")
    # Create dummy models to prevent app crash
    class User:
        pass
    class TradingConfig:
        pass
    class TradeHistory:
        pass
    class MLModel:
        pass

# Import services with serverless-friendly fallbacks
try:
    # Only import lightweight services for serverless
    from services.signal_analyzer import SignalAnalyzer
    services_available = True
    logger.info("Services imported successfully")
except ImportError as e:
    logger.warning(f"Services not available during startup: {e}")
    services_available = False
    class SignalAnalyzer:
        def __init__(self, *args, **kwargs):
            pass

# Import and register routes blueprint
try:
    from routes import api, main
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(main)
    logger.info("Routes registered successfully")
except ImportError as e:
    logger.error(f"Error importing routes: {e}")
    # Create minimal routes to keep app running
    from flask import Blueprint
    api = Blueprint('api', __name__, url_prefix='/api')
    main = Blueprint('main', __name__)
    
    @main.route('/')
    def index():
        return render_template('index.html')
    
    @api.route('/health')
    def health():
        return {'status': 'ok', 'services_available': services_available}
    
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(main)

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services_available': services_available
    })

if __name__ == "__main__":
    app.run(debug=False)