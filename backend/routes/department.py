from flask import Blueprint, request, jsonify, session
from models.user import User, db
from models.company import Department, DepartmentField, DepartmentItem
from utils.security import SecurityValidator, require_login, require_admin, AuditLogger
from datetime import datetime
import json

department_bp = Blueprint('department', __name__, url_prefix='/department')


@department_bp.route('/create', methods=['POST'])
@require_login
def create_department():
    """Créer un nouveau département - VERSION CORRIGÉE POUR FLOWERP"""
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    # VÉRIFICATION RENFORCÉE : S'assurer que l'utilisateur a une company_id
    if not user.company_id:
        return jsonify({
            'success': False,
            'error': 'Vous devez d\'abord créer ou être associé à une entreprise'
        }), 403
    
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    if not name:
        return jsonify({
            'success': False,
            'error': 'Le nom du département est requis'
        }), 400
    
    # CORRECTION : Toujours utiliser la company_id de l'utilisateur connecté
    company_id = user.company_id
    
    try:
        department = Department(
            name=name,
            code=SecurityValidator.sanitize_input(data.get('code', '')),
            description=SecurityValidator.sanitize_input(data.get('description', ''), allow_html=True),
            company_id=company_id,  # CORRIGÉ : company_id obligatoire
            parent_id=data.get('parent_id'),
            manager_id=data.get('manager_id'),
            budget=data.get('budget', 0),
            budget_spent=data.get('budget_spent', 0),
            is_active=True
        )
        
        db.session.add(department)
        db.session.commit()
        
        # Créer les champs personnalisés si fournis
        custom_fields = data.get('custom_fields', [])
        for field_data in custom_fields:
            field = DepartmentField(
                department_id=department.id,
                name=SecurityValidator.sanitize_input(field_data['name']),
                field_type=field_data['field_type'],
                is_required=field_data.get('is_required', False),
                default_value=field_data.get('default_value'),
                options=json.dumps(field_data.get('options')) if field_data.get('options') else None,
                order=field_data.get('order', 0)
            )
            db.session.add(field)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'department_created',
            'department',
            department.id,
            {'name': name, 'company_id': company_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Département créé avec succès',
            'department': department.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la création: {str(e)}'
        }), 500


@department_bp.route('/list', methods=['GET'])
@require_login
def list_departments():
    """Lister les départements - VERSION CORRIGÉE avec deleted_at"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({
            'success': False,
            'error': 'Aucune entreprise associée à votre compte'
        }), 403
    
    company_id = user.company_id
    
    # Filtrer les départements non supprimés (deleted_at IS NULL)
    if not user.is_admin:
        departments = Department.query.filter(
            Department.company_id == company_id,
            Department.deleted_at.is_(None)
        ).all()
    else:
        departments = Department.query.filter(
            Department.company_id == company_id,
            Department.deleted_at.is_(None)
        ).all()
    
    return jsonify({
        'success': True,
        'departments': [dept.to_dict() for dept in departments],
        'count': len(departments)
    }), 200

@department_bp.route('/get/<int:dept_id>', methods=['GET'])
@require_login
def get_department(dept_id):
    """Récupérer un département non supprimé"""
    # Vérifier si le département existe et n'est pas supprimé
    department = Department.query.filter(
        Department.id == dept_id,
        Department.deleted_at.is_(None)
    ).first_or_404()
    
    user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    include_items = request.args.get('include_items', 'false').lower() == 'true'
    
    return jsonify({
        'success': True,
        'department': department.to_dict(include_items=include_items)
    }), 200
@department_bp.route('/update/<int:dept_id>', methods=['PUT'])
@require_login
def update_department(dept_id):
    """Mettre à jour un département"""
    department = Department.query.get_or_404(dept_id)
    user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    data = request.get_json()
    
    try:
        if 'name' in data:
            department.name = SecurityValidator.sanitize_input(data['name'])
        if 'code' in data:
            department.code = SecurityValidator.sanitize_input(data['code'])
        if 'description' in data:
            department.description = SecurityValidator.sanitize_input(data['description'], allow_html=True)
        if 'manager_id' in data:
            department.manager_id = data['manager_id']
        if 'budget' in data:
            department.budget = data['budget']
        if 'budget_spent' in data:
            department.budget_spent = data['budget_spent']
        if 'is_active' in data:
            department.is_active = data['is_active']
        
        department.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'department_updated',
            'department',
            dept_id,
            data
        )
        
        return jsonify({
            'success': True,
            'message': 'Département mis à jour',
            'department': department.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la mise à jour: {str(e)}'
        }), 500


@department_bp.route('/delete/<int:dept_id>', methods=['DELETE'])
@require_admin
def delete_department(dept_id):
    """Supprimer un département - VERSION SOFT DELETE"""
    department = Department.query.get_or_404(dept_id)
    
    try:
        # Logger AVANT suppression
        AuditLogger.log_action(
            session['user_id'],
            'department_deleted',
            'department',
            dept_id,
            {'name': department.name}
        )
        
        # SOFT DELETE avec deleted_at
        department.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Département supprimé'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la suppression: {str(e)}'
        }), 500

# Gestion des champs personnalisés
@department_bp.route('/<int:dept_id>/fields/add', methods=['POST'])
@require_login
def add_custom_field(dept_id):
    """Ajouter un champ personnalisé"""
    department = Department.query.get_or_404(dept_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    data = request.get_json()
    
    try:
        field = DepartmentField(
            department_id=dept_id,
            name=SecurityValidator.sanitize_input(data['name']),
            field_type=data['field_type'],
            is_required=data.get('is_required', False),
            default_value=data.get('default_value'),
            options=json.dumps(data.get('options')) if data.get('options') else None,
            order=data.get('order', 0)
        )
        
        db.session.add(field)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Champ ajouté',
            'field': field.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


# Gestion des items du département
@department_bp.route('/<int:dept_id>/items/add', methods=['POST'])
@require_login
def add_item(dept_id):
    """Ajouter un item au département"""
    department = Department.query.get_or_404(dept_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    data = request.get_json()
    
    try:
        item = DepartmentItem(
            department_id=dept_id,
            item_type=SecurityValidator.sanitize_input(data['item_type']),
            title=SecurityValidator.sanitize_input(data['title']),
            description=SecurityValidator.sanitize_input(data.get('description', ''), allow_html=True),
            status=data.get('status', 'active'),
            created_by_id=session['user_id']
        )
        
        # Données personnalisées
        if 'data' in data:
            item.set_data(data['data'])
        
        db.session.add(item)
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'item_added',
            'department_item',
            item.id,
            {'department_id': dept_id, 'item_type': data['item_type'], 'title': data['title']}
        )
        
        return jsonify({
            'success': True,
            'message': 'Item ajouté',
            'item': item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@department_bp.route('/<int:dept_id>/items/list', methods=['GET'])
@require_login
def list_items(dept_id):
    """Lister les items d'un département"""
    department = Department.query.get_or_404(dept_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    item_type = request.args.get('item_type')
    status = request.args.get('status', 'active')
    
    query = DepartmentItem.query.filter_by(department_id=dept_id)
    
    if item_type:
        query = query.filter_by(item_type=item_type)
    if status:
        query = query.filter_by(status=status)
    
    items = query.order_by(DepartmentItem.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items],
        'count': len(items)
    }), 200


@department_bp.route('/items/<int:item_id>/update', methods=['PUT'])
@require_login
def update_item(item_id):
    """Mettre à jour un item"""
    item = DepartmentItem.query.get_or_404(item_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and user.company_id != item.department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    data = request.get_json()
    
    try:
        if 'title' in data:
            item.title = SecurityValidator.sanitize_input(data['title'])
        if 'description' in data:
            item.description = SecurityValidator.sanitize_input(data['description'], allow_html=True)
        if 'status' in data:
            item.status = data['status']
        if 'data' in data:
            item.set_data(data['data'])
        
        item.updated_at = datetime.utcnow()
        item.updated_by_id = session['user_id']
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'item_updated',
            'department_item',
            item_id,
            data
        )
        
        return jsonify({
            'success': True,
            'message': 'Item mis à jour',
            'item': item.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@department_bp.route('/items/<int:item_id>/delete', methods=['DELETE'])
@require_login
def delete_item(item_id):
    """Supprimer un item"""
    item = DepartmentItem.query.get_or_404(item_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and user.company_id != item.department.company_id:
        return jsonify({
            'success': False,
            'error': 'Accès non autorisé'
        }), 403
    
    try:
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'item_deleted',
            'department_item',
            item_id,
            {'title': item.title}
        )
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item supprimé'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@department_bp.route('/stats', methods=['GET'])
@require_login
def department_stats():
    """Statistiques des départements pour l'entreprise de l'utilisateur"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({
            'success': False,
            'error': 'Aucune entreprise associée'
        }), 403
    
    try:
        # Compter les départements actifs
        total_departments = Department.query.filter_by(
            company_id=user.company_id, 
            is_active=True
        ).count()
        
        # Budget total
        total_budget_result = db.session.query(
            db.func.sum(Department.budget)
        ).filter_by(
            company_id=user.company_id, 
            is_active=True
        ).first()
        
        total_budget = float(total_budget_result[0]) if total_budget_result[0] else 0
        
        # Budget dépensé total
        total_spent_result = db.session.query(
            db.func.sum(Department.budget_spent)
        ).filter_by(
            company_id=user.company_id, 
            is_active=True
        ).first()
        
        total_spent = float(total_spent_result[0]) if total_spent_result[0] else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_departments': total_departments,
                'total_budget': total_budget,
                'total_spent': total_spent,
                'remaining_budget': total_budget - total_spent
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors du calcul des statistiques: {str(e)}'
        }), 500