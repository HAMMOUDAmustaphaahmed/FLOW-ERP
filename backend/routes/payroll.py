# routes/payroll.py
"""Routes pour la gestion de la paie - Version corrigée"""
from flask import Blueprint, request, jsonify, session, render_template, send_file
from database import db
from models.user import User
from models.payroll import (
    SalaryConfig, EmployeeSalary, LeaveRequest, SalaryAdvance, 
    Attendance, Payslip
)
from models.company import Company
from utils.security import require_login, require_admin, AuditLogger
from datetime import datetime, date, timedelta
from sqlalchemy import and_, extract
from decimal import Decimal
import calendar
from models.employee_request import EmployeeRequest
from sqlalchemy import extract, or_

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


# ==================== CONFIGURATION ====================

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
        
        return jsonify({'success': True, 'config': config.to_dict()}), 200
        
    except Exception as e:
        print(f"Erreur get_config: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@payroll_bp.route('/approved-leave-requests', methods=['GET'])
@require_login
def get_approved_leave_requests():
    """
    🆕 Récupérer TOUTES les demandes de congés APPROUVÉES
    (visibles dans l'onglet Congés de Manage Payroll)
    """
    from models.employee_request import EmployeeRequest
    from sqlalchemy import extract, or_
    
    current_user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Filtres
    status = request.args.get('status', 'approved')  # Par défaut: approuvées
    leave_type = request.args.get('leave_type')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base : uniquement les demandes de type 'leave'
    query = EmployeeRequest.query.filter_by(type='leave')
    
    # Filtre statut
    if status:
        query = query.filter_by(status=status)
    
    # Filtre type de congé
    if leave_type:
        query = query.filter_by(leave_type=leave_type)
    
    # Filtre par date
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
    
    # Recherche textuelle
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
    
    return jsonify({
        'success': True,
        'leave_requests': [req.to_dict() for req in requests]
    }), 200


@payroll_bp.route('/approved-advances', methods=['GET'])
@require_login
def get_approved_advances():
    """
    🆕 Récupérer TOUTES les demandes d'avances APPROUVÉES
    (visibles dans l'onglet Avances de Manage Payroll)
    """
    from models.employee_request import EmployeeRequest
    from sqlalchemy import extract, or_
    
    current_user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Filtres
    status = request.args.get('status', 'approved')  # Par défaut: approuvées
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base : uniquement les demandes de type 'loan'
    query = EmployeeRequest.query.filter_by(type='loan')
    
    # Filtre statut
    if status:
        query = query.filter_by(status=status)
    
    # Filtre par date
    if month and year:
        query = query.filter(
            extract('month', EmployeeRequest.created_at) == month,
            extract('year', EmployeeRequest.created_at) == year
        )
    elif year:
        query = query.filter(
            extract('year', EmployeeRequest.created_at) == year
        )
    
    # Recherche textuelle
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
    
    # Transformer en format compatible avec l'ancien système d'avances
    advances = []
    for req in requests:
        advances.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': req.user.get_full_name(),
            'amount': float(req.amount) if req.amount else 0,
            'loan_type': req.loan_type,
            'reason': req.reason,
            'status': req.status,
            'approved_by': req.approved_by.get_full_name() if req.approved_by else None,
            'approved_at': req.approved_at.isoformat() if req.approved_at else None,
            'request_date': req.created_at.isoformat(),
            'blockchain_hash': req.blockchain_hash,
            'is_in_blockchain': req.is_in_blockchain,
            # Champs pour compatibilité
            'repayment_months': 1,  # Par défaut
            'monthly_deduction': float(req.amount) if req.amount else 0,
            'remaining_amount': float(req.amount) if req.amount and req.status == 'approved' else 0,
            'disbursement_date': req.approved_at.date().isoformat() if req.approved_at else None
        })
    
    return jsonify({
        'success': True,
        'advances': advances
    }), 200


@payroll_bp.route('/blockchain/request-history/<int:request_id>', methods=['GET'])
@require_login
def get_request_blockchain_history(request_id):
    """
    🆕 Récupérer l'historique blockchain d'une demande spécifique
    """
    from models.employee_request import EmployeeRequest
    
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # Vérifier les permissions
    current_user = User.query.get(session['user_id'])
    if not (current_user.is_admin or 
            current_user.can_access_payroll or 
            employee_request.user_id == current_user.id):
        return jsonify({'error': 'Accès refusé'}), 403
    
    blockchain = current_app.extensions.get('blockchain')
    if not blockchain:
        return jsonify({'error': 'Blockchain non disponible'}), 500
    
    # Récupérer l'historique
    history = blockchain.get_transaction_history('employee_request', str(request_id))
    
    return jsonify({
        'success': True,
        'request_id': request_id,
        'blockchain_hash': employee_request.blockchain_hash,
        'block_index': employee_request.blockchain_block_index,
        'is_in_blockchain': employee_request.is_in_blockchain,
        'history': history,
        'chain_valid': blockchain.is_chain_valid()
    }), 200

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

@payroll_bp.route('/leave-request', methods=['POST'])
@require_login
def create_leave_request():
    """Créer une demande de congé"""
    user_id = session['user_id']
    data = request.get_json()
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        days_count = (end_date - start_date).days + 1
        
        leave_request = LeaveRequest(
            user_id=user_id,
            leave_type=data['leave_type'],
            start_date=start_date,
            end_date=end_date,
            days_count=days_count,
            reason=data.get('reason', ''),
            is_paid=data.get('is_paid', True)
        )
        
        db.session.add(leave_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Demande de congé créée',
            'leave_request': leave_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@payroll_bp.route('/leave-requests', methods=['GET'])
@require_login
def get_leave_requests():
    """
    🆕 Récupérer les demandes de congés depuis employee_requests
    Compatible avec l'ancien système pour l'interface payroll
    """
    from models.employee_request import EmployeeRequest
    from sqlalchemy import extract, or_
    
    current_user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Filtres
    status = request.args.get('status', 'approved')  # Par défaut: approuvées
    leave_type = request.args.get('leave_type')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base : uniquement les demandes de type 'leave'
    query = EmployeeRequest.query.filter_by(type='leave')
    
    # Filtre statut
    if status:
        query = query.filter_by(status=status)
    
    # Filtre type de congé
    if leave_type:
        query = query.filter_by(leave_type=leave_type)
    
    # Filtre par date
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
    
    # Recherche textuelle
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
    
    # Transformer en format compatible avec l'ancien système
    leave_requests = []
    for req in requests:
        leave_requests.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': req.user.get_full_name(),
            'leave_type': req.leave_type or 'annual',  # Défaut si non spécifié
            'start_date': req.start_date.isoformat() if req.start_date else None,
            'end_date': req.end_date.isoformat() if req.end_date else None,
            'days_count': req.days or 0,
            'reason': req.reason,
            'status': req.status,
            'is_paid': True,  # Par défaut
            'deduction_amount': 0,  # À calculer si nécessaire
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

@payroll_bp.route('/leave-request/<int:request_id>/review', methods=['POST'])
@require_admin
def review_leave_request(request_id):
    """Approuver ou rejeter une demande de congé"""
    data = request.get_json()
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    try:
        leave_request.status = data['status']
        leave_request.review_comment = data.get('review_comment', '')
        leave_request.reviewed_by_id = session['user_id']
        leave_request.reviewed_at = datetime.utcnow()
        
        # Calculer déduction si non payé
        if data['status'] == 'approved' and not leave_request.is_paid:
            salary = EmployeeSalary.query.filter_by(
                user_id=leave_request.user_id, 
                is_active=True
            ).first()
            
            if salary:
                user = User.query.get(leave_request.user_id)
                config = SalaryConfig.query.filter_by(company_id=user.company_id).first()
                
                if config:
                    daily_rate = float(salary.base_salary) / config.working_days_per_month
                    leave_request.deduction_amount = Decimal(str(daily_rate * leave_request.days_count))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Demande traitée',
            'leave_request': leave_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== AVANCES SUR SALAIRE ====================

@payroll_bp.route('/advance', methods=['POST'])
@require_login
def create_advance_request():
    """Créer une demande d'avance"""
    user_id = session['user_id']
    data = request.get_json()
    
    try:
        advance = SalaryAdvance(
            user_id=user_id,
            amount=Decimal(str(data['amount'])),
            reason=data.get('reason', ''),
            repayment_months=data.get('repayment_months', 1)
        )
        
        advance.calculate_monthly_deduction()
        
        db.session.add(advance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Demande d\'avance créée',
            'advance': advance.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@payroll_bp.route('/advances', methods=['GET'])
@require_login
def get_advances():
    """
    🆕 Récupérer les demandes d'avances depuis employee_requests
    Compatible avec l'ancien système pour l'interface payroll
    """
    from models.employee_request import EmployeeRequest
    from sqlalchemy import extract, or_
    
    current_user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (current_user.is_admin or current_user.can_access_payroll):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Filtres
    status = request.args.get('status', 'approved')  # Par défaut: approuvées
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '').strip()
    
    # Query de base : uniquement les demandes de type 'loan'
    query = EmployeeRequest.query.filter_by(type='loan')
    
    # Filtre statut
    if status:
        query = query.filter_by(status=status)
    
    # Filtre par date
    if month and year:
        query = query.filter(
            extract('month', EmployeeRequest.created_at) == month,
            extract('year', EmployeeRequest.created_at) == year
        )
    elif year:
        query = query.filter(
            extract('year', EmployeeRequest.created_at) == year
        )
    
    # Recherche textuelle
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
    
    # Transformer en format compatible avec l'ancien système d'avances
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
            # Champs pour compatibilité avec l'ancien système
            'repayment_months': 1,  # Par défaut
            'monthly_deduction': float(req.amount) if req.amount else 0,
            'remaining_amount': float(req.amount) if req.amount and req.status == 'approved' else 0,
            'disbursement_date': req.approved_at.date().isoformat() if req.approved_at else None
        })
    
    return jsonify({
        'success': True,
        'advances': advances
    }), 200

@payroll_bp.route('/advance/<int:advance_id>/review', methods=['POST'])
@require_admin
def review_advance(advance_id):
    """Approuver ou rejeter une avance"""
    data = request.get_json()
    advance = SalaryAdvance.query.get_or_404(advance_id)
    
    try:
        advance.status = data['status']
        advance.approved_by_id = session['user_id']
        advance.approved_at = datetime.utcnow()
        
        if data['status'] == 'approved':
            advance.disbursement_date = datetime.strptime(
                data.get('disbursement_date', date.today().isoformat()),
                '%Y-%m-%d'
            ).date()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Avance traitée',
            'advance': advance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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
        
        # Congés du mois
        leave_days = db.session.query(db.func.sum(LeaveRequest.days_count)).filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == 'approved',
            LeaveRequest.start_date >= first_day,
            LeaveRequest.end_date <= last_day
        ).scalar() or 0
        
        leave_deduction = db.session.query(db.func.sum(LeaveRequest.deduction_amount)).filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == 'approved',
            LeaveRequest.start_date >= first_day,
            LeaveRequest.end_date <= last_day
        ).scalar() or 0
        
        # Absences du mois
        absence_days = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.date >= first_day,
            Attendance.date <= last_day,
            Attendance.status == 'absent',
            Attendance.is_justified == False
        ).count()
        
        absence_deduction = db.session.query(db.func.sum(Attendance.deduction_amount)).filter(
            Attendance.user_id == user_id,
            Attendance.date >= first_day,
            Attendance.date <= last_day
        ).scalar() or 0
        
        # Avances à déduire
        advance_deduction = db.session.query(db.func.sum(SalaryAdvance.monthly_deduction)).filter(
            SalaryAdvance.user_id == user_id,
            SalaryAdvance.status == 'approved',
            SalaryAdvance.remaining_amount > 0
        ).scalar() or 0
        
        # Calculer salaire brut
        base_salary = salary.base_salary
        gross_salary = salary.get_gross_salary()
        
        # Calculer cotisations
        cnss_employee = Decimal(str(gross_salary)) * Decimal(str(config.cnss_rate / 100))
        cnss_employer = Decimal(str(gross_salary)) * Decimal(str(config.cnss_employer_rate / 100))
        
        # IRPP (simplifié - à adapter selon barème tunisien)
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
            Decimal(str(leave_deduction)) +
            Decimal(str(absence_deduction)) +
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
        
        payslip.leave_deduction = Decimal(str(leave_deduction))
        payslip.absence_deduction = Decimal(str(absence_deduction))
        payslip.advance_deduction = Decimal(str(advance_deduction))
        
        payslip.cnss_employee = cnss_employee
        payslip.cnss_employer = cnss_employer
        payslip.irpp = irpp
        
        payslip.total_deductions = total_deductions
        payslip.net_salary = net_salary
        
        payslip.working_days = config.working_days_per_month
        payslip.days_worked = config.working_days_per_month - leave_days - absence_days
        payslip.leave_days = leave_days
        payslip.absence_days = absence_days
        
        payslip.status = 'draft'
        
        db.session.commit()
        
        # Mettre à jour le montant restant des avances
        advances = SalaryAdvance.query.filter(
            SalaryAdvance.user_id == user_id,
            SalaryAdvance.status == 'approved',
            SalaryAdvance.remaining_amount > 0
        ).all()
        
        for adv in advances:
            adv.remaining_amount -= adv.monthly_deduction
            if adv.remaining_amount <= 0:
                adv.remaining_amount = 0
                adv.status = 'repaid'
        
        db.session.commit()
        
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
    """Récupérer les fiches de paie"""
    try:
        current_user = User.query.get(session['user_id'])
        
        if current_user.is_admin:
            user_id = request.args.get('user_id', type=int)
            query = Payslip.query
            if user_id:
                query = query.filter_by(user_id=user_id)
        else:
            query = Payslip.query.filter_by(user_id=current_user.id)
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        status = request.args.get('status')
        
        if month:
            query = query.filter_by(month=month)
        if year:
            query = query.filter_by(year=year)
        if status:
            query = query.filter_by(status=status)
        
        payslips = query.order_by(Payslip.year.desc(), Payslip.month.desc()).all()
        
        return jsonify({
            'success': True,
            'payslips': [p.to_dict() for p in payslips]
        }), 200
        
    except Exception as e:
        print(f"Erreur get_payslips: {str(e)}")
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