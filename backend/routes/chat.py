# routes/chat.py
"""Routes pour la messagerie interne"""
from flask import Blueprint, request, jsonify, session, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from database import db
from models.user import User
from models.chat import ChatMessage, ChatConversation, ChatGroup, ChatGroupMember, ChatFile
from utils.security import require_login, SecurityValidator, AuditLogger
from datetime import datetime
from werkzeug.utils import secure_filename
import os

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# Configuration SocketIO (à initialiser dans app.py)
socketio = None

def init_socketio(app):
    """Initialiser SocketIO"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect')
    def handle_connect():
        """Connexion WebSocket"""
        if 'user_id' not in session:
            return False
        
        user_id = session['user_id']
        join_room(f'user_{user_id}')
        
        # Notifier que l'utilisateur est en ligne
        user = User.query.get(user_id)
        if user:
            user.is_online = True
            user.last_seen = datetime.utcnow()
            db.session.commit()
            
            emit('user_status', {
                'user_id': user_id,
                'status': 'online'
            }, broadcast=True)
    
    # AJOUTER CE GESTIONNAIRE POUR REJOINDRE LES ROOMS
    @socketio.on('join_room')
    def handle_join_room(data):
        """Rejoindre une room de conversation ou groupe"""
        if 'user_id' not in session:
            return {'error': 'Non authentifié'}
        
        user_id = session['user_id']
        conversation_id = data.get('conversation_id')
        group_id = data.get('group_id')
        
        if conversation_id:
            # Vérifier que l'utilisateur a accès à cette conversation
            conversation = ChatConversation.query.get(conversation_id)
            if conversation and (conversation.user1_id == user_id or conversation.user2_id == user_id):
                join_room(f'conversation_{conversation_id}')
                print(f"Utilisateur {user_id} a rejoint conversation_{conversation_id}")
            else:
                return {'error': 'Accès non autorisé'}
        elif group_id:
            # Vérifier que l'utilisateur est membre du groupe
            membership = ChatGroupMember.query.filter_by(
                group_id=group_id,
                user_id=user_id,
                is_active=True
            ).first()
            if membership:
                join_room(f'group_{group_id}')
                print(f"Utilisateur {user_id} a rejoint group_{group_id}")
            else:
                return {'error': 'Accès non autorisé'}
        
        return {'success': True}
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Déconnexion WebSocket"""
        if 'user_id' in session:
            user_id = session['user_id']
            user = User.query.get(user_id)
            if user:
                user.is_online = False
                user.last_seen = datetime.utcnow()
                db.session.commit()
                
                emit('user_status', {
                    'user_id': user_id,
                    'status': 'offline',
                    'last_seen': user.last_seen.isoformat()
                }, broadcast=True)

    @socketio.on('typing')
    def handle_typing(data):
        """Notification de frappe"""
        conversation_id = data.get('conversation_id')
        user_id = session['user_id']
        
        emit('user_typing', {
            'user_id': user_id,
            'conversation_id': conversation_id
        }, room=f'conversation_{conversation_id}', include_self=False)
    
    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        """Arrêt de frappe"""
        conversation_id = data.get('conversation_id')
        user_id = session['user_id']
        
        emit('user_stop_typing', {
            'user_id': user_id,
            'conversation_id': conversation_id
        }, room=f'conversation_{conversation_id}', include_self=False)
    
    return socketio


# =============== CONVERSATIONS ===============

@chat_bp.route('/conversations', methods=['GET'])
@require_login
def get_conversations():
    """Liste des conversations de l'utilisateur"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Conversations 1-to-1
    conversations = ChatConversation.query.filter(
        db.or_(
            ChatConversation.user1_id == user_id,
            ChatConversation.user2_id == user_id
        )
    ).order_by(ChatConversation.last_message_at.desc()).all()
    
    # Groupes
    group_memberships = ChatGroupMember.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    result = {
        'conversations': [],
        'groups': []
    }
    
    # Conversations 1-to-1
    for conv in conversations:
        other_user = conv.user2 if conv.user1_id == user_id else conv.user1
        
        # Compter les non-lus
        unread_count = ChatMessage.query.filter_by(
            conversation_id=conv.id,
            is_read=False
        ).filter(
            ChatMessage.sender_id != user_id
        ).count()
        
        result['conversations'].append({
            'id': conv.id,
            'other_user': {
                'id': other_user.id,
                'username': other_user.username,
                'full_name': other_user.get_full_name(),
                'is_online': getattr(other_user, 'is_online', False),
                'last_seen': other_user.last_seen.isoformat() if hasattr(other_user, 'last_seen') and other_user.last_seen else None
            },
            'last_message': conv.last_message_preview,
            'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
            'unread_count': unread_count
        })
    
    # Groupes - FIX: utiliser .count() au lieu de len()
    for membership in group_memberships:
        group = membership.group
        
        unread_count = ChatMessage.query.filter_by(
            group_id=group.id,
            is_read=False
        ).filter(
            ChatMessage.sender_id != user_id
        ).count()
        
        # FIX: Utiliser .count() pour les relations dynamiques
        members_count = group.members.filter_by(is_active=True).count()
        
        result['groups'].append({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'members_count': members_count,  # FIX appliqué ici
            'last_message': group.last_message_preview,
            'last_message_at': group.last_message_at.isoformat() if group.last_message_at else None,
            'unread_count': unread_count,
            'is_admin': membership.is_admin
        })
    
    return jsonify({
        'success': True,
        **result
    }), 200



@chat_bp.route('/users/available', methods=['GET'])
@require_login
def get_available_users():
    """Récupérer tous les utilisateurs disponibles pour créer un groupe"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Chercher dans la même entreprise, exclure l'utilisateur actuel
    users = User.query.filter(
        User.company_id == user.company_id,
        User.id != user.id,
        User.is_active == True
    ).all()
    
    return jsonify({
        'success': True,
        'users': [{
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name(),
            'email': u.email,
            'is_online': getattr(u, 'is_online', False)
        } for u in users]
    })

@chat_bp.route('/conversation/<int:other_user_id>', methods=['GET'])
@require_login
def get_or_create_conversation(other_user_id):
    """Récupérer ou créer une conversation 1-to-1"""
    user_id = session['user_id']
    
    if user_id == other_user_id:
        return jsonify({'error': 'Impossible de créer une conversation avec soi-même'}), 400
    
    # Vérifier que l'autre utilisateur existe et est de la même entreprise
    other_user = User.query.get_or_404(other_user_id)
    current_user = User.query.get(user_id)
    
    if other_user.company_id != current_user.company_id:
        return jsonify({'error': 'Utilisateur non accessible'}), 403
    
    # Chercher une conversation existante
    conversation = ChatConversation.query.filter(
        db.or_(
            db.and_(
                ChatConversation.user1_id == user_id,
                ChatConversation.user2_id == other_user_id
            ),
            db.and_(
                ChatConversation.user1_id == other_user_id,
                ChatConversation.user2_id == user_id
            )
        )
    ).first()
    
    if not conversation:
        # Créer nouvelle conversation
        conversation = ChatConversation(
            user1_id=min(user_id, other_user_id),
            user2_id=max(user_id, other_user_id)
        )
        db.session.add(conversation)
        db.session.commit()
    
    # SUPPRIMER cette partie qui cause l'erreur
    # # Rejoindre la room WebSocket
    # if socketio:
    #     join_room(f'conversation_{conversation.id}')
    
    return jsonify({
        'success': True,
        'conversation': conversation.to_dict()
    }), 200

@chat_bp.route('/messages/read', methods=['POST'])
@require_login
def mark_messages_read():
    """Marquer un message comme lu"""
    user_id = session['user_id']
    data = request.get_json()
    
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'error': 'message_id requis'}), 400
    
    try:
        message = ChatMessage.query.get_or_404(message_id)
        
        # Vérifier les permissions
        if message.conversation_id:
            conversation = message.conversation
            if conversation.user1_id != user_id and conversation.user2_id != user_id:
                return jsonify({'error': 'Accès non autorisé'}), 403
        elif message.group_id:
            membership = ChatGroupMember.query.filter_by(
                group_id=message.group_id,
                user_id=user_id,
                is_active=True
            ).first()
            if not membership:
                return jsonify({'error': 'Accès non autorisé'}), 403
        else:
            return jsonify({'error': 'Message invalide'}), 400
        
        # Marquer comme lu
        if not message.is_read and message.sender_id != user_id:
            message.is_read = True
            message.read_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/messages/<int:conversation_id>', methods=['GET'])
@require_login
def get_messages(conversation_id):
    """Récupérer les messages d'une conversation"""
    user_id = session['user_id']
    
    conversation = ChatConversation.query.get_or_404(conversation_id)
    
    # Vérifier l'accès
    if conversation.user1_id != user_id and conversation.user2_id != user_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    messages_query = ChatMessage.query.filter_by(
        conversation_id=conversation_id
    ).order_by(ChatMessage.created_at.desc())
    
    pagination = messages_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Marquer comme lus
    ChatMessage.query.filter_by(
        conversation_id=conversation_id,
        is_read=False
    ).filter(
        ChatMessage.sender_id != user_id
    ).update({'is_read': True, 'read_at': datetime.utcnow()})
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'messages': [msg.to_dict() for msg in reversed(pagination.items)],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@chat_bp.route('/send', methods=['POST'])
@require_login
def send_message():
    """Envoyer un message"""
    user_id = session['user_id']
    data = request.get_json()
    
    conversation_id = data.get('conversation_id')
    group_id = data.get('group_id')
    content = SecurityValidator.sanitize_input(data.get('content', ''), allow_html=False)
    
    if not content:
        return jsonify({'error': 'Message vide'}), 400
    
    try:
        if conversation_id:
            # Message 1-to-1
            conversation = ChatConversation.query.get_or_404(conversation_id)
            
            # Vérifier l'accès
            if conversation.user1_id != user_id and conversation.user2_id != user_id:
                return jsonify({'error': 'Accès non autorisé'}), 403
            
            message = ChatMessage(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=content
            )
            
            db.session.add(message)
            
            # Mettre à jour la conversation
            conversation.last_message_preview = content[:100]
            conversation.last_message_at = datetime.utcnow()
            
            db.session.commit()
            
            # Envoyer via WebSocket
            if socketio:
                socketio.emit('new_message', message.to_dict(), 
                            room=f'conversation_{conversation_id}')
                
                # Notifier l'autre utilisateur
                other_user_id = conversation.user2_id if conversation.user1_id == user_id else conversation.user1_id
                socketio.emit('notification', {
                    'type': 'new_message',
                    'from': User.query.get(user_id).get_full_name(),
                    'message': content[:50],
                    'conversation_id': conversation_id
                }, room=f'user_{other_user_id}')
        
        elif group_id:
            # Message de groupe
            group = ChatGroup.query.get_or_404(group_id)
            
            # Vérifier que l'utilisateur est membre
            membership = ChatGroupMember.query.filter_by(
                group_id=group_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not membership:
                return jsonify({'error': 'Non membre du groupe'}), 403
            
            message = ChatMessage(
                group_id=group_id,
                sender_id=user_id,
                content=content
            )
            
            db.session.add(message)
            
            # Mettre à jour le groupe
            group.last_message_preview = content[:100]
            group.last_message_at = datetime.utcnow()
            
            db.session.commit()
            
            # Envoyer via WebSocket
            if socketio:
                socketio.emit('new_message', message.to_dict(), 
                            room=f'group_{group_id}')
        
        else:
            return jsonify({'error': 'conversation_id ou group_id requis'}), 400
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============== GROUPES ===============

@chat_bp.route('/groups', methods=['GET'])
@require_login
def list_groups():
    """Lister les groupes de l'utilisateur"""
    user_id = session['user_id']
    
    memberships = ChatGroupMember.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    groups = []
    for membership in memberships:
        group = membership.group
        groups.append({
            **group.to_dict(),
            'is_admin': membership.is_admin
        })
    
    return jsonify({
        'success': True,
        'groups': groups
    }), 200


@chat_bp.route('/groups/create', methods=['POST'])
@require_login
def create_group():
    """Créer un groupe"""
    user_id = session['user_id']
    data = request.get_json()
    
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    description = SecurityValidator.sanitize_input(data.get('description', ''))
    member_ids = data.get('member_ids', [])
    
    if not name:
        return jsonify({'error': 'Nom requis'}), 400
    
    try:
        group = ChatGroup(
            name=name,
            description=description,
            created_by_id=user_id
        )
        
        db.session.add(group)
        db.session.flush()
        
        # Ajouter le créateur comme admin
        creator_member = ChatGroupMember(
            group_id=group.id,
            user_id=user_id,
            is_admin=True
        )
        db.session.add(creator_member)
        
        # Ajouter les autres membres
        for member_id in member_ids:
            if member_id != user_id:
                member = ChatGroupMember(
                    group_id=group.id,
                    user_id=member_id,
                    is_admin=False
                )
                db.session.add(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'group': group.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Ajouter cette route si elle n'existe pas
@chat_bp.route('/groups/<int:group_id>/messages', methods=['GET'])
@require_login
def get_group_messages(group_id):
    """Récupérer les messages d'un groupe"""
    user_id = session['user_id']
    
    # Vérifier que l'utilisateur est membre du groupe
    membership = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    if not membership:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    messages_query = ChatMessage.query.filter_by(
        group_id=group_id
    ).order_by(ChatMessage.created_at.desc())
    
    pagination = messages_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Marquer comme lus
    ChatMessage.query.filter_by(
        group_id=group_id,
        is_read=False
    ).filter(
        ChatMessage.sender_id != user_id
    ).update({'is_read': True, 'read_at': datetime.utcnow()})
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'messages': [msg.to_dict() for msg in reversed(pagination.items)],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@chat_bp.route('/groups/<int:group_id>/members', methods=['GET'])
@require_login
def get_group_members(group_id):
    """Liste des membres d'un groupe"""
    user_id = session['user_id']
    
    # Vérifier que l'utilisateur est membre
    membership = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    if not membership:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    members = ChatGroupMember.query.filter_by(
        group_id=group_id,
        is_active=True
    ).all()
    
    return jsonify({
        'success': True,
        'members': [m.to_dict() for m in members]
    }), 200


# =============== FICHIERS ===============

@chat_bp.route('/upload', methods=['POST'])
@require_login
def upload_file():
    """Uploader un fichier"""
    user_id = session['user_id']
    
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    
    file = request.files['file']
    conversation_id = request.form.get('conversation_id', type=int)
    group_id = request.form.get('group_id', type=int)
    
    if not file.filename:
        return jsonify({'error': 'Fichier invalide'}), 400
    
    # Limite de taille (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'Fichier trop volumineux (max 10MB)'}), 400
    
    try:
        filename = secure_filename(file.filename)
        
        # Sauvegarder le fichier
        upload_folder = os.path.join('uploads', 'chat_files')
        os.makedirs(upload_folder, exist_ok=True)
        
        unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # Créer l'entrée en DB
        chat_file = ChatFile(
            filename=filename,
            filepath=filepath,
            file_size=file_size,
            mime_type=file.content_type,
            uploaded_by_id=user_id,
            conversation_id=conversation_id,
            group_id=group_id
        )
        
        db.session.add(chat_file)
        db.session.commit()
        
        # Créer un message avec le fichier
        message_content = f"[Fichier: {filename}]"
        
        message = ChatMessage(
            conversation_id=conversation_id,
            group_id=group_id,
            sender_id=user_id,
            content=message_content,
            file_id=chat_file.id
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Notifier via WebSocket
        if socketio:
            room = f'conversation_{conversation_id}' if conversation_id else f'group_{group_id}'
            socketio.emit('new_message', message.to_dict(), room=room)
        
        return jsonify({
            'success': True,
            'file': chat_file.to_dict(),
            'message': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============== RECHERCHE ===============

@chat_bp.route('/search', methods=['GET'])
@require_login
def search_messages():
    """Rechercher dans l'historique"""
    user_id = session['user_id']
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'success': True, 'results': []}), 200
    
    # Rechercher dans les conversations 1-to-1
    conversations = ChatConversation.query.filter(
        db.or_(
            ChatConversation.user1_id == user_id,
            ChatConversation.user2_id == user_id
        )
    ).all()
    
    conversation_ids = [c.id for c in conversations]
    
    # Rechercher dans les groupes
    memberships = ChatGroupMember.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    group_ids = [m.group_id for m in memberships]
    
    # Recherche
    search_pattern = f'%{query}%'
    
    messages = ChatMessage.query.filter(
        db.or_(
            ChatMessage.conversation_id.in_(conversation_ids),
            ChatMessage.group_id.in_(group_ids)
        ),
        ChatMessage.content.ilike(search_pattern)
    ).order_by(ChatMessage.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'results': [msg.to_dict() for msg in messages]
    }), 200


# =============== PAGE PRINCIPALE ===============

@chat_bp.route('/', methods=['GET'])
@require_login
def chat_page():
    """Page principale du chat"""
    user = User.query.get(session['user_id'])
    return render_template('internal_chat.html', user=user)