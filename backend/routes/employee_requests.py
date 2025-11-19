# routes/employee_requests.py
"""Routes pour la gestion des demandes avec hiérarchie et blockchain"""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app
from database import db
from models.user import User
from models.employee_request import EmployeeRequest
from utils.security import require_login, require_admin, AuditLogger
from datetime import datetime, timedelta

employee_requests_bp = Blueprint('employee_requests', __name__, url_prefix='/api/employee-requests')


def get_blockchain():
    """Récupère l'instance blockchain"""
    return current_app.extensions.get('blockchain')


def add_to_blockchain(request_obj, action_type, user_id):
    """Ajoute une transaction à la blockchain"""
    blockchain = get_blockchain()
    if not blockchain:
        return False
    
    transaction = {
        'type': 'employee_request',
        'action': action_type,
        'entity_type': 'employee_request',
        'entity_id': request_obj.id,
        'user_id': user_id,
        'request_type': request_obj.type,
        'requester_id': request_obj.user_id,
        'requester_name': request_obj.user.get_full_name(),
        'status': request_obj.status,
        'details': {
            'type': request_obj.type,
            'reason': request_obj.reason[:100] if request_obj.reason else None,
            'expected_approver': request_obj.expected_approver_id,
            'actual_approver': request_obj.approved_by_id if request_obj.approved_by_id else None
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Ajouter des détails spécifiques selon le type
    if request_obj.type == 'leave':
        transaction['details'].update({
            'leave_type': request_obj.leave_type,
            'start_date': request_obj.start_date.isoformat() if request_obj.start_date else None,
            'end_date': request_obj.end_date.isoformat() if request_obj.end_date else None,
            'days': request_obj.days
        })
    elif request_obj.type == 'loan':
        transaction['details'].update({
            'amount': float(request_obj.amount) if request_obj.amount else None
        })
    
    blockchain.add_transaction(transaction)
    
    # Miner immédiatement pour les actions importantes
    if action_type in ['approved', 'rejected']:
        blockchain.mine_pending_transactions(f"system_payroll")
        
        # Mettre à jour l'enregistrement avec le hash blockchain
        latest_block = blockchain.get_latest_block()
        if latest_block:
            request_obj.blockchain_hash = latest_block['hash']
            request_obj.blockchain_block_index = latest_block['index']
            request_obj.is_in_blockchain = True
            db.session.commit()
    
    return True


@employee_requests_bp.route('/create', methods=['POST'])
@require_login
def create_request():
    """Créer une nouvelle demande avec approbateur automatique"""
    data = request.get_json()
    user_id = session['user_id']
    
    request_type = data.get('type')
    if request_type not in ['loan', 'leave', 'permission']:
        return jsonify({'error': 'Type de demande invalide'}), 400
    
    try:
        # Vérifier que l'utilisateur existe
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utilisateur introuvable'}), 404
        
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
            
            # Vérifier jours disponibles
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
        
        # Ajouter à la session AVANT de définir l'approbateur
        db.session.add(employee_request)
        db.session.flush()
        
        # 🆕 Définir l'approbateur attendu selon la hiérarchie
        try:
            employee_request.set_expected_approver()
        except ValueError as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
        
        # Flush again après avoir défini l'approbateur
        db.session.flush()
        
        # 🆕 Ajouter à la blockchain
        add_to_blockchain(employee_request, 'created', user_id)
        
        # Commit final
        db.session.commit()
        
        # Logger dans l'audit
        AuditLogger.log_action(
            user_id,
            'request_created',
            'employee_request',
            employee_request.id,
            {
                'type': request_type, 
                'status': 'pending',
                'expected_approver': employee_request.expected_approver_id
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Demande créée avec succès',
            'request': employee_request.to_dict(),
            'hierarchy_info': employee_request.get_approval_hierarchy_info()
        }), 201
        
    except ValueError as ve:
        db.session.rollback()
        print(f"Erreur de validation: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Erreur inattendue: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
        
@employee_requests_bp.route('/my-requests', methods=['GET'])
@require_login
def get_my_requests():
    """Récupérer les demandes de l'utilisateur connecté"""
    user_id = session['user_id']
    
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


@employee_requests_bp.route('/pending-for-me', methods=['GET'])
@require_login
def get_pending_for_me():
    """
    🆕 Récupérer les demandes en attente qui doivent être traitées par l'utilisateur
    selon la hiérarchie d'approbation
    """
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Filtres
    request_type = request.args.get('type')
    
    # Query de base : demandes où je suis l'approbateur attendu
    query = EmployeeRequest.query.filter(
        EmployeeRequest.expected_approver_id == user_id,
        EmployeeRequest.status == 'pending'
    )
    
    # OU si je suis admin, je vois toutes les demandes pending
    if user.is_admin:
        query = EmployeeRequest.query.filter_by(status='pending')
    
    if request_type:
        query = query.filter_by(type=request_type)
    
    requests = query.order_by(EmployeeRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'requests': [req.to_dict() for req in requests],
        'count': len(requests)
    }), 200


@employee_requests_bp.route('/all', methods=['GET'])
@require_login
def get_all_requests():
    """Récupérer toutes les demandes selon les permissions"""
    user = User.query.get(session['user_id'])
    
    status = request.args.get('status')
    request_type = request.args.get('type')
    department_id = request.args.get('department_id')
    
    # Query de base selon le rôle
    if user.is_admin or user.role == 'directeur_rh':
        # Admin et DRH voient tout
        query = EmployeeRequest.query
    elif user.role == 'department_manager' and user.department_id:
        # Chef voit son département
        query = EmployeeRequest.query.join(User).filter(
            User.department_id == user.department_id
        )
    elif user.role == 'assistant_administratif':
        # Assistant admin voit tout (lecture seule)
        query = EmployeeRequest.query
    else:
        # Autres : uniquement leurs propres demandes
        query = EmployeeRequest.query.filter_by(user_id=user.id)
    
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
@require_login
def approve_request(request_id):
    """Approuver une demande avec vérification hiérarchique"""
    user = User.query.get(session['user_id'])
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # 🆕 Vérifier les permissions selon la hiérarchie
    if not employee_request.can_be_approved_by(user):
        return jsonify({
            'error': 'Vous n\'êtes pas autorisé à approuver cette demande selon la hiérarchie',
            'expected_approver': employee_request.expected_approver.get_full_name() if employee_request.expected_approver else 'Admin'
        }), 403
    
    data = request.get_json()
    
    try:
        employee_request.status = 'approved'
        employee_request.approved_by_id = user.id
        employee_request.approved_at = datetime.utcnow()
        employee_request.admin_comment = data.get('comment')
        
        db.session.flush()
        
        # 🆕 Ajouter à la blockchain
        add_to_blockchain(employee_request, 'approved', user.id)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'request_approved',
            'employee_request',
            request_id,
            {
                'type': employee_request.type, 
                'user_id': employee_request.user_id,
                'approver_role': user.role
            }
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
@require_login
def reject_request(request_id):
    """Rejeter une demande avec vérification hiérarchique"""
    user = User.query.get(session['user_id'])
    employee_request = EmployeeRequest.query.get_or_404(request_id)
    
    # 🆕 Vérifier les permissions selon la hiérarchie
    if not employee_request.can_be_approved_by(user):
        return jsonify({
            'error': 'Vous n\'êtes pas autorisé à rejeter cette demande selon la hiérarchie'
        }), 403
    
    data = request.get_json()
    
    try:
        employee_request.status = 'rejected'
        employee_request.approved_by_id = user.id
        employee_request.approved_at = datetime.utcnow()
        employee_request.admin_comment = data.get('comment', 'Demande rejetée')
        
        db.session.flush()
        
        # 🆕 Ajouter à la blockchain
        add_to_blockchain(employee_request, 'rejected', user.id)
        
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            user.id,
            'request_rejected',
            'employee_request',
            request_id,
            {
                'type': employee_request.type, 
                'user_id': employee_request.user_id,
                'approver_role': user.role
            }
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
    
    if employee_request.user_id != user_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    if employee_request.status != 'pending':
        return jsonify({'error': 'Seules les demandes en attente peuvent être annulées'}), 400
    
    try:
        employee_request.status = 'cancelled'
        db.session.flush()
        
        # Ajouter à la blockchain
        add_to_blockchain(employee_request, 'cancelled', user_id)
        
        db.session.commit()
        
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

@employee_requests_bp.route('/admin/dashboard', methods=['GET'])
@require_login
def get_admin_dashboard_stats():
    """
    📊 Statistiques du dashboard admin pour les demandes
    """
    user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not (user.is_admin or user.role == 'department_manager'):
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    try:
        # Construire la query de base selon les permissions
        if user.is_admin or user.role == 'directeur_rh':
            # Admin et DRH voient tout
            base_query = EmployeeRequest.query
        elif user.role == 'department_manager' and user.department_id:
            # Chef voit son département
            base_query = EmployeeRequest.query.join(User).filter(
                User.department_id == user.department_id
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Accès refusé'
            }), 403
        
        # Calculer les statistiques
        stats = {
            'pending': base_query.filter_by(status='pending').count(),
            'approved': base_query.filter_by(status='approved').count(),
            'rejected': base_query.filter_by(status='rejected').count(),
            'cancelled': base_query.filter_by(status='cancelled').count()
        }
        
        # Statistiques par type
        stats['by_type'] = {
            'loan': base_query.filter_by(type='loan').count(),
            'leave': base_query.filter_by(type='leave').count(),
            'permission': base_query.filter_by(type='permission').count()
        }
        
        # Demandes récentes (7 derniers jours)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        stats['recent'] = base_query.filter(
            EmployeeRequest.created_at >= seven_days_ago
        ).count()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        print(f"Erreur get_admin_dashboard_stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@employee_requests_bp.route('/stats', methods=['GET'])
@require_login
def get_stats():
    """Statistiques des demandes pour l'utilisateur"""
    user_id = session['user_id']
    
    loan_count = EmployeeRequest.query.filter_by(user_id=user_id, type='loan').count()
    leave_count = EmployeeRequest.query.filter_by(user_id=user_id, type='leave').count()
    permission_count = EmployeeRequest.query.filter_by(user_id=user_id, type='permission').count()
    
    pending_count = EmployeeRequest.query.filter_by(user_id=user_id, status='pending').count()
    approved_count = EmployeeRequest.query.filter_by(user_id=user_id, status='approved').count()
    rejected_count = EmployeeRequest.query.filter_by(user_id=user_id, status='rejected').count()
    
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