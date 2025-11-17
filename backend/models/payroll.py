# models/payroll.py
"""Modèles pour la gestion des salaires et de la paie"""
from datetime import datetime
from database import db
import json


class SalaryConfig(db.Model):
    """Configuration globale des salaires pour l'entreprise"""
    
    __tablename__ = 'salary_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Configuration des jours de travail
    working_days_per_week = db.Column(db.Integer, default=5)  # Jours/semaine
    working_hours_per_day = db.Column(db.Float, default=8.0)  # Heures/jour
    working_days_per_month = db.Column(db.Integer, default=22)  # Jours/mois
    
    # Taux de cotisation
    cnss_rate = db.Column(db.Float, default=9.18)  # % CNSS employé
    cnss_employer_rate = db.Column(db.Float, default=16.57)  # % CNSS employeur
    irpp_rate = db.Column(db.Float, default=0.0)  # % IRPP (progressif)
    
    # Congés
    annual_leave_days = db.Column(db.Integer, default=30)  # Jours/an
    sick_leave_days = db.Column(db.Integer, default=15)  # Jours/an
    
    # Pénalités
    absence_penalty_rate = db.Column(db.Float, default=100.0)  # % du salaire journalier
    late_penalty_rate = db.Column(db.Float, default=50.0)  # % du salaire horaire
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'working_days_per_week': self.working_days_per_week,
            'working_hours_per_day': self.working_hours_per_day,
            'working_days_per_month': self.working_days_per_month,
            'cnss_rate': self.cnss_rate,
            'cnss_employer_rate': self.cnss_employer_rate,
            'irpp_rate': self.irpp_rate,
            'annual_leave_days': self.annual_leave_days,
            'sick_leave_days': self.sick_leave_days,
            'absence_penalty_rate': self.absence_penalty_rate,
            'late_penalty_rate': self.late_penalty_rate
        }


class EmployeeSalary(db.Model):
    """Salaire de base et primes d'un employé"""
    
    __tablename__ = 'employee_salaries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Salaire de base
    base_salary = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    currency = db.Column(db.String(3), default='TND')
    
    # Primes mensuelles fixes
    transport_allowance = db.Column(db.Numeric(10, 3), default=0)  # Prime transport
    food_allowance = db.Column(db.Numeric(10, 3), default=0)  # Prime panier
    housing_allowance = db.Column(db.Numeric(10, 3), default=0)  # Prime logement
    responsibility_bonus = db.Column(db.Numeric(10, 3), default=0)  # Prime responsabilité
    
    # Type de paiement
    payment_type = db.Column(db.String(20), default='monthly')  # monthly, hourly
    hourly_rate = db.Column(db.Numeric(10, 3))  # Si paiement horaire
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    effective_date = db.Column(db.Date, default=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='salary_info')
    
    def get_total_allowances(self):
        """Total des primes"""
        return float(
            (self.transport_allowance or 0) +
            (self.food_allowance or 0) +
            (self.housing_allowance or 0) +
            (self.responsibility_bonus or 0)
        )
    
    def get_gross_salary(self):
        """Salaire brut (base + primes)"""
        return float(self.base_salary) + self.get_total_allowances()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'base_salary': float(self.base_salary),
            'currency': self.currency,
            'allowances': {
                'transport': float(self.transport_allowance or 0),
                'food': float(self.food_allowance or 0),
                'housing': float(self.housing_allowance or 0),
                'responsibility': float(self.responsibility_bonus or 0),
                'total': self.get_total_allowances()
            },
            'gross_salary': self.get_gross_salary(),
            'payment_type': self.payment_type,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'is_active': self.is_active,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None
        }


class LeaveRequest(db.Model):
    """Demandes de congés"""
    
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Type de congé
    leave_type = db.Column(db.String(50), nullable=False)  # annual, sick, unpaid, maternity
    
    # Dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_count = db.Column(db.Integer, nullable=False)
    
    # Raison
    reason = db.Column(db.Text)
    attachment = db.Column(db.String(255))  # Justificatif (certificat médical, etc.)
    
    # Statut
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    review_comment = db.Column(db.Text)
    
    # Impact sur le salaire
    is_paid = db.Column(db.Boolean, default=True)
    deduction_amount = db.Column(db.Numeric(10, 3), default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref='leave_requests')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'days_count': self.days_count,
            'reason': self.reason,
            'status': self.status,
            'is_paid': self.is_paid,
            'deduction_amount': float(self.deduction_amount) if self.deduction_amount else 0,
            'reviewed_by': self.reviewed_by.get_full_name() if self.reviewed_by else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_comment': self.review_comment,
            'created_at': self.created_at.isoformat()
        }


class SalaryAdvance(db.Model):
    """Avances sur salaire"""
    
    __tablename__ = 'salary_advances'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Montant
    amount = db.Column(db.Numeric(10, 3), nullable=False)
    currency = db.Column(db.String(3), default='TND')
    
    # Raison
    reason = db.Column(db.Text)
    
    # Remboursement
    repayment_months = db.Column(db.Integer, default=1)  # Nombre de mois pour rembourser
    monthly_deduction = db.Column(db.Numeric(10, 3))  # Montant mensuel à déduire
    remaining_amount = db.Column(db.Numeric(10, 3))  # Montant restant
    
    # Statut
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, repaid
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    
    # Dates
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    disbursement_date = db.Column(db.Date)  # Date de versement
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref='salary_advances')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def calculate_monthly_deduction(self):
        """Calcule la déduction mensuelle"""
        if self.repayment_months > 0:
            self.monthly_deduction = self.amount / self.repayment_months
            self.remaining_amount = self.amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'amount': float(self.amount),
            'currency': self.currency,
            'reason': self.reason,
            'repayment_months': self.repayment_months,
            'monthly_deduction': float(self.monthly_deduction) if self.monthly_deduction else 0,
            'remaining_amount': float(self.remaining_amount) if self.remaining_amount else 0,
            'status': self.status,
            'approved_by': self.approved_by.get_full_name() if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'request_date': self.request_date.isoformat(),
            'disbursement_date': self.disbursement_date.isoformat() if self.disbursement_date else None
        }


class Attendance(db.Model):
    """Présences et absences"""
    
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False)
    
    # Heures
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    hours_worked = db.Column(db.Float, default=0)
    
    # Statut
    status = db.Column(db.String(20), default='present')  # present, absent, late, half_day
    is_justified = db.Column(db.Boolean, default=False)
    justification = db.Column(db.Text)
    
    # Déductions
    deduction_amount = db.Column(db.Numeric(10, 3), default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='attendances')
    
    __table_args__ = (
        db.Index('idx_user_date', 'user_id', 'date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat(),
            'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.isoformat() if self.check_out else None,
            'hours_worked': self.hours_worked,
            'status': self.status,
            'is_justified': self.is_justified,
            'justification': self.justification,
            'deduction_amount': float(self.deduction_amount) if self.deduction_amount else 0
        }


class Payslip(db.Model):
    """Fiche de paie mensuelle"""
    
    __tablename__ = 'payslips'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Période
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    # Salaire
    base_salary = db.Column(db.Numeric(12, 3), nullable=False)
    
    # Primes
    transport_allowance = db.Column(db.Numeric(10, 3), default=0)
    food_allowance = db.Column(db.Numeric(10, 3), default=0)
    housing_allowance = db.Column(db.Numeric(10, 3), default=0)
    responsibility_bonus = db.Column(db.Numeric(10, 3), default=0)
    performance_bonus = db.Column(db.Numeric(10, 3), default=0)
    overtime_pay = db.Column(db.Numeric(10, 3), default=0)
    
    # Salaire brut
    gross_salary = db.Column(db.Numeric(12, 3), nullable=False)
    
    # Déductions
    leave_deduction = db.Column(db.Numeric(10, 3), default=0)  # Congés non payés
    absence_deduction = db.Column(db.Numeric(10, 3), default=0)  # Absences
    advance_deduction = db.Column(db.Numeric(10, 3), default=0)  # Avances
    late_deduction = db.Column(db.Numeric(10, 3), default=0)  # Retards
    
    # Cotisations
    cnss_employee = db.Column(db.Numeric(10, 3), default=0)
    cnss_employer = db.Column(db.Numeric(10, 3), default=0)
    irpp = db.Column(db.Numeric(10, 3), default=0)
    
    # Total déductions
    total_deductions = db.Column(db.Numeric(12, 3), default=0)
    
    # Salaire net
    net_salary = db.Column(db.Numeric(12, 3), nullable=False)
    
    # Métadonnées
    working_days = db.Column(db.Integer)
    days_worked = db.Column(db.Integer)
    leave_days = db.Column(db.Integer, default=0)
    absence_days = db.Column(db.Integer, default=0)
    
    # Statut
    status = db.Column(db.String(20), default='draft')  # draft, validated, paid
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    
    # PDF
    pdf_path = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref='payslips')
    validated_by = db.relationship('User', foreign_keys=[validated_by_id])
    
    __table_args__ = (
        db.Index('idx_user_period', 'user_id', 'year', 'month'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'period': f"{self.year}-{self.month:02d}",
            'month': self.month,
            'year': self.year,
            'base_salary': float(self.base_salary),
            'allowances': {
                'transport': float(self.transport_allowance or 0),
                'food': float(self.food_allowance or 0),
                'housing': float(self.housing_allowance or 0),
                'responsibility': float(self.responsibility_bonus or 0),
                'performance': float(self.performance_bonus or 0),
                'overtime': float(self.overtime_pay or 0)
            },
            'gross_salary': float(self.gross_salary),
            'deductions': {
                'leave': float(self.leave_deduction or 0),
                'absence': float(self.absence_deduction or 0),
                'advance': float(self.advance_deduction or 0),
                'late': float(self.late_deduction or 0),
                'cnss': float(self.cnss_employee or 0),
                'irpp': float(self.irpp or 0),
                'total': float(self.total_deductions)
            },
            'net_salary': float(self.net_salary),
            'days': {
                'working': self.working_days,
                'worked': self.days_worked,
                'leave': self.leave_days,
                'absence': self.absence_days
            },
            'status': self.status,
            'validated_by': self.validated_by.get_full_name() if self.validated_by else None,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'pdf_path': self.pdf_path
        }