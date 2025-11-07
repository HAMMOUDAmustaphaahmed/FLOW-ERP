import os
from datetime import timedelta

class Config:
    """Configuration principale de FlowERP"""
    
    # Sécurité
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    
    # Base de données MySQL avec XAMPP
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost/flowerp'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # False pour le développement
    SESSION_COOKIE_HTTPONLY = True  # Protection XSS
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protection CSRF
    
    # Blockchain
    BLOCKCHAIN_DIFFICULTY = 4
    BLOCKCHAIN_SYNC_INTERVAL = 300  # 5 minutes
    BLOCKCHAIN_PORT = 5001
    
    # Sécurité des mots de passe
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Rate limiting
    RATE_LIMIT_LOGIN = "5 per minute"
    RATE_LIMIT_API = "100 per minute"
    
    # Upload
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'flowrp.log'


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    # Pour MySQL avec XAMPP
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/flowerp'


class ProductionConfig(Config):
    DEBUG = False
    # Production - ajuster selon votre serveur
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost/flowerp'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_flowrp.db'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}