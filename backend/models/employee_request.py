# models/employee_request.py
"""Modèle pour les demandes des employés (prêts, congés, permissions)"""
from datetime import datetime
from database import db


class EmployeeRequest(db.Model):
    """Demandes des employés"""
    
    __tablename__ = 'employee_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Utilisateur qui fait la demande
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Type de demande: loan, leave, permission
    type = db.Column(db.String(20), nullable=False)
    
    # Statut: pending, approved, rejected, cancelled
    status = db.Column(db.String(20), default='pending')
    
    # Données pour prêt d'argent
    loan_type = db.Column(db.String(20))  # salary (avance salaire), bonus (avance prime)
    amount = db.Column(db.Numeric(10, 2))  # Montant demandé
    
    # Données pour congé
    leave_type = db.Column(db.String(20))  # paid, sick, exceptional
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    days = db.Column(db.Integer)  # Nombre de jours
    
    # Données pour permission
    permission_date = db.Column(db.Date)
    start_time = db.Column(db.String(5))  # Format HH:MM
    end_time = db.Column(db.String(5))  # Format HH:MM
    
    # Raison commune à tous les types
    reason = db.Column(db.Text)
    
    # Approbation
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    admin_comment = db.Column(db.Text)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', 
                          foreign_keys=[user_id], 
                          backref='employee_requests')
    approved_by = db.relationship('User', 
                                 foreign_keys=[approved_by_id])
    
    # Index pour améliorer les performances
    __table_args__ = (
        db.Index('idx_user_status', 'user_id', 'status'),
        db.Index('idx_type_status', 'type', 'status'),
        db.Index('idx_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convertir en dictionnaire"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username,
            'type': self.type,
            'status': self.status,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Ajouter les données spécifiques selon le type
        if self.type == 'loan':
            data.update({
                'loan_type': self.loan_type,
                'amount': float(self.amount) if self.amount else None
            })
        elif self.type == 'leave':
            data.update({
                'leave_type': self.leave_type,
                'start_date': self.start_date.isoformat() if self.start_date else None,
                'end_date': self.end_date.isoformat() if self.end_date else None,
                'days': self.days
            })
        elif self.type == 'permission':
            data.update({
                'date': self.permission_date.isoformat() if self.permission_date else None,
                'start_time': self.start_time,
                'end_time': self.end_time
            })
        
        # Ajouter les infos d'approbation si disponibles
        if self.approved_by_id:
            data.update({
                'approved_by_id': self.approved_by_id,
                'approved_by_name': f"{self.approved_by.first_name} {self.approved_by.last_name}".strip() or self.approved_by.username,
                'approved_at': self.approved_at.isoformat() if self.approved_at else None,
                'admin_comment': self.admin_comment
            })
        
        return data
    
    def get_type_label(self) -> str:
        """Retourne le label du type en français"""
        labels = {
            'loan': 'Prêt d\'argent',
            'leave': 'Congé',
            'permission': 'Permission'
        }
        return labels.get(self.type, self.type)
    
    def get_status_label(self) -> str:
        """Retourne le label du statut en français"""
        labels = {
            'pending': 'En attente',
            'approved': 'Approuvé',
            'rejected': 'Rejeté',
            'cancelled': 'Annulé'
        }
        return labels.get(self.status, self.status)
    
    def can_be_cancelled(self) -> bool:
        """Vérifie si la demande peut être annulée"""
        return self.status == 'pending'
    
    def can_be_modified(self) -> bool:
        """Vérifie si la demande peut être modifiée"""
        return self.status == 'pending'
    
    def __repr__(self):
        return f'<EmployeeRequest {self.id} - {self.type} - {self.status}>'