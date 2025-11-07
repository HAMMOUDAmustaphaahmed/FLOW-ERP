import re
import secrets
import hashlib
from functools import wraps
from flask import request, jsonify, session, current_app
from datetime import datetime, timedelta
import bleach
from typing import Optional


class SecurityValidator:
    """Validateur de sécurité pour FlowERP"""
    
    # Patterns pour validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    PHONE_PATTERN = re.compile(r'^\+?[0-9]{8,15}$')
    
    # Mots de passe courants à interdire
    COMMON_PASSWORDS = [
        'password', '123456', 'password123', 'admin', 'azerty',
        'qwerty', 'letmein', 'welcome', 'monkey', '1234567890'
    ]
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """Valide une adresse email"""
        if not email or len(email) > 120:
            return False, "Email invalide"
        
        if not SecurityValidator.EMAIL_PATTERN.match(email):
            return False, "Format d'email invalide"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Valide un nom d'utilisateur"""
        if not username:
            return False, "Nom d'utilisateur requis"
        
        if len(username) < 3 or len(username) > 30:
            return False, "Le nom d'utilisateur doit contenir entre 3 et 30 caractères"
        
        if not SecurityValidator.USERNAME_PATTERN.match(username):
            return False, "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, - et _"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str, username: str = None) -> tuple[bool, str]:
        """Valide un mot de passe selon les règles de sécurité"""
        if not password:
            return False, "Mot de passe requis"
        
        if len(password) < 8:
            return False, "Le mot de passe doit contenir au moins 8 caractères"
        
        if len(password) > 128:
            return False, "Le mot de passe est trop long"
        
        # Vérifier la présence de différents types de caractères
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
        
        if not has_upper:
            return False, "Le mot de passe doit contenir au moins une majuscule"
        
        if not has_lower:
            return False, "Le mot de passe doit contenir au moins une minuscule"
        
        if not has_digit:
            return False, "Le mot de passe doit contenir au moins un chiffre"
        
        if not has_special:
            return False, "Le mot de passe doit contenir au moins un caractère spécial"
        
        # Vérifier si le mot de passe est commun
        if password.lower() in SecurityValidator.COMMON_PASSWORDS:
            return False, "Ce mot de passe est trop commun"
        
        # Vérifier si le mot de passe contient le nom d'utilisateur
        if username and username.lower() in password.lower():
            return False, "Le mot de passe ne doit pas contenir le nom d'utilisateur"
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text: str, allow_html: bool = False) -> str:
        """Nettoie une entrée utilisateur pour prévenir les injections XSS"""
        if not text:
            return ""
        
        # Supprimer les espaces en début et fin
        text = text.strip()
        
        if allow_html:
            # Autoriser seulement certaines balises HTML sûres
            allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
            text = bleach.clean(text, tags=allowed_tags, strip=True)
        else:
            # Supprimer toutes les balises HTML
            text = bleach.clean(text, tags=[], strip=True)
        
        return text
    
    @staticmethod
    def validate_sql_safe(text: str) -> bool:
        """Vérifie si le texte ne contient pas de patterns SQL dangereux"""
        # Patterns SQL dangereux
        dangerous_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
            r'(--|;|\/\*|\*\/)',
            r'(\bOR\b.*=.*)',
            r'(\bUNION\b.*\bSELECT\b)',
            r'(\'.*--)',
            r'(xp_.*)',
            r'(sp_.*)'
        ]
        
        text_upper = text.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return False
        
        return True


class RateLimiter:
    """Limiteur de taux pour prévenir les abus"""
    
    def __init__(self):
        self.attempts = {}
    
    def is_allowed(self, identifier: str, max_attempts: int = 5, 
                   window_minutes: int = 15) -> tuple[bool, Optional[int]]:
        """
        Vérifie si une action est autorisée
        Retourne (autorisé, secondes_restantes)
        """
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Nettoyer les anciennes tentatives
        window = timedelta(minutes=window_minutes)
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier]
            if now - attempt < window
        ]
        
        # Vérifier le nombre de tentatives
        if len(self.attempts[identifier]) >= max_attempts:
            oldest_attempt = min(self.attempts[identifier])
            wait_until = oldest_attempt + window
            seconds_remaining = int((wait_until - now).total_seconds())
            return False, seconds_remaining
        
        # Ajouter la nouvelle tentative
        self.attempts[identifier].append(now)
        return True, None
    
    def reset(self, identifier: str):
        """Réinitialise le compteur pour un identifiant"""
        if identifier in self.attempts:
            del self.attempts[identifier]


# Instance globale du rate limiter
rate_limiter = RateLimiter()


def require_login(f):
    """Décorateur pour exiger une authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Décorateur pour exiger des droits administrateur"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        from models.user import User
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin rights required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(max_attempts: int = 5, window_minutes: int = 15):
    """Décorateur pour limiter le taux de requêtes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Utiliser l'IP comme identifiant
            identifier = request.remote_addr
            
            allowed, seconds_remaining = rate_limiter.is_allowed(
                identifier, max_attempts, window_minutes
            )
            
            if not allowed:
                return jsonify({
                    'error': 'Too many requests',
                    'retry_after': seconds_remaining
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def generate_csrf_token() -> str:
    """Génère un token CSRF"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token(token: str) -> bool:
    """Valide un token CSRF"""
    return token == session.get('csrf_token')


def generate_secure_token(length: int = 32) -> str:
    """Génère un token sécurisé aléatoire"""
    return secrets.token_urlsafe(length)


def hash_data(data: str) -> str:
    """Hash des données avec SHA-256"""
    return hashlib.sha256(data.encode()).hexdigest()


class AuditLogger:
    """Logger pour l'audit de sécurité"""
    
    @staticmethod
    def log_login_attempt(username: str, ip_address: str, success: bool, 
                         failure_reason: str = None):
        """Enregistre une tentative de connexion"""
        from models.user import LoginAttempt
        from database import db
        
        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            user_agent=request.headers.get('User-Agent', '')[:255],
            success=success,
            failure_reason=failure_reason
        )
        db.session.add(attempt)
        db.session.commit()
    
    @staticmethod
    def log_action(user_id: int, action: str, entity_type: str, 
                  entity_id: int, details: dict = None):
        """Enregistre une action utilisateur dans la blockchain"""
        # CORRECTION: Utiliser current_app.extensions au lieu d'importer blockchain
        try:
            blockchain = current_app.extensions.get('blockchain')
            if blockchain:
                transaction = {
                    'type': 'action',
                    'user_id': user_id,
                    'action': action,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'details': details or {},
                    'ip_address': request.remote_addr,
                    'timestamp': datetime.utcnow().isoformat()
                }
                blockchain.add_transaction(transaction)
        except Exception as e:
            # Logger l'erreur mais ne pas bloquer l'application
            print(f"Blockchain logging error: {e}")