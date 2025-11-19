# routes/projects.py
"""Routes pour la gestion de projets"""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import db
from models.user import User
from models.project import (
    Project, ProjectTask, ProjectMilestone, ProjectMember,
    ProjectSprint, TaskTimeEntry, ProjectTemplate
)
from utils.security import require_login, SecurityValidator, AuditLogger
from datetime import datetime, timedelta
from sqlalchemy import or_, and_

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


# ==================== PAGES HTML ====================

@projects_bp.route('/all')
@require_login
def projects_all_page():
    """Page: Liste de tous les projets"""
    user = User.query.get(session['user_id'])
    return render_template('projects_all.html', user=user)


@projects_bp.route('/gantt')
@require_login
def projects_gantt_page():
    """Page: Diagramme de Gantt"""
    user = User.query.get(session['user_id'])
    return render_template('projects_gantt.html', user=user)


@projects_bp.route('/tasks')
@require_login
def projects_tasks_page():
    """Page: Affectation de tâches"""
    user = User.query.get(session['user_id'])
    return render_template('projects_tasks.html', user=user)


@projects_bp.route('/calendar')
@require_login
def projects_calendar_page():
    """Page: Calendrier partagé"""
    user = User.query.get(session['user_id'])
    return render_template('projects_calendar.html', user=user)


@projects_bp.route('/kanban')
@require_login
def projects_kanban_page():
    """Page: Tableau Kanban"""
    user = User.query.get(session['user_id'])
    return render_template('projects_kanban.html', user=user)


@projects_bp.route('/create')
@require_login
def projects_create_page():
    """Page: Création de projet"""
    user = User.query.get(session['user_id'])
    return render_template('projects_create.html', user=user)

@projects_bp.route('/api/tasks/my-tasks', methods=['GET'])
@require_login
def get_my_tasks():
    """Récupérer les tâches assignées à l'utilisateur connecté"""
    user = User.query.get(session['user_id'])
    
    tasks = ProjectTask.query.join(Project).filter(
        ProjectTask.assigned_to_id == user.id,
        Project.company_id == user.company_id
    ).all()
    
    return jsonify({
        'success': True,
        'tasks': [t.to_dict() for t in tasks]
    })

@projects_bp.route('/api/tasks/assigned-by-me', methods=['GET'])
@require_login
def get_tasks_assigned_by_me():
    """Récupérer les tâches assignées par l'utilisateur connecté"""
    user = User.query.get(session['user_id'])
    
    tasks = ProjectTask.query.join(Project).filter(
        ProjectTask.created_by_id == user.id,
        Project.company_id == user.company_id
    ).all()
    
    return jsonify({
        'success': True,
        'tasks': [t.to_dict() for t in tasks]
    })

@projects_bp.route('/api/tasks/all', methods=['GET'])
@require_login
def get_all_tasks():
    """Récupérer toutes les tâches (admin seulement)"""
    user = User.query.get(session['user_id'])
    
    if not user.is_admin:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    tasks = ProjectTask.query.join(Project).filter(
        Project.company_id == user.company_id
    ).all()
    
    return jsonify({
        'success': True,
        'tasks': [t.to_dict() for t in tasks]
    })
    
# ==================== API: GESTION PROJETS ====================

@projects_bp.route('/api/list', methods=['GET'])
@require_login
def list_projects():
    """Liste tous les projets avec filtres"""
    user = User.query.get(session['user_id'])
    
    # Filtres
    status = request.args.get('status')
    department_id = request.args.get('department_id', type=int)
    priority = request.args.get('priority')
    project_manager_id = request.args.get('project_manager_id', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base selon permissions
    if user.is_admin:
        query = Project.query.filter_by(company_id=user.company_id)
    else:
        # Voir projets de son département + projets où il est membre
        query = Project.query.filter(
            and_(
                Project.company_id == user.company_id,
                or_(
                    Project.department_id == user.department_id,
                    Project.members.any(ProjectMember.user_id == user.id)
                )
            )
        )
    
    # Appliquer filtres
    if status:
        query = query.filter_by(status=status)
    if department_id:
        query = query.filter_by(department_id=department_id)
    if priority:
        query = query.filter_by(priority=priority)
    if project_manager_id:
        query = query.filter_by(project_manager_id=project_manager_id)
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                Project.name.ilike(search_pattern),
                Project.description.ilike(search_pattern),
                Project.code.ilike(search_pattern)
            )
        )
    
    # Tri
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_by == 'progress':
        query = query.order_by(Project.progress_percentage.desc() if sort_order == 'desc' else Project.progress_percentage.asc())
    elif sort_by == 'deadline':
        query = query.order_by(Project.end_date.desc() if sort_order == 'desc' else Project.end_date.asc())
    else:
        query = query.order_by(Project.created_at.desc() if sort_order == 'desc' else Project.created_at.asc())
    
    projects = query.filter(Project.archived_at.is_(None)).all()
    
    return jsonify({
        'success': True,
        'projects': [p.to_dict() for p in projects]
    })


@projects_bp.route('/api/create', methods=['POST'])
@require_login
def create_project():
    """Créer un nouveau projet"""
    user = User.query.get(session['user_id'])
    data = request.get_json()
    
    # Validation
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    if not name:
        return jsonify({'error': 'Le nom du projet est requis'}), 400
    
    try:
        # Générer code unique
        project_count = Project.query.filter_by(company_id=user.company_id).count()
        code = f"PROJ-{project_count + 1:04d}"
        
        # Créer projet
        project = Project(
            name=name,
            description=SecurityValidator.sanitize_input(data.get('description', '')),
            code=code,
            company_id=user.company_id,
            department_id=data.get('department_id'),
            project_manager_id=data.get('project_manager_id') or user.id,
            created_by_id=user.id,
            priority=data.get('priority', 'normal'),
            project_type=data.get('project_type', 'internal'),
            visibility=data.get('visibility', 'department'),
            methodology=data.get('methodology', 'agile'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            total_budget=data.get('total_budget'),
            enable_gantt=data.get('enable_gantt', True),
            enable_kanban=data.get('enable_kanban', True),
            enable_time_tracking=data.get('enable_time_tracking', True),
            enable_budget_tracking=data.get('enable_budget_tracking', True)
        )
        
        # Tags
        if data.get('tags'):
            project.set_tags(data['tags'])
        
        # Configuration budget
        if data.get('budget_config'):
            project.set_budget_config(data['budget_config'])
        
        db.session.add(project)
        db.session.flush()
        
        # Ajouter membres d'équipe
        if data.get('members'):
            for member_data in data['members']:
                member = ProjectMember(
                    project_id=project.id,
                    user_id=member_data['user_id'],
                    role=member_data.get('role'),
                    allocation_percentage=member_data.get('allocation_percentage', 100)
                )
                db.session.add(member)
        
        # Ajouter jalons
        if data.get('milestones'):
            for milestone_data in data['milestones']:
                milestone = ProjectMilestone(
                    project_id=project.id,
                    name=milestone_data['name'],
                    target_date=datetime.fromisoformat(milestone_data['target_date']),
                    description=milestone_data.get('description'),
                    criteria=milestone_data.get('criteria')
                )
                db.session.add(milestone)
        
        # Créer sprints si Agile
        if data.get('sprints') and project.methodology == 'agile':
            sprint_duration = data['sprints'].get('duration_weeks', 2)
            sprint_count = data['sprints'].get('count', 4)
            
            current_date = project.start_date
            for i in range(sprint_count):
                sprint = ProjectSprint(
                    project_id=project.id,
                    name=f"Sprint {i+1}",
                    sprint_number=i+1,
                    start_date=current_date,
                    end_date=current_date + timedelta(weeks=sprint_duration)
                )
                db.session.add(sprint)
                current_date = sprint.end_date + timedelta(days=1)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'project_created',
            'project',
            project.id,
            {'name': name, 'code': code}
        )
        
        return jsonify({
            'success': True,
            'message': 'Projet créé avec succès',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@projects_bp.route('/api/<int:project_id>', methods=['GET'])
@require_login
def get_project(project_id):
    """Récupérer un projet"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    # Vérifier permissions
    if not user.is_admin and project.company_id != user.company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Données complètes
    data = project.to_dict()
    data['members'] = [{
        'user_id': m.user_id,
        'name': m.user.get_full_name(),
        'role': m.role,
        'allocation': m.allocation_percentage
    } for m in project.members]
    
    data['milestones'] = [{
        'id': m.id,
        'name': m.name,
        'target_date': m.target_date.isoformat(),
        'status': m.status
    } for m in project.milestones]
    
    return jsonify({'success': True, 'project': data})


# ==================== API: GESTION TÂCHES ====================

@projects_bp.route('/api/<int:project_id>/tasks', methods=['POST'])
@require_login
def create_task(project_id):
    """Créer une tâche"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    data = request.get_json()
    
    try:
        task = ProjectTask(
            project_id=project_id,
            title=SecurityValidator.sanitize_input(data['title']),
            description=SecurityValidator.sanitize_input(data.get('description', '')),
            task_type=data.get('task_type', 'task'),
            assigned_to_id=data.get('assigned_to_id'),
            priority=data.get('priority', 'P3'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            estimated_hours=data.get('estimated_hours'),
            sprint_id=data.get('sprint_id'),
            story_points=data.get('story_points'),
            created_by_id=user.id
        )
        
        if data.get('labels'):
            task.labels = json.dumps(data['labels'])
        
        if data.get('dependencies'):
            task.dependencies = json.dumps(data['dependencies'])
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@require_login
def update_task(task_id):
    """Mettre à jour une tâche"""
    task = ProjectTask.query.get_or_404(task_id)
    data = request.get_json()
    
    try:
        if 'title' in data:
            task.title = SecurityValidator.sanitize_input(data['title'])
        if 'status' in data:
            task.status = data['status']
            if data['status'] == 'completed':
                task.completed_at = datetime.utcnow()
                task.progress_percentage = 100
        if 'progress_percentage' in data:
            task.progress_percentage = data['progress_percentage']
        if 'kanban_column' in data:
            task.kanban_column = data['kanban_column']
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'task': task.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/api/<int:project_id>/tasks/list', methods=['GET'])
@require_login
def list_tasks(project_id):
    """Liste toutes les tâches d'un projet"""
    project = Project.query.get_or_404(project_id)
    
    status = request.args.get('status')
    assigned_to = request.args.get('assigned_to_id', type=int)
    
    query = ProjectTask.query.filter_by(project_id=project_id)
    
    if status:
        query = query.filter_by(status=status)
    if assigned_to:
        query = query.filter_by(assigned_to_id=assigned_to)
    
    tasks = query.all()
    
    return jsonify({
        'success': True,
        'tasks': [t.to_dict() for t in tasks]
    })


# ==================== API: GANTT ====================

@projects_bp.route('/api/gantt/<int:project_id>', methods=['GET'])
@require_login
def get_gantt_data(project_id):
    """Données pour diagramme de Gantt"""
    project = Project.query.get_or_404(project_id)
    
    # Préparer données pour lib Gantt (format dhtmlxGantt ou similaire)
    tasks_data = []
    links_data = []
    
    for task in project.tasks:
        tasks_data.append({
            'id': task.id,
            'text': task.title,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'duration': (task.due_date - task.start_date).days if task.start_date and task.due_date else 1,
            'progress': task.progress_percentage / 100,
            'parent': 0,
            'type': 'task'
        })
        
        # Dépendances
        for dep_id in task.get_dependencies():
            links_data.append({
                'id': f"{task.id}-{dep_id}",
                'source': dep_id,
                'target': task.id,
                'type': '0'  # finish_to_start
            })
    
    # Jalons
    for milestone in project.milestones:
        tasks_data.append({
            'id': f"m-{milestone.id}",
            'text': milestone.name,
            'start_date': milestone.target_date.isoformat(),
            'duration': 0,
            'parent': 0,
            'type': 'milestone'
        })
    
    return jsonify({
        'success': True,
        'data': {
            'tasks': tasks_data,
            'links': links_data
        }
    })


# ==================== API: KANBAN ====================

@projects_bp.route('/api/kanban/<int:project_id>', methods=['GET'])
@require_login
def get_kanban_data(project_id):
    """Données pour Kanban"""
    project = Project.query.get_or_404(project_id)
    
    columns = {
        'backlog': [],
        'todo': [],
        'in_progress': [],
        'in_review': [],
        'completed': []
    }
    
    for task in project.tasks:
        column = task.kanban_column or 'backlog'
        columns[column].append(task.to_dict())
    
    return jsonify({
        'success': True,
        'columns': columns
    })


@projects_bp.route('/api/kanban/move-task', methods=['POST'])
@require_login
def move_kanban_task():
    """Déplacer une tâche dans Kanban"""
    data = request.get_json()
    
    task = ProjectTask.query.get_or_404(data['task_id'])
    task.kanban_column = data['target_column']
    task.kanban_order = data.get('order', 0)
    
    # Auto-update status
    status_map = {
        'backlog': 'todo',
        'todo': 'todo',
        'in_progress': 'in_progress',
        'in_review': 'in_review',
        'completed': 'completed'
    }
    task.status = status_map.get(data['target_column'], task.status)
    
    db.session.commit()
    
    return jsonify({'success': True})


# ==================== API: CALENDRIER ====================

@projects_bp.route('/api/calendar/events', methods=['GET'])
@require_login
def get_calendar_events():
    """Événements pour calendrier"""
    user = User.query.get(session['user_id'])
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    department_id = request.args.get('department_id', type=int)
    
    # Query tâches
    query = ProjectTask.query.join(Project).filter(
        Project.company_id == user.company_id
    )
    
    if start_date:
        query = query.filter(ProjectTask.start_date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(ProjectTask.due_date <= datetime.fromisoformat(end_date))
    if department_id:
        query = query.filter(Project.department_id == department_id)
    
    tasks = query.all()
    
    events = []
    for task in tasks:
        events.append({
            'id': task.id,
            'title': task.title,
            'start': task.start_date.isoformat() if task.start_date else None,
            'end': task.due_date.isoformat() if task.due_date else None,
            'backgroundColor': get_priority_color(task.priority),
            'assigned_to': task.assigned_to.get_full_name() if task.assigned_to else None
        })
    
    return jsonify({'success': True, 'events': events})


def get_priority_color(priority):
    """Couleurs selon priorité"""
    colors = {
        'P1': '#dc3545',
        'P2': '#fd7e14',
        'P3': '#0d6efd',
        'P4': '#6c757d'
    }
    return colors.get(priority, '#0d6efd')
