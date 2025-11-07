# models/department_table.py
"""Modèle pour les tableaux personnalisés des départements"""
from datetime import datetime
from database import db
import json


class DepartmentTable(db.Model):
    """Table personnalisée pour un département"""
    
    __tablename__ = 'department_tables'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    # Informations de la table
    name = db.Column(db.String(100), nullable=False)  # Ex: "parc_informatique", "employees"
    display_name = db.Column(db.String(200), nullable=False)  # Ex: "Parc Informatique"
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='table')  # Icône Font Awesome
    
    # Configuration
    is_active = db.Column(db.Boolean, default=True)
    allow_import = db.Column(db.Boolean, default=True)  # Autoriser import CSV/Excel
    allow_export = db.Column(db.Boolean, default=True)  # Autoriser export
    
    # Permissions
    view_permission = db.Column(db.String(50), default='department')  # all, department, manager_only
    edit_permission = db.Column(db.String(50), default='department')
    delete_permission = db.Column(db.String(50), default='manager_only')
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    department = db.relationship('Department', backref='custom_tables')
    columns = db.relationship('TableColumn', back_populates='table', 
                             cascade='all, delete-orphan', order_by='TableColumn.order')
    rows = db.relationship('TableRow', back_populates='table', 
                          cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def to_dict(self, include_columns=True, include_rows=False) -> dict:
        data = {
            'id': self.id,
            'department_id': self.department_id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'is_active': self.is_active,
            'allow_import': self.allow_import,
            'allow_export': self.allow_export,
            'view_permission': self.view_permission,
            'edit_permission': self.edit_permission,
            'delete_permission': self.delete_permission,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'rows_count': len(self.rows)
        }
        
        if include_columns:
            data['columns'] = [col.to_dict() for col in self.columns]
        
        if include_rows:
            data['rows'] = [row.to_dict() for row in self.rows]
        
        return data
    
    def __repr__(self):
        return f'<DepartmentTable {self.display_name}>'


class TableColumn(db.Model):
    """Colonne d'une table personnalisée"""
    
    __tablename__ = 'table_columns'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('department_tables.id'), nullable=False)
    
    # Informations de la colonne
    name = db.Column(db.String(100), nullable=False)  # Nom technique (ex: "serial_number")
    display_name = db.Column(db.String(200), nullable=False)  # Nom affiché (ex: "Numéro de série")
    
    # Type de données
    data_type = db.Column(db.String(50), nullable=False)  
    # Types: text, number, decimal, date, datetime, boolean, email, phone, 
    #        url, select, multiselect, file, image, user, department
    
    # Configuration du type
    type_config = db.Column(db.Text)  # JSON pour config spécifique
    # Ex pour select: {"options": ["Option 1", "Option 2"]}
    # Ex pour number: {"min": 0, "max": 1000}
    # Ex pour decimal: {"decimals": 2, "currency": "TND"}
    
    # Validation
    is_required = db.Column(db.Boolean, default=False)
    is_unique = db.Column(db.Boolean, default=False)
    default_value = db.Column(db.Text)
    validation_rules = db.Column(db.Text)  # JSON
    
    # Affichage
    order = db.Column(db.Integer, default=0)
    width = db.Column(db.Integer)  # Largeur en pixels
    is_visible = db.Column(db.Boolean, default=True)
    is_sortable = db.Column(db.Boolean, default=True)
    is_filterable = db.Column(db.Boolean, default=True)
    
    # Format d'affichage
    display_format = db.Column(db.String(100))  # Ex: "0,0.00" pour nombres
    prefix = db.Column(db.String(20))  # Ex: "$" ou "TND"
    suffix = db.Column(db.String(20))  # Ex: "kg", "m²"
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation
    table = db.relationship('DepartmentTable', back_populates='columns')
    
    def get_config(self) -> dict:
        """Récupère la configuration JSON"""
        return json.loads(self.type_config) if self.type_config else {}
    
    def set_config(self, config: dict):
        """Définit la configuration JSON"""
        self.type_config = json.dumps(config)
    
    def get_validation_rules(self) -> dict:
        """Récupère les règles de validation"""
        return json.loads(self.validation_rules) if self.validation_rules else {}
    
    def set_validation_rules(self, rules: dict):
        """Définit les règles de validation"""
        self.validation_rules = json.dumps(rules)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'table_id': self.table_id,
            'name': self.name,
            'display_name': self.display_name,
            'data_type': self.data_type,
            'type_config': self.get_config(),
            'is_required': self.is_required,
            'is_unique': self.is_unique,
            'default_value': self.default_value,
            'validation_rules': self.get_validation_rules(),
            'order': self.order,
            'width': self.width,
            'is_visible': self.is_visible,
            'is_sortable': self.is_sortable,
            'is_filterable': self.is_filterable,
            'display_format': self.display_format,
            'prefix': self.prefix,
            'suffix': self.suffix
        }
    
    def __repr__(self):
        return f'<TableColumn {self.display_name}>'


class TableRow(db.Model):
    """Ligne de données dans une table personnalisée"""
    
    __tablename__ = 'table_rows'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('department_tables.id'), nullable=False)
    
    # Données (JSON contenant toutes les valeurs des colonnes)
    data = db.Column(db.Text, nullable=False)  # JSON: {"serial_number": "ABC123", "brand": "Dell", ...}
    
    # Métadonnées
    row_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    table = db.relationship('DepartmentTable', back_populates='rows')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    # Index pour recherche rapide
    __table_args__ = (
        db.Index('idx_table_active', 'table_id', 'is_active'),
    )
    
    def get_data(self) -> dict:
        """Récupère les données JSON"""
        return json.loads(self.data) if self.data else {}
    
    def set_data(self, data_dict: dict):
        """Définit les données JSON"""
        self.data = json.dumps(data_dict)
    
    def get_value(self, column_name: str):
        """Récupère la valeur d'une colonne spécifique"""
        data = self.get_data()
        return data.get(column_name)
    
    def set_value(self, column_name: str, value):
        """Définit la valeur d'une colonne spécifique"""
        data = self.get_data()
        data[column_name] = value
        self.set_data(data)
    
    def to_dict(self, include_audit=False) -> dict:
        result = {
            'id': self.id,
            'table_id': self.table_id,
            'data': self.get_data(),
            'row_order': self.row_order,
            'is_active': self.is_active
        }
        
        if include_audit:
            result.update({
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat(),
                'created_by_id': self.created_by_id,
                'updated_by_id': self.updated_by_id
            })
        
        return result
    
    def __repr__(self):
        return f'<TableRow {self.id}>'


class TableTemplate(db.Model):
    """Templates prédéfinis pour créer rapidement des tables"""
    
    __tablename__ = 'table_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # IT, HR, Finance, Sales, etc.
    icon = db.Column(db.String(50))
    
    # Configuration du template (JSON)
    template_config = db.Column(db.Text, nullable=False)
    # Contient: columns, default_data, permissions, etc.
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_config(self) -> dict:
        return json.loads(self.template_config) if self.template_config else {}
    
    def set_config(self, config: dict):
        self.template_config = json.dumps(config)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'icon': self.icon,
            'config': self.get_config(),
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<TableTemplate {self.display_name}>'