# init_payroll_db.py
"""Script pour initialiser les tables de la paie"""
from app import create_app
from database import db
from models.payroll import (
    SalaryConfig, EmployeeSalary, LeaveRequest, 
    SalaryAdvance, Attendance, Payslip
)

def init_payroll_tables():
    """Créer les tables de la paie"""
    app = create_app('development')
    
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        
        print("✅ Tables de paie créées avec succès!")
        
        # Créer une configuration par défaut pour chaque entreprise
        from models.company import Company
        
        companies = Company.query.all()
        
        for company in companies:
            existing_config = SalaryConfig.query.filter_by(company_id=company.id).first()
            
            if not existing_config:
                config = SalaryConfig(
                    company_id=company.id,
                    working_days_per_week=5,
                    working_hours_per_day=8.0,
                    working_days_per_month=22,
                    cnss_rate=9.18,
                    cnss_employer_rate=16.57,
                    irpp_rate=0.0,
                    annual_leave_days=30,
                    sick_leave_days=15,
                    absence_penalty_rate=100.0,
                    late_penalty_rate=50.0
                )
                
                db.session.add(config)
                print(f"✅ Configuration créée pour {company.name}")
        
        db.session.commit()
        print("✅ Configurations par défaut créées!")

if __name__ == '__main__':
    init_payroll_tables()