# models/user.py
"""Modèle User - Version corrigée sans import circulaire"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

# Import de l'instance db depuis database.py (pas app.py!)
from database import db


class User(UserMixin, db.Model):
    """Modèle utilisateur avec sécurité renforcée"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Informations personnelles
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    
    # Rôles et permissions
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(50), default='user')  # admin, manager, user
    
    # Sécurité
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    
    # Relations - Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relations inversées - PAS DE DÉFINITION ICI, utilisées via backref dans Company et Department
    # company = backref créé par Company.users
    # department = backref créé par Department.employees
    
    def set_password(self, password: str):
        """Hash le mot de passe de manière sécurisée (bcrypt via werkzeug)"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password: str) -> bool:
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    def is_account_locked(self) -> bool:
        """Vérifie si le compte est verrouillé"""
        if self.account_locked_until:
            if datetime.utcnow() < self.account_locked_until:
                return True
            else:
                # Déverrouiller automatiquement après expiration
                self.account_locked_until = None
                self.failed_login_attempts = 0
                db.session.commit()
        return False
    
    def increment_failed_login(self):
        """Incrémente les tentatives de connexion échouées"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Verrouiller le compte pour 30 minutes après 5 tentatives
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()
    
    def reset_failed_login(self):
        """Réinitialise les tentatives de connexion échouées"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def generate_2fa_secret(self):
        """Génère un secret pour l'authentification à deux facteurs"""
        self.two_factor_secret = secrets.token_hex(16)
        db.session.commit()
        return self.two_factor_secret
    
    def to_dict(self, include_sensitive=False) -> dict:
        """Convertit l'utilisateur en dictionnaire"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'company_id': self.company_id,
            'department_id': self.department_id
        }
        
        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'account_locked': self.is_account_locked(),
                'two_factor_enabled': self.two_factor_enabled
            })
        
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'


class LoginAttempt(db.Model):
    """Enregistre toutes les tentatives de connexion pour l'audit"""
    
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255))
    success = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'ip_address': self.ip_address,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return f'<LoginAttempt {self.username} - {self.success}>'


class Session(db.Model):
    """Gère les sessions utilisateur actives"""
    
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref='sessions')
    
    def is_expired(self) -> bool:
        """Vérifie si la session a expiré"""
        return datetime.utcnow() > self.expires_at
    
    def refresh(self):
        """Rafraîchit l'activité de la session"""
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def invalidate(self):
        """Invalide la session"""
        self.is_active = False
        db.session.commit()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Session {self.user_id}>'  