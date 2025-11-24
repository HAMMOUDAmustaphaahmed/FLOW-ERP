# models/billing.py
"""
Modèles pour le module de Facturation & Comptabilité Avancée
"""
from datetime import datetime
from database import db
import json
from decimal import Decimal
from sqlalchemy import func, and_, or_


class Customer(db.Model):
    """Client avec historique financier complet"""
    
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations de base
    name = db.Column(db.String(200), nullable=False)
    legal_name = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    
    # Adresse
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Tunisie')
    
    # Informations fiscales
    tax_id = db.Column(db.String(50))  # Matricule fiscale client
    tax_exempt = db.Column(db.Boolean, default=False)
    
    # Conditions commerciales
    payment_terms = db.Column(db.Integer, default=30)  # Jours
    credit_limit = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='TND')
    
    # Classification
    customer_type = db.Column(db.String(50), default='regular')  # regular, vip, prospect
    industry = db.Column(db.String(100))
    risk_score = db.Column(db.Integer, default=50)  # 0-100
    
    # Statistiques
    total_purchases = db.Column(db.Numeric(15, 2), default=0)
    outstanding_balance = db.Column(db.Numeric(15, 2), default=0)
    last_purchase_date = db.Column(db.DateTime)
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='customers')
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    payments = db.relationship('Payment', backref='customer', lazy='dynamic')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'legal_name': self.legal_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'postal_code': self.postal_code,
            'country': self.country,
            'tax_id': self.tax_id,
            'tax_exempt': self.tax_exempt,
            'payment_terms': self.payment_terms,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0,
            'currency': self.currency,
            'customer_type': self.customer_type,
            'industry': self.industry,
            'risk_score': self.risk_score,
            'total_purchases': float(self.total_purchases) if self.total_purchases else 0,
            'outstanding_balance': float(self.outstanding_balance) if self.outstanding_balance else 0,
            'last_purchase_date': self.last_purchase_date.isoformat() if self.last_purchase_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'invoices_count': self.invoices.count()
        }


class Invoice(db.Model):
    """Facture avec workflow de validation"""
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Numérotation
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    
    # Dates
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    delivery_date = db.Column(db.Date)
    
    # Montants
    subtotal = db.Column(db.Numeric(15, 2), default=0)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    total_amount = db.Column(db.Numeric(15, 2), default=0)
    amount_paid = db.Column(db.Numeric(15, 2), default=0)
    balance_due = db.Column(db.Numeric(15, 2), default=0)
    
    # Devise
    currency = db.Column(db.String(3), default='TND')
    exchange_rate = db.Column(db.Numeric(10, 6), default=1)
    
    # Statut et workflow
    status = db.Column(db.String(50), default='draft')  # draft, sent, viewed, approved, paid, overdue, cancelled
    approval_status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    approval_level = db.Column(db.Integer, default=1)  # Niveau d'approbation (1-3)
    
    # Métadonnées
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # PDF
    pdf_path = db.Column(db.String(500))
    pdf_generated_at = db.Column(db.DateTime)
    
    # Relance
    reminder_sent_count = db.Column(db.Integer, default=0)
    last_reminder_sent = db.Column(db.DateTime)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='invoices')
    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'customer_id': self.customer_id,
            'invoice_number': self.invoice_number,
            'sequence_number': self.sequence_number,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0,
            'balance_due': float(self.balance_due) if self.balance_due else 0,
            'currency': self.currency,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else 1,
            'status': self.status,
            'approval_status': self.approval_status,
            'approval_level': self.approval_level,
            'notes': self.notes,
            'terms_conditions': self.terms_conditions,
            'pdf_generated_at': self.pdf_generated_at.isoformat() if self.pdf_generated_at else None,
            'reminder_sent_count': self.reminder_sent_count,
            'created_at': self.created_at.isoformat(),
            'days_overdue': self.get_days_overdue(),
            'customer_name': self.customer.name if self.customer else None
        }
        
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
            
        return data
    
    def get_days_overdue(self):
        """Calculer les jours de retard"""
        if self.status == 'paid' or self.balance_due <= 0:
            return 0
        if self.due_date and datetime.utcnow().date() > self.due_date:
            return (datetime.utcnow().date() - self.due_date).days
        return 0
    
    def calculate_totals(self):
        """Recalculer les totaux"""
        self.subtotal = sum(item.amount for item in self.items)
        
        # Calcul des taxes
        tax_amount = Decimal('0')
        for item in self.items:
            if item.tax_rate:
                tax_amount += item.amount * (item.tax_rate.rate / Decimal('100'))
        
        self.tax_amount = tax_amount
        self.total_amount = self.subtotal + tax_amount
        self.balance_due = self.total_amount - self.amount_paid


class InvoiceItem(db.Model):
    """Ligne de facture détaillée"""
    
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    # Description
    description = db.Column(db.String(500), nullable=False)
    product_code = db.Column(db.String(100))
    
    # Quantité et prix
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Taxes
    tax_rate_id = db.Column(db.Integer, db.ForeignKey('tax_rates.id'))
    
    # Analytique
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    project_code = db.Column(db.String(100))
    
    # Relations
    tax_rate = db.relationship('TaxRate')
    department = db.relationship('Department')
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'product_code': self.product_code,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'amount': float(self.amount) if self.amount else 0,
            'tax_rate_id': self.tax_rate_id,
            'department_id': self.department_id,
            'project_code': self.project_code,
            'tax_rate_value': self.tax_rate.rate if self.tax_rate else 0
        }


class Payment(db.Model):
    """Paiements multi-devises avec rapprochement"""
    
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    
    # Informations de paiement
    payment_number = db.Column(db.String(50), unique=True)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='TND')
    exchange_rate = db.Column(db.Numeric(10, 6), default=1)
    
    # Méthode de paiement
    payment_method = db.Column(db.String(50), nullable=False)  # cash, check, bank_transfer, card, online
    payment_reference = db.Column(db.String(200))
    
    # Compte bancaire
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'))
    
    # Statut
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed, refunded
    reconciliation_status = db.Column(db.String(50), default='unreconciled')  # unreconciled, reconciled
    
    # Notes
    notes = db.Column(db.Text)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='payments')
    bank_account = db.relationship('BankAccount')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'customer_id': self.customer_id,
            'invoice_id': self.invoice_id,
            'payment_number': self.payment_number,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else 1,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'bank_account_id': self.bank_account_id,
            'status': self.status,
            'reconciliation_status': self.reconciliation_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'customer_name': self.customer.name if self.customer else None,
            'invoice_number': self.invoice.invoice_number if self.invoice else None
        }


class Expense(db.Model):
    """Dépenses avec catégorisation et justificatifs"""
    
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations de base
    expense_number = db.Column(db.String(50), unique=True)
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Catégorisation
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100))
    
    # Fournisseur
    vendor_name = db.Column(db.String(200))
    vendor_tax_id = db.Column(db.String(50))
    
    # Analytique
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    project_code = db.Column(db.String(100))
    
    # Justificatifs
    receipt_path = db.Column(db.String(500))
    receipt_number = db.Column(db.String(100))
    
    # Statut
    status = db.Column(db.String(50), default='pending')  # pending, approved, reimbursed, rejected
    payment_status = db.Column(db.String(50), default='unpaid')  # unpaid, paid
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='expenses')
    department = db.relationship('Department')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'expense_number': self.expense_number,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'amount': float(self.amount) if self.amount else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'category': self.category,
            'subcategory': self.subcategory,
            'vendor_name': self.vendor_name,
            'vendor_tax_id': self.vendor_tax_id,
            'department_id': self.department_id,
            'project_code': self.project_code,
            'receipt_path': self.receipt_path,
            'receipt_number': self.receipt_number,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat(),
            'department_name': self.department.name if self.department else None
        }


class BankAccount(db.Model):
    """Comptes bancaires avec synchronisation"""
    
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations bancaires
    bank_name = db.Column(db.String(200), nullable=False)
    account_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    iban = db.Column(db.String(34))
    swift_code = db.Column(db.String(11))
    
    # Devise
    currency = db.Column(db.String(3), default='TND')
    
    # Solde
    current_balance = db.Column(db.Numeric(15, 2), default=0)
    last_reconciliation_date = db.Column(db.Date)
    
    # Synchronisation
    is_sync_enabled = db.Column(db.Boolean, default=False)
    sync_method = db.Column(db.String(50))  # sftp, api, manual
    last_sync_date = db.Column(db.DateTime)
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations
    company = db.relationship('Company', backref='bank_accounts')
    payments = db.relationship('Payment', backref='bank_account_rel', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'bank_name': self.bank_name,
            'account_name': self.account_name,
            'account_number': self.account_number,
            'iban': self.iban,
            'swift_code': self.swift_code,
            'currency': self.currency,
            'current_balance': float(self.current_balance) if self.current_balance else 0,
            'last_reconciliation_date': self.last_reconciliation_date.isoformat() if self.last_reconciliation_date else None,
            'is_sync_enabled': self.is_sync_enabled,
            'sync_method': self.sync_method,
            'last_sync_date': self.last_sync_date.isoformat() if self.last_sync_date else None,
            'is_active': self.is_active
        }


class TaxRate(db.Model):
    """Taux de TVA paramétrables"""
    
    __tablename__ = 'tax_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations fiscales
    name = db.Column(db.String(100), nullable=False)  # Ex: "TVA 19%"
    rate = db.Column(db.Numeric(5, 2), nullable=False)  # 19.00
    tax_type = db.Column(db.String(50), default='vat')  # vat, sales_tax, etc.
    
    # Applicabilité
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Règles spécifiques
    applies_to = db.Column(db.String(50), default='all')  # all, products, services
    country = db.Column(db.String(100))
    
    # Relations
    company = db.relationship('Company', backref='tax_rates')
    invoice_items = db.relationship('InvoiceItem', backref='tax_rate_rel', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'rate': float(self.rate) if self.rate else 0,
            'tax_type': self.tax_type,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'applies_to': self.applies_to,
            'country': self.country
        }


class AccountingEntry(db.Model):
    """Écritures comptables automatiques"""
    
    __tablename__ = 'accounting_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations de base
    entry_number = db.Column(db.String(50), unique=True)
    entry_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    
    # Montants
    debit_amount = db.Column(db.Numeric(15, 2), default=0)
    credit_amount = db.Column(db.Numeric(15, 2), default=0)
    
    # Comptes
    account_debit = db.Column(db.String(20), nullable=False)
    account_credit = db.Column(db.String(20), nullable=False)
    
    # Source
    source_type = db.Column(db.String(50))  # invoice, payment, expense, manual
    source_id = db.Column(db.Integer)
    
    # Analytique
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    project_code = db.Column(db.String(100))
    
    # Statut
    is_posted = db.Column(db.Boolean, default=False)
    posted_at = db.Column(db.DateTime)
    
    # Relations
    company = db.relationship('Company', backref='accounting_entries')
    department = db.relationship('Department')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entry_number': self.entry_number,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'description': self.description,
            'debit_amount': float(self.debit_amount) if self.debit_amount else 0,
            'credit_amount': float(self.credit_amount) if self.credit_amount else 0,
            'account_debit': self.account_debit,
            'account_credit': self.account_credit,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'department_id': self.department_id,
            'project_code': self.project_code,
            'is_posted': self.is_posted,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None
        }


class FiscalReport(db.Model):
    """Déclarations fiscales pré-remplies"""
    
    __tablename__ = 'fiscal_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations de déclaration
    report_type = db.Column(db.String(100), nullable=False)  # tva, income_tax, etc.
    period_type = db.Column(db.String(50), nullable=False)  # monthly, quarterly, annual
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # Données de la déclaration
    report_data = db.Column(db.Text)  # JSON avec les données pré-remplies
    
    # Statut
    status = db.Column(db.String(50), default='draft')  # draft, submitted, approved
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    
    # Fichiers
    generated_pdf_path = db.Column(db.String(500))
    submission_reference = db.Column(db.String(200))
    
    # Relations
    company = db.relationship('Company', backref='fiscal_reports')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'report_type': self.report_type,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'report_data': json.loads(self.report_data) if self.report_data else {},
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'generated_pdf_path': self.generated_pdf_path,
            'submission_reference': self.submission_reference
        }

class CashFlowForecast(db.Model):
    """Prévisions de trésorerie intelligentes"""
    
    __tablename__ = 'cash_flow_forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Période
    forecast_date = db.Column(db.Date, nullable=False)
    period_type = db.Column(db.String(50), default='monthly')  # weekly, monthly, quarterly
    period_count = db.Column(db.Integer, default=12)  # Nombre de périodes
    
    # Données de prévision
    forecast_data = db.Column(db.Text, nullable=False)  # JSON avec les prévisions
    
    # Métadonnées
    confidence_score = db.Column(db.Numeric(5, 2))  # Score de confiance 0-100
    assumptions = db.Column(db.Text)  # Hypothèses utilisées
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='cash_flow_forecasts')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'forecast_date': self.forecast_date.isoformat() if self.forecast_date else None,
            'period_type': self.period_type,
            'period_count': self.period_count,
            'forecast_data': json.loads(self.forecast_data) if self.forecast_data else {},
            'confidence_score': float(self.confidence_score) if self.confidence_score else 0,
            'assumptions': self.assumptions,
            'created_at': self.created_at.isoformat()
        }


class PaymentReminder(db.Model):
    """Relances automatiques avec scoring"""
    
    __tablename__ = 'payment_reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Informations de relance
    reminder_type = db.Column(db.String(50), nullable=False)  # email, sms, letter
    reminder_stage = db.Column(db.Integer, default=1)  # 1, 2, 3 (premier, deuxième, troisième relance)
    scheduled_date = db.Column(db.Date, nullable=False)
    sent_date = db.Column(db.DateTime)
    
    # Contenu
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    
    # Statut
    status = db.Column(db.String(50), default='scheduled')  # scheduled, sent, failed, cancelled
    response_status = db.Column(db.String(50))  # paid, promised, disputed, ignored
    
    # Métriques
    open_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    company = db.relationship('Company', backref='payment_reminders')
    invoice = db.relationship('Invoice', backref='reminders')
    customer = db.relationship('Customer', backref='reminders')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'invoice_id': self.invoice_id,
            'customer_id': self.customer_id,
            'reminder_type': self.reminder_type,
            'reminder_stage': self.reminder_stage,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'sent_date': self.sent_date.isoformat() if self.sent_date else None,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'response_status': self.response_status,
            'open_count': self.open_count,
            'click_count': self.click_count,
            'created_at': self.created_at.isoformat(),
            'invoice_number': self.invoice.invoice_number if self.invoice else None,
            'customer_name': self.customer.name if self.customer else None
        }


class InvoiceTemplate(db.Model):
    """Templates de factures personnalisables"""
    
    __tablename__ = 'invoice_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Informations du template
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    
    # Configuration
    template_config = db.Column(db.Text, nullable=False)  # JSON avec la configuration
    header_html = db.Column(db.Text)
    footer_html = db.Column(db.Text)
    css_styles = db.Column(db.Text)
    
    # Logo et branding
    logo_path = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#3B82F6')
    secondary_color = db.Column(db.String(7), default='#1E40AF')
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations
    company = db.relationship('Company', backref='invoice_templates')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'is_default': self.is_default,
            'template_config': json.loads(self.template_config) if self.template_config else {},
            'header_html': self.header_html,
            'footer_html': self.footer_html,
            'css_styles': self.css_styles,
            'logo_path': self.logo_path,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'is_active': self.is_active
        }


class FinancialDashboard(db.Model):
    """Configuration du tableau de bord financier"""
    
    __tablename__ = 'financial_dashboards'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Configuration
    dashboard_config = db.Column(db.Text, nullable=False)  # JSON avec la configuration des widgets
    default_view = db.Column(db.String(50), default='overview')  # overview, cashflow, receivables, payables
    
    # Préférences
    refresh_interval = db.Column(db.Integer, default=5)  # minutes
    show_alerts = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    company = db.relationship('Company', backref='financial_dashboards')
    user = db.relationship('User', backref='financial_dashboard')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'dashboard_config': json.loads(self.dashboard_config) if self.dashboard_config else {},
            'default_view': self.default_view,
            'refresh_interval': self.refresh_interval,
            'show_alerts': self.show_alerts,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }