from flask import Blueprint, request, jsonify, session, render_template
from models.user import User
from database import db
from models.company import Department
from utils.security import (
    SecurityValidator, require_login, require_admin, AuditLogger
)
from datetime import datetime

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/create', methods=['POST'])
@require_admin
def create_user():
    """Créer un nouvel utilisateur (Admin uniquement)"""
    data = request.get_json()
    admin = User.query.get(session['user_id'])
    
    # Validation des données
    username = SecurityValidator.sanitize_input(data.get('username', ''))
    email = SecurityValidator.sanitize_input(data.get('email', ''))
    password = data.get('password', '')
    
    # Validation du nom d'utilisateur
    valid, error_msg = SecurityValidator.validate_username(username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Vérifier l'unicité
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400
    
    # Validation de l'email
    valid, error_msg = SecurityValidator.validate_email(email)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Vérifier l'unicité de l'email
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Cet email existe déjà'}), 400
    
    # Validation du mot de passe
    valid, error_msg = SecurityValidator.validate_password(password, username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        # Créer l'utilisateur
        user = User(
            username=username,
            email=email,
            first_name=SecurityValidator.sanitize_input(data.get('first_name', '')),
            last_name=SecurityValidator.sanitize_input(data.get('last_name', '')),
            phone=SecurityValidator.sanitize_input(data.get('phone', '')),
            is_admin=data.get('is_admin', False),
            is_active=data.get('is_active', True),
            role=data.get('role', 'user'),
            company_id=data.get('company_id', admin.company_id),
            department_id=data.get('department_id')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'user_created',
            'user',
            user.id,
            {'username': username, 'email': email, 'role': user.role}
        )
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur créé avec succès',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500


@users_bp.route('/list', methods=['GET'])
@require_admin
def list_users():
    """Lister tous les utilisateurs"""
    admin = User.query.get(session['user_id'])
    
    # Filtrer par entreprise si non super admin
    if admin.company_id:
        users = User.query.filter_by(company_id=admin.company_id).all()
    else:
        users = User.query.all()
    
    return jsonify({
        'success': True,
        'users': [user.to_dict() for user in users]
    }), 200


@users_bp.route('/get/<int:user_id>', methods=['GET'])
@require_login
def get_user(user_id):
    """Récupérer un utilisateur"""
    current_user = User.query.get(session['user_id'])
    user = User.query.get_or_404(user_id)
    
    # Vérifier les permissions
    if not current_user.is_admin and current_user.id != user_id:
        if current_user.company_id != user.company_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'user': user.to_dict(include_sensitive=current_user.is_admin)
    }), 200


@users_bp.route('/update/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Mettre à jour un utilisateur"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    try:
        # Mise à jour des champs
        if 'first_name' in data:
            user.first_name = SecurityValidator.sanitize_input(data['first_name'])
        if 'last_name' in data:
            user.last_name = SecurityValidator.sanitize_input(data['last_name'])
        if 'email' in data:
            email = SecurityValidator.sanitize_input(data['email'])
            valid, error = SecurityValidator.validate_email(email)
            if valid:
                # Vérifier l'unicité
                existing = User.query.filter_by(email=email).first()
                if existing and existing.id != user_id:
                    return jsonify({'error': 'Cet email existe déjà'}), 400
                user.email = email
        if 'phone' in data:
            user.phone = SecurityValidator.sanitize_input(data['phone'])
        if 'role' in data:
            user.role = data['role']
        if 'department_id' in data:
            user.department_id = data['department_id']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'user_updated',
            'user',
            user_id,
            data
        )
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur mis à jour',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la mise à jour: {str(e)}'}), 500


@users_bp.route('/delete/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Désactiver un utilisateur"""
    if user_id == session['user_id']:
        return jsonify({'error': 'Vous ne pouvez pas supprimer votre propre compte'}), 400
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'user_deleted',
            'user',
            user_id,
            {'username': user.username}
        )
        
        # Soft delete
        user.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur désactivé'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500


@users_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@require_admin
def reset_user_password(user_id):
    """Réinitialiser le mot de passe d'un utilisateur"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    new_password = data.get('new_password', '')
    
    # Valider le nouveau mot de passe
    valid, error_msg = SecurityValidator.validate_password(new_password, user.username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'password_reset_by_admin',
            'user',
            user_id,
            {'reset_by': session['username']}
        )
        
        return jsonify({
            'success': True,
            'message': 'Mot de passe réinitialisé avec succès'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@users_bp.route('/unlock/<int:user_id>', methods=['POST'])
@require_admin
def unlock_user(user_id):
    """Déverrouiller un compte utilisateur"""
    user = User.query.get_or_404(user_id)
    
    try:
        user.failed_login_attempts = 0
        user.account_locked_until = None
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'account_unlocked',
            'user',
            user_id,
            {'unlocked_by': session['username']}
        )
        
        return jsonify({
            'success': True,
            'message': 'Compte déverrouillé'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# Route pour la page HTML
@users_bp.route('/manage', methods=['GET'])
@require_admin
def manage_users_page():
    """Page de gestion des utilisateurs"""
    return render_template('users.html')