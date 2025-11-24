# routes/dashboard_custom.py
"""Routes pour le dashboard personnalisable type Power BI"""
from flask import Blueprint, request, jsonify, session
from database import db
from models.user import User
from models.company import Department
from models.project import Project
from models.ticket import Ticket
from models.employee_request import EmployeeRequest
from models.payroll import Payslip, Attendance
from datetime import datetime, timedelta
from sqlalchemy import func, distinct
import json

dashboard_custom_bp = Blueprint('dashboard_custom', __name__, url_prefix='/api/dashboard')


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


@dashboard_custom_bp.route('/widgets/list', methods=['GET'])
def list_user_widgets():
    """Liste des widgets personnalisés de l'utilisateur"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    from models.dashboard import DashboardWidget
    
    widgets = DashboardWidget.query.filter_by(
        user_id=user.id,
        is_active=True
    ).order_by(DashboardWidget.position_order).all()
    
    return jsonify({
        'success': True,
        'widgets': [w.to_dict() for w in widgets]
    })


@dashboard_custom_bp.route('/widgets/create', methods=['POST'])
def create_widget():
    """Créer un nouveau widget personnalisé"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    from models.dashboard import DashboardWidget
    
    data = request.json
    
    # Vérifier les permissions
    widget_type = data.get('widget_type')
    department_id = data.get('department_id')
    
    if department_id:
        accessible_depts = get_accessible_departments(user)
        accessible_ids = [d.id for d in accessible_depts]
        
        if department_id not in accessible_ids:
            return jsonify({'error': 'Accès non autorisé à ce département'}), 403
    
    widget = DashboardWidget(
        user_id=user.id,
        title=data.get('title'),
        widget_type=widget_type,
        chart_type=data.get('chart_type', 'bar'),
        data_source=data.get('data_source'),
        department_id=department_id,
        filters=json.dumps(data.get('filters', {})),
        size=data.get('size', 'medium'),
        position_order=data.get('position_order', 0)
    )
    
    db.session.add(widget)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'widget': widget.to_dict()
    })


@dashboard_custom_bp.route('/widgets/<int:widget_id>/update', methods=['PUT'])
def update_widget(widget_id):
    """Mettre à jour un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    from models.dashboard import DashboardWidget
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    data = request.json
    
    widget.title = data.get('title', widget.title)
    widget.chart_type = data.get('chart_type', widget.chart_type)
    widget.size = data.get('size', widget.size)
    widget.position_order = data.get('position_order', widget.position_order)
    
    if 'filters' in data:
        widget.filters = json.dumps(data['filters'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'widget': widget.to_dict()
    })


@dashboard_custom_bp.route('/widgets/<int:widget_id>/delete', methods=['DELETE'])
def delete_widget(widget_id):
    """Supprimer un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    from models.dashboard import DashboardWidget
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    db.session.delete(widget)
    db.session.commit()
    
    return jsonify({'success': True})


@dashboard_custom_bp.route('/widgets/<int:widget_id>/data', methods=['GET'])
def get_widget_data(widget_id):
    """Récupérer les données d'un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    from models.dashboard import DashboardWidget
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    # Générer les données selon le type
    data = generate_widget_data(widget, user)
    
    return jsonify({
        'success': True,
        'data': data
    })


def generate_widget_data(widget, user):
    """Génère les données pour un widget selon son type"""
    filters = json.loads(widget.filters) if widget.filters else {}
    date_range = filters.get('date_range', 'week')
    
    # Calculer les dates
    end_date = datetime.utcnow()
    if date_range == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0)
    elif date_range == 'week':
        start_date = end_date - timedelta(days=7)
    elif date_range == 'month':
        start_date = end_date - timedelta(days=30)
    elif date_range == 'quarter':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=7)
    
    data_source = widget.data_source
    
    if data_source == 'employees':
        return get_employees_data(widget, user, start_date, end_date)
    elif data_source == 'projects':
        return get_projects_data(widget, user, start_date, end_date)
    elif data_source == 'tickets':
        return get_tickets_data(widget, user, start_date, end_date)
    elif data_source == 'requests':
        return get_requests_data(widget, user, start_date, end_date)
    elif data_source == 'attendance':
        return get_attendance_data(widget, user, start_date, end_date)
    elif data_source == 'payroll':
        return get_payroll_data(widget, user, start_date, end_date)
    elif data_source == 'departments':
        return get_departments_data(widget, user, start_date, end_date)
    
    return {'labels': [], 'datasets': []}


def get_employees_data(widget, user, start_date, end_date):
    """Données employés"""
    query = User.query.filter(
        User.company_id == user.company_id,
        User.is_active == True,
        User.created_at >= start_date,
        User.created_at <= end_date
    )
    
    # Filtrer par département si nécessaire
    if widget.department_id:
        query = query.filter_by(department_id=widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        query = query.filter_by(department_id=user.department_id)
    
    if widget.widget_type == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Employés',
            'type': 'single'
        }
    
    elif widget.widget_type == 'distribution':
        # Distribution par rôle
        roles = db.session.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.company_id == user.company_id,
            User.is_active == True
        )
        
        if widget.department_id:
            roles = roles.filter_by(department_id=widget.department_id)
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
    
    elif widget.widget_type == 'trend':
        # Tendance d'embauche
        daily_data = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.company_id == user.company_id,
            User.created_at >= start_date,
            User.created_at <= end_date
        )
        
        if widget.department_id:
            daily_data = daily_data.filter_by(department_id=widget.department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            daily_data = daily_data.filter_by(department_id=user.department_id)
        
        daily_data = daily_data.group_by(func.date(User.created_at)).all()
        
        return {
            'labels': [str(d.date) for d in daily_data],
            'datasets': [{
                'label': 'Nouveaux employés',
                'data': [d.count for d in daily_data]
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': []}


def get_projects_data(widget, user, start_date, end_date):
    """Données projets"""
    query = Project.query.filter(
        Project.company_id == user.company_id,
        Project.created_at >= start_date,
        Project.created_at <= end_date
    )
    
    if widget.department_id:
        query = query.filter_by(department_id=widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        query = query.filter_by(department_id=user.department_id)
    
    if widget.widget_type == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Projets',
            'type': 'single'
        }
    
    elif widget.widget_type == 'distribution':
        # Distribution par statut
        statuses = db.session.query(
            Project.status,
            func.count(Project.id).label('count')
        ).filter(
            Project.company_id == user.company_id
        )
        
        if widget.department_id:
            statuses = statuses.filter_by(department_id=widget.department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
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
    
    return {'labels': [], 'datasets': []}


def get_tickets_data(widget, user, start_date, end_date):
    """Données tickets"""
    query = Ticket.query.filter(
        Ticket.created_at >= start_date,
        Ticket.created_at <= end_date
    )
    
    if widget.department_id:
        query = query.filter_by(department_id=widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter_by(department_id=user.department_id)
    
    if widget.widget_type == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Tickets',
            'type': 'single'
        }
    
    elif widget.widget_type == 'distribution':
        # Distribution par statut
        statuses = db.session.query(
            Ticket.status,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        if widget.department_id:
            statuses = statuses.filter_by(department_id=widget.department_id)
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
    
    return {'labels': [], 'datasets': []}


def get_requests_data(widget, user, start_date, end_date):
    """Données demandes employés"""
    query = EmployeeRequest.query.filter(
        EmployeeRequest.created_at >= start_date,
        EmployeeRequest.created_at <= end_date
    )
    
    # Filtrer selon les permissions
    if not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            # Chef de département voit son département
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if widget.widget_type == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Demandes',
            'type': 'single'
        }
    
    elif widget.widget_type == 'distribution':
        # Distribution par type
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
    
    return {'labels': [], 'datasets': []}


def get_attendance_data(widget, user, start_date, end_date):
    """Données présences"""
    if not user.can_access_payroll:
        return {'error': 'Accès non autorisé'}
    
    query = Attendance.query.filter(
        Attendance.date >= start_date.date(),
        Attendance.date <= end_date.date()
    )
    
    if widget.department_id:
        query = query.join(User).filter(User.department_id == widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if widget.widget_type == 'trend':
        daily_data = db.session.query(
            Attendance.date,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.date >= start_date.date(),
            Attendance.date <= end_date.date()
        ).group_by(Attendance.date).all()
        
        return {
            'labels': [str(d.date) for d in daily_data],
            'datasets': [{
                'label': 'Présences',
                'data': [d.count for d in daily_data]
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': []}


def get_payroll_data(widget, user, start_date, end_date):
    """Données paie"""
    if not user.can_access_payroll:
        return {'error': 'Accès non autorisé'}
    
    query = Payslip.query.filter(
        Payslip.created_at >= start_date,
        Payslip.created_at <= end_date
    )
    
    if widget.department_id:
        query = query.join(User).filter(User.department_id == widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.join(User).filter(User.department_id == user.department_id)
    
    if widget.widget_type == 'sum':
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
    
    return {'labels': [], 'datasets': []}


def get_departments_data(widget, user, start_date, end_date):
    """Données départements"""
    query = Department.query.filter(
        Department.company_id == user.company_id,
        Department.is_active == True
    )
    
    if widget.department_id:
        query = query.filter_by(id=widget.department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter_by(id=user.department_id)
    
    if widget.widget_type == 'count':
        count = query.count()
        return {
            'value': count,
            'label': 'Départements',
            'type': 'single'
        }
    
    elif widget.widget_type == 'comparison':
        # Comparaison des départements
        depts = query.all()
        
        return {
            'labels': [d.name for d in depts],
            'datasets': [{
                'label': 'Nombre d\'employés',
                'data': [d.employees.count() for d in depts]
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': []}


@dashboard_custom_bp.route('/available-sources', methods=['GET'])
def get_available_sources():
    """Liste des sources de données disponibles selon les permissions"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    sources = []
    
    # Sources de base (tous)
    sources.extend([
        {'id': 'employees', 'label': 'Employés', 'icon': 'users'},
        {'id': 'departments', 'label': 'Départements', 'icon': 'building'},
        {'id': 'projects', 'label': 'Projets', 'icon': 'project-diagram'},
        {'id': 'tickets', 'label': 'Tickets', 'icon': 'ticket-alt'},
        {'id': 'requests', 'label': 'Demandes', 'icon': 'file-alt'}
    ])
    
    # Sources RH (admin + DRH)
    if user.can_access_payroll:
        sources.extend([
            {'id': 'payroll', 'label': 'Paie', 'icon': 'money-bill'},
            {'id': 'attendance', 'label': 'Présences', 'icon': 'clock'}
        ])
    
    return jsonify({
        'success': True,
        'sources': sources
    })


@dashboard_custom_bp.route('/templates', methods=['GET'])
def get_templates():
    """Templates de widgets prédéfinis"""
    templates = [
        {
            'id': 'employee_count',
            'title': 'Nombre d\'employés',
            'widget_type': 'count',
            'data_source': 'employees',
            'chart_type': 'number',
            'icon': 'users'
        },
        {
            'id': 'role_distribution',
            'title': 'Distribution des rôles',
            'widget_type': 'distribution',
            'data_source': 'employees',
            'chart_type': 'doughnut',
            'icon': 'chart-pie'
        },
        {
            'id': 'project_status',
            'title': 'Statut des projets',
            'widget_type': 'distribution',
            'data_source': 'projects',
            'chart_type': 'bar',
            'icon': 'tasks'
        },
        {
            'id': 'ticket_trend',
            'title': 'Évolution des tickets',
            'widget_type': 'trend',
            'data_source': 'tickets',
            'chart_type': 'line',
            'icon': 'chart-line'
        },
        {
            'id': 'payroll_sum',
            'title': 'Masse salariale',
            'widget_type': 'sum',
            'data_source': 'payroll',
            'chart_type': 'number',
            'icon': 'money-bill',
            'requires_permission': 'can_access_payroll'
        }
    ]
    
    return jsonify({
        'success': True,
        'templates': templates
    })