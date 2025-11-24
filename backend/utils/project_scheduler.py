from database import db
from models.project import Project, ProjectMilestone
from datetime import date, datetime
from utils.security import AuditLogger


def check_all_projects():
    """Vérifie tous les projets actifs"""
    from sqlalchemy import or_
    
    # Récupérer tous les projets actifs ou suspendus
    projects = Project.query.filter(
        or_(Project.status == 'active', Project.status == 'suspended'),
        Project.archived_at.is_(None)
    ).all()
    
    updated_count = 0
    
    for project in projects:
        updated = check_single_project(project)
        if updated:
            updated_count += 1
    
    db.session.commit()
    
    return {
        'checked': len(projects),
        'updated': updated_count,
        'timestamp': datetime.utcnow().isoformat()
    }


def check_single_project(project):
    """Vérifie un projet spécifique"""
    updated = False
    today = date.today()
    
    # 1. Calculer la progression
    if len(project.tasks) > 0:
        completed_tasks = sum(1 for task in project.tasks if task.status == 'completed')
        old_progress = project.progress_percentage
        new_progress = int((completed_tasks / len(project.tasks)) * 100)
        
        if old_progress != new_progress:
            project.progress_percentage = new_progress
            updated = True
        
        # 2. Si toutes les tâches sont complétées
        if completed_tasks == len(project.tasks) and project.status != 'completed':
            project.status = 'completed'
            project.updated_at = datetime.utcnow()
            updated = True
            
            AuditLogger.log_action(
                None,
                'project_auto_completed',
                'project',
                project.id,
                {'reason': 'all_tasks_completed', 'progress': 100}
            )
    
    # 3. Vérifier les dates
    if project.end_date:
        if today > project.end_date:
            if project.status == 'active':
                if project.progress_percentage < 100:
                    # Projet en retard
                    project.status = 'delayed'
                    updated = True
                    
                    AuditLogger.log_action(
                        None,
                        'project_delayed',
                        'project',
                        project.id,
                        {
                            'end_date': project.end_date.isoformat(),
                            'progress': project.progress_percentage
                        }
                    )
                else:
                    # Terminé après la deadline
                    project.status = 'completed'
                    updated = True
    
    # 4. Vérifier les jalons
    for milestone in project.milestones:
        if milestone.target_date < today and milestone.status == 'pending':
            milestone.status = 'missed'
            updated = True
    
    # 5. Vérifier si le projet doit démarrer
    if project.status == 'planned' and project.start_date:
        if today >= project.start_date:
            project.status = 'active'
            updated = True
            
            AuditLogger.log_action(
                None,
                'project_auto_started',
                'project',
                project.id,
                {'start_date': project.start_date.isoformat()}
            )
    
    if updated:
        project.updated_at = datetime.utcnow()
    
    return updated


def get_project_health_status(project):
    """Retourne le statut de santé du projet"""
    from datetime import date
    
    today = date.today()
    
    # Calculs
    is_delayed = project.end_date and today > project.end_date and project.status != 'completed'
    
    days_remaining = 0
    if project.end_date and today <= project.end_date:
        days_remaining = (project.end_date - today).days
    
    progress = project.progress_percentage
    
    # Déterminer le statut de santé
    if is_delayed:
        health = 'critical'
    elif days_remaining <= 7 and progress < 80:
        health = 'warning'
    elif days_remaining <= 14 and progress < 50:
        health = 'warning'
    elif progress >= 80:
        health = 'good'
    else:
        health = 'normal'
    
    return {
        'health': health,
        'is_delayed': is_delayed,
        'days_remaining': days_remaining,
        'progress': progress,
        'status': project.status
    }


# Route Flask pour exécuter manuellement
def register_scheduler_routes(app):
    """Enregistre les routes du scheduler"""
    
    @app.route('/api/admin/projects/check-all', methods=['POST'])
    def admin_check_all_projects():
        """Route admin pour vérifier tous les projets"""
        from flask import session, jsonify
        from models.user import User
        
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        user = User.query.get(session['user_id'])
        if not user.is_admin:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        try:
            result = check_all_projects()
            return jsonify({
                'success': True,
                'message': f'{result["updated"]} projets mis à jour sur {result["checked"]} vérifiés',
                'result': result
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/projects/<int:project_id>/health', methods=['GET'])
    def get_project_health(project_id):
        """Obtenir le statut de santé d'un projet"""
        from flask import session, jsonify
        from models.user import User
        
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        project = Project.query.get_or_404(project_id)
        user = User.query.get(session['user_id'])
        
        if not user.is_admin and project.company_id != user.company_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        health_status = get_project_health_status(project)
        
        return jsonify({
            'success': True,
            'health': health_status
        })