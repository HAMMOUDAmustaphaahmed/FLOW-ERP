# models/company.py
from datetime import datetime
from database import db
import json


class Company(db.Model):
    """Modèle de l'entreprise"""
    
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(200), nullable=False, unique=True)
    
    # Informations légales
    legal_name = db.Column(db.String(200))
    tax_id = db.Column(db.String(50), unique=True)  # Matricule fiscale
    registration_number = db.Column(db.String(50))
    
    # Adresse
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    
    # Contact
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    
    # Informations additionnelles
    industry = db.Column(db.String(100))
    employee_count = db.Column(db.Integer)
    founded_date = db.Column(db.Date)
    logo_url = db.Column(db.String(255))
    
    # Paramètres
    currency = db.Column(db.String(3), default='TND')
    timezone = db.Column(db.String(50), default='Africa/Tunis')
    language = db.Column(db.String(5), default='fr')
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations - Définir UNIQUEMENT ici avec backref pour créer la relation inverse automatiquement
    users = db.relationship('User', 
                           foreign_keys='User.company_id',
                           backref=db.backref('company', lazy='select'),
                           lazy='dynamic',
                           overlaps="creator,companies_created")
    
    creator = db.relationship('User',
                             foreign_keys=[created_by_id],
                             backref='companies_created',
                             overlaps="users,company")
    
    departments = db.relationship('Department', 
                                 back_populates='company', 
                                 lazy='dynamic', 
                                 cascade='all, delete-orphan')
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'legal_name': self.legal_name,
            'tax_id': self.tax_id,
            'registration_number': self.registration_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'industry': self.industry,
            'employee_count': self.employee_count,
            'founded_date': self.founded_date.isoformat() if self.founded_date else None,
            'currency': self.currency,
            'timezone': self.timezone,
            'language': self.language,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'departments_count': self.departments.count(),
            'users_count': self.users.count()
        }
    
    def __repr__(self):
        return f'<Company {self.name}>'



class Department(db.Model):
    """Modèle de département dynamique"""
    
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    description = db.Column(db.Text)
    
    # Hiérarchie
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Manager (Chef de département)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Permissions du manager
    manager_can_add_users = db.Column(db.Boolean, default=True)
    manager_can_edit_budget = db.Column(db.Boolean, default=False)
    manager_can_create_tables = db.Column(db.Boolean, default=True)
    manager_can_delete_items = db.Column(db.Boolean, default=True)
    
    # Budget
    budget = db.Column(db.Numeric(15, 2))
    budget_spent = db.Column(db.Numeric(15, 2), default=0)
    
    # Statut - CHANGED: is_active is now a column, not a property
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relations
    company = db.relationship('Company', back_populates='departments')
    
    employees = db.relationship('User', 
                               foreign_keys='User.department_id',
                               backref=db.backref('department', lazy='select'),
                               lazy='dynamic',
                               overlaps="manager")
    
    manager = db.relationship('User', 
                             foreign_keys=[manager_id],
                             overlaps="employees,department")
    
    # Sous-départements
    children = db.relationship('Department', 
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')
    
    # Données dynamiques (caractéristiques personnalisées)
    custom_fields = db.relationship('DepartmentField', 
                                   back_populates='department',
                                   cascade='all, delete-orphan',
                                   lazy='dynamic')
    
    items = db.relationship('DepartmentItem', 
                           back_populates='department',
                           cascade='all, delete-orphan',
                           lazy='dynamic')
    
    def to_dict(self, include_items=False) -> dict:
        """Convert department to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'company_id': self.company_id,
            'parent_id': self.parent_id,
            'manager_id': self.manager_id,
            'budget': float(self.budget) if self.budget else None,
            'budget_spent': float(self.budget_spent) if self.budget_spent else 0,
            'budget_remaining': float(self.budget - self.budget_spent) if self.budget else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'employees_count': self.employees.count(),
            'custom_fields': [field.to_dict() for field in self.custom_fields],
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
        
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        
        return data
    
    def __repr__(self):
        return f'<Department {self.name}>'
    
    def is_deleted(self):
        """Check if department is soft-deleted"""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Marquer comme supprimé"""
        self.deleted_at = datetime.utcnow()
        self.is_active = False
    
    def restore(self):
        """Restaurer le département"""
        self.deleted_at = None
        self.is_active = True

class DepartmentField(db.Model):
    """Champs personnalisés pour les départements"""
    
    __tablename__ = 'department_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, date, file, etc.
    is_required = db.Column(db.Boolean, default=False)
    default_value = db.Column(db.Text)
    options = db.Column(db.Text)  # Pour les listes déroulantes (JSON)
    
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    department = db.relationship('Department', back_populates='custom_fields')
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'field_type': self.field_type,
            'is_required': self.is_required,
            'default_value': self.default_value,
            'options': json.loads(self.options) if self.options else None,
            'order': self.order
        }
    
    def __repr__(self):
        return f'<DepartmentField {self.name}>'


class DepartmentItem(db.Model):
    """Items dans un département (employés, équipements, factures, etc.)"""
    
    __tablename__ = 'department_items'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    item_type = db.Column(db.String(50), nullable=False)  # employee, equipment, invoice, etc.
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Données JSON pour stocker les valeurs des champs personnalisés
    data = db.Column(db.Text)  # JSON
    
    # Statut
    status = db.Column(db.String(50), default='active')
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    department = db.relationship('Department', back_populates='items')
    created_by = db.relationship('User', 
                                foreign_keys=[created_by_id],
                                backref='items_created')
    updated_by = db.relationship('User', 
                                foreign_keys=[updated_by_id],
                                backref='items_updated')
    
    # Index pour recherche rapide
    __table_args__ = (
        db.Index('idx_dept_item_type', 'department_id', 'item_type'),
    )
    
    def get_data(self) -> dict:
        """Récupère les données JSON"""
        return json.loads(self.data) if self.data else {}
    
    def set_data(self, data_dict: dict):
        """Définit les données JSON"""
        self.data = json.dumps(data_dict)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'department_id': self.department_id,
            'item_type': self.item_type,
            'title': self.title,
            'description': self.description,
            'data': self.get_data(),
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by_id': self.created_by_id,
            'updated_by_id': self.updated_by_id
        }
    
    def __repr__(self):
        return f'<DepartmentItem {self.title}>'