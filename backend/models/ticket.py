# models/ticket.py
"""Système de tickets pour signalement de problèmes avec hiérarchie"""
from datetime import datetime, timedelta
from database import db
import json


class Ticket(db.Model):
    """Ticket de signalement avec hiérarchie d'assignation"""
    
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)  # Ex: TKT-2025-001
    
    # Créateur
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    
    # Assignation
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_at = db.Column(db.DateTime)
    
    # Informations du ticket
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    # Catégories: production, quality_control, warehouse, it_support, hr, maintenance, security, other
    
    priority = db.Column(db.String(20), default='normale')
    # Priorités: basse, normale, haute, critique, urgente
    
    status = db.Column(db.String(20), default='en_attente')
    # Statuts: en_attente, en_cours, resolu, ferme, reouvert
    
    # Localisation du problème
    location = db.Column(db.String(200))  # Ex: "Atelier A, Machine 3"
    equipment = db.Column(db.String(200))  # Ex: "PC-001", "Machine CNC"
    
    # Tags pour catégorisation fine
    tags = db.Column(db.Text)  # JSON: ["urgent", "machine", "électrique"]
    
    # Résolution
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    resolution_comment = db.Column(db.Text)
    resolution_time_minutes = db.Column(db.Integer)  # Temps de résolution en minutes
    
    # SLA (Service Level Agreement)
    sla_deadline = db.Column(db.DateTime)  # Date limite selon priorité
    is_overdue = db.Column(db.Boolean, default=False)
    is_escalated = db.Column(db.Boolean, default=False)
    escalated_at = db.Column(db.DateTime)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Réouverture
    reopened_at = db.Column(db.DateTime)
    reopened_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reopen_reason = db.Column(db.Text)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    # Blockchain
    blockchain_hash = db.Column(db.String(64))
    is_in_blockchain = db.Column(db.Boolean, default=False)
    
    # Relations
    creator = db.relationship('User', foreign_keys=[created_by_id], backref='created_tickets')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tickets')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
    escalated_to = db.relationship('User', foreign_keys=[escalated_to_id])
    reopened_by = db.relationship('User', foreign_keys=[reopened_by_id])
    department = db.relationship('Department', backref='tickets')
    
    comments = db.relationship('TicketComment', back_populates='ticket', cascade='all, delete-orphan', order_by='TicketComment.created_at')
    attachments = db.relationship('TicketAttachment', back_populates='ticket', cascade='all, delete-orphan')
    history = db.relationship('TicketHistory', back_populates='ticket', cascade='all, delete-orphan', order_by='TicketHistory.created_at')
    
    # Index
    __table_args__ = (
        db.Index('idx_status_priority', 'status', 'priority'),
        db.Index('idx_assigned_status', 'assigned_to_id', 'status'),
        db.Index('idx_creator_status', 'created_by_id', 'status'),
    )
    
    def generate_ticket_number(self):
        """Génère un numéro de ticket unique"""
        year = datetime.utcnow().year
        # Compter les tickets de cette année
        count = Ticket.query.filter(
            Ticket.ticket_number.like(f'TKT-{year}-%')
        ).count() + 1
        
        self.ticket_number = f'TKT-{year}-{count:04d}'
    
    def calculate_sla_deadline(self):
        """Calcule la deadline selon la priorité"""
        sla_hours = {
            'urgente': 2,      # 2 heures
            'critique': 4,     # 4 heures
            'haute': 24,       # 1 jour
            'normale': 72,     # 3 jours
            'basse': 168       # 7 jours
        }
        
        hours = sla_hours.get(self.priority, 72)
        self.sla_deadline = datetime.utcnow() + timedelta(hours=hours)
    
    def assign_to_responsible(self):
        """Assigne automatiquement selon la hiérarchie"""
        from models.user import User
        
        creator = User.query.get(self.created_by_id)
        if not creator:
            return
        
        # Logique d'assignation selon hiérarchie
        if creator.role in ['employee', 'technician'] and creator.department_id:
            # Technicien/Employé -> Chef de département
            from models.company import Department
            dept = Department.query.get(creator.department_id)
            if dept and dept.manager_id:
                self.assigned_to_id = dept.manager_id
                self.assigned_at = datetime.utcnow()
                return
        
        if creator.role == 'department_manager':
            # Chef de département -> Directeur RH ou Admin
            drh = User.query.filter_by(role='directeur_rh', is_active=True, company_id=creator.company_id).first()
            if drh:
                self.assigned_to_id = drh.id
            else:
                admin = User.query.filter_by(is_admin=True, is_active=True, company_id=creator.company_id).first()
                if admin:
                    self.assigned_to_id = admin.id
            self.assigned_at = datetime.utcnow()
            return
        
        # Par défaut -> Admin
        admin = User.query.filter_by(is_admin=True, is_active=True, company_id=creator.company_id).first()
        if admin:
            self.assigned_to_id = admin.id
            self.assigned_at = datetime.utcnow()
    
    def check_overdue(self):
        """Vérifie si le ticket est en retard"""
        if self.status in ['resolu', 'ferme']:
            return False
        
        if self.sla_deadline and datetime.utcnow() > self.sla_deadline:
            self.is_overdue = True
            return True
        return False
    
    def escalate(self):
        """Escalade le ticket au niveau supérieur"""
        if self.is_escalated:
            return
        
        from models.user import User
        
        current_assigned = User.query.get(self.assigned_to_id)
        if not current_assigned:
            return
        
        # Escalade selon hiérarchie
        if current_assigned.role == 'department_manager':
            # Chef -> DRH ou Admin
            drh = User.query.filter_by(role='directeur_rh', is_active=True, company_id=current_assigned.company_id).first()
            if drh:
                self.escalated_to_id = drh.id
            else:
                admin = User.query.filter_by(is_admin=True, is_active=True, company_id=current_assigned.company_id).first()
                if admin:
                    self.escalated_to_id = admin.id
        elif current_assigned.role == 'directeur_rh':
            # DRH -> Admin
            admin = User.query.filter_by(is_admin=True, is_active=True, company_id=current_assigned.company_id).first()
            if admin:
                self.escalated_to_id = admin.id
        
        if self.escalated_to_id:
            self.is_escalated = True
            self.escalated_at = datetime.utcnow()
            self.assigned_to_id = self.escalated_to_id
    
    def resolve(self, resolved_by_id, comment):
        """Marque le ticket comme résolu"""
        self.status = 'resolu'
        self.resolved_by_id = resolved_by_id
        self.resolved_at = datetime.utcnow()
        self.resolution_comment = comment
        
        # Calculer temps de résolution
        if self.created_at:
            delta = self.resolved_at - self.created_at
            self.resolution_time_minutes = int(delta.total_seconds() / 60)
    
    def reopen(self, reopened_by_id, reason):
        """Réouvre un ticket résolu"""
        if self.status not in ['resolu', 'ferme']:
            return False
        
        self.status = 'reouvert'
        self.reopened_at = datetime.utcnow()
        self.reopened_by_id = reopened_by_id
        self.reopen_reason = reason
        return True
    
    def get_tags(self):
        """Récupère les tags JSON"""
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags_list):
        """Définit les tags JSON"""
        self.tags = json.dumps(tags_list)
    
    def to_dict(self, include_comments=False, include_attachments=False):
        """Convertit en dictionnaire"""
        data = {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'location': self.location,
            'equipment': self.equipment,
            'tags': self.get_tags(),
            'department_id': self.department_id,
            'creator': {
                'id': self.creator.id,
                'name': self.creator.get_full_name(),
                'email': self.creator.email,
                'role': self.creator.role
            } if self.creator else None,
            'assigned_to': {
                'id': self.assigned_to.id,
                'name': self.assigned_to.get_full_name(),
                'role': self.assigned_to.role
            } if self.assigned_to else None,
            'department': self.department.name if self.department else None,
            'sla_deadline': self.sla_deadline.isoformat() if self.sla_deadline else None,
            'is_overdue': self.is_overdue,
            'is_escalated': self.is_escalated,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_time_minutes': self.resolution_time_minutes,
            'resolution_comment': self.resolution_comment,
            'blockchain_hash': self.blockchain_hash,
            'is_in_blockchain': self.is_in_blockchain
        }
        
        if include_comments:
            data['comments'] = [c.to_dict() for c in self.comments]
            data['comments_count'] = len(self.comments)
        
        if include_attachments:
            data['attachments'] = [a.to_dict() for a in self.attachments]
            data['attachments_count'] = len(self.attachments)
        
        return data
    
    def __repr__(self):
        return f'<Ticket {self.ticket_number} - {self.title}>'


class TicketComment(db.Model):
    """Commentaires sur un ticket"""
    
    __tablename__ = 'ticket_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    comment = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Note interne (visible seulement aux responsables)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    ticket = db.relationship('Ticket', back_populates='comments')
    user = db.relationship('User', backref='ticket_comments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user': {
                'id': self.user.id,
                'name': self.user.get_full_name()
            } if self.user else None,
            'comment': self.comment,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TicketAttachment(db.Model):
    """Pièces jointes d'un ticket"""
    
    __tablename__ = 'ticket_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # En bytes
    mime_type = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    ticket = db.relationship('Ticket', back_populates='attachments')
    uploaded_by = db.relationship('User', backref='ticket_attachments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_by': self.uploaded_by.get_full_name() if self.uploaded_by else None,
            'created_at': self.created_at.isoformat()
        }


class TicketHistory(db.Model):
    """Historique des changements de statut"""
    
    __tablename__ = 'ticket_history'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    action = db.Column(db.String(50), nullable=False)
    # Actions: created, assigned, status_changed, priority_changed, resolved, closed, reopened, escalated
    
    old_value = db.Column(db.String(200))
    new_value = db.Column(db.String(200))
    comment = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relations
    ticket = db.relationship('Ticket', back_populates='history')
    user = db.relationship('User', backref='ticket_actions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'user': self.user.get_full_name() if self.user else None,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'comment': self.comment,
            'created_at': self.created_at.isoformat()
        }