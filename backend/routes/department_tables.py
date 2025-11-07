# routes/department_tables.py
"""Routes pour la gestion des tableaux personnalisés des départements"""
from flask import Blueprint, request, jsonify, session
from database import db
from models.user import User
from models.company import Department
from models.department_table import DepartmentTable, TableColumn, TableRow, TableTemplate
from utils.security import SecurityValidator, require_login, AuditLogger
from datetime import datetime
import json

dept_tables_bp = Blueprint('dept_tables', __name__, url_prefix='/api/department-tables')


def check_table_permission(table, user, permission_type='view'):
    """Vérifie les permissions d'accès à une table"""
    if table.department.deleted_at is not None:
        return False
    # Admin a tous les droits
    if user.is_admin:
        return True
    
    # Vérifier que l'utilisateur appartient au même département
    if user.company_id != table.department.company_id:
        return False
    
    # Vérifier les permissions spécifiques
    permission_field = f"{permission_type}_permission"
    permission = getattr(table, permission_field, 'department')
    
    if permission == 'all':
        return True
    elif permission == 'department':
        return user.department_id == table.department_id
    elif permission == 'manager_only':
        return user.id == table.department.manager_id or user.is_admin
    
    return False


@dept_tables_bp.route('/create', methods=['POST'])
@require_login
def create_table():
    """Créer une nouvelle table personnalisée"""
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    department_id = data.get('department_id')
    if not department_id:
        return jsonify({'error': 'department_id requis'}), 400
    
    department = Department.query.get_or_404(department_id)
    
    # Vérifier les permissions (manager ou admin)
    if not user.is_admin and user.id != department.manager_id:
        return jsonify({'error': 'Seul le chef de département peut créer des tables'}), 403
    
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    display_name = SecurityValidator.sanitize_input(data.get('display_name', ''))
    
    if not name or not display_name:
        return jsonify({'error': 'name et display_name requis'}), 400
    
    # Vérifier l'unicité du nom dans le département
    existing = DepartmentTable.query.filter_by(
        department_id=department_id,
        name=name
    ).first()
    
    if existing:
        return jsonify({'error': 'Une table avec ce nom existe déjà'}), 400
    
    try:
        table = DepartmentTable(
            department_id=department_id,
            name=name,
            display_name=display_name,
            description=SecurityValidator.sanitize_input(data.get('description', '')),
            icon=data.get('icon', 'table'),
            allow_import=data.get('allow_import', True),
            allow_export=data.get('allow_export', True),
            view_permission=data.get('view_permission', 'department'),
            edit_permission=data.get('edit_permission', 'department'),
            delete_permission=data.get('delete_permission', 'manager_only'),
            created_by_id=user.id
        )
        
        db.session.add(table)
        db.session.flush()
        
        # Créer les colonnes
        columns_data = data.get('columns', [])
        for idx, col_data in enumerate(columns_data):
            column = TableColumn(
                table_id=table.id,
                name=SecurityValidator.sanitize_input(col_data['name']),
                display_name=SecurityValidator.sanitize_input(col_data['display_name']),
                data_type=col_data['data_type'],
                is_required=col_data.get('is_required', False),
                is_unique=col_data.get('is_unique', False),
                default_value=col_data.get('default_value'),
                order=col_data.get('order', idx),
                width=col_data.get('width'),
                is_visible=col_data.get('is_visible', True),
                is_sortable=col_data.get('is_sortable', True),
                is_filterable=col_data.get('is_filterable', True),
                display_format=col_data.get('display_format'),
                prefix=col_data.get('prefix'),
                suffix=col_data.get('suffix')
            )
            
            if 'type_config' in col_data:
                column.set_config(col_data['type_config'])
            
            if 'validation_rules' in col_data:
                column.set_validation_rules(col_data['validation_rules'])
            
            db.session.add(column)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'table_created',
            'department_table',
            table.id,
            {'name': name, 'department_id': department_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Table créée avec succès',
            'table': table.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_tables_bp.route('/list/<int:department_id>', methods=['GET'])
@require_login
def list_tables(department_id):
    """Lister les tables d'un département"""
    user = User.query.get(session['user_id'])
    department = Department.query.get_or_404(department_id)
    
    # Vérifier les permissions
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    tables = DepartmentTable.query.filter_by(
        department_id=department_id,
        is_active=True
    ).all()
    
    # Filtrer selon les permissions
    accessible_tables = []
    for table in tables:
        if check_table_permission(table, user, 'view'):
            accessible_tables.append(table.to_dict(include_columns=True))
    
    return jsonify({
        'success': True,
        'tables': accessible_tables
    }), 200


@dept_tables_bp.route('/get/<int:table_id>', methods=['GET'])
@require_login
def get_table(table_id):
    """Récupérer une table avec ses données"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'view'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    include_rows = request.args.get('include_rows', 'true').lower() == 'true'
    
    return jsonify({
        'success': True,
        'table': table.to_dict(include_columns=True, include_rows=include_rows)
    }), 200


@dept_tables_bp.route('/update/<int:table_id>', methods=['PUT'])
@require_login
def update_table(table_id):
    """Mettre à jour une table"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'edit'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        if 'display_name' in data:
            table.display_name = SecurityValidator.sanitize_input(data['display_name'])
        if 'description' in data:
            table.description = SecurityValidator.sanitize_input(data['description'])
        if 'icon' in data:
            table.icon = data['icon']
        
        table.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'table': table.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_tables_bp.route('/delete/<int:table_id>', methods=['DELETE'])
@require_login
def delete_table(table_id):
    """Supprimer une table"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'delete'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        table.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Table supprimée'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# ============= GESTION DES LIGNES =============

@dept_tables_bp.route('/<int:table_id>/rows/add', methods=['POST'])
@require_login
def add_row(table_id):
    """Ajouter une ligne dans une table"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'edit'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    row_data = data.get('data', {})
    
    # Valider les données selon les colonnes
    validation_errors = validate_row_data(table, row_data)
    if validation_errors:
        return jsonify({'errors': validation_errors}), 400
    
    try:
        row = TableRow(
            table_id=table_id,
            created_by_id=user.id
        )
        row.set_data(row_data)
        
        db.session.add(row)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ligne ajoutée',
            'row': row.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_tables_bp.route('/rows/<int:row_id>', methods=['GET'])
@require_login
def get_row(row_id):
    """Récupérer une ligne"""
    user = User.query.get(session['user_id'])
    row = TableRow.query.get_or_404(row_id)
    
    if not check_table_permission(row.table, user, 'view'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'row': row.to_dict(include_audit=True)
    }), 200


@dept_tables_bp.route('/rows/<int:row_id>', methods=['PUT'])
@require_login
def update_row(row_id):
    """Mettre à jour une ligne"""
    user = User.query.get(session['user_id'])
    row = TableRow.query.get_or_404(row_id)
    
    if not check_table_permission(row.table, user, 'edit'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    row_data = data.get('data', {})
    
    validation_errors = validate_row_data(row.table, row_data)
    if validation_errors:
        return jsonify({'errors': validation_errors}), 400
    
    try:
        row.set_data(row_data)
        row.updated_at = datetime.utcnow()
        row.updated_by_id = user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'row': row.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@dept_tables_bp.route('/rows/<int:row_id>', methods=['DELETE'])
@require_login
def delete_row(row_id):
    """Supprimer une ligne"""
    user = User.query.get(session['user_id'])
    row = TableRow.query.get_or_404(row_id)
    
    if not check_table_permission(row.table, user, 'delete'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        db.session.delete(row)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ligne supprimée'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# ============= GESTION DES COLONNES =============

@dept_tables_bp.route('/<int:table_id>/columns/add', methods=['POST'])
@require_login
def add_column(table_id):
    """Ajouter une colonne à une table"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'edit'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        column = TableColumn(
            table_id=table_id,
            name=SecurityValidator.sanitize_input(data['name']),
            display_name=SecurityValidator.sanitize_input(data['display_name']),
            data_type=data['data_type'],
            is_required=data.get('is_required', False),
            is_unique=data.get('is_unique', False),
            order=data.get('order', len(table.columns))
        )
        
        if 'type_config' in data:
            column.set_config(data['type_config'])
        
        db.session.add(column)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'column': column.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# ============= TEMPLATES =============

@dept_tables_bp.route('/templates', methods=['GET'])
@require_login
def list_templates():
    """Lister les templates disponibles"""
    category = request.args.get('category')
    
    query = TableTemplate.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    
    templates = query.all()
    
    return jsonify({
        'success': True,
        'templates': [t.to_dict() for t in templates]
    }), 200


@dept_tables_bp.route('/create-from-template', methods=['POST'])
@require_login
def create_from_template():
    """Créer une table depuis un template"""
    user = User.query.get(session['user_id'])
    data = request.get_json()
    
    template_id = data.get('template_id')
    department_id = data.get('department_id')
    custom_name = data.get('custom_name')
    
    template = TableTemplate.query.get_or_404(template_id)
    department = Department.query.get_or_404(department_id)
    
    # Vérifier permissions
    if not user.is_admin and user.id != department.manager_id:
        return jsonify({'error': 'Permission refusée'}), 403
    
    try:
        config = template.get_config()
        
        # Créer la table
        table = DepartmentTable(
            department_id=department_id,
            name=custom_name or template.name,
            display_name=custom_name or template.display_name,
            description=template.description,
            icon=template.icon,
            created_by_id=user.id
        )
        
        db.session.add(table)
        db.session.flush()
        
        # Créer les colonnes depuis le template
        for col_config in config.get('columns', []):
            column = TableColumn(
                table_id=table.id,
                **col_config
            )
            db.session.add(column)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'table': table.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# ============= STATISTIQUES =============

@dept_tables_bp.route('/<int:table_id>/stats', methods=['GET'])
@require_login
def get_table_stats(table_id):
    """Statistiques d'une table"""
    user = User.query.get(session['user_id'])
    table = DepartmentTable.query.get_or_404(table_id)
    
    if not check_table_permission(table, user, 'view'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    total_rows = table.rows.count()
    active_rows = TableRow.query.filter_by(table_id=table_id, is_active=True).count()
    
    # Statistiques par colonne numérique
    column_stats = {}
    for column in table.columns:
        if column.data_type in ['number', 'decimal']:
            values = []
            for row in table.rows:
                val = row.get_value(column.name)
                if val is not None:
                    try:
                        values.append(float(val))
                    except:
                        pass
            
            if values:
                column_stats[column.name] = {
                    'count': len(values),
                    'sum': sum(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
    
    return jsonify({
        'success': True,
        'stats': {
            'total_rows': total_rows,
            'active_rows': active_rows,
            'columns_count': len(table.columns),
            'column_stats': column_stats
        }
    }), 200


# ============= FONCTIONS UTILITAIRES =============

def validate_row_data(table, row_data):
    """Valide les données d'une ligne selon les colonnes"""
    errors = {}
    
    for column in table.columns:
        value = row_data.get(column.name)
        
        # Champ requis
        if column.is_required and (value is None or value == ''):
            errors[column.name] = f"{column.display_name} est requis"
            continue
        
        # Validation du type
        if value is not None and value != '':
            if column.data_type == 'number':
                try:
                    float(value)
                except ValueError:
                    errors[column.name] = f"{column.display_name} doit être un nombre"
            
            elif column.data_type == 'email':
                valid, msg = SecurityValidator.validate_email(str(value))
                if not valid:
                    errors[column.name] = msg
            
            elif column.data_type == 'phone':
                valid, msg = SecurityValidator.validate_phone(str(value))
                if not valid:
                    errors[column.name] = msg
        
        # Unicité
        if column.is_unique and value:
            existing = TableRow.query.filter_by(table_id=table.id).all()
            for row in existing:
                if row.get_value(column.name) == value:
                    errors[column.name] = f"Cette valeur existe déjà pour {column.display_name}"
                    break
    
    return errors