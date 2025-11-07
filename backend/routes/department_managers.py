# routes/department_managers.py
"""Routes pour la gestion des chefs de département"""
from flask import Blueprint, request, jsonify, session
from database import db
from models.user import User
from models.company import Department
from utils.security import (
    SecurityValidator, require_login, require_admin, AuditLogger
)
from datetime import datetime

dept_managers_bp = Blueprint('dept_managers', __name__, url_prefix='/api/department-managers')


@dept_managers_bp.route('/assign', methods=['POST'])
@require_admin
def assign_manager():
    """Assigner un chef à un département"""
    data = request.get_json()
    
    department_id = data.get('department_id')
    user_id = data.get('user_id')
    
    if not department_id or not user_id:
        return jsonify({'error': 'department_id et user_id requis'}), 400
    
    department = Department.query.get_or_404(department_id)
    user = User.query.get_or_404(user_id)
    
    # Vérifier que l'utilisateur appartient à la même entreprise
    if user.company_id != department.company_id:
        return jsonify({'error': 'L\'utilisateur doit appartenir à la même entreprise'}), 400
    
    try:
        # Retirer l'ancien manager s'il existe
        old_manager_id = department.manager_id
        
        # Assigner le nouveau manager
        department.manager_id = user_id
        user.department_id = department_id
        user.role = 'manager'
        
        # Définir les permissions du manager
        department.manager_can_add_users = data.get('can_add_users', True)
        department.manager_can_edit_budget = data.get('can_edit_budget', False)
        department.manager_can_create_tables = data.get('can_create_tables', True)
        department.manager_can_delete_items = data.get('can_delete_items', True)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'manager_assigned',
            'department',
            department_id,
            {
                'user_id': user_id,
                'old_manager_id': old_manager_id,
                'username': user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'{user.username} assigné comme chef de département',
            'department': department.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_managers_bp.route('/remove/<int:department_id>', methods=['POST'])
@require_admin
def remove_manager(department_id):
    """Retirer le chef d'un département"""
    department = Department.query.get_or_404(department_id)
    
    if not department.manager_id:
        return jsonify({'error': 'Aucun chef assigné'}), 400
    
    try:
        old_manager = User.query.get(department.manager_id)
        if old_manager:
            old_manager.role = 'user'
        
        department.manager_id = None
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'manager_removed',
            'department',
            department_id,
            {'old_manager_id': old_manager.id if old_manager else None}
        )
        
        return jsonify({
            'success': True,
            'message': 'Chef de département retiré'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_managers_bp.route('/permissions/<int:department_id>', methods=['PUT'])
@require_admin
def update_manager_permissions(department_id):
    """Mettre à jour les permissions du chef de département"""
    department = Department.query.get_or_404(department_id)
    data = request.get_json()
    
    try:
        if 'can_add_users' in data:
            department.manager_can_add_users = data['can_add_users']
        if 'can_edit_budget' in data:
            department.manager_can_edit_budget = data['can_edit_budget']
        if 'can_create_tables' in data:
            department.manager_can_create_tables = data['can_create_tables']
        if 'can_delete_items' in data:
            department.manager_can_delete_items = data['can_delete_items']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Permissions mises à jour',
            'permissions': {
                'can_add_users': department.manager_can_add_users,
                'can_edit_budget': department.manager_can_edit_budget,
                'can_create_tables': department.manager_can_create_tables,
                'can_delete_items': department.manager_can_delete_items
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_managers_bp.route('/my-department', methods=['GET'])
@require_login
def get_my_department():
    """Récupérer le département géré par l'utilisateur connecté"""
    user = User.query.get(session['user_id'])
    
    # Trouver le département où l'utilisateur est manager
    department = Department.query.filter_by(manager_id=user.id).first()
    
    if not department:
        return jsonify({
            'success': False,
            'message': 'Vous n\'êtes pas chef de département'
        }), 404
    
    return jsonify({
        'success': True,
        'department': department.to_dict(),
        'permissions': {
            'can_add_users': department.manager_can_add_users,
            'can_edit_budget': department.manager_can_edit_budget,
            'can_create_tables': department.manager_can_create_tables,
            'can_delete_items': department.manager_can_delete_items
        }
    }), 200


@dept_managers_bp.route('/create-user', methods=['POST'])
@require_login
def manager_create_user():
    """Permet au chef de département de créer un utilisateur dans son département"""
    user = User.query.get(session['user_id'])
    
    # Vérifier que l'utilisateur est chef de département
    department = Department.query.filter_by(manager_id=user.id).first()
    
    if not department:
        return jsonify({'error': 'Vous n\'êtes pas chef de département'}), 403
    
    if not department.manager_can_add_users:
        return jsonify({'error': 'Permission refusée'}), 403
    
    data = request.get_json()
    
    username = SecurityValidator.sanitize_input(data.get('username', ''))
    email = SecurityValidator.sanitize_input(data.get('email', ''))
    password = data.get('password', '')
    
    # Validations
    valid, error_msg = SecurityValidator.validate_username(username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400
    
    valid, error_msg = SecurityValidator.validate_email(email)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Cet email existe déjà'}), 400
    
    valid, error_msg = SecurityValidator.validate_password(password, username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        new_user = User(
            username=username,
            email=email,
            first_name=SecurityValidator.sanitize_input(data.get('first_name', '')),
            last_name=SecurityValidator.sanitize_input(data.get('last_name', '')),
            phone=SecurityValidator.sanitize_input(data.get('phone', '')),
            company_id=user.company_id,
            department_id=department.id,
            role='user',
            is_admin=False,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'user_created_by_manager',
            'user',
            new_user.id,
            {
                'username': username,
                'department_id': department.id,
                'created_by_manager': user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur créé avec succès',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_managers_bp.route('/department-users', methods=['GET'])
@require_login
def get_department_users():
    """Liste des utilisateurs du département géré"""
    user = User.query.get(session['user_id'])
    
    department = Department.query.filter_by(manager_id=user.id).first()
    
    if not department:
        return jsonify({'error': 'Vous n\'êtes pas chef de département'}), 403
    
    users = User.query.filter_by(
        department_id=department.id,
        is_active=True
    ).all()
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    }), 200