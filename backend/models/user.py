# models/user.py
"""Modèle User avec système de permissions avancé"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from database import db


class User(UserMixin, db.Model):
    """Modèle utilisateur avec sécurité renforcée et permissions"""
    
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
    role = db.Column(db.String(50), default='employee')  # admin, department_manager, employee, technician
    
    # Permissions détaillées (pour les rôles non-admin)
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    can_create = db.Column(db.Boolean, default=False)
    can_update = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_add_tables = db.Column(db.Boolean, default=False)
    can_add_columns = db.Column(db.Boolean, default=False)
    
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
    
    def set_password(self, password: str):
        """Hash le mot de passe de manière sécurisée"""
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
                self.account_locked_until = None
                self.failed_login_attempts = 0
                db.session.commit()
        return False
    
    def increment_failed_login(self):
        """Incrémente les tentatives de connexion échouées"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()
    
    def reset_failed_login(self):
        """Réinitialise les tentatives de connexion échouées"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def set_role_permissions(self, role: str):
        """Configure les permissions selon le rôle"""
        self.role = role
        
        if role == 'admin':
            self.is_admin = True
            self.can_read = True
            self.can_write = True
            self.can_create = True
            self.can_update = True
            self.can_delete = True
            self.can_add_tables = True
            self.can_add_columns = True
        
        elif role == 'department_manager':
            self.is_admin = False
            self.can_read = True
            self.can_write = True
            self.can_create = True
            self.can_update = True
            self.can_delete = True
            self.can_add_tables = True
            self.can_add_columns = True
        
        elif role == 'employee':
            self.is_admin = False
            self.can_read = True
            self.can_write = True
            self.can_create = True
            self.can_update = True
            self.can_delete = False
            self.can_add_tables = False
            self.can_add_columns = False
        
        elif role == 'technician':
            self.is_admin = False
            self.can_read = True
            self.can_write = False
            self.can_create = False
            self.can_update = False
            self.can_delete = False
            self.can_add_tables = False
            self.can_add_columns = False
    
    def has_permission(self, permission: str) -> bool:
        """Vérifie si l'utilisateur a une permission spécifique"""
        if self.is_admin:
            return True
        
        permission_map = {
            'read': self.can_read,
            'write': self.can_write,
            'create': self.can_create,
            'update': self.can_update,
            'delete': self.can_delete,
            'add_tables': self.can_add_tables,
            'add_columns': self.can_add_columns
        }
        
        return permission_map.get(permission, False)
    
    def get_full_name(self) -> str:
        """Retourne le nom complet"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_role_display(self) -> str:
        """Retourne le rôle en français"""
        role_map = {
            'admin': 'Administrateur',
            'department_manager': 'Chef de département',
            'employee': 'Employé',
            'technician': 'Technicien'
        }
        return role_map.get(self.role, 'Utilisateur')
    
    def to_dict(self, include_sensitive=False) -> dict:
        """Convertit l'utilisateur en dictionnaire"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'phone': self.phone,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'role': self.role,
            'role_display': self.get_role_display(),
            'permissions': {
                'read': self.can_read,
                'write': self.can_write,
                'create': self.can_create,
                'update': self.can_update,
                'delete': self.can_delete,
                'add_tables': self.can_add_tables,
                'add_columns': self.can_add_columns
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'company_id': self.company_id,
            'department_id': self.department_id
        }
        
        # Ajouter les infos du département si disponible
        if self.department_id:
            try:
                data['department_name'] = self.department.name if hasattr(self, 'department') and self.department else None
            except:
                data['department_name'] = None
        
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