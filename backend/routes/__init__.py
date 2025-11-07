"""
Routes package initialization
Exports all blueprints
"""

from .auth import auth_bp
from .company import company_bp
from .department import department_bp
from .dashboard import dashboard_bp
from .users import users_bp

__all__ = [
    'auth_bp',
    'company_bp',
    'department_bp',
    'dashboard_bp',
    'users_bp'
]