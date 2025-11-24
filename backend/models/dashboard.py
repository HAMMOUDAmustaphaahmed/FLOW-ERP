# models/dashboard.py
"""Modèles pour le dashboard personnalisable"""
from datetime import datetime
from database import db
import json


class DashboardWidget(db.Model):
    """Widget personnalisé sur le dashboard"""
    
    __tablename__ = 'dashboard_widgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Configuration du widget
    title = db.Column(db.String(200), nullable=False)
    widget_type = db.Column(db.String(50), nullable=False)
    # Types: count, distribution, trend, comparison, sum, avg, gauge
    
    chart_type = db.Column(db.String(50), default='bar')
    # Types: bar, line, pie, doughnut, radar, polarArea, number, gauge, table
    
    data_source = db.Column(db.String(100), nullable=False)
    # Sources: employees, projects, tickets, requests, attendance, payroll, departments
    
    # Filtres
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    filters = db.Column(db.Text)  # JSON pour filtres avancés
    
    # Apparence
    size = db.Column(db.String(20), default='medium')  # small, medium, large, full
    color_scheme = db.Column(db.String(50), default='blue')
    position_order = db.Column(db.Integer, default=0)
    
    # État
    is_active = db.Column(db.Boolean, default=True)
    refresh_interval = db.Column(db.Integer, default=300)  # Secondes
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='dashboard_widgets')
    department = db.relationship('Department', backref='widgets')
    
    def get_filters(self):
        """Récupère les filtres JSON"""
        return json.loads(self.filters) if self.filters else {}
    
    def set_filters(self, filters_dict):
        """Définit les filtres JSON"""
        self.filters = json.dumps(filters_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'widget_type': self.widget_type,
            'chart_type': self.chart_type,
            'data_source': self.data_source,
            'department_id': self.department_id,
            'filters': self.get_filters(),
            'size': self.size,
            'color_scheme': self.color_scheme,
            'position_order': self.position_order,
            'is_active': self.is_active,
            'refresh_interval': self.refresh_interval,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<DashboardWidget {self.title}>'


class DashboardLayout(db.Model):
    """Layout sauvegardé du dashboard"""
    
    __tablename__ = 'dashboard_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    layout_config = db.Column(db.Text, nullable=False)  # JSON: positions, tailles
    
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='dashboard_layouts')
    
    def get_config(self):
        return json.loads(self.layout_config) if self.layout_config else {}
    
    def set_config(self, config):
        self.layout_config = json.dumps(config)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'config': self.get_config(),
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<DashboardLayout {self.name}>'