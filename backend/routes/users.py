from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from models.user import User
from database import db
from models.company import Department
from utils.security import (
    SecurityValidator, require_login, require_admin, AuditLogger
)
from datetime import datetime
from sqlalchemy import or_

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
    role = data.get('role', 'employee')
    
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
    
    # Validation du rôle
    valid_roles = ['admin', 'department_manager', 'employee', 'technician']
    if role not in valid_roles:
        return jsonify({'error': 'Rôle invalide'}), 400
    
    # Validation du département pour les rôles non-admin
    department_id = data.get('department_id')
    if role != 'admin' and not department_id:
        return jsonify({'error': 'Le département est requis pour ce rôle'}), 400
    
    # Pour department_manager, vérifier que le département n'a pas déjà un manager
    if role == 'department_manager' and department_id:
        dept = Department.query.get(department_id)
        if dept and dept.manager_id:
            existing_manager = User.query.get(dept.manager_id)
            if existing_manager and existing_manager.is_active:
                return jsonify({
                    'error': f'Ce département a déjà un chef: {existing_manager.get_full_name()}'
                }), 400
    
    try:
        # Créer l'utilisateur
        user = User(
            username=username,
            email=email,
            first_name=SecurityValidator.sanitize_input(data.get('first_name', '')),
            last_name=SecurityValidator.sanitize_input(data.get('last_name', '')),
            phone=SecurityValidator.sanitize_input(data.get('phone', '')),
            is_active=data.get('is_active', True),
            company_id=admin.company_id,
            department_id=department_id
        )
        user.set_password(password)
        user.set_role_permissions(role)
        
        # Permissions personnalisées si fournies
        if 'permissions' in data:
            perms = data['permissions']
            user.can_read = perms.get('read', user.can_read)
            user.can_write = perms.get('write', user.can_write)
            user.can_create = perms.get('create', user.can_create)
            user.can_update = perms.get('update', user.can_update)
            user.can_delete = perms.get('delete', user.can_delete)
            user.can_add_tables = perms.get('add_tables', user.can_add_tables)
            user.can_add_columns = perms.get('add_columns', user.can_add_columns)
        
        db.session.add(user)
        db.session.flush()
        
        # Si c'est un department_manager, l'assigner au département
        if role == 'department_manager' and department_id:
            dept = Department.query.get(department_id)
            if dept:
                dept.manager_id = user.id
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'user_created',
            'user',
            user.id,
            {
                'username': username, 
                'email': email, 
                'role': user.role,
                'department_id': department_id
            }
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
@require_login
def list_users():
    """Lister tous les utilisateurs avec filtres et recherche - AVEC PERMISSIONS"""
    user = User.query.get(session['user_id'])
    
    # 🔒 VÉRIFICATION DES PERMISSIONS
    # Seuls admin, directeur_rh et assistant_administratif peuvent voir la liste users
    if not (user.is_admin or user.role in ['directeur_rh', 'assistant_administratif']):
        return jsonify({
            'success': False,
            'error': 'Accès refusé. Vous n\'avez pas les permissions pour consulter la liste des utilisateurs.'
        }), 403
    
    # Paramètres de recherche et filtrage
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role')
    department_filter = request.args.get('department_id', type=int)
    status_filter = request.args.get('status')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Query de base - filtrer par entreprise
    if user.is_admin or user.role in ['directeur_rh', 'assistant_administratif']:
        # Ils voient TOUS les users de l'entreprise
        query = User.query.filter_by(company_id=user.company_id)
    else:
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Recherche textuelle
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.phone.ilike(search_pattern)
            )
        )
    
    # Filtres
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if department_filter:
        query = query.filter_by(department_id=department_filter)
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    # Tri par défaut
    query = query.order_by(User.created_at.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@users_bp.route('/search', methods=['GET'])
@require_login
def search_users():
    """Recherche dynamique d'utilisateurs (pour autocomplete)"""
    user = User.query.get(session['user_id'])
    search = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not search or len(search) < 2:
        return jsonify({'success': True, 'users': []}), 200
    
    # Query de base
    if user.is_admin and user.company_id:
        query = User.query.filter_by(company_id=user.company_id, is_active=True)
    else:
        if not user.department_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        query = User.query.filter_by(
            company_id=user.company_id,
            department_id=user.department_id,
            is_active=True
        )
    
    # Recherche
    search_pattern = f'%{search}%'
    query = query.filter(
        or_(
            User.username.ilike(search_pattern),
            User.email.ilike(search_pattern),
            User.first_name.ilike(search_pattern),
            User.last_name.ilike(search_pattern)
        )
    ).limit(limit)
    
    users = query.all()
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    }), 200


@users_bp.route('/get/<int:user_id>', methods=['GET'])
@require_login
def get_user(user_id):
    """Récupérer un utilisateur"""
    current_user = User.query.get(session['user_id'])
    user = User.query.get_or_404(user_id)
    
    # Vérifier les permissions
    if not current_user.is_admin:
        if current_user.id != user_id:
            if current_user.company_id != user.company_id:
                return jsonify({'error': 'Accès non autorisé'}), 403
            if current_user.role != 'department_manager' or current_user.department_id != user.department_id:
                return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'user': user.to_dict(include_sensitive=current_user.is_admin)
    }), 200


@users_bp.route('/update/<int:user_id>', methods=['PUT'])
@require_login
def update_user(user_id):
    """Mettre à jour un utilisateur"""
    current_user = User.query.get(session['user_id'])
    user = User.query.get_or_404(user_id)
    
    # Vérifier les permissions
    if not current_user.is_admin:
        if current_user.role == 'department_manager':
            if user.department_id != current_user.department_id:
                return jsonify({'error': 'Accès non autorisé'}), 403
        else:
            return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        # Mise à jour des champs de base
        if 'first_name' in data:
            user.first_name = SecurityValidator.sanitize_input(data['first_name'])
        if 'last_name' in data:
            user.last_name = SecurityValidator.sanitize_input(data['last_name'])
        if 'email' in data:
            email = SecurityValidator.sanitize_input(data['email'])
            valid, error = SecurityValidator.validate_email(email)
            if valid:
                existing = User.query.filter_by(email=email).first()
                if existing and existing.id != user_id:
                    return jsonify({'error': 'Cet email existe déjà'}), 400
                user.email = email
        if 'phone' in data:
            user.phone = SecurityValidator.sanitize_input(data['phone'])
        
        # Mise à jour du rôle et permissions (admin uniquement)
        if current_user.is_admin:
            if 'role' in data:
                old_role = user.role
                new_role = data['role']
                user.set_role_permissions(new_role)
                
                # Si changement de department_manager
                if old_role == 'department_manager' and new_role != 'department_manager':
                    # Retirer comme manager du département
                    if user.department_id:
                        dept = Department.query.get(user.department_id)
                        if dept and dept.manager_id == user.id:
                            dept.manager_id = None
                
                elif new_role == 'department_manager' and user.department_id:
                    # Assigner comme manager
                    dept = Department.query.get(user.department_id)
                    if dept:
                        dept.manager_id = user.id
            
            if 'department_id' in data:
                old_dept_id = user.department_id
                new_dept_id = data['department_id']
                
                # Si c'était un manager, le retirer de l'ancien département
                if user.role == 'department_manager' and old_dept_id:
                    old_dept = Department.query.get(old_dept_id)
                    if old_dept and old_dept.manager_id == user.id:
                        old_dept.manager_id = None
                
                user.department_id = new_dept_id
                
                # Si c'est un manager, l'assigner au nouveau département
                if user.role == 'department_manager' and new_dept_id:
                    new_dept = Department.query.get(new_dept_id)
                    if new_dept:
                        new_dept.manager_id = user.id
            
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            # Permissions personnalisées
            if 'permissions' in data:
                perms = data['permissions']
                user.can_read = perms.get('read', user.can_read)
                user.can_write = perms.get('write', user.can_write)
                user.can_create = perms.get('create', user.can_create)
                user.can_update = perms.get('update', user.can_update)
                user.can_delete = perms.get('delete', user.can_delete)
                user.can_add_tables = perms.get('add_tables', user.can_add_tables)
                user.can_add_columns = perms.get('add_columns', user.can_add_columns)
        
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
@require_login
def delete_user(user_id):
    """Désactiver un utilisateur - PERMISSIONS STRICTES"""
    current_user = User.query.get(session['user_id'])
    
    # 🔒 VÉRIFICATION : Seuls admin et directeur_rh peuvent supprimer
    # Assistant admin NE PEUT PAS supprimer
    if not current_user.can_delete_users:
        return jsonify({
            'success': False,
            'error': 'Accès refusé. Vous n\'avez pas la permission de supprimer des utilisateurs.'
        }), 403
    
    # Ne pas se supprimer soi-même
    if user_id == session['user_id']:
        return jsonify({'error': 'Vous ne pouvez pas supprimer votre propre compte'}), 400
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Si c'est un manager, le retirer du département
        if user.role == 'department_manager' and user.department_id:
            dept = Department.query.get(user.department_id)
            if dept and dept.manager_id == user.id:
                dept.manager_id = None
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'user_deleted',
            'user',
            user_id,
            {'username': user.username, 'deleted_by': current_user.username}
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
    
    valid, error_msg = SecurityValidator.validate_password(new_password, user.username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        db.session.commit()
        
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


@users_bp.route('/manage', methods=['GET'])
@require_login
def manage_users_page():
    """Page de gestion des utilisateurs - AVEC VÉRIFICATION"""
    current_user = User.query.get(session['user_id'])
    
    # Seuls admin, directeur_rh et assistant_administratif peuvent accéder
    if not (current_user.is_admin or current_user.role in ['directeur_rh', 'assistant_administratif']):
        return redirect(url_for('dashboard'))
    
    return render_template('users_manage.html', user=current_user)