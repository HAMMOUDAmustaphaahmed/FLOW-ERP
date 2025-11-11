# routes/employee_requests.py
"""Routes pour la gestion des demandes des employés (prêts, congés, permissions)"""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import db
from models.user import User
from models.employee_request import EmployeeRequest
from utils.security import require_login, require_admin, AuditLogger
from datetime import datetime, timedelta

employee_requests_bp = Blueprint('employee_requests', __name__, url_prefix='/api/employee-requests')


@employee_requests_bp.route('/profile-page')
@require_login
def profile_page():
    """Page de profil de l'utilisateur"""
    user = User.query.get(session['user_id'])
    
    if not user or not user.is_active:
        return redirect(url_for('auth.login_page'))
    
    # Calculer les statistiques
    days_in_company = (datetime.utcnow() - user.created_at).days
    
    # Compter les demandes en attente
    pending_requests = EmployeeRequest.query.filter_by(
        user_id=user.id,
        status='pending'
    ).count()
    
    # Jours de congés restants (exemple: 30 jours par an)
    total_leave_days = 30
    used_leave_days = db.session.query(db.func.sum(EmployeeRequest.days)).filter(
        EmployeeRequest.user_id == user.id,
        EmployeeRequest.type == 'leave',
        EmployeeRequest.status == 'approved',
        EmployeeRequest.created_at >= datetime(datetime.utcnow().year, 1, 1)
    ).scalar() or 0
    
    remaining_leaves = total_leave_days - used_leave_days
    
    return render_template('profile.html', 
                          user=user,
                          days_in_company=days_in_company,
                          pending_requests=pending_requests,
                          remaining_leaves=remaining_leaves)


@employee_requests_bp.route('/create', methods=['POST'])
@require_login
def create_request():
    """Créer une nouvelle demande"""
    data = request.get_json()
    user_id = session['user_id']
    
    request_type = data.get('type')
    if request_type not in ['loan', 'leave', 'permission']:
        return jsonify({'error': 'Type de demande invalide'}), 400
    
    try:
        # Créer la demande
        employee_request = EmployeeRequest(
            user_id=user_id,
            type=request_type,
            status='pending'
        )
        
        # Données spécifiques selon le type
        if request_type == 'loan':
            employee_request.loan_type = data.get('loan_type')
            employee_request.amount = data.get('amount')
            employee_request.reason = data.get('reason')
            
        elif request_type == 'leave':
            employee_request.leave_type = data.get('leave_type')
            employee_request.start_date = datetime.fromisoformat(data.get('start_date'))
            employee_request.end_date = datetime.fromisoformat(data.get('end_date'))
            employee_request.days = data.get('days')
            employee_request.reason = data.get('reason')
            
            # Vérifier si assez de jours disponibles
            user = User.query.get(user_id)
            total_leave_days = 30
            used_leave_days = db.session.query(db.func.sum(EmployeeRequest.days)).filter(
                EmployeeRequest.user_id == user_id,
                EmployeeRequest.type == 'leave',
                EmployeeRequest.status == 'approved',
                EmployeeRequest.created_at >= datetime(datetime.utcnow().year, 1, 1)
            ).scalar() or 0
            
            remaining = total_leave_days - used_leave_days
            if data.get('days') > remaining:
                return jsonify({
                    'error': f'Vous n\'avez que {remaining} jours de congés disponibles'
                }), 400
            
        elif request_type == 'permission':
            employee_request.permission_date = datetime.fromisoformat(data.get('date'))
            employee_request.start_time = data.get('start_time')
            employee_request.end_time = data.get('end_time')
            employee_request.reason = data.get('reason')
        
        db.session.add(employee_request)
        db.session.commit()
        
        # Logger dans la blockchain
        AuditLogger.log_action(
            user_id,
            'request_created',
            'employee_request',
            employee_request.id,
            {'type': request_type, 'status': 'pending'}
        )
        
        return jsonify({
            'success': True,
            'message': 'Demande créée avec succès',
            'request': employee_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@employee_requests_bp.route('/my-requests', methods=['GET'])
@require_login
def get_my_requests():
    """Récupérer les demandes de l'utilisateur connecté"""
    user_id = session['user_id']
    
    # Filtres
    status = request.args.get('status')
    request_type = request.args.get('type')
    
    query = EmployeeRequest.query.filter_by(user_id=user_id)
    
    if status:
        query = query.filter_by(status=status)
    if request_type:
        query = query.filter_by(type=request_type)
    
    requests = query.order_by(EmployeeRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'requests': [req.to_dict() for req in requests]
    }), 200


@employee_requests_bp.route('/all', methods=['GET'])
@require_admin
def get_all_requests():
    """Récupérer toutes les demandes (admin/manager)"""
    user = User.query.get(session['user_id'])
    
    # Filtres
    status = request.args.get('status')
    request_type = request.args.get('type')
    department_id = request.args.get('department_id')
    
    # Query de base
    if user.is_admin:
        query = EmployeeRequest.query
    elif user.role == 'department_manager' and user.department_id:
        # Manager voit uniquement les demandes de son département
        query = EmployeeRequest.query.join(User).filter(
            User.department_id == user.department_id
        )
    else:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Appliquer les filtres
    if status:
        query = query.filter(EmployeeRequest.status == status)
    if request_type:
        query = query.filter(EmployeeRequest.type == request_type)
    if department_id:
        query = query.join(User).filter(User.department_id == department_id)
    
    requests = query.order_by(EmployeeRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'requests': [req.to_dict() for req in requests]
    }), 200


@employee_requests_bp.route('/approve/<int:request_id>', methods=['POST'])
@require_admin
def approve_request(request_id):
    """Approuver une demande"""
    user = User.query.get(session['user_id'])
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # Vérifier les permissions
    if not user.is_admin:
        if user.role != 'department_manager':
            return jsonify({'error': 'Accès non autorisé'}), 403
        if employee_request.user.department_id != user.department_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        employee_request.status = 'approved'
        employee_request.approved_by_id = user.id
        employee_request.approved_at = datetime.utcnow()
        employee_request.admin_comment = data.get('comment')
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'request_approved',
            'employee_request',
            request_id,
            {'type': employee_request.type, 'user_id': employee_request.user_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Demande approuvée',
            'request': employee_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@employee_requests_bp.route('/reject/<int:request_id>', methods=['POST'])
@require_admin
def reject_request(request_id):
    """Rejeter une demande"""
    user = User.query.get(session['user_id'])
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # Vérifier les permissions
    if not user.is_admin:
        if user.role != 'department_manager':
            return jsonify({'error': 'Accès non autorisé'}), 403
        if employee_request.user.department_id != user.department_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    try:
        employee_request.status = 'rejected'
        employee_request.approved_by_id = user.id
        employee_request.approved_at = datetime.utcnow()
        employee_request.admin_comment = data.get('comment', 'Demande rejetée')
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'request_rejected',
            'employee_request',
            request_id,
            {'type': employee_request.type, 'user_id': employee_request.user_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Demande rejetée',
            'request': employee_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@employee_requests_bp.route('/cancel/<int:request_id>', methods=['POST'])
@require_login
def cancel_request(request_id):
    """Annuler une demande (par l'employé)"""
    user_id = session['user_id']
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # Vérifier que c'est bien la demande de l'utilisateur
    if employee_request.user_id != user_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # On ne peut annuler que les demandes en attente
    if employee_request.status != 'pending':
        return jsonify({'error': 'Seules les demandes en attente peuvent être annulées'}), 400
    
    try:
        employee_request.status = 'cancelled'
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user_id,
            'request_cancelled',
            'employee_request',
            request_id,
            {'type': employee_request.type}
        )
        
        return jsonify({
            'success': True,
            'message': 'Demande annulée'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@employee_requests_bp.route('/stats', methods=['GET'])
@require_login
def get_stats():
    """Statistiques des demandes pour l'utilisateur"""
    user_id = session['user_id']
    
    # Compter par type
    loan_count = EmployeeRequest.query.filter_by(user_id=user_id, type='loan').count()
    leave_count = EmployeeRequest.query.filter_by(user_id=user_id, type='leave').count()
    permission_count = EmployeeRequest.query.filter_by(user_id=user_id, type='permission').count()
    
    # Compter par statut
    pending_count = EmployeeRequest.query.filter_by(user_id=user_id, status='pending').count()
    approved_count = EmployeeRequest.query.filter_by(user_id=user_id, status='approved').count()
    rejected_count = EmployeeRequest.query.filter_by(user_id=user_id, status='rejected').count()
    
    # Jours de congés utilisés cette année
    used_leave_days = db.session.query(db.func.sum(EmployeeRequest.days)).filter(
        EmployeeRequest.user_id == user_id,
        EmployeeRequest.type == 'leave',
        EmployeeRequest.status == 'approved',
        EmployeeRequest.created_at >= datetime(datetime.utcnow().year, 1, 1)
    ).scalar() or 0
    
    return jsonify({
        'success': True,
        'stats': {
            'by_type': {
                'loan': loan_count,
                'leave': leave_count,
                'permission': permission_count
            },
            'by_status': {
                'pending': pending_count,
                'approved': approved_count,
                'rejected': rejected_count
            },
            'leave_days': {
                'total': 30,
                'used': used_leave_days,
                'remaining': 30 - used_leave_days
            }
        }
    }), 200


@employee_requests_bp.route('/admin/dashboard', methods=['GET'])
@require_admin
def admin_dashboard():
    """Dashboard admin pour gérer toutes les demandes"""
    user = User.query.get(session['user_id'])
    
    # Statistiques globales
    total_pending = EmployeeRequest.query.filter_by(status='pending').count()
    total_approved = EmployeeRequest.query.filter_by(status='approved').count()
    total_rejected = EmployeeRequest.query.filter_by(status='rejected').count()
    
    # Demandes récentes
    recent_requests = EmployeeRequest.query.order_by(
        EmployeeRequest.created_at.desc()
    ).limit(10).all()
    
    return jsonify({
        'success': True,
        'stats': {
            'pending': total_pending,
            'approved': total_approved,
            'rejected': total_rejected
        },
        'recent_requests': [req.to_dict() for req in recent_requests]
    }), 200