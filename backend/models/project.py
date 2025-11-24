# models/project.py
"""Modèles pour la gestion de projets"""
from datetime import datetime
from database import db
import json


class Project(db.Model):
    """Modèle de projet"""
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informations de base
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.String(20), unique=True)  # Code unique du projet (ex: PROJ-001)
    
    # Relations
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    project_manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Statut et priorité
    status = db.Column(db.String(20), default='planned')  # planned, active, completed, suspended, cancelled
    priority = db.Column(db.String(20), default='normal')  # critical, high, normal, low
    
    # Type et visibilité
    project_type = db.Column(db.String(50), default='internal')  # internal, client, r_and_d, maintenance
    visibility = db.Column(db.String(20), default='department')  # public, department, team, confidential
    
    # Planning
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Integer)
    actual_hours = db.Column(db.Integer, default=0)
    
    # Progression
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Budget
    total_budget = db.Column(db.Numeric(15, 2))
    spent_budget = db.Column(db.Numeric(15, 2), default=0)
    budget_config = db.Column(db.Text)  # JSON: {labor: X, material: Y, software: Z, external: W}
    
    # Méthodologie
    methodology = db.Column(db.String(50), default='agile')  # agile, waterfall, kanban, hybrid
    
    # Configuration
    enable_gantt = db.Column(db.Boolean, default=True)
    enable_kanban = db.Column(db.Boolean, default=True)
    enable_time_tracking = db.Column(db.Boolean, default=True)
    enable_budget_tracking = db.Column(db.Boolean, default=True)
    
    # Intégrations
    git_repository = db.Column(db.String(255))
    slack_channel = db.Column(db.String(100))
    webhook_url = db.Column(db.String(255))
    
    # Tags et labels
    tags = db.Column(db.Text)  # JSON array
    
    # Blockchain
    blockchain_hash = db.Column(db.String(64))
    is_in_blockchain = db.Column(db.Boolean, default=False)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = db.Column(db.DateTime)
    
    # Relations
    company = db.relationship('Company', backref='projects')
    department = db.relationship('Department', backref='projects')
    project_manager = db.relationship('User', foreign_keys=[project_manager_id], backref='managed_projects')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_projects')
    
    tasks = db.relationship('ProjectTask', back_populates='project', cascade='all, delete-orphan')
    milestones = db.relationship('ProjectMilestone', back_populates='project', cascade='all, delete-orphan')
    members = db.relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    sprints = db.relationship('ProjectSprint', back_populates='project', cascade='all, delete-orphan')
    
    def get_tags(self):
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags_list):
        self.tags = json.dumps(tags_list)
    
    def get_budget_config(self):
        return json.loads(self.budget_config) if self.budget_config else {}
    
    def set_budget_config(self, config):
        self.budget_config = json.dumps(config)
    
    def calculate_progress(self):
        """Calcule la progression basée sur les tâches"""
        if not self.tasks:
            return 0
        
        completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
        return int((completed_tasks / len(self.tasks)) * 100)
    
    def to_dict(self):
        """Conversion en dictionnaire avec statut enrichi"""
        from datetime import date
        
        # Calculer si le projet est en retard
        is_delayed = False
        if self.end_date and date.today() > self.end_date and self.status != 'completed':
            is_delayed = True
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'status': self.status,
            'is_delayed': is_delayed,  # Nouveau champ
            'priority': self.priority,
            'project_type': self.project_type,
            'visibility': self.visibility,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'progress_percentage': self.progress_percentage,
            'total_budget': float(self.total_budget) if self.total_budget else 0,
            'spent_budget': float(self.spent_budget) if self.spent_budget else 0,
            'project_manager': {
                'id': self.project_manager.id,
                'name': self.project_manager.get_full_name()
            } if self.project_manager else None,
            'department': self.department.name if self.department else None,
            'tags': self.get_tags(),
            'task_count': len(self.tasks),
            'member_count': len(self.members),
            'completed_tasks': sum(1 for t in self.tasks if t.status == 'completed'),
            'created_at': self.created_at.isoformat(),
            'days_remaining': (self.end_date - date.today()).days if self.end_date and date.today() <= self.end_date else 0
        }
class ProjectTask(db.Model):
    """Tâche de projet"""
    
    __tablename__ = 'project_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Informations
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50), default='task')  # task, bug, feature, maintenance, documentation, design, test
    
    # Assignation
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Statut et priorité
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, in_review, completed, blocked
    priority = db.Column(db.String(10), default='P3')  # P1, P2, P3, P4
    
    # Planning
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Integer)
    actual_hours = db.Column(db.Integer, default=0)
    
    # Progression
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Dépendances
    dependencies = db.Column(db.Text)  # JSON: [task_id1, task_id2...]
    dependency_type = db.Column(db.String(20))  # finish_to_start, start_to_start, finish_to_finish
    
    # Kanban
    kanban_column = db.Column(db.String(50), default='backlog')
    kanban_order = db.Column(db.Integer, default=0)
    
    # Sprint
    sprint_id = db.Column(db.Integer, db.ForeignKey('project_sprints.id'))
    story_points = db.Column(db.Integer)
    
    # Tags
    labels = db.Column(db.Text)  # JSON array
    
    # Checklist
    checklist = db.Column(db.Text)  # JSON: [{title: "", completed: false}, ...]
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    project = db.relationship('Project', back_populates='tasks')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tasks')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    sprint = db.relationship('ProjectSprint', back_populates='tasks')
    time_entries = db.relationship('TaskTimeEntry', back_populates='task', cascade='all, delete-orphan')
    
    def get_dependencies(self):
        return json.loads(self.dependencies) if self.dependencies else []
    
    def get_labels(self):
        return json.loads(self.labels) if self.labels else []
    
    def get_checklist(self):
        return json.loads(self.checklist) if self.checklist else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type,
            'status': self.status,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'progress_percentage': self.progress_percentage,
            'assigned_to': {
                'id': self.assigned_to.id,
                'name': self.assigned_to.get_full_name()
            } if self.assigned_to else None,
            'labels': self.get_labels(),
            'dependencies': self.get_dependencies(),
            'created_at': self.created_at.isoformat()
        }


class ProjectMilestone(db.Model):
    """Jalon de projet"""
    
    __tablename__ = 'project_milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.Date, nullable=False)
    criteria = db.Column(db.Text)  # Critères de validation
    
    status = db.Column(db.String(20), default='pending')  # pending, reached, missed
    reached_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    project = db.relationship('Project', back_populates='milestones')


class ProjectMember(db.Model):
    """Membre d'équipe projet"""
    
    __tablename__ = 'project_members'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    role = db.Column(db.String(50))  # product_owner, scrum_master, developer, designer, qa, stakeholder
    allocation_percentage = db.Column(db.Integer, default=100)  # % temps alloué
    hours_per_week = db.Column(db.Integer)
    
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    
    # Relations
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', backref='project_memberships')


class ProjectSprint(db.Model):
    """Sprint Agile"""
    
    __tablename__ = 'project_sprints'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    sprint_number = db.Column(db.Integer)
    goal = db.Column(db.Text)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    status = db.Column(db.String(20), default='planned')  # planned, active, completed
    
    capacity_hours = db.Column(db.Integer)  # Heures disponibles
    committed_story_points = db.Column(db.Integer)
    completed_story_points = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    project = db.relationship('Project', back_populates='sprints')
    tasks = db.relationship('ProjectTask', back_populates='sprint')


class TaskTimeEntry(db.Model):
    """Enregistrement de temps sur tâche"""
    
    __tablename__ = 'task_time_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('project_tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    hours = db.Column(db.Numeric(5, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    
    is_billable = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    task = db.relationship('ProjectTask', back_populates='time_entries')
    user = db.relationship('User', backref='time_entries')


class ProjectTemplate(db.Model):
    """Template de projet réutilisable"""
    
    __tablename__ = 'project_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # web_dev, marketing, infrastructure
    
    template_config = db.Column(db.Text)  # JSON: structure complète du template
    
    is_active = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_by = db.relationship('User', backref='project_templates')
