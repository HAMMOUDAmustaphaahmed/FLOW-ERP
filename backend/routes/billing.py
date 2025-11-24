# routes/billing.py
"""
Module de Facturation & Comptabilité Avancée 💰
"""
from flask import Blueprint, request, jsonify, session, send_file
from database import db
from models.user import User
from models.company import Company
from models.billing import (
    Customer, Invoice, InvoiceItem, Payment, Expense, 
    BankAccount, TaxRate, AccountingEntry, FiscalReport,
    CashFlowForecast, PaymentReminder, InvoiceTemplate, FinancialDashboard
)
from utils.security import SecurityValidator, require_login, require_admin, AuditLogger
from utils.pdf_generator import PDFGenerator
from utils.email_service import EmailService
from datetime import datetime, timedelta
import json
import io
from sqlalchemy import func, and_, or_
from decimal import Decimal

billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

# ============= GESTION DES CLIENTS =============

@billing_bp.route('/customers/create', methods=['POST'])
@require_login
def create_customer():
    """Créer un nouveau client"""
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    if not name:
        return jsonify({'error': 'Le nom du client est requis'}), 400
    
    try:
        customer = Customer(
            company_id=user.company_id,
            name=name,
            legal_name=SecurityValidator.sanitize_input(data.get('legal_name', '')),
            email=SecurityValidator.sanitize_input(data.get('email', '')),
            phone=SecurityValidator.sanitize_input(data.get('phone', '')),
            address=SecurityValidator.sanitize_input(data.get('address', '')),
            city=SecurityValidator.sanitize_input(data.get('city', '')),
            postal_code=SecurityValidator.sanitize_input(data.get('postal_code', '')),
            country=SecurityValidator.sanitize_input(data.get('country', 'Tunisie')),
            tax_id=SecurityValidator.sanitize_input(data.get('tax_id', '')),
            tax_exempt=data.get('tax_exempt', False),
            payment_terms=data.get('payment_terms', 30),
            credit_limit=data.get('credit_limit', 0),
            currency=data.get('currency', 'TND'),
            customer_type=data.get('customer_type', 'regular'),
            industry=SecurityValidator.sanitize_input(data.get('industry', '')),
            risk_score=data.get('risk_score', 50),
            created_by_id=user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'customer_created',
            'customer',
            customer.id,
            {'name': name, 'company_id': user.company_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Client créé avec succès',
            'customer': customer.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500


@billing_bp.route('/customers/list', methods=['GET'])
@require_login
def list_customers():
    """Lister les clients"""
    user = User.query.get(session['user_id'])
    
    customers = Customer.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).order_by(Customer.name).all()
    
    return jsonify({
        'success': True,
        'customers': [customer.to_dict() for customer in customers]
    }), 200


@billing_bp.route('/customers/<int:customer_id>', methods=['GET'])
@require_login
def get_customer(customer_id):
    """Récupérer un client avec son historique"""
    user = User.query.get(session['user_id'])
    customer = Customer.query.filter_by(
        id=customer_id,
        company_id=user.company_id
    ).first_or_404()
    
    # Récupérer l'historique des factures
    invoices = Invoice.query.filter_by(
        customer_id=customer_id
    ).order_by(Invoice.issue_date.desc()).limit(10).all()
    
    # Récupérer l'historique des paiements
    payments = Payment.query.filter_by(
        customer_id=customer_id
    ).order_by(Payment.payment_date.desc()).limit(10).all()
    
    customer_data = customer.to_dict()
    customer_data['recent_invoices'] = [inv.to_dict() for inv in invoices]
    customer_data['recent_payments'] = [pay.to_dict() for pay in payments]
    
    return jsonify({
        'success': True,
        'customer': customer_data
    }), 200


# ============= GESTION DES FACTURES =============

@billing_bp.route('/invoices/create', methods=['POST'])
@require_login
def create_invoice():
    """Créer une nouvelle facture"""
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'Le client est requis'}), 400
    
    try:
        # Générer le numéro de facture
        last_invoice = Invoice.query.filter_by(
            company_id=user.company_id
        ).order_by(Invoice.sequence_number.desc()).first()
        
        sequence_number = (last_invoice.sequence_number + 1) if last_invoice else 1
        invoice_number = f"FACT-{datetime.now().year}-{sequence_number:06d}"
        
        invoice = Invoice(
            company_id=user.company_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            sequence_number=sequence_number,
            issue_date=datetime.fromisoformat(data['issue_date']).date() if data.get('issue_date') else datetime.utcnow().date(),
            due_date=datetime.fromisoformat(data['due_date']).date() if data.get('due_date') else (datetime.utcnow() + timedelta(days=30)).date(),
            delivery_date=datetime.fromisoformat(data['delivery_date']).date() if data.get('delivery_date') else None,
            currency=data.get('currency', 'TND'),
            exchange_rate=data.get('exchange_rate', 1),
            notes=SecurityValidator.sanitize_input(data.get('notes', '')),
            terms_conditions=SecurityValidator.sanitize_input(data.get('terms_conditions', '')),
            internal_notes=SecurityValidator.sanitize_input(data.get('internal_notes', '')),
            created_by_id=user.id
        )
        
        db.session.add(invoice)
        db.session.flush()  # Pour obtenir l'ID sans commit
        
        # Ajouter les lignes de facture
        items = data.get('items', [])
        for item_data in items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=SecurityValidator.sanitize_input(item_data['description']),
                product_code=SecurityValidator.sanitize_input(item_data.get('product_code', '')),
                quantity=Decimal(str(item_data['quantity'])),
                unit_price=Decimal(str(item_data['unit_price'])),
                tax_rate_id=item_data.get('tax_rate_id'),
                department_id=item_data.get('department_id'),
                project_code=SecurityValidator.sanitize_input(item_data.get('project_code', ''))
            )
            item.amount = item.quantity * item.unit_price
            db.session.add(item)
        
        # Calculer les totaux
        invoice.calculate_totals()
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'invoice_created',
            'invoice',
            invoice.id,
            {'invoice_number': invoice_number, 'customer_id': customer_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Facture créée avec succès',
            'invoice': invoice.to_dict(include_items=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500


@billing_bp.route('/invoices/<int:invoice_id>/pdf', methods=['GET'])
@require_login
def generate_invoice_pdf(invoice_id):
    """Générer le PDF d'une facture"""
    user = User.query.get(session['user_id'])
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=user.company_id
    ).first_or_404()
    
    try:
        # Générer le PDF
        pdf_generator = PDFGenerator()
        pdf_data = pdf_generator.generate_invoice_pdf(invoice)
        
        # Mettre à jour la facture
        invoice.pdf_generated_at = datetime.utcnow()
        db.session.commit()
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{invoice.invoice_number}.pdf"
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la génération du PDF: {str(e)}'}), 500


@billing_bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@require_login
def send_invoice(invoice_id):
    """Envoyer une facture par email"""
    user = User.query.get(session['user_id'])
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=user.company_id
    ).first_or_404()
    
    data = request.get_json()
    recipient_email = data.get('recipient_email', invoice.customer.email)
    
    if not recipient_email:
        return jsonify({'error': 'Email du destinataire requis'}), 400
    
    try:
        # Générer le PDF si pas encore fait
        if not invoice.pdf_generated_at:
            pdf_generator = PDFGenerator()
            pdf_data = pdf_generator.generate_invoice_pdf(invoice)
        
        # Envoyer l'email
        email_service = EmailService()
        email_service.send_invoice_email(
            to_email=recipient_email,
            invoice=invoice,
            pdf_data=pdf_data
        )
        
        # Mettre à jour le statut
        invoice.status = 'sent'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Facture envoyée avec succès'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'envoi: {str(e)}'}), 500


# ============= TABLEAU DE BORD FINANCIER =============

@billing_bp.route('/dashboard/overview', methods=['GET'])
@require_login
def financial_overview():
    """Vue d'ensemble financière"""
    user = User.query.get(session['user_id'])
    
    try:
        # Chiffre d'affaires du mois
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == user.company_id,
            Invoice.issue_date >= month_start,
            Invoice.status.in_(['sent', 'approved', 'paid'])
        ).scalar() or 0
        
        # Factures en attente
        pending_invoices = Invoice.query.filter_by(
            company_id=user.company_id,
            status='sent'
        ).count()
        
        # Retards de paiement
        overdue_invoices = Invoice.query.filter(
            Invoice.company_id == user.company_id,
            Invoice.balance_due > 0,
            Invoice.due_date < datetime.utcnow().date(),
            Invoice.status.in_(['sent', 'approved'])
        ).count()
        
        # Trésorerie
        cash_balance = db.session.query(func.sum(BankAccount.current_balance)).filter(
            BankAccount.company_id == user.company_id,
            BankAccount.is_active == True
        ).scalar() or 0
        
        # Dépenses du mois
        monthly_expenses = db.session.query(func.sum(Expense.total_amount)).filter(
            Expense.company_id == user.company_id,
            Expense.expense_date >= month_start,
            Expense.status == 'approved'
        ).scalar() or 0
        
        # Ratio de retard
        total_invoices = Invoice.query.filter_by(company_id=user.company_id).count()
        overdue_ratio = (overdue_invoices / total_invoices * 100) if total_invoices > 0 else 0
        
        return jsonify({
            'success': True,
            'overview': {
                'monthly_revenue': float(monthly_revenue),
                'pending_invoices': pending_invoices,
                'overdue_invoices': overdue_invoices,
                'cash_balance': float(cash_balance),
                'monthly_expenses': float(monthly_expenses),
                'overdue_ratio': round(overdue_ratio, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul: {str(e)}'}), 500


@billing_bp.route('/dashboard/cashflow', methods=['GET'])
@require_login
def cashflow_data():
    """Données de trésorerie"""
    user = User.query.get(session['user_id'])
    
    try:
        # Cash-flow des 12 derniers mois
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        
        cashflow_data = []
        for i in range(12):
            month = twelve_months_ago + timedelta(days=30*i)
            month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Revenus du mois
            monthly_income = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.company_id == user.company_id,
                Invoice.issue_date >= month_start,
                Invoice.issue_date <= month_end,
                Invoice.status.in_(['sent', 'approved', 'paid'])
            ).scalar() or 0
            
            # Dépenses du mois
            monthly_expenses = db.session.query(func.sum(Expense.total_amount)).filter(
                Expense.company_id == user.company_id,
                Expense.expense_date >= month_start,
                Expense.expense_date <= month_end,
                Expense.status == 'approved'
            ).scalar() or 0
            
            cashflow_data.append({
                'month': month_start.strftime('%Y-%m'),
                'income': float(monthly_income),
                'expenses': float(monthly_expenses),
                'net_cashflow': float(monthly_income - monthly_expenses)
            })
        
        return jsonify({
            'success': True,
            'cashflow': cashflow_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul: {str(e)}'}), 500


# ============= RAPPORTS FINANCIERS =============

@billing_bp.route('/reports/profit-loss', methods=['GET'])
@require_login
def profit_loss_report():
    """Rapport Profit & Loss"""
    user = User.query.get(session['user_id'])
    
    period = request.args.get('period', 'monthly')  # monthly, quarterly, yearly
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Implémentation du calcul P&L
        # Ceci est un exemple simplifié
        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.utcnow()
            if period == 'monthly':
                start = end.replace(day=1)
            elif period == 'quarterly':
                quarter_month = ((end.month - 1) // 3) * 3 + 1
                start = end.replace(month=quarter_month, day=1)
            else:  # yearly
                start = end.replace(month=1, day=1)
        
        # Revenus
        revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == user.company_id,
            Invoice.issue_date >= start,
            Invoice.issue_date <= end,
            Invoice.status.in_(['sent', 'approved', 'paid'])
        ).scalar() or 0
        
        # Dépenses
        expenses = db.session.query(func.sum(Expense.total_amount)).filter(
            Expense.company_id == user.company_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
            Expense.status == 'approved'
        ).scalar() or 0
        
        profit_loss = revenue - expenses
        
        return jsonify({
            'success': True,
            'report': {
                'period': f"{start.date()} to {end.date()}",
                'revenue': float(revenue),
                'expenses': float(expenses),
                'net_income': float(profit_loss),
                'margin_percentage': round((profit_loss / revenue * 100) if revenue > 0 else 0, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul: {str(e)}'}), 500


# ============= RELANCES AUTOMATIQUES =============

@billing_bp.route('/reminders/generate', methods=['POST'])
@require_login
def generate_payment_reminders():
    """Générer les relances automatiques"""
    user = User.query.get(session['user_id'])
    
    try:
        # Factures en retard
        overdue_invoices = Invoice.query.filter(
            Invoice.company_id == user.company_id,
            Invoice.balance_due > 0,
            Invoice.due_date < datetime.utcnow().date(),
            Invoice.status.in_(['sent', 'approved'])
        ).all()
        
        reminders_created = 0
        for invoice in overdue_invoices:
            days_overdue = (datetime.utcnow().date() - invoice.due_date).days
            
            # Déterminer le stade de relance
            if days_overdue <= 7:
                stage = 1
            elif days_overdue <= 15:
                stage = 2
            else:
                stage = 3
            
            # Vérifier si une relance existe déjà pour ce stade
            existing_reminder = PaymentReminder.query.filter_by(
                invoice_id=invoice.id,
                reminder_stage=stage
            ).first()
            
            if not existing_reminder:
                reminder = PaymentReminder(
                    company_id=user.company_id,
                    invoice_id=invoice.id,
                    customer_id=invoice.customer_id,
                    reminder_type='email',
                    reminder_stage=stage,
                    scheduled_date=datetime.utcnow().date(),
                    subject=f"Rappel de paiement - Facture {invoice.invoice_number}",
                    message=f"Votre facture {invoice.invoice_number} est en retard de {days_overdue} jours.",
                    created_by_id=user.id
                )
                db.session.add(reminder)
                reminders_created += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{reminders_created} relances générées',
            'reminders_created': reminders_created
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la génération: {str(e)}'}), 500


# ============= STATISTIQUES AVANCÉES =============

@billing_bp.route('/stats/executive', methods=['GET'])
@require_login
def executive_stats():
    """Statistiques pour le tableau de bord executive"""
    user = User.query.get(session['user_id'])
    
    try:
        # Cash-flow
        cash_balance = db.session.query(func.sum(BankAccount.current_balance)).filter(
            BankAccount.company_id == user.company_id,
            BankAccount.is_active == True
        ).scalar() or 0
        
        # Revenus du mois vs mois précédent
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == user.company_id,
            Invoice.issue_date >= current_month,
            Invoice.status.in_(['sent', 'approved', 'paid'])
        ).scalar() or 0
        
        previous_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == user.company_id,
            Invoice.issue_date >= previous_month,
            Invoice.issue_date < current_month,
            Invoice.status.in_(['sent', 'approved', 'paid'])
        ).scalar() or 0
        
        revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        
        # Délais de paiement moyens
        paid_invoices = Invoice.query.filter(
            Invoice.company_id == user.company_id,
            Invoice.status == 'paid',
            Invoice.amount_paid > 0
        ).all()
        
        if paid_invoices:
            avg_payment_days = sum(
                (inv.payments.first().payment_date - inv.issue_date).days 
                for inv in paid_invoices if inv.payments.first()
            ) / len(paid_invoices)
        else:
            avg_payment_days = 0
        
        # Alertes
        high_risk_customers = Customer.query.filter(
            Customer.company_id == user.company_id,
            Customer.risk_score >= 80,
            Customer.outstanding_balance > 0
        ).count()
        
        return jsonify({
            'success': True,
            'executive_stats': {
                'cash_balance': float(cash_balance),
                'cash_flow_percentage': 82,  # Exemple
                'revenue_growth': round(revenue_growth, 1),
                'avg_payment_days': round(avg_payment_days, 1),
                'high_risk_alerts': high_risk_customers,
                'compliance_status': 'all_clear'  # Exemple
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul: {str(e)}'}), 500