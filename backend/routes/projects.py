# routes/projects.py - VERSION COMPLÈTE AVEC TOUTES LES FONCTIONNALITÉS
"""Routes complètes pour la gestion de projets avec permissions"""
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


# ==================== HELPER: PERMISSIONS ====================

def can_manage_project(user, project):
    """Vérifie si l'utilisateur peut gérer le projet"""
    if user.is_admin:
        return True
    if project.project_manager_id == user.id:
        return True
    if user.role == 'department_manager' and user.department_id == project.department_id:
        return True
    return False


def can_edit_task(user, task):
    """Vérifie si l'utilisateur peut modifier la tâche"""
    if user.is_admin:
        return True
    if task.project.project_manager_id == user.id:
        return True
    if user.role == 'department_manager' and user.department_id == task.project.department_id:
        return True
    if task.assigned_to_id == user.id:
        return True
    return False


# ==================== PAGES HTML ====================

@projects_bp.route('/all')
@require_login
def projects_all_page():
    """Page: Liste de tous les projets"""
    user = User.query.get(session['user_id'])
    return render_template('projects_all.html', user=user)


@projects_bp.route('/<int:project_id>')
@require_login
def project_detail_page(project_id):
    """Page: Détails du projet"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and project.company_id != user.company_id:
        return redirect(url_for('projects.projects_all_page'))
    
    return render_template('project_detail.html', project=project, user=user)


@projects_bp.route('/gantt')
@require_login
def projects_gantt_page():
    """Page: Diagramme de Gantt"""
    user = User.query.get(session['user_id'])
    return render_template('projects_gantt.html', user=user)


@projects_bp.route('/kanban')
@require_login
def projects_kanban_page():
    """Page: Tableau Kanban"""
    user = User.query.get(session['user_id'])
    return render_template('projects_kanban.html', user=user)


@projects_bp.route('/calendar')
@require_login
def projects_calendar_page():
    """Page: Calendrier partagé"""
    user = User.query.get(session['user_id'])
    return render_template('projects_calendar.html', user=user)


@projects_bp.route('/tasks')
@require_login
def projects_tasks_page():
    """Page: Mes tâches"""
    user = User.query.get(session['user_id'])
    return render_template('projects_tasks.html', user=user)


@projects_bp.route('/create')
@require_login
def projects_create_page():
    """Page: Création de projet"""
    user = User.query.get(session['user_id'])
    return render_template('projects_create.html', user=user)


# ==================== API: PROJETS ====================

@projects_bp.route('/api/list', methods=['GET'])
@require_login
def list_projects():
    """Liste tous les projets avec filtres - VERSION DEBUG"""
    user = User.query.get(session['user_id'])
    print(f"DEBUG: User {user.id} - Admin: {user.is_admin} - Company: {user.company_id}")  # Debug
    
    status = request.args.get('status')
    department_id = request.args.get('department_id', type=int)
    
    # Debug: Vérifier les projets dans la base
    all_company_projects = Project.query.filter_by(company_id=user.company_id).all()
    print(f"DEBUG: Tous les projets de l'entreprise: {len(all_company_projects)}")
    for p in all_company_projects:
        print(f"  - Projet: {p.name} (ID: {p.id}, Status: {p.status})")
    
    if user.is_admin:
        query = Project.query.filter_by(company_id=user.company_id)
        print("DEBUG: Mode ADMIN - tous les projets de l'entreprise")
    else:
        query = Project.query.filter(
            and_(
                Project.company_id == user.company_id,
                or_(
                    Project.department_id == user.department_id,
                    Project.project_manager_id == user.id,
                    Project.members.any(ProjectMember.user_id == user.id)
                )
            )
        )
        print(f"DEBUG: Mode USER - département: {user.department_id}, PM: {user.id}")
    
    if status:
        query = query.filter_by(status=status)
        print(f"DEBUG: Filtre status: {status}")
    
    if department_id:
        query = query.filter_by(department_id=department_id)
        print(f"DEBUG: Filtre département: {department_id}")
    
    projects = query.filter(Project.archived_at.is_(None)).all()
    print(f"DEBUG: Projets après filtres: {len(projects)}")
    
    return jsonify({
        'success': True,
        'projects': [p.to_dict() for p in projects],
        'debug': {
            'total_company_projects': len(all_company_projects),
            'filtered_projects': len(projects),
            'user_company': user.company_id,
            'user_is_admin': user.is_admin
        }
    })

@projects_bp.route('/api/<int:project_id>', methods=['GET'])
@require_login
def get_project(project_id):
    """Récupérer un projet avec toutes ses données"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    if not user.is_admin and project.company_id != user.company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = project.to_dict()
    
    # Ajouter infos de permissions
    data['can_manage'] = can_manage_project(user, project)
    
    # Membres
    data['members'] = [{
        'id': m.id,
        'user_id': m.user_id,
        'name': m.user.get_full_name(),
        'role': m.role,
        'allocation': m.allocation_percentage
    } for m in project.members]
    
    # Tâches avec détails complets
    data['tasks'] = [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'status': t.status,
        'priority': t.priority,
        'progress_percentage': t.progress_percentage,
        'due_date': t.due_date.isoformat() if t.due_date else None,
        'start_date': t.start_date.isoformat() if t.start_date else None,
        'assigned_to': {
            'id': t.assigned_to.id,
            'name': t.assigned_to.get_full_name()
        } if t.assigned_to else None,
        'estimated_hours': t.estimated_hours,
        'actual_hours': t.actual_hours,
        'kanban_column': t.kanban_column
    } for t in project.tasks]
    
    # Jalons
    data['milestones'] = [{
        'id': m.id,
        'name': m.name,
        'description': m.description,
        'target_date': m.target_date.isoformat(),
        'status': m.status
    } for m in project.milestones]
    
    return jsonify({'success': True, 'project': data})


@projects_bp.route('/api/create', methods=['POST'])
@require_login
def create_project():
    """Créer un nouveau projet"""
    user = User.query.get(session['user_id'])
    data = request.get_json()
    
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    if not name:
        return jsonify({'error': 'Le nom du projet est requis'}), 400
    
    try:
        project_count = Project.query.filter_by(company_id=user.company_id).count()
        code = f"PROJ-{project_count + 1:04d}"
        
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
            methodology=data.get('methodology', 'agile'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        )
        
        if data.get('tags'):
            project.set_tags(data['tags'])
        
        db.session.add(project)
        db.session.flush()
        
        # Ajouter membres
        if data.get('members'):
            for member_data in data['members']:
                member = ProjectMember(
                    project_id=project.id,
                    user_id=member_data['user_id'],
                    role=member_data.get('role'),
                    allocation_percentage=member_data.get('allocation_percentage', 100)
                )
                db.session.add(member)
        
        db.session.commit()
        
        AuditLogger.log_action(user.id, 'project_created', 'project', project.id, {'name': name})
        
        return jsonify({
            'success': True,
            'message': 'Projet créé avec succès',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@projects_bp.route('/api/<int:project_id>/update', methods=['PUT'])
@require_login
def update_project(project_id):
    """Mettre à jour un projet"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    if not can_manage_project(user, project):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        if 'status' in data:
            project.status = data['status']
        if 'progress_percentage' in data:
            project.progress_percentage = data['progress_percentage']
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'project': project.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== API: TÂCHES - CRUD COMPLET ====================


@projects_bp.route('/api/tasks/<int:task_id>', methods=['GET'])
@require_login
def get_task(task_id):
    """Récupérer une tâche"""
    task = ProjectTask.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])
    
    data = task.to_dict()
    data['can_edit'] = can_edit_task(user, task)
    data['project_name'] = task.project.name
    
    return jsonify({'success': True, 'task': data})

@projects_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@require_login
def update_task(task_id):
    """Mettre à jour une tâche avec vérification de complétion du projet"""
    task = ProjectTask.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])
    
    if not can_edit_task(user, task):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        if 'title' in data:
            task.title = SecurityValidator.sanitize_input(data['title'])
        if 'description' in data:
            task.description = SecurityValidator.sanitize_input(data['description'])
        if 'status' in data:
            task.status = data['status']
            if data['status'] == 'completed':
                task.completed_at = datetime.utcnow()
                task.progress_percentage = 100
        if 'progress_percentage' in data:
            task.progress_percentage = data['progress_percentage']
        if 'priority' in data:
            task.priority = data['priority']
        if 'assigned_to_id' in data:
            task.assigned_to_id = data['assigned_to_id']
        if 'start_date' in data:
            task.start_date = datetime.fromisoformat(data['start_date']) if data['start_date'] else None
        if 'due_date' in data:
            task.due_date = datetime.fromisoformat(data['due_date']) if data['due_date'] else None
        if 'kanban_column' in data:
            task.kanban_column = data['kanban_column']
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Vérifier automatiquement la complétion du projet
        check_and_update_project_completion(task.project)
        
        return jsonify({
            'success': True,
            'message': 'Tâche mise à jour',
            'task': task.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@projects_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@require_login
def delete_task(task_id):
    """Supprimer une tâche"""
    task = ProjectTask.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])
    
    if not can_manage_project(user, task.project):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tâche supprimée'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== API: MES TÂCHES ====================

@projects_bp.route('/api/tasks/my-tasks', methods=['GET'])
@require_login
def get_my_tasks():
    """Récupérer les tâches assignées à l'utilisateur"""
    user = User.query.get(session['user_id'])
    
    tasks = ProjectTask.query.join(Project).filter(
        ProjectTask.assigned_to_id == user.id,
        Project.company_id == user.company_id
    ).all()
    
    return jsonify({
        'success': True,
        'tasks': [{
            **t.to_dict(),
            'project_name': t.project.name
        } for t in tasks]
    })


@projects_bp.route('/api/tasks/assigned-by-me', methods=['GET'])
@require_login
def get_tasks_assigned_by_me():
    """Tâches créées par l'utilisateur"""
    user = User.query.get(session['user_id'])
    
    tasks = ProjectTask.query.join(Project).filter(
        ProjectTask.created_by_id == user.id,
        Project.company_id == user.company_id
    ).all()
    
    return jsonify({
        'success': True,
        'tasks': [{
            **t.to_dict(),
            'project_name': t.project.name
        } for t in tasks]
    })


@projects_bp.route('/api/tasks/all', methods=['GET'])
@require_login
def get_all_tasks():
    """Toutes les tâches (admin/manager)"""
    user = User.query.get(session['user_id'])
    
    if user.is_admin:
        tasks = ProjectTask.query.join(Project).filter(
            Project.company_id == user.company_id
        ).all()
    elif user.role == 'department_manager':
        tasks = ProjectTask.query.join(Project).filter(
            Project.department_id == user.department_id
        ).all()
    else:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'tasks': [{
            **t.to_dict(),
            'project_name': t.project.name
        } for t in tasks]
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
        columns[column].append({
            **task.to_dict(),
            'assigned_to': {
                'id': task.assigned_to.id,
                'name': task.assigned_to.get_full_name()
            } if task.assigned_to else None
        })
    
    return jsonify({
        'success': True,
        'columns': columns
    })


@projects_bp.route('/api/kanban/move-task', methods=['POST'])
@require_login
def move_kanban_task():
    """Déplacer une tâche dans Kanban"""
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    task = ProjectTask.query.get_or_404(data['task_id'])
    
    if not can_edit_task(user, task):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    task.kanban_column = data['target_column']
    
    # Auto-update status
    status_map = {
        'backlog': 'todo',
        'todo': 'todo',
        'in_progress': 'in_progress',
        'in_review': 'in_review',
        'completed': 'completed'
    }
    task.status = status_map.get(data['target_column'], task.status)
    
    if task.status == 'completed':
        task.completed_at = datetime.utcnow()
        task.progress_percentage = 100
    
    db.session.commit()
    
    return jsonify({'success': True})


# ==================== API: GANTT ====================

@projects_bp.route('/api/gantt/<int:project_id>', methods=['GET'])
@require_login
def get_gantt_data(project_id):
    """Données pour Gantt"""
    project = Project.query.get_or_404(project_id)
    
    tasks_data = []
    links_data = []
    
    for task in project.tasks:
        if task.start_date and task.due_date:
            tasks_data.append({
                'id': task.id,
                'text': task.title,
                'start_date': task.start_date.isoformat(),
                'end_date': task.due_date.isoformat(),
                'progress': task.progress_percentage / 100,
                'priority': task.priority,
                'status': task.status,
                'type': 'task'
            })
    
    return jsonify({
        'success': True,
        'data': {
            'tasks': tasks_data,
            'links': links_data
        }
    })


@projects_bp.route('/api/<int:project_id>/tasks', methods=['POST'])
@require_login
def create_task(project_id):
    """Créer une tâche - CORRIGÉ"""
    project = Project.query.get_or_404(project_id)  # Doit retourner 404 si projet non trouvé
    user = User.query.get(session['user_id'])
    
    if not can_manage_project(user, project):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        task = ProjectTask(
            project_id=project_id,
            title=SecurityValidator.sanitize_input(data['title']),
            description=SecurityValidator.sanitize_input(data.get('description', '')),
            assigned_to_id=data.get('assigned_to_id'),
            priority=data.get('priority', 'P3'),
            status='todo',
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            estimated_hours=data.get('estimated_hours'),
            kanban_column=data.get('kanban_column', 'backlog'),
            created_by_id=user.id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tâche créée avec succès',
            'task': task.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
# ==================== API: COMPLÉTION AUTOMATIQUE ====================

def check_and_update_project_completion(project):
    """Vérifie et met à jour automatiquement le statut du projet"""
    from datetime import date
    
    # 1. Vérifier si toutes les tâches sont complétées
    total_tasks = len(project.tasks)
    if total_tasks > 0:
        completed_tasks = sum(1 for task in project.tasks if task.status == 'completed')
        project.progress_percentage = int((completed_tasks / total_tasks) * 100)
        
        # Si toutes les tâches sont complétées
        if completed_tasks == total_tasks and project.status != 'completed':
            project.status = 'completed'
            project.updated_at = datetime.utcnow()
            
            # Logger l'événement
            AuditLogger.log_action(
                None,
                'project_auto_completed',
                'project',
                project.id,
                {'reason': 'all_tasks_completed'}
            )
    
    # 2. Vérifier si la date de fin est dépassée
    if project.end_date and date.today() > project.end_date:
        if project.status == 'active' and project.progress_percentage < 100:
            # Projet en retard
            project.status = 'delayed'
        elif project.progress_percentage == 100 and project.status != 'completed':
            # Projet terminé après la deadline
            project.status = 'completed'
    
    # 3. Vérifier les jalons
    if project.milestones:
        for milestone in project.milestones:
            if milestone.target_date < date.today() and milestone.status == 'pending':
                milestone.status = 'missed'
    
    db.session.commit()


@projects_bp.route('/api/<int:project_id>/check-completion', methods=['POST'])
@require_login
def check_project_completion(project_id):
    """Vérifier manuellement la complétion du projet"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    if not can_manage_project(user, project):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        check_and_update_project_completion(project)
        
        return jsonify({
            'success': True,
            'message': 'Statut du projet vérifié',
            'project': project.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/api/<int:project_id>/mark-complete', methods=['POST'])
@require_login
def mark_project_complete(project_id):
    """Marquer manuellement un projet comme terminé"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get(session['user_id'])
    
    if not can_manage_project(user, project):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        project.status = 'completed'
        project.progress_percentage = 100
        project.updated_at = datetime.utcnow()
        
        # Marquer toutes les tâches comme complétées
        for task in project.tasks:
            if task.status != 'completed':
                task.status = 'completed'
                task.progress_percentage = 100
                task.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        AuditLogger.log_action(
            user.id,
            'project_manually_completed',
            'project',
            project.id,
            {}
        )
        
        return jsonify({
            'success': True,
            'message': 'Projet marqué comme terminé',
            'project': project.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# ==================== API: CALENDRIER ====================

@projects_bp.route('/api/calendar/events', methods=['GET'])
@require_login
def get_calendar_events():
    """Événements pour calendrier"""
    user = User.query.get(session['user_id'])
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    query = ProjectTask.query.join(Project).filter(
        Project.company_id == user.company_id
    )
    
    if start_date:
        query = query.filter(ProjectTask.due_date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(ProjectTask.due_date <= datetime.fromisoformat(end_date))
    
    tasks = query.all()
    
    events = []
    for task in tasks:
        if task.due_date:
            color = {
                'P1': '#dc3545',
                'P2': '#fd7e14',
                'P3': '#0d6efd',
                'P4': '#6c757d'
            }.get(task.priority, '#0d6efd')
            
            events.append({
                'id': task.id,
                'title': task.title,
                'start': task.start_date.isoformat() if task.start_date else task.due_date.isoformat(),
                'end': task.due_date.isoformat(),
                'backgroundColor': color,
                'priority': task.priority,
                'status': task.status,
                'assigned_to': task.assigned_to.get_full_name() if task.assigned_to else None
            })
    
    return jsonify({'success': True, 'events': events})