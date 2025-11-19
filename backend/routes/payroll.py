# routes/payroll.py - VERSION COMPLÈTE
"""Routes pour la gestion de la paie - Version complète et améliorée"""
from flask import Blueprint, request, jsonify, session, render_template, send_file, current_app
from database import db
from models.user import User
from models.payroll import (
    SalaryConfig, EmployeeSalary, LeaveRequest, SalaryAdvance, 
    Attendance, Payslip
)
from models.company import Company
from models.employee_request import EmployeeRequest
from utils.security import require_login, require_admin, AuditLogger
from datetime import datetime, date, timedelta
from sqlalchemy import and_, extract, or_
from decimal import Decimal
import calendar

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')


# ==================== PAGES HTML ====================

@payroll_bp.route('/manage', methods=['GET'])
@require_admin
def payroll_manage_page():
    """Page de gestion de la paie"""
    current_user = User.query.get(session['user_id'])
    return render_template('payroll_manage.html', user=current_user)


@payroll_bp.route('/my-payslips', methods=['GET'])
@require_login
def my_payslips_page():
    """Page des fiches de paie de l'employé"""
    current_user = User.query.get(session['user_id'])
    return render_template('my_payslips.html', user=current_user)


# ==================== API ENDPOINTS ====================

@payroll_bp.route('/config', methods=['GET'])
@require_login
def get_config():
    """Récupérer la configuration des salaires"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user or not user.company_id:
            return jsonify({
                'success': False, 
                'error': 'Utilisateur ou entreprise non trouvé'
            }), 404
        
        config = SalaryConfig.query.filter_by(company_id=user.company_id).first()
        
        if not config:
            # Créer une configuration par défaut
            config = SalaryConfig(
                company_id=user.company_id,
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
            db.session.commit()
            
            # Logger dans blockchain
            blockchain = current_app.extensions.get('blockchain')
            if blockchain:
                blockchain.add_transaction({
                    'type': 'payroll_config_created',
                    'company_id': user.company_id,
                    'config_id': config.id,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return jsonify({'success': True, 'config': config.to_dict()}), 200
        
    except Exception as e:
        print(f"Erreur get_config: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Erreur serveur: {str(e)}'
        }), 500


@payroll_bp.route('/config', methods=['POST', 'PUT'])
@require_admin
def update_config():
    """Créer ou mettre à jour la configuration"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user or not user.company_id:
            return jsonify({
                'success': False,
                'error': 'Utilisateur ou entreprise non trouvé'
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
        
        config = SalaryConfig.query.filter_by(company_id=user.company_id).first()
        
        if not config:
            config = SalaryConfig(company_id=user.company_id)
            db.session.add(config)
        
        # Mise à jour des champs
        if 'working_days_per_week' in data:
            config.working_days_per_week = int(data['working_days_per_week'])
        if 'working_hours_per_day' in data:
            config.working_hours_per_day = float(data['working_hours_per_day'])
        if 'working_days_per_month' in data:
            config.working_days_per_month = int(data['working_days_per_month'])
        if 'cnss_rate' in data:
            config.cnss_rate = float(data['cnss_rate'])
        if 'cnss_employer_rate' in data:
            config.cnss_employer_rate = float(data['cnss_employer_rate'])
        if 'irpp_rate' in data:
            config.irpp_rate = float(data['irpp_rate'])
        if 'annual_leave_days' in data:
            config.annual_leave_days = int(data['annual_leave_days'])
        if 'sick_leave_days' in data:
            config.sick_leave_days = int(data['sick_leave_days'])
        if 'absence_penalty_rate' in data:
            config.absence_penalty_rate = float(data['absence_penalty_rate'])
        if 'late_penalty_rate' in data:
            config.late_penalty_rate = float(data['late_penalty_rate'])
        
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Logger dans blockchain
        blockchain = current_app.extensions.get('blockchain')
        if blockchain:
            blockchain.add_transaction({
                'type': 'payroll_config_updated',
                'company_id': user.company_id,
                'config_id': config.id,
                'updated_by': user.id,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        AuditLogger.log_action(
            session['user_id'],
            'config_updated',
            'salary_config',
            config.id,
            {'company_id': user.company_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Configuration mise à jour',
            'config': config.to_dict()
        }), 200
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Valeur invalide: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"Erreur update_config: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Erreur serveur: {str(e)}'
        }), 500


# ==================== SALAIRES EMPLOYÉS ====================

@payroll_bp.route('/salary/<int:user_id>', methods=['GET'])
@require_login
def get_employee_salary(user_id):
    """Récupérer le salaire d'un employé"""
    try:
        current_user = User.query.get(session['user_id'])
        
        # Vérifier permissions
        if not current_user.is_admin and current_user.id != user_id:
            return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
        
        salary = EmployeeSalary.query.filter_by(user_id=user_id, is_active=True).first()
        
        if not salary:
            return jsonify({
                'success': False, 
                'message': 'Salaire non configuré'
            }), 404
        
        return jsonify({'success': True, 'salary': salary.to_dict()}), 200
        
    except Exception as e:
        print(f"Erreur get_employee_salary: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500


@payroll_bp.route('/salary/<int:user_id>', methods=['POST', 'PUT'])
@require_admin
def update_employee_salary(user_id):
    """Créer ou mettre à jour le salaire d'un employé"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
        
        # Vérifier que l'utilisateur existe
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'Utilisateur non trouvé'
            }), 404
        
        salary = EmployeeSalary.query.filter_by(user_id=user_id, is_active=True).first()
        
        if not salary:
            salary = EmployeeSalary(user_id=user_id)
            db.session.add(salary)
        
        # Mise à jour
        if 'base_salary' in data:
            salary.base_salary = Decimal(str(data['base_salary']))
        if 'transport_allowance' in data:
            salary.transport_allowance = Decimal(str(data['transport_allowance']))
        if 'food_allowance' in data:
            salary.food_allowance = Decimal(str(data['food_allowance']))
        if 'housing_allowance' in data:
            salary.housing_allowance = Decimal(str(data['housing_allowance']))
        if 'responsibility_bonus' in data:
            salary.responsibility_bonus = Decimal(str(data['responsibility_bonus']))
        if 'payment_type' in data:
            salary.payment_type = data['payment_type']
        if 'hourly_rate' in data:
            salary.hourly_rate = Decimal(str(data['hourly_rate']))
        
        salary.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Logger dans blockchain
        blockchain = current_app.extensions.get('blockchain')
        if blockchain:
            blockchain.add_transaction({
                'type': 'salary_updated',
                'user_id': user_id,
                'salary_id': salary.id,
                'base_salary': float(salary.base_salary),
                'updated_by': session['user_id'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        AuditLogger.log_action(
            session['user_id'],
            'salary_updated',
            'employee_salary',
            salary.id,
            {'user_id': user_id, 'base_salary': float(salary.base_salary)}
        )
        
        return jsonify({
            'success': True,
            'message': 'Salaire mis à jour',
            'salary': salary.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur update_employee_salary: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Erreur serveur: {str(e)}'
        }), 500


# ==================== DEMANDES DE CONGÉS ====================

@payroll_bp.route('/leave-requests', methods=['GET'])
@require_login
def get_leave_requests():
    """Récupérer les demandes de congés depuis employee_requests"""
    from models.employee_request import EmployeeRequest
    
    current_user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Filtres
    status = request.args.get('status', 'approved')
    leave_type = request.args.get('leave_type')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base
    query = EmployeeRequest.query.filter_by(type='leave')
    
    if status:
        query = query.filter_by(status=status)
    
    if leave_type:
        query = query.filter_by(leave_type=leave_type)
    
    if month and year:
        query = query.filter(
            or_(
                extract('month', EmployeeRequest.start_date) == month,
                extract('month', EmployeeRequest.end_date) == month
            ),
            or_(
                extract('year', EmployeeRequest.start_date) == year,
                extract('year', EmployeeRequest.end_date) == year
            )
        )
    elif year:
        query = query.filter(
            or_(
                extract('year', EmployeeRequest.start_date) == year,
                extract('year', EmployeeRequest.end_date) == year
            )
        )
    
    if search:
        query = query.join(User).filter(
            or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%')
            )
        )
    
    requests = query.order_by(EmployeeRequest.created_at.desc()).all()
    
    leave_requests = []
    for req in requests:
        leave_requests.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': req.user.get_full_name(),
            'leave_type': req.leave_type or 'annual',
            'start_date': req.start_date.isoformat() if req.start_date else None,
            'end_date': req.end_date.isoformat() if req.end_date else None,
            'days_count': req.days or 0,
            'reason': req.reason,
            'status': req.status,
            'is_paid': True,
            'deduction_amount': 0,
            'reviewed_by': req.approved_by.get_full_name() if req.approved_by else None,
            'reviewed_at': req.approved_at.isoformat() if req.approved_at else None,
            'review_comment': req.admin_comment,
            'created_at': req.created_at.isoformat(),
            'blockchain_hash': req.blockchain_hash,
            'is_in_blockchain': req.is_in_blockchain
        })
    
    return jsonify({
        'success': True,
        'leave_requests': leave_requests
    }), 200


# ==================== AVANCES SUR SALAIRE ====================

@payroll_bp.route('/advances', methods=['GET'])
@require_login
def get_advances():
    """Récupérer les demandes d'avances depuis employee_requests"""
    from models.employee_request import EmployeeRequest
    
    current_user = User.query.get(session['user_id'])
    
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    status = request.args.get('status', 'approved')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    query = EmployeeRequest.query.filter_by(type='loan')
    
    if status:
        query = query.filter_by(status=status)
    
    if month and year:
        query = query.filter(
            extract('month', EmployeeRequest.created_at) == month,
            extract('year', EmployeeRequest.created_at) == year
        )
    elif year:
        query = query.filter(
            extract('year', EmployeeRequest.created_at) == year
        )
    
    if search:
        query = query.join(User).filter(
            or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%')
            )
        )
    
    requests = query.order_by(EmployeeRequest.created_at.desc()).all()
    
    advances = []
    for req in requests:
        advances.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': req.user.get_full_name(),
            'amount': float(req.amount) if req.amount else 0,
            'currency': 'TND',
            'loan_type': req.loan_type,
            'reason': req.reason,
            'status': req.status,
            'approved_by': req.approved_by.get_full_name() if req.approved_by else None,
            'approved_at': req.approved_at.isoformat() if req.approved_at else None,
            'request_date': req.created_at.isoformat(),
            'blockchain_hash': req.blockchain_hash,
            'is_in_blockchain': req.is_in_blockchain,
            'repayment_months': 1,
            'monthly_deduction': float(req.amount) if req.amount else 0,
            'remaining_amount': float(req.amount) if req.amount and req.status == 'approved' else 0,
            'disbursement_date': req.approved_at.date().isoformat() if req.approved_at else None
        })
    
    return jsonify({
        'success': True,
        'advances': advances
    }), 200


# ==================== FICHES DE PAIE ====================

@payroll_bp.route('/generate-payslip/<int:user_id>', methods=['POST'])
@require_admin
def generate_payslip(user_id):
    """Générer la fiche de paie d'un employé"""
    data = request.get_json()
    month = data['month']
    year = data['year']
    
    user = User.query.get_or_404(user_id)
    
    # Vérifier si fiche existe déjà
    existing = Payslip.query.filter_by(user_id=user_id, month=month, year=year).first()
    if existing and existing.status != 'draft':
        return jsonify({'success': False, 'error': 'Fiche de paie déjà générée'}), 400
    
    try:
        # Récupérer config
        config = SalaryConfig.query.filter_by(company_id=user.company_id).first()
        if not config:
            return jsonify({'success': False, 'error': 'Configuration manquante'}), 400
        
        # Récupérer salaire
        salary = EmployeeSalary.query.filter_by(user_id=user_id, is_active=True).first()
        if not salary:
            return jsonify({'success': False, 'error': 'Salaire non configuré'}), 400
        
        # Calculer période
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        # Congés du mois (depuis employee_requests)
        leave_days = db.session.query(db.func.sum(EmployeeRequest.days)).filter(
            EmployeeRequest.user_id == user_id,
            EmployeeRequest.type == 'leave',
            EmployeeRequest.status == 'approved',
            EmployeeRequest.start_date >= first_day,
            EmployeeRequest.end_date <= last_day
        ).scalar() or 0
        
        # Avances à déduire
        advance_deduction = db.session.query(db.func.sum(EmployeeRequest.amount)).filter(
            EmployeeRequest.user_id == user_id,
            EmployeeRequest.type == 'loan',
            EmployeeRequest.status == 'approved',
            extract('month', EmployeeRequest.approved_at) == month,
            extract('year', EmployeeRequest.approved_at) == year
        ).scalar() or 0
        
        # Calculer salaire brut
        base_salary = salary.base_salary
        gross_salary = salary.get_gross_salary()
        
        # Calculer cotisations
        cnss_employee = Decimal(str(gross_salary)) * Decimal(str(config.cnss_rate / 100))
        cnss_employer = Decimal(str(gross_salary)) * Decimal(str(config.cnss_employer_rate / 100))
        
        # IRPP (barème tunisien simplifié)
        taxable_income = float(gross_salary) - float(cnss_employee)
        if taxable_income <= 5000:
            irpp = 0
        elif taxable_income <= 20000:
            irpp = Decimal(str(taxable_income * 0.26 - 1300))
        elif taxable_income <= 30000:
            irpp = Decimal(str(taxable_income * 0.28 - 1700))
        elif taxable_income <= 50000:
            irpp = Decimal(str(taxable_income * 0.32 - 2900))
        else:
            irpp = Decimal(str(taxable_income * 0.35 - 4400))
        
        irpp = max(irpp, Decimal('0'))
        
        # Total déductions
        total_deductions = (
            Decimal(str(advance_deduction)) +
            cnss_employee +
            irpp
        )
        
        # Salaire net
        net_salary = Decimal(str(gross_salary)) - total_deductions
        
        # Créer ou mettre à jour fiche de paie
        if existing:
            payslip = existing
        else:
            payslip = Payslip(user_id=user_id, month=month, year=year)
            db.session.add(payslip)
        
        payslip.base_salary = base_salary
        payslip.transport_allowance = salary.transport_allowance
        payslip.food_allowance = salary.food_allowance
        payslip.housing_allowance = salary.housing_allowance
        payslip.responsibility_bonus = salary.responsibility_bonus
        payslip.gross_salary = Decimal(str(gross_salary))
        
        payslip.leave_deduction = 0
        payslip.absence_deduction = 0
        payslip.advance_deduction = Decimal(str(advance_deduction))
        
        payslip.cnss_employee = cnss_employee
        payslip.cnss_employer = cnss_employer
        payslip.irpp = irpp
        
        payslip.total_deductions = total_deductions
        payslip.net_salary = net_salary
        
        payslip.working_days = config.working_days_per_month
        payslip.days_worked = config.working_days_per_month - leave_days
        payslip.leave_days = leave_days
        payslip.absence_days = 0
        
        payslip.status = 'draft'
        
        db.session.commit()
        
        # Logger dans blockchain
        blockchain = current_app.extensions.get('blockchain')
        if blockchain:
            blockchain.add_transaction({
                'type': 'payslip_generated',
                'payslip_id': payslip.id,
                'user_id': user_id,
                'month': month,
                'year': year,
                'net_salary': float(net_salary),
                'generated_by': session['user_id'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message': 'Fiche de paie générée',
            'payslip': payslip.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur generate_payslip: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payroll_bp.route('/payslips', methods=['GET'])
@require_login
def get_payslips():
    """Récupérer les fiches de paie - AVEC CONTEXTE"""
    try:
        current_user = User.query.get(session['user_id'])
        
        # 🔑 NOUVEAU: Paramètre context pour distinguer profile vs manage
        context = request.args.get('context', 'manage')  # 'profile' ou 'manage'
        
        # 🔒 LOGIQUE CORRIGÉE:
        # - Si context='profile' → TOUJOURS ses propres fiches (même pour admin)
        # - Si context='manage' ET admin/DRH → TOUTES les fiches
        # - Si context='manage' ET non-admin → ses propres fiches (fallback)
        
        if context == 'profile':
            # 📌 MODE PROFILE: Tout le monde voit UNIQUEMENT ses propres fiches
            query = Payslip.query.filter_by(user_id=current_user.id)
            print(f"✅ [PROFILE MODE] User {current_user.id} ({current_user.role}) - Own payslips only")
        
        elif context == 'manage':
            # 📌 MODE MANAGE: Admin/DRH voient tout, les autres leurs fiches
            if current_user.is_admin or current_user.role == 'directeur_rh':
                user_id = request.args.get('user_id', type=int)
                query = Payslip.query
                if user_id:
                    query = query.filter_by(user_id=user_id)
                print(f"✅ [MANAGE MODE] Admin/DRH {current_user.id} - All payslips")
            else:
                # Non-admin en mode manage → ses propres fiches
                query = Payslip.query.filter_by(user_id=current_user.id)
                print(f"⚠️ [MANAGE MODE] Non-admin {current_user.id} - Own payslips only")
        
        else:
            # Contexte invalide → fallback sécurisé
            query = Payslip.query.filter_by(user_id=current_user.id)
            print(f"⚠️ [UNKNOWN CONTEXT] User {current_user.id} - Own payslips only (fallback)")
        
        # Filtres supplémentaires
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        if month:
            query = query.filter_by(month=month)
        if year:
            query = query.filter_by(year=year)
        if status:
            query = query.filter_by(status=status)
        
        if search:
            query = query.join(User).filter(
                or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        payslips = query.order_by(Payslip.year.desc(), Payslip.month.desc()).all()
        
        # 🔍 DEBUG: Afficher les user_ids retournés
        if payslips:
            user_ids = list(set(p.user_id for p in payslips))
            print(f"📊 Returned payslips: {len(payslips)} - User IDs: {user_ids}")
        
        return jsonify({
            'success': True,
            'payslips': [p.to_dict() for p in payslips]
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur get_payslips: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@payroll_bp.route('/payslip/<int:payslip_id>/validate', methods=['POST'])
@require_admin
def validate_payslip(payslip_id):
    """Valider une fiche de paie"""
    payslip = Payslip.query.get_or_404(payslip_id)
    
    try:
        payslip.status = 'validated'
        payslip.validated_by_id = session['user_id']
        payslip.validated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Logger dans blockchain
        blockchain = current_app.extensions.get('blockchain')
        if blockchain:
            blockchain.add_transaction({
                'type': 'payslip_validated',
                'payslip_id': payslip.id,
                'validated_by': session['user_id'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message': 'Fiche de paie validée',
            'payslip': payslip.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@payroll_bp.route('/payslip/<int:payslip_id>/pdf', methods=['GET'])
@require_login
def download_payslip_pdf(payslip_id):
    """Télécharger la fiche de paie en PDF"""
    from utils.payslip_pdf import generate_payslip_pdf
    import os
    
    current_user = User.query.get(session['user_id'])
    payslip = Payslip.query.get_or_404(payslip_id)
    
    # Vérifier les permissions
    if not current_user.can_access_payroll and current_user.id != payslip.user_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        user = User.query.get(payslip.user_id)
        company = Company.query.get(user.company_id)
        
        # Générer le PDF
        pdf_path = generate_payslip_pdf(payslip, user, company)
        
        # Sauvegarder le chemin dans la base
        if not payslip.pdf_path:
            payslip.pdf_path = pdf_path
            db.session.commit()
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(pdf_path)
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur génération PDF: {str(e)}'}), 500