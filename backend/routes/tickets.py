# routes/tickets.py
"""Routes pour la gestion des tickets avec hiérarchie par département"""
from flask import Blueprint, request, jsonify, session, render_template, current_app
from database import db
from models.user import User
from models.company import Department
from models.ticket import Ticket, TicketComment, TicketAttachment, TicketHistory
from utils.security import require_login, SecurityValidator, AuditLogger
from datetime import datetime
from werkzeug.utils import secure_filename
import os

tickets_bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')


def get_blockchain():
    """Récupère l'instance blockchain"""
    return current_app.extensions.get('blockchain')


def add_to_blockchain(ticket, action_type, user_id):
    """Ajoute une transaction à la blockchain"""
    blockchain = get_blockchain()
    if not blockchain:
        return False
    
    transaction = {
        'type': 'ticket',
        'action': action_type,
        'entity_type': 'ticket',
        'entity_id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'user_id': user_id,
        'creator_id': ticket.created_by_id,
        'department_id': ticket.department_id,
        'status': ticket.status,
        'priority': ticket.priority,
        'category': ticket.category,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    blockchain.add_transaction(transaction)
    
    # Miner pour les actions importantes
    if action_type in ['created', 'resolved', 'escalated']:
        blockchain.mine_pending_transactions('system_tickets')
        
        latest_block = blockchain.get_latest_block()
        if latest_block:
            ticket.blockchain_hash = latest_block['hash']
            ticket.is_in_blockchain = True
            db.session.commit()
    
    return True



def can_view_ticket(ticket, user):
    """Vérifie si un user peut voir un ticket"""
    # Admin voit tout
    if user.is_admin:
        return True
    
    # Créateur du ticket peut le voir
    if ticket.created_by_id == user.id:
        return True
    
    # Assigné peut le voir
    if ticket.assigned_to_id == user.id:
        return True
    
    # Chef de département peut voir les tickets de son département
    if user.role == 'department_manager' and user.department_id == ticket.department_id:
        return True
    
    # Membres du même département peuvent voir les tickets du département
    if user.department_id == ticket.department_id:
        return True
    
    return False


def can_modify_ticket(ticket, user):
    """Vérifie si un user peut modifier/résoudre un ticket"""
    # Admin peut tout modifier
    if user.is_admin:
        return True
    
    # Chef de département peut modifier les tickets de son département
    if user.role == 'department_manager' and user.department_id == ticket.department_id:
        return True
    
    # L'assigné peut modifier son ticket
    if ticket.assigned_to_id == user.id:
        return True
    
    return False


# ==================== CRÉATION ====================

@tickets_bp.route('/create', methods=['POST'])
@require_login
def create_ticket():
    """Créer un nouveau ticket - AVEC DÉPARTEMENT OBLIGATOIRE"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    data = request.get_json()
    
    title = SecurityValidator.sanitize_input(data.get('title', ''))
    description = SecurityValidator.sanitize_input(data.get('description', ''), allow_html=False)
    category = data.get('category')
    priority = data.get('priority', 'normale')
    department_id = data.get('department_id')  # NOUVEAU: département obligatoire
    
    # Validation
    if not title or not description or not category:
        return jsonify({'error': 'Titre, description et catégorie requis'}), 400
    
    if not department_id:
        return jsonify({'error': 'Le département est requis'}), 400
    
    # Vérifier que le département existe
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Département invalide'}), 400
    
    # Vérifier que l'utilisateur a accès à ce département
    if user.company_id != department.company_id:
        return jsonify({'error': 'Accès non autorisé à ce département'}), 403
    
    valid_categories = ['production', 'quality_control', 'warehouse', 'it_support', 
                       'hr', 'maintenance', 'security', 'other']
    if category not in valid_categories:
        return jsonify({'error': 'Catégorie invalide'}), 400
    
    valid_priorities = ['basse', 'normale', 'haute', 'critique', 'urgente']
    if priority not in valid_priorities:
        return jsonify({'error': 'Priorité invalide'}), 400
    
    try:
        ticket = Ticket(
            created_by_id=user_id,
            department_id=department_id,  # Département assigné dès la création
            title=title,
            description=description,
            category=category,
            priority=priority,
            location=SecurityValidator.sanitize_input(data.get('location', '')),
            equipment=SecurityValidator.sanitize_input(data.get('equipment', '')),
            status='en_attente'
        )
        
        # Générer numéro de ticket
        ticket.generate_ticket_number()
        
        # Tags
        if 'tags' in data:
            ticket.set_tags(data['tags'])
        
        # Calculer SLA
        ticket.calculate_sla_deadline()
        
        db.session.add(ticket)
        db.session.flush()
        
        # Historique
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=user_id,
            action='created',
            new_value=f'Créé par {user.get_full_name()} pour le département {department.name}'
        )
        db.session.add(history)
        
        db.session.commit()
        
        # Blockchain
        add_to_blockchain(ticket, 'created', user_id)
        
        # Logger
        AuditLogger.log_action(
            user_id,
            'ticket_created',
            'ticket',
            ticket.id,
            {'ticket_number': ticket.ticket_number, 'category': category, 'department_id': department_id}
        )
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} créé avec succès',
            'ticket': ticket.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur create_ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


# ==================== CONSULTATION ====================

@tickets_bp.route('/my-tickets', methods=['GET'])
@require_login
def get_my_tickets():
    """Récupérer mes tickets créés"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    status = request.args.get('status')
    category = request.args.get('category')
    
    # Base query: tickets créés par l'utilisateur OU dans son département
    query = Ticket.query.filter(
        db.or_(
            Ticket.created_by_id == user_id,
            Ticket.department_id == user.department_id
        )
    )
    
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Filtrer selon permissions
    accessible_tickets = [t for t in tickets if can_view_ticket(t, user)]
    
    return jsonify({
        'success': True,
        'tickets': [t.to_dict() for t in accessible_tickets],
        'count': len(accessible_tickets)
    }), 200


@tickets_bp.route('/assigned-to-me', methods=['GET'])
@require_login
def get_assigned_to_me():
    """Récupérer les tickets assignés à moi"""
    user_id = session['user_id']
    
    status = request.args.get('status', 'en_attente,en_cours,reouvert')
    statuses = status.split(',')
    
    query = Ticket.query.filter(
        Ticket.assigned_to_id == user_id,
        Ticket.status.in_(statuses)
    )
    
    tickets = query.order_by(
        Ticket.priority.desc(),
        Ticket.created_at.asc()
    ).all()
    
    return jsonify({
        'success': True,
        'tickets': [t.to_dict() for t in tickets],
        'count': len(tickets)
    }), 200


@tickets_bp.route('/all', methods=['GET'])
@require_login
def get_all_tickets():
    """Récupérer tous les tickets selon permissions"""
    user = User.query.get(session['user_id'])
    
    # Admin voit tous les tickets de l'entreprise
    if user.is_admin:
        # Jointure avec Department pour filtrer par entreprise
        query = Ticket.query.join(Department).filter(Department.company_id == user.company_id)
    # Chef de département voit les tickets de son département
    elif user.role == 'department_manager' and user.department_id:
        query = Ticket.query.filter_by(department_id=user.department_id)
    # Autres utilisateurs : leurs tickets + tickets de leur département
    else:
        if not user.department_id:
            return jsonify({
                'success': True,
                'tickets': [],
                'count': 0,
                'message': 'Vous devez être assigné à un département pour voir les tickets'
            }), 200
        
        query = Ticket.query.filter(
            db.or_(
                Ticket.created_by_id == user.id,
                Ticket.department_id == user.department_id
            )
        )
    
    # Appliquer les filtres
    status = request.args.get('status')
    category = request.args.get('category')
    priority = request.args.get('priority')
    overdue_only = request.args.get('overdue', 'false').lower() == 'true'
    
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if priority:
        query = query.filter_by(priority=priority)
    if overdue_only:
        query = query.filter_by(is_overdue=True)
    
    tickets = query.order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).all()
    
    print(f"Utilisateur: {user.username} (Admin: {user.is_admin})")
    print(f"Nombre total de tickets dans la base: {Ticket.query.count()}")
    print(f"Tickets après filtrage: {len(tickets)}")

    # Vérifier les données de chaque ticket
    for ticket in tickets:
        print(f" - Ticket {ticket.id}: {ticket.ticket_number}, Département: {ticket.department_id}, Créé par: {ticket.created_by_id}")
    # Debug: Afficher le nombre de tickets trouvés
    print(f"Tickets trouvés: {len(tickets)}")
    for ticket in tickets:
        print(f"Ticket {ticket.id}: {ticket.ticket_number} - Département: {ticket.department_id}")
    
    # Pour l'admin, pas besoin de double vérification des permissions
    if user.is_admin:
        accessible_tickets = tickets
    else:
        accessible_tickets = [t for t in tickets if can_view_ticket(t, user)]
    
    return jsonify({
        'success': True,
        'tickets': [t.to_dict() for t in accessible_tickets],
        'count': len(accessible_tickets)
    }), 200
@tickets_bp.route('/<int:ticket_id>', methods=['GET'])
@require_login
def get_ticket_details(ticket_id):
    """Détails complets d'un ticket"""
    user = User.query.get(session['user_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier permissions
    if not can_view_ticket(ticket, user):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'ticket': ticket.to_dict(include_comments=True, include_attachments=True),
        'can_modify': can_modify_ticket(ticket, user)
    }), 200


# ==================== ASSIGNATION ====================

@tickets_bp.route('/<int:ticket_id>/assign', methods=['POST'])
@require_login
def assign_ticket(ticket_id):
    """Assigner un ticket à un user DU MÊME DÉPARTEMENT"""
    user = User.query.get(session['user_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier permissions
    if not can_modify_ticket(ticket, user):
        return jsonify({'error': 'Seul le chef de département ou l\'admin peut assigner'}), 403
    
    data = request.get_json()
    assigned_to_id = data.get('assigned_to_id')
    
    if not assigned_to_id:
        return jsonify({'error': 'assigned_to_id requis'}), 400
    
    assigned_user = User.query.get_or_404(assigned_to_id)
    
    # VÉRIFICATION: L'assigné doit être du même département
    if assigned_user.department_id != ticket.department_id:
        return jsonify({
            'error': 'L\'utilisateur doit appartenir au même département que le ticket'
        }), 400
    
    try:
        old_assigned_name = ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Aucun'
        
        ticket.assigned_to_id = assigned_to_id
        ticket.assigned_at = datetime.utcnow()
        ticket.status = 'en_cours'
        
        # Historique
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            action='assigned',
            old_value=old_assigned_name,
            new_value=assigned_user.get_full_name()
        )
        db.session.add(history)
        
        db.session.commit()
        
        # Blockchain
        add_to_blockchain(ticket, 'assigned', user.id)
        
        return jsonify({
            'success': True,
            'message': f'Ticket assigné à {assigned_user.get_full_name()}',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== RÉSOLUTION ====================

@tickets_bp.route('/<int:ticket_id>/resolve', methods=['POST'])
@require_login
def resolve_ticket(ticket_id):
    """Marquer un ticket comme résolu"""
    user = User.query.get(session['user_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier permissions: Assigné, Chef de département, ou Admin
    if not can_modify_ticket(ticket, user):
        return jsonify({'error': 'Seul l\'assigné, le chef de département ou l\'admin peut résoudre'}), 403
    
    data = request.get_json()
    comment = SecurityValidator.sanitize_input(data.get('comment', ''), allow_html=False)
    
    if not comment:
        return jsonify({'error': 'Commentaire de résolution requis'}), 400
    
    try:
        ticket.resolve(user.id, comment)
        
        # Historique
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            action='resolved',
            new_value=f'Résolu en {ticket.resolution_time_minutes} minutes par {user.get_full_name()}',
            comment=comment
        )
        db.session.add(history)
        
        db.session.commit()
        
        # Blockchain
        add_to_blockchain(ticket, 'resolved', user.id)
        
        return jsonify({
            'success': True,
            'message': f'Ticket résolu en {ticket.resolution_time_minutes} minutes',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/<int:ticket_id>/reopen', methods=['POST'])
@require_login
def reopen_ticket(ticket_id):
    """Réouvrir un ticket"""
    user = User.query.get(session['user_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier permissions
    if not can_view_ticket(ticket, user):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    reason = SecurityValidator.sanitize_input(data.get('reason', ''), allow_html=False)
    
    if not reason:
        return jsonify({'error': 'Raison requise'}), 400
    
    try:
        success = ticket.reopen(user.id, reason)
        
        if not success:
            return jsonify({'error': 'Ce ticket ne peut pas être réouvert'}), 400
        
        # Historique
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            action='reopened',
            comment=reason
        )
        db.session.add(history)
        
        db.session.commit()
        
        # Blockchain
        add_to_blockchain(ticket, 'reopened', user.id)
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== COMMENTAIRES ====================

@tickets_bp.route('/<int:ticket_id>/comments', methods=['POST'])
@require_login
def add_comment(ticket_id):
    """Ajouter un commentaire"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier permissions
    if not can_view_ticket(ticket, user):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    comment_text = SecurityValidator.sanitize_input(data.get('comment', ''), allow_html=False)
    is_internal = data.get('is_internal', False)
    
    if not comment_text:
        return jsonify({'error': 'Commentaire vide'}), 400
    
    try:
        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=user_id,
            comment=comment_text,
            is_internal=is_internal
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== LISTE USERS POUR ASSIGNATION ====================

@tickets_bp.route('/department/<int:department_id>/users', methods=['GET'])
@require_login
def get_department_users(department_id):
    """Liste des users d'un département pour assignation"""
    
    user = User.query.get(session['user_id'])
        
    # Validation du department_id
    if not department_id or department_id <= 0:
        return jsonify({'error': 'ID de département invalide'}), 400
            
    department = Department.query.get_or_404(department_id)
    
    # Vérifier accès
    if not user.is_admin and user.company_id != department.company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    users = User.query.filter_by(
        department_id=department_id,
        is_active=True
    ).all()
    
    return jsonify({
        'success': True,
        'users': [{
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name(),
            'role': u.role
        } for u in users]
    }), 200


# ==================== STATISTIQUES ====================

@tickets_bp.route('/stats', methods=['GET'])
@require_login
def get_ticket_stats():
    """Statistiques des tickets - PAR DÉPARTEMENT"""
    user = User.query.get(session['user_id'])
    
    # Query de base selon permissions
    if user.is_admin:
        base_query = Ticket.query
    elif user.role == 'department_manager' and user.department_id:
        base_query = Ticket.query.filter_by(department_id=user.department_id)
    else:
        if not user.department_id:
            return jsonify({'success': True, 'stats': {}}), 200
        base_query = Ticket.query.filter_by(department_id=user.department_id)
    
    stats = {
        'total': base_query.count(),
        'en_attente': base_query.filter_by(status='en_attente').count(),
        'en_cours': base_query.filter_by(status='en_cours').count(),
        'resolu': base_query.filter_by(status='resolu').count(),
        'overdue': base_query.filter_by(is_overdue=True).count(),
        'by_priority': {
            'urgente': base_query.filter_by(priority='urgente').count(),
            'critique': base_query.filter_by(priority='critique').count(),
            'haute': base_query.filter_by(priority='haute').count(),
            'normale': base_query.filter_by(priority='normale').count(),
            'basse': base_query.filter_by(priority='basse').count()
        },
        'by_category': {}
    }
    
    # Par catégorie
    categories = ['production', 'quality_control', 'warehouse', 'it_support', 'hr', 'maintenance', 'security']
    for cat in categories:
        stats['by_category'][cat] = base_query.filter_by(category=cat).count()
    
    # Temps de résolution moyen
    resolved_tickets = base_query.filter(Ticket.resolution_time_minutes.isnot(None)).all()
    if resolved_tickets:
        avg_resolution = sum(t.resolution_time_minutes for t in resolved_tickets) / len(resolved_tickets)
        stats['avg_resolution_minutes'] = round(avg_resolution, 2)
    
    return jsonify({
        'success': True,
        'stats': stats
    }), 200


# ==================== LISTE DÉPARTEMENTS ====================

@tickets_bp.route('/departments', methods=['GET'])
@require_login
def get_departments_list():
    """Liste des départements pour sélection - TOUS les départements de l'entreprise"""
    user = User.query.get(session['user_id'])
    
    # TOUS les utilisateurs voient TOUS les départements de l'entreprise
    departments = Department.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).filter(Department.deleted_at.is_(None)).all()
    
    return jsonify({
        'success': True,
        'departments': [{
            'id': d.id,
            'name': d.name,
            'code': d.code
        } for d in departments]
    }), 200


# ==================== PAGE HTML ====================

@tickets_bp.route('/page', methods=['GET'])
@require_login
def tickets_page():
    """Page de gestion des tickets"""
    user = User.query.get(session['user_id'])
    return render_template('tickets.html', user=user)