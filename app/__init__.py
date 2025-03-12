# app/__init__.py
from flask import Flask
from config import Config
from flask_cors import CORS
from flask_login import LoginManager
from flask_restful import Api
from flask_apscheduler import APScheduler

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Flask extensions
    CORS(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    api = Api(app)
    
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # Register blueprints (grouped routes)
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # If you want, initialize your scheduled jobs here or in a separate file (e.g., scheduler.py)

    return app
