# routes/dashboard.py
"""Routes pour le dashboard Power BI personnalisable"""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import db
from models.user import User
from models.company import Department, Company
from models.dashboard import DashboardWidget
from models.department_table import DepartmentTable, TableRow
from models.project import Project, ProjectTask
from models.ticket import Ticket
from models.employee_request import EmployeeRequest
from models.payroll import Attendance, Payslip
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, and_, or_
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def check_auth():
    """Vérifie l'authentification"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

def get_accessible_departments(user):
    """Retourne les départements accessibles par l'utilisateur"""
    if user.is_admin or user.role == 'directeur_rh':
        # Admin et DRH voient tous les départements
        return Department.query.filter_by(
            company_id=user.company_id,
            is_active=True,
            deleted_at=None
        ).all()
    elif user.department_id:
        # Autres users : seulement leur département
        dept = Department.query.get(user.department_id)
        return [dept] if dept and dept.deleted_at is None else []
    return []

def get_date_range(time_filter, start_date=None, end_date=None):
    """Calcule les dates selon le filtre"""
    end = datetime.utcnow()
    
    if time_filter == 'custom' and start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            return start, end
        except:
            pass
    
    if time_filter == 'today':
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == 'week':
        start = end - timedelta(days=7)
    elif time_filter == 'month':
        start = end - timedelta(days=30)
    elif time_filter == 'quarter':
        start = end - timedelta(days=90)
    elif time_filter == 'year':
        start = end - timedelta(days=365)
    else:
        start = end - timedelta(days=7)
    
    return start, end

# ==================== ROUTES PRINCIPALES ====================

@dashboard_bp.route('/page', methods=['GET'])
def dashboard_page():
    """Page du dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_active:
        session.clear()
        return redirect(url_for('auth.login_page'))
    
    return render_template('dashboard.html', user=user)

@dashboard_bp.route('/widgets/list', methods=['GET'])
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

@dashboard_bp.route('/widgets/create', methods=['POST'])
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
    
    try:
        widget = DashboardWidget(
            user_id=user.id,
            title=data.get('title', 'Nouveau Widget'),
            widget_type=data.get('widget_type', 'count'),
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
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

@dashboard_bp.route('/widgets/<int:widget_id>/update', methods=['PUT'])
def update_widget(widget_id):
    """Mettre à jour un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    data = request.json
    
    try:
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
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

@dashboard_bp.route('/widgets/<int:widget_id>/delete', methods=['DELETE'])
def delete_widget(widget_id):
    """Supprimer un widget"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    widget = DashboardWidget.query.get_or_404(widget_id)
    
    if widget.user_id != user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    try:
        db.session.delete(widget)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

@dashboard_bp.route('/widgets/<int:widget_id>/data', methods=['GET'])
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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Générer les données selon le type
    data = generate_widget_data(widget, user, time_filter, department_id, start_date, end_date)
    
    return jsonify({
        'success': True,
        'data': data
    })

# ==================== GÉNÉRATION DES DONNÉES ====================

def generate_widget_data(widget, user, time_filter, department_filter=None, start_date=None, end_date=None):
    """Génère les données pour un widget selon son type"""
    filters = widget.get_filters()
    metric = filters.get('metric', 'count')
    start, end = get_date_range(time_filter, start_date, end_date)
    
    data_source = widget.data_source
    department_id = department_filter or widget.department_id
    
    # Vérifier les permissions
    if department_id and not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id != int(department_id):
            return {'error': 'Accès non autorisé'}
    
    # Router vers la fonction appropriée
    if data_source == 'employees':
        return get_employees_data(widget, user, metric, start, end, department_id)
    elif data_source == 'projects':
        return get_projects_data(widget, user, metric, start, end, department_id)
    elif data_source == 'tickets':
        return get_tickets_data(widget, user, metric, start, end, department_id)
    elif data_source == 'requests':
        return get_requests_data(widget, user, metric, start, end, department_id)
    elif data_source == 'tables':
        return get_tables_data(widget, user, metric, start, end, department_id)
    elif data_source == 'attendance':
        return get_attendance_data(widget, user, metric, start, end, department_id)
    elif data_source == 'payroll':
        return get_payroll_data(widget, user, metric, start, end, department_id)
    elif data_source == 'departments':
        return get_departments_data(widget, user, metric, start, end, department_id)
    elif data_source == 'tasks':
        return get_tasks_data(widget, user, metric, start, end, department_id)
    
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
        
        # Calculer le changement
        prev_start = start_date - (end_date - start_date)
        prev_count = User.query.filter(
            User.company_id == user.company_id,
            User.is_active == True,
            User.created_at >= prev_start,
            User.created_at < start_date
        )
        if department_id:
            prev_count = prev_count.filter_by(department_id=department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            prev_count = prev_count.filter_by(department_id=user.department_id)
        prev_count = prev_count.count()
        
        change = ((count - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        return {
            'value': count,
            'label': 'Employés Actifs',
            'type': 'single',
            'change': round(change, 1),
            'format': 'number'
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
            'assistant_administratif': 'Assistants Admin',
            'department_manager': 'Managers',
            'employee': 'Employés',
            'technician': 'Techniciens'
        }
        
        return {
            'labels': [role_labels.get(r.role, r.role) for r in roles],
            'datasets': [{
                'label': 'Distribution des rôles',
                'data': [r.count for r in roles],
                'backgroundColor': ['#0078d4', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4']
            }],
            'type': 'chart'
        }
    
    elif metric == 'new_hires':
        query = query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        )
        
        # Grouper par jour
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
            'labels': [d.date.strftime('%d/%m') for d in daily_data],
            'datasets': [{
                'label': 'Nouvelles embauches',
                'data': [d.count for d in daily_data],
                'borderColor': '#0078d4',
                'backgroundColor': 'rgba(0, 120, 212, 0.1)',
                'tension': 0.4,
                'fill': True
            }],
            'type': 'chart'
        }
    
    elif metric == 'by_department':
        depts = db.session.query(
            Department.name,
            func.count(User.id).label('count')
        ).join(
            User, User.department_id == Department.id
        ).filter(
            User.company_id == user.company_id,
            User.is_active == True,
            Department.is_active == True,
            Department.deleted_at == None
        ).group_by(Department.name).all()
        
        return {
            'labels': [d.name for d in depts],
            'datasets': [{
                'label': 'Employés par département',
                'data': [d.count for d in depts],
                'backgroundColor': ['#0078d4', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4']
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
        active_count = query.filter_by(status='active').count()
        
        return {
            'value': count,
            'label': 'Projets Totaux',
            'type': 'single',
            'sublabel': f'{active_count} actifs',
            'format': 'number'
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
                'data': [s.count for s in statuses],
                'backgroundColor': ['#0078d4', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444']
            }],
            'type': 'chart'
        }
    
    elif metric == 'completion_rate':
        total = query.count()
        completed = query.filter_by(status='completed').count()
        rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'value': f'{rate:.1f}%',
            'label': 'Taux de complétion',
            'type': 'single',
            'sublabel': f'{completed}/{total} projets',
            'format': 'percentage'
        }
    
    elif metric == 'progress_trend':
        projects = query.filter(
            Project.updated_at >= start_date,
            Project.updated_at <= end_date
        ).all()
        
        # Grouper par semaine
        weekly_progress = {}
        for project in projects:
            week = project.updated_at.isocalendar()[1]
            if week not in weekly_progress:
                weekly_progress[week] = []
            weekly_progress[week].append(project.progress_percentage)
        
        labels = [f'Sem {w}' for w in sorted(weekly_progress.keys())]
        data = [sum(weekly_progress[w]) / len(weekly_progress[w]) for w in sorted(weekly_progress.keys())]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Progression moyenne',
                'data': data,
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'tension': 0.4,
                'fill': True
            }],
            'type': 'chart'
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
        open_count = query.filter(Ticket.status.in_(['en_attente', 'en_cours', 'reouvert'])).count()
        
        return {
            'value': count,
            'label': 'Tickets Totaux',
            'type': 'single',
            'sublabel': f'{open_count} ouverts',
            'format': 'number'
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
                'data': [s.count for s in statuses],
                'backgroundColor': ['#f59e0b', '#0078d4', '#10b981', '#8b5cf6', '#ef4444']
            }],
            'type': 'chart'
        }
    
    elif metric == 'by_priority':
        priorities = db.session.query(
            Ticket.priority,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        if department_id:
            priorities = priorities.filter_by(department_id=department_id)
        
        priorities = priorities.group_by(Ticket.priority).all()
        
        priority_labels = {
            'critique': 'Critique',
            'haute': 'Haute',
            'normale': 'Normale',
            'basse': 'Basse'
        }
        
        return {
            'labels': [priority_labels.get(p.priority, p.priority) for p in priorities],
            'datasets': [{
                'label': 'Tickets par priorité',
                'data': [p.count for p in priorities],
                'backgroundColor': ['#ef4444', '#f59e0b', '#10b981', '#06b6d4']
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}

def get_tasks_data(widget, user, metric, start_date, end_date, department_id):
    """Données tâches de projets"""
    query = ProjectTask.query.join(Project).filter(
        Project.company_id == user.company_id
    )
    
    if department_id:
        query = query.filter(Project.department_id == department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter(Project.department_id == user.department_id)
    
    if metric == 'count':
        count = query.count()
        completed = query.filter_by(status='completed').count()
        
        return {
            'value': count,
            'label': 'Tâches Totales',
            'type': 'single',
            'sublabel': f'{completed} complétées',
            'format': 'number'
        }
    
    elif metric == 'by_status':
        statuses = db.session.query(
            ProjectTask.status,
            func.count(ProjectTask.id).label('count')
        ).join(Project).filter(
            Project.company_id == user.company_id
        )
        
        if department_id:
            statuses = statuses.filter(Project.department_id == department_id)
        
        statuses = statuses.group_by(ProjectTask.status).all()
        
        status_labels = {
            'todo': 'À faire',
            'in_progress': 'En cours',
            'in_review': 'En révision',
            'completed': 'Complétées',
            'blocked': 'Bloquées'
        }
        
        return {
            'labels': [status_labels.get(s.status, s.status) for s in statuses],
            'datasets': [{
                'label': 'Tâches par statut',
                'data': [s.count for s in statuses],
                'backgroundColor': ['#f59e0b', '#0078d4', '#8b5cf6', '#10b981', '#ef4444']
            }],
            'type': 'chart'
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
        pending = query.filter_by(status='pending').count()
        
        return {
            'value': count,
            'label': 'Demandes',
            'type': 'single',
            'sublabel': f'{pending} en attente',
            'format': 'number'
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
                'data': [t.count for t in types],
                'backgroundColor': ['#0078d4', '#10b981', '#f59e0b']
            }],
            'type': 'chart'
        }
    
    elif metric == 'by_status':
        statuses = db.session.query(
            EmployeeRequest.status,
            func.count(EmployeeRequest.id).label('count')
        ).filter(
            EmployeeRequest.created_at >= start_date,
            EmployeeRequest.created_at <= end_date
        ).group_by(EmployeeRequest.status).all()
        
        status_labels = {
            'pending': 'En attente',
            'approved': 'Approuvées',
            'rejected': 'Refusées'
        }
        
        return {
            'labels': [status_labels.get(s.status, s.status) for s in statuses],
            'datasets': [{
                'label': 'Statuts des demandes',
                'data': [s.count for s in statuses],
                'backgroundColor': ['#f59e0b', '#10b981', '#ef4444']
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}

def get_tables_data(widget, user, metric, start_date, end_date, department_id):
    """Données tables personnalisées"""
    query = DepartmentTable.query.join(Department).filter(
        Department.company_id == user.company_id,
        DepartmentTable.is_active == True,
        Department.deleted_at == None
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
            'label': 'Tables Personnalisées',
            'type': 'single',
            'format': 'number'
        }
    
    elif metric == 'entries_count':
        count = db.session.query(func.count(TableRow.id)).join(
            DepartmentTable
        ).join(
            Department
        ).filter(
            Department.company_id == user.company_id,
            TableRow.is_active == True,
            Department.deleted_at == None
        )
        
        if department_id:
            count = count.filter(Department.id == department_id)
        elif not (user.is_admin or user.role == 'directeur_rh'):
            if user.department_id:
                count = count.filter(Department.id == user.department_id)
        
        count = count.scalar() or 0
        
        return {
            'value': count,
            'label': 'Entrées Totales',
            'type': 'single',
            'format': 'number'
        }
    
    elif metric == 'by_table':
        tables = query.all()
        table_data = []
        
        for table in tables:
            entries_count = TableRow.query.filter_by(
                table_id=table.id,
                is_active=True
            ).count()
            table_data.append({
                'name': table.display_name,
                'count': entries_count
            })
        
        # Trier par nombre d'entrées
        table_data.sort(key=lambda x: x['count'], reverse=True)
        table_data = table_data[:10]  # Top 10
        
        return {
            'labels': [t['name'] for t in table_data],
            'datasets': [{
                'label': 'Entrées par table',
                'data': [t['count'] for t in table_data],
                'backgroundColor': '#0078d4'
            }],
            'type': 'chart'
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
        total = query.count()
        rate = (count / total * 100) if total > 0 else 0
        
        return {
            'value': f'{rate:.1f}%',
            'label': 'Taux de présence',
            'type': 'single',
            'sublabel': f'{count}/{total}',
            'format': 'percentage'
        }
    
    elif metric == 'trend':
        daily_data = db.session.query(
            Attendance.date,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.date >= start_date.date(),
            Attendance.date <= end_date.date(),
            Attendance.status == 'present'
        ).group_by(Attendance.date).order_by(Attendance.date).all()
        
        return {
            'labels': [d.date.strftime('%d/%m') for d in daily_data],
            'datasets': [{
                'label': 'Présences',
                'data': [d.count for d in daily_data],
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'tension': 0.4,
                'fill': True
            }],
            'type': 'chart'
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
        )
        
        if department_id:
            total = total.join(User).filter(User.department_id == department_id)
        
        total = total.scalar() or 0
        
        return {
            'value': float(total),
            'label': 'Masse Salariale',
            'type': 'single',
            'format': 'currency'
        }
    
    elif metric == 'trend':
        monthly_data = db.session.query(
            func.strftime('%Y-%m', Payslip.created_at).label('month'),
            func.sum(Payslip.net_salary).label('total')
        ).filter(
            Payslip.created_at >= start_date,
            Payslip.created_at <= end_date
        ).group_by(func.strftime('%Y-%m', Payslip.created_at)).all()
        
        return {
            'labels': [d.month for d in monthly_data],
            'datasets': [{
                'label': 'Masse salariale',
                'data': [float(d.total) for d in monthly_data],
                'borderColor': '#0078d4',
                'backgroundColor': 'rgba(0, 120, 212, 0.1)',
                'tension': 0.4,
                'fill': True
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}

def get_departments_data(widget, user, metric, start_date, end_date, department_id):
    """Données départements"""
    query = Department.query.filter(
        Department.company_id == user.company_id,
        Department.is_active == True,
        Department.deleted_at == None
    )
    
    if department_id:
        query = query.filter_by(id=department_id)
    elif not (user.is_admin or user.role == 'directeur_rh'):
        if user.department_id:
            query = query.filter_by(id=user.department_id)
    
    if metric == 'count':
        count = query.count()
        
        return {
            'value': count,
            'label': 'Départements Actifs',
            'type': 'single',
            'format': 'number'
        }
    
    elif metric == 'comparison':
        depts = query.all()
        
        return {
            'labels': [d.name for d in depts],
            'datasets': [{
                'label': 'Nombre d\'employés',
                'data': [len([u for u in d.employees if u.is_active]) for d in depts],
                'backgroundColor': '#0078d4'
            }],
            'type': 'chart'
        }
    
    return {'labels': [], 'datasets': [], 'type': 'chart'}

# ==================== TEMPLATES & SOURCES ====================

@dashboard_bp.route('/available-sources', methods=['GET'])
def get_available_sources():
    """Liste des sources de données disponibles selon les permissions"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    sources = [
        {'id': 'employees', 'label': 'Employés', 'icon': 'users'},
        {'id': 'departments', 'label': 'Départements', 'icon': 'building'},
        {'id': 'projects', 'label': 'Projets', 'icon': 'project-diagram'},
        {'id': 'tasks', 'label': 'Tâches', 'icon': 'tasks'},
        {'id': 'tickets', 'label': 'Tickets', 'icon': 'ticket-alt'},
        {'id': 'requests', 'label': 'Demandes', 'icon': 'file-alt'},
        {'id': 'tables', 'label': 'Tables', 'icon': 'table'}
    ]
    
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

@dashboard_bp.route('/templates', methods=['GET'])
def get_templates():
    """Templates de widgets prédéfinis"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    templates = [
        {
            'id': 'employee_count',
            'title': 'Nombre d\'employés',
            'widget_type': 'count',
            'data_source': 'employees',
            'chart_type': 'number',
            'icon': 'users',
            'metric': 'count'
        },
        {
            'id': 'role_distribution',
            'title': 'Distribution des rôles',
            'widget_type': 'distribution',
            'data_source': 'employees',
            'chart_type': 'doughnut',
            'icon': 'chart-pie',
            'metric': 'by_role'
        },
        {
            'id': 'new_hires',
            'title': 'Nouvelles embauches',
            'widget_type': 'trend',
            'data_source': 'employees',
            'chart_type': 'line',
            'icon': 'chart-line',
            'metric': 'new_hires'
        },
        {
            'id': 'project_status',
            'title': 'Statut des projets',
            'widget_type': 'distribution',
            'data_source': 'projects',
            'chart_type': 'bar',
            'icon': 'tasks',
            'metric': 'by_status'
        },
        {
            'id': 'ticket_status',
            'title': 'Tickets par statut',
            'widget_type': 'distribution',
            'data_source': 'tickets',
            'chart_type': 'pie',
            'icon': 'ticket-alt',
            'metric': 'by_status'
        },
        {
            'id': 'ticket_priority',
            'title': 'Tickets par priorité',
            'widget_type': 'distribution',
            'data_source': 'tickets',
            'chart_type': 'bar',
            'icon': 'exclamation-triangle',
            'metric': 'by_priority'
        },
        {
            'id': 'requests_type',
            'title': 'Types de demandes',
            'widget_type': 'distribution',
            'data_source': 'requests',
            'chart_type': 'doughnut',
            'icon': 'file-alt',
            'metric': 'by_type'
        },
        {
            'id': 'table_entries',
            'title': 'Entrées par table',
            'widget_type': 'comparison',
            'data_source': 'tables',
            'chart_type': 'bar',
            'icon': 'table',
            'metric': 'by_table'
        },
        {
            'id': 'dept_comparison',
            'title': 'Comparaison départements',
            'widget_type': 'comparison',
            'data_source': 'departments',
            'chart_type': 'bar',
            'icon': 'building',
            'metric': 'comparison'
        }
    ]
    
    # Ajouter templates RH si permissions
    if user.can_access_payroll:
        templates.extend([
            {
                'id': 'payroll_total',
                'title': 'Masse salariale',
                'widget_type': 'sum',
                'data_source': 'payroll',
                'chart_type': 'number',
                'icon': 'money-bill',
                'metric': 'total_salary'
            },
            {
                'id': 'attendance_rate',
                'title': 'Taux de présence',
                'widget_type': 'rate',
                'data_source': 'attendance',
                'chart_type': 'number',
                'icon': 'clock',
                'metric': 'present'
            },
            {
                'id': 'attendance_trend',
                'title': 'Évolution présences',
                'widget_type': 'trend',
                'data_source': 'attendance',
                'chart_type': 'line',
                'icon': 'chart-line',
                'metric': 'trend'
            }
        ])
    
    return jsonify({
        'success': True,
        'templates': templates
    })

@dashboard_bp.route('/layout/save', methods=['POST'])
def save_layout():
    """Sauvegarder le layout du dashboard"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    data = request.json
    layout = data.get('layout', [])
    
    try:
        # Mettre à jour les positions des widgets
        for item in layout:
            widget_id = int(item['id'])
            widget = DashboardWidget.query.get(widget_id)
            
            if widget and widget.user_id == user.id:
                # Calculer position_order basé sur x et y
                widget.position_order = item.get('y', 0) * 100 + item.get('x', 0)
        
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

# ==================== STATISTIQUES GLOBALES ====================

@dashboard_bp.route('/global-stats', methods=['GET'])
def get_global_stats():
    """Statistiques globales pour le header du dashboard"""
    user = check_auth()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    
    try:
        company = Company.query.get(user.company_id)
        
        # Départements
        dept_count = Department.query.filter_by(
            company_id=user.company_id,
            is_active=True,
            deleted_at=None
        ).count()
        
        # Employés
        emp_count = User.query.filter_by(
            company_id=user.company_id,
            is_active=True
        ).count()
        
        # Projets actifs
        proj_count = Project.query.filter_by(
            company_id=user.company_id,
            status='active'
        ).count()
        
        # Tickets ouverts
        ticket_count = Ticket.query.filter(
            Ticket.status.in_(['en_attente', 'en_cours', 'reouvert'])
        ).count()
        
        # Tables
        table_count = DepartmentTable.query.join(Department).filter(
            Department.company_id == user.company_id,
            DepartmentTable.is_active == True,
            Department.deleted_at == None
        ).count()
        
        # Entrées
        entry_count = db.session.query(func.count(TableRow.id)).join(
            DepartmentTable
        ).join(
            Department
        ).filter(
            Department.company_id == user.company_id,
            TableRow.is_active == True,
            Department.deleted_at == None
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'stats': {
                'company_name': company.name if company else '',
                'departments': dept_count,
                'employees': emp_count,
                'projects': proj_count,
                'tickets': ticket_count,
                'tables': table_count,
                'entries': entry_count
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500