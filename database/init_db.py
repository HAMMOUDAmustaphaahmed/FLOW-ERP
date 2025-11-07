"""
Database initialization script for FlowERP
Creates all tables and optionally seeds sample data
"""

import sys
import os
from datetime import datetime, date

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.models.user import db, User, LoginAttempt
from backend.models.company import Company, Department, DepartmentField, DepartmentItem
from backend.models.blockchain import Blockchain

def init_database(app, seed_data=False):
    """Initialize database with tables - Version corrigée"""
    with app.app_context():
        print("🗄️  Creating database tables...")
        
        # Désactiver les contraintes de clés étrangères (MySQL)
        if db.engine.url.drivername == 'mysql':
            db.session.execute('SET FOREIGN_KEY_CHECKS=0;')
        
        # Drop all tables dans un ordre spécifique
        try:
            # Ordre de suppression pour éviter les dépendances
            DepartmentItem.__table__.drop(db.engine)
            DepartmentField.__table__.drop(db.engine)
            LoginAttempt.__table__.drop(db.engine)
            Department.__table__.drop(db.engine)
            Company.__table__.drop(db.engine)
            User.__table__.drop(db.engine)
        except Exception as e:
            print(f"Note: Certaines tables n'existaient pas: {e}")
        
        # Réactiver les contraintes
        if db.engine.url.drivername == 'mysql':
            db.session.execute('SET FOREIGN_KEY_CHECKS=1;')
        
        # Create all tables
        db.create_all()
        
        print("✅ Database tables created successfully!")
        
        if seed_data:
            print("\n🌱 Seeding sample data...")
            seed_sample_data()
            print("✅ Sample data seeded successfully!")

def seed_sample_data():
    """Seed sample data for testing"""
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@flowrp.tn',
        first_name='Admin',
        last_name='FlowERP',
        is_admin=True,
        is_active=True,
        role='admin'
    )
    admin.set_password('Admin@123')
    db.session.add(admin)
    db.session.commit()
    print("  👤 Admin user created (username: admin, password: Admin@123)")
    
    # Create sample company
    company = Company(
        name='TechCorp Tunisia',
        legal_name='TechCorp Tunisia SARL',
        tax_id='1234567/A/M/000',
        registration_number='B123456789',
        address='123 Avenue Habib Bourguiba',
        city='Tunis',
        state='Tunis',
        postal_code='1000',
        country='Tunisie',
        phone='+216 71 123 456',
        email='contact@techcorp.tn',
        website='https://www.techcorp.tn',
        industry='technology',
        employee_count=50,
        founded_date=date(2020, 1, 1),
        currency='TND',
        timezone='Africa/Tunis',
        language='fr',
        created_by_id=admin.id
    )
    db.session.add(company)
    db.session.commit()
    print("  🏢 Sample company created")
    
    # Associate admin with company
    admin.company_id = company.id
    db.session.commit()
    
    # Create sample departments
    departments_data = [
        {
            'name': 'Ressources Humaines',
            'code': 'RH',
            'description': 'Gestion du personnel et recrutement',
            'budget': 50000.00,
            'budget_spent': 25000.00
        },
        {
            'name': 'Informatique',
            'code': 'IT',
            'description': 'Développement et infrastructure',
            'budget': 100000.00,
            'budget_spent': 45000.00
        },
        {
            'name': 'Finance',
            'code': 'FIN',
            'description': 'Comptabilité et gestion financière',
            'budget': 75000.00,
            'budget_spent': 30000.00
        },
        {
            'name': 'Marketing',
            'code': 'MKT',
            'description': 'Communication et marketing digital',
            'budget': 60000.00,
            'budget_spent': 40000.00
        }
    ]
    
    departments = []
    for dept_data in departments_data:
        dept = Department(
            company_id=company.id,
            manager_id=admin.id,
            **dept_data
        )
        db.session.add(dept)
        departments.append(dept)
    
    db.session.commit()
    print(f"  📊 {len(departments)} departments created")
    
    # Create sample users
    users_data = [
        {
            'username': 'john.doe',
            'email': 'john.doe@techcorp.tn',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'manager',
            'department': departments[0]
        },
        {
            'username': 'jane.smith',
            'email': 'jane.smith@techcorp.tn',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'role': 'user',
            'department': departments[1]
        },
        {
            'username': 'bob.wilson',
            'email': 'bob.wilson@techcorp.tn',
            'first_name': 'Bob',
            'last_name': 'Wilson',
            'role': 'user',
            'department': departments[2]
        }
    ]
    
    for user_data in users_data:
        dept = user_data.pop('department')
        user = User(
            company_id=company.id,
            department_id=dept.id,
            is_active=True,
            **user_data
        )
        user.set_password('User@123')
        db.session.add(user)
    
    db.session.commit()
    print(f"  👥 {len(users_data)} sample users created (password: User@123)")
    
    # Add custom fields to IT department
    it_dept = departments[1]
    custom_fields = [
        {
            'name': 'Modèle',
            'field_type': 'text',
            'is_required': True,
            'order': 1
        },
        {
            'name': 'Numéro de série',
            'field_type': 'text',
            'is_required': True,
            'order': 2
        },
        {
            'name': 'Date d\'achat',
            'field_type': 'date',
            'is_required': False,
            'order': 3
        },
        {
            'name': 'État',
            'field_type': 'select',
            'is_required': True,
            'options': '["Excellent", "Bon", "Moyen", "Mauvais"]',
            'order': 4
        }
    ]
    
    for field_data in custom_fields:
        field = DepartmentField(
            department_id=it_dept.id,
            **field_data
        )
        db.session.add(field)
    
    db.session.commit()
    print("  🔧 Custom fields added to IT department")
    
    # Add sample items
    items_data = [
        {
            'department_id': it_dept.id,
            'item_type': 'equipment',
            'title': 'Dell Latitude 5520',
            'description': 'Laptop pour développeur',
            'data': {
                'Modèle': 'Dell Latitude 5520',
                'Numéro de série': 'DL5520-001',
                'Date d\'achat': '2023-01-15',
                'État': 'Excellent'
            },
            'status': 'active',
            'created_by_id': admin.id
        },
        {
            'department_id': it_dept.id,
            'item_type': 'equipment',
            'title': 'MacBook Pro M2',
            'description': 'Laptop pour design',
            'data': {
                'Modèle': 'MacBook Pro 14" M2',
                'Numéro de série': 'MBP-M2-002',
                'Date d\'achat': '2023-06-20',
                'État': 'Excellent'
            },
            'status': 'active',
            'created_by_id': admin.id
        }
    ]
    
    for item_data in items_data:
        import json
        data = item_data.pop('data')
        item = DepartmentItem(**item_data)
        item.data = json.dumps(data)
        db.session.add(item)
    
    db.session.commit()
    print(f"  📦 {len(items_data)} sample items added")


def main():
    """Main execution"""
    print("=" * 60)
    print("FlowERP Database Initialization")
    print("=" * 60)
    print()
    
    # Ask for confirmation
    response = input("⚠️  This will DELETE all existing data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Ask about sample data
    seed = input("Do you want to seed sample data? (yes/no): ")
    seed_data = seed.lower() == 'yes'
    
    # Create app and initialize
    app = create_app('development')
    init_database(app, seed_data=seed_data)
    
    print()
    print("=" * 60)
    print("✨ Database initialization complete!")
    print("=" * 60)
    
    if seed_data:
        print("\n📝 Sample credentials:")
        print("   Admin: username='admin', password='Admin@123'")
        print("   Users: username='john.doe/jane.smith/bob.wilson', password='User@123'")


if __name__ == '__main__':
    main()