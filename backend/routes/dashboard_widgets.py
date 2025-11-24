# routes/dashboard_widgets.py - Nouveau fichier à créer
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import db
from models.user import User
from models.company import Department
from models.dashboard import DashboardWidget
from models.department_table import DepartmentTable, TableRow
from models.project import Project
from models.ticket import Ticket
from models.employee_request import EmployeeRequest
from models.payroll import Attendance, Payslip
from datetime import datetime, timedelta
from sqlalchemy import func
import json

dashboard_widgets_bp = Blueprint('dashboard_widgets', __name__, url_prefix='/api/dashboard')


def check_auth():
    """Vérifie l'authentification"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])


def get_accessible_departments(user):
    """Retourne les départements accessibles par l'utilisateur"""
    if user.is_admin or user.role == 'directeur_rh':
        return Department.query.filter_by(
            company_id=user.company_id,
            is_active=True
        ).all()
    elif user.department_id:
        return [Department.query.get(user.department_id)]
    return []


def get_date_range(time_filter):
    """Calcule les dates selon le filtre"""
    end_date = datetime.utcnow()
    
    if time_filter == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == 'week':
        start_date = end_date - timedelta(days=7)
    elif time_filter == 'month':
        start_date = end_date - timedelta(days=30)
    elif time_filter == 'quarter':
        start_date = end_date - timedelta(days=90)
    elif time_filter == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=7)
    
    return start_date, end_date


@dashboard_widgets_bp.route('/widgets/list', methods=['GET'])
def list_user_widgets():
    """Liste des widgets personnalisés de l'utilisateur"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widgets = DashboardWidget.query.filter_by(
        user_id=user.id,
        is_active=True
    ).order_by(DashboardWidget.position_order).all()
    
    return jsonify({
        'success': True,
        'widgets': [w.to_dict() for w in widgets]
    })


@dashboard_widgets_bp.route('/widgets/create', methods=['POST'])
def create_widget():
    """Créer un nouveau widget personnalisé"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    data = request.json
    
    # Vérifier les permissions pour le département
    department_id = data.get('department_id')
    if department_id:
        accessible_depts = get_accessible_departments(user)
        accessible_ids = [d.id for d in accessible_depts]
        
        if int(department_id) not in accessible_ids:
            return jsonify({'error': 'Accès non autorisé à ce département'}), 403
    elif not (user.is_admin or user.role == 'directeur_rh'):
        # Si pas admin/DRH, forcer le département de l'utilisateur
        department_id = user.department_id
    
    widget = DashboardWidget(
        user_id=user.id,
        title=data.get('title'),
        widget_type=data.get('widget_type'),
        chart_type=data.get('chart_type', 'bar'),
        data_source=data.get('data_source'),
        department_id=department_id,
        size=data.get('size', '2x1'),
        color_scheme=data.get('color_scheme', 'blue'),
        position_order=data.get('position_order', 0)
    )
    
    widget.set_filters(data.get('filters', {}))
    
    db.session.add(widget)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'widget': widget.to_dict()
    })


@dashboard_widgets_bp.route('/widgets/<int:widget_id>/update', methods=['PUT'])
def update_widget(widget_id):
    """Mettre à jour un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    data = request.json
    
    widget.title = data.get('title', widget.title)
    widget.widget_type = data.get('widget_type', widget.widget_type)
    widget.chart_type = data.get('chart_type', widget.chart_type)
    widget.data_source = data.get('data_source', widget.data_source)
    widget.size = data.get('size', widget.size)
    widget.color_scheme = data.get('color_scheme', widget.color_scheme)
    widget.position_order = data.get('position_order', widget.position_order)
    
    if 'department_id' in data:
        department_id = data['department_id']
        if department_id:
            accessible_depts = get_accessible_departments(user)
            accessible_ids = [d.id for d in accessible_depts]
            if int(department_id) not in accessible_ids:
                return jsonify({'error': 'Accès non autorisé à ce département'}), 403
        widget.department_id = department_id
    
    if 'filters' in data:
        widget.set_filters(data['filters'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'widget': widget.to_dict()
    })


@dashboard_widgets_bp.route('/widgets/<int:widget_id>/delete', methods=['DELETE'])
def delete_widget(widget_id):
    """Supprimer un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    db.session.delete(widget)
    db.session.commit()
    
    return jsonify({'success': True})


@dashboard_widgets_bp.route('/widgets/<int:widget_id>/data', methods=['GET'])
def get_widget_data(widget_id):
    """Récupérer les données d'un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    time_filter = request.args.get('time_filter', 'week')
    department_id = request.args.get('department_id')
    
    # Générer les données selon le type
    data = generate_widget_data(widget, user, time_filter, department_id)
    
    return jsonify({
        'success': True,
        'data': data
    })


def generate_widget_data(widget, user, time_filter, department_filter=None):
    """Génère les données pour un widget selon son type"""
    filters = widget.get_filters()
    metric = filters.get('metric', 'count')
    start_date, end_date = get_date_range(time_filter)
    
    data_source = widget.data_source
    department_id = department_filter or widget.department_id
    
    # Vérifier les permissions
    if department_id and not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id != int(department_id):
            return {'error': 'Accès non autorisé'}
    
    # Employés
    if data_source == 'employees':
        return get_employees_data(widget, user, metric, start_date, end_date, department_id)
    
    # Projets
    elif data_source == 'projects':
        return get_projects_data(widget, user, metric, start_date, end_date, department_id)
    
    # Tickets
    elif data_source == 'tickets':
        return get_tickets_data(widget, user, metric, start_date, end_date, department_id)
    
    # Demandes
    elif data_source == 'requests':
        return get_requests_data(widget, user, metric, start_date, end_date, department_id)
    
    # Tables personnalisées
    elif data_source == 'tables':
        return get_tables_data(widget, user, metric, start_date, end_date, department_id)
    
    # Présences
    elif data_source == 'attendance':
        return get_attendance_data(widget, user, metric, start_date, end_date, department_id)
    
    # Paie
    elif data_source == 'payroll':
        return get_payroll_data(widget, user, metric, start_date, end_date, department_id)
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_employees_data(widget, user, metric, start_date, end_date, department_id):
    """Données employés"""
    query = User.query.filter(
        User.company_id == user.company_id,
        User.is_active == True
    )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        query = query.filter_by(department_id=user.department_id)
    
    if metric == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Employés',
            'type': 'single',
            'change': 8
        }
    
    elif metric == 'by_role':
        roles = db.session.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.company_id == user.company_id,
            User.is_active == True
        )
        
        if department_id:
            roles = roles.filter_by(department_id=department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            roles = roles.filter_by(department_id=user.department_id)
        
        roles = roles.group_by(User.role).all()
        
        role_labels = {
            'admin': 'Administrateurs',
            'directeur_rh': 'Directeurs RH',
            'department_manager': 'Managers',
            'employee': 'Employés',
            'technician': 'Techniciens'
        }
        
        return {
            'labels': [role_labels.get(r.role, r.role) for r in roles],
            'datasets': [{
                'label': 'Distribution des rôles',
                'data': [r.count for r in roles]
            }],
            'type': 'chart'
        }
    
    elif metric == 'new_hires':
        query = query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        )
        
        daily_data = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.company_id == user.company_id,
            User.created_at >= start_date,
            User.created_at <= end_date
        )
        
        if department_id:
            daily_data = daily_data.filter_by(department_id=department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            daily_data = daily_data.filter_by(department_id=user.department_id)
        
        daily_data = daily_data.group_by(func.date(User.created_at)).all()
        
        return {
            'labels': [str(d.date) for d in daily_data],
            'datasets': [{
                'label': 'Nouvelles embauches',
                'data': [d.count for d in daily_data]
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_projects_data(widget, user, metric, start_date, end_date, department_id):
    """Données projets"""
    query = Project.query.filter(
        Project.company_id == user.company_id
    )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter_by(department_id=user.department_id)
    
    if metric == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Projets',
            'type': 'single'
        }
    
    elif metric == 'by_status':
        statuses = db.session.query(
            Project.status,
            func.count(Project.id).label('count')
        ).filter(
            Project.company_id == user.company_id
        )
        
        if department_id:
            statuses = statuses.filter_by(department_id=department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            if user.department_id:
                statuses = statuses.filter_by(department_id=user.department_id)
        
        statuses = statuses.group_by(Project.status).all()
        
        status_labels = {
            'planned': 'Planifiés',
            'active': 'Actifs',
            'completed': 'Terminés',
            'suspended': 'Suspendus',
            'cancelled': 'Annulés'
        }
        
        return {
            'labels': [status_labels.get(s.status, s.status) for s in statuses],
            'datasets': [{
                'label': 'Statuts des projets',
                'data': [s.count for s in statuses]
            }],
            'type': 'chart'
        }
    
    elif metric == 'completion_rate':
        completed = query.filter_by(status='completed').count()
        total = query.count()
        rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'value': f'{rate:.1f}%',
            'label': 'Taux de complétion',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_tickets_data(widget, user, metric, start_date, end_date, department_id):
    """Données tickets"""
    query = Ticket.query.filter(
        Ticket.created_at >= start_date,
        Ticket.created_at <= end_date
    )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter_by(department_id=user.department_id)
    
    if metric == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Tickets',
            'type': 'single'
        }
    
    elif metric == 'by_status':
        statuses = db.session.query(
            Ticket.status,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        if department_id:
            statuses = statuses.filter_by(department_id=department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            if user.department_id:
                statuses = statuses.filter_by(department_id=user.department_id)
        
        statuses = statuses.group_by(Ticket.status).all()
        
        status_labels = {
            'en_attente': 'En attente',
            'en_cours': 'En cours',
            'resolu': 'Résolus',
            'ferme': 'Fermés',
            'reouvert': 'Réouverts'
        }
        
        return {
            'labels': [status_labels.get(s.status, s.status) for s in statuses],
            'datasets': [{
                'label': 'Statuts des tickets',
                'data': [s.count for s in statuses]
            }],
            'type': 'chart'
        }
    
    elif metric == 'response_time':
        avg_time = db.session.query(
            func.avg(Ticket.resolution_time_minutes)
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.resolution_time_minutes.isnot(None)
        )
        
        if department_id:
            avg_time = avg_time.filter_by(department_id=department_id)
        
        avg_time = avg_time.scalar() or 0
        
        return {
            'value': f'{avg_time:.0f} min',
            'label': 'Temps de réponse moyen',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_requests_data(widget, user, metric, start_date, end_date, department_id):
    """Données demandes employés"""
    query = EmployeeRequest.query.filter(
        EmployeeRequest.created_at >= start_date,
        EmployeeRequest.created_at <= end_date
    )
    
    if not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if metric == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Demandes',
            'type': 'single'
        }
    
    elif metric == 'by_type':
        types = db.session.query(
            EmployeeRequest.type,
            func.count(EmployeeRequest.id).label('count')
        ).filter(
            EmployeeRequest.created_at >= start_date,
            EmployeeRequest.created_at <= end_date
        ).group_by(EmployeeRequest.type).all()
        
        type_labels = {
            'loan': 'Prêts',
            'leave': 'Congés',
            'permission': 'Permissions'
        }
        
        return {
            'labels': [type_labels.get(t.type, t.type) for t in types],
            'datasets': [{
                'label': 'Types de demandes',
                'data': [t.count for t in types]
            }],
            'type': 'chart'
        }
    
    elif metric == 'pending':
        count = query.filter_by(status='pending').count()
        return {
            'value': count,
            'label': 'Demandes en attente',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_tables_data(widget, user, metric, start_date, end_date, department_id):
    """Données tables personnalisées"""
    query = DepartmentTable.query.join(Department).filter(
        Department.company_id == user.company_id,
        DepartmentTable.is_active == True
    )
    
    if department_id:
        query = query.filter(Department.id == department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter(Department.id == user.department_id)
    
    if metric == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Tables',
            'type': 'single'
        }
    
    elif metric == 'entries_count':
        count = db.session.query(func.count(TableRow.id)).join(
            DepartmentTable
        ).join(
            Department
        ).filter(
            Department.company_id == user.company_id,
            TableRow.is_active == True
        )
        
        if department_id:
            count = count.filter(Department.id == department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            if user.department_id:
                count = count.filter(Department.id == user.department_id)
        
        count = count.scalar() or 0
        
        return {
            'value': count,
            'label': 'Entrées totales',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_attendance_data(widget, user, metric, start_date, end_date, department_id):
    """Données présences"""
    if not user.can_access_payroll:
        return {'error': 'Accès non autorisé'}
    
    query = Attendance.query.filter(
        Attendance.date >= start_date.date(),
        Attendance.date <= end_date.date()
    )
    
    if department_id:
        query = query.join(User).filter(User.department_id == department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if metric == 'present':
        count = query.filter_by(status='present').count()
        return {
            'value': count,
            'label': 'Présents',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


def get_payroll_data(widget, user, metric, start_date, end_date, department_id):
    """Données paie"""
    if not user.can_access_payroll:
        return {'error': 'Accès non autorisé'}
    
    query = Payslip.query.filter(
        Payslip.created_at >= start_date,
        Payslip.created_at <= end_date
    )
    
    if department_id:
        query = query.join(User).filter(User.department_id == department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if metric == 'total_salary':
        total = db.session.query(
            func.sum(Payslip.net_salary)
        ).filter(
            Payslip.created_at >= start_date,
            Payslip.created_at <= end_date
        ).scalar() or 0
        
        return {
            'value': float(total),
            'label': 'Masse salariale',
            'format': 'currency',
            'type': 'single'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}


@dashboard_widgets_bp.route('/layout/save', methods=['POST'])
def save_layout():
    """Sauvegarder le layout du dashboard"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    data = request.json
    layout = data.get('layout', [])
    
    # Mettre à jour les positions des widgets
    for item in layout:
        widget_id = int(item['id'])
        widget = DashboardWidget.query.get(widget_id)
        
        if widget and widget.user_id == user.id:
            widget.position_order = item.get('y', 0) * 100 + item.get('x', 0)
    
    db.session.commit()
    
    return jsonify({'success': True})