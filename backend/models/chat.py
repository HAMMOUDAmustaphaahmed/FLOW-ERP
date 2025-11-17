# models/chat.py
"""Modèles pour la messagerie interne"""
from datetime import datetime
from database import db
import json


class ChatConversation(db.Model):
    """Conversation 1-to-1 entre deux utilisateurs"""
    
    __tablename__ = 'chat_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Les deux utilisateurs (toujours user1_id < user2_id)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Métadonnées
    last_message_preview = db.Column(db.String(200))
    last_message_at = db.Column(db.DateTime)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user1 = db.relationship('User', foreign_keys=[user1_id], backref='conversations_as_user1')
    user2 = db.relationship('User', foreign_keys=[user2_id], backref='conversations_as_user2')
    messages = db.relationship('ChatMessage', back_populates='conversation', 
                               cascade='all, delete-orphan', lazy='dynamic')
    
    # Index pour recherche rapide
    __table_args__ = (
        db.Index('idx_conv_users', 'user1_id', 'user2_id'),
        db.UniqueConstraint('user1_id', 'user2_id', name='unique_conversation')
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'last_message_preview': self.last_message_preview,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ChatConversation {self.id}>'


class ChatGroup(db.Model):
    """Groupe de discussion"""
    
    __tablename__ = 'chat_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Avatar du groupe
    avatar_url = db.Column(db.String(255))
    
    # Métadonnées
    last_message_preview = db.Column(db.String(200))
    last_message_at = db.Column(db.DateTime)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    members = db.relationship('ChatGroupMember', back_populates='group', 
                             cascade='all, delete-orphan', lazy='dynamic')
    messages = db.relationship('ChatMessage', back_populates='group', 
                              cascade='all, delete-orphan', lazy='dynamic')
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'members_count': self.members.filter_by(is_active=True).count(),
            'last_message_preview': self.last_message_preview,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'created_at': self.created_at.isoformat(),
            'created_by_id': self.created_by_id
        }
    
    def __repr__(self):
        return f'<ChatGroup {self.name}>'


class ChatGroupMember(db.Model):
    """Membre d'un groupe"""
    
    __tablename__ = 'chat_group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Notifications
    muted = db.Column(db.Boolean, default=False)
    
    # Audit
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    
    # Relations
    group = db.relationship('ChatGroup', back_populates='members')
    user = db.relationship('User', backref='group_memberships')
    
    # Index
    __table_args__ = (
        db.Index('idx_group_user', 'group_id', 'user_id'),
        db.UniqueConstraint('group_id', 'user_id', name='unique_group_member')
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': self.user.get_full_name(),
                'is_online': getattr(self.user, 'is_online', False)
            },
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'muted': self.muted,
            'joined_at': self.joined_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ChatGroupMember {self.user_id} in {self.group_id}>'


class ChatMessage(db.Model):
    """Message de chat"""
    
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Conversation ou groupe
    conversation_id = db.Column(db.Integer, db.ForeignKey('chat_conversations.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'))
    
    # Expéditeur
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Contenu
    content = db.Column(db.Text, nullable=False)
    
    # Type de message
    message_type = db.Column(db.String(50), default='text')  # text, file, image, system
    
    # Fichier attaché
    file_id = db.Column(db.Integer, db.ForeignKey('chat_files.id'))
    
    # Statut
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Réaction (emoji)
    reactions = db.Column(db.Text)  # JSON: {"👍": [user_id1, user_id2], "❤️": [user_id3]}
    
    # Message en réponse à un autre
    reply_to_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'))
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    conversation = db.relationship('ChatConversation', back_populates='messages')
    group = db.relationship('ChatGroup', back_populates='messages')
    sender = db.relationship('User', foreign_keys=[sender_id])
    file = db.relationship('ChatFile', backref='message')
    reply_to = db.relationship('ChatMessage', remote_side=[id], backref='replies')
    
    # Index pour recherche
    __table_args__ = (
        db.Index('idx_conv_messages', 'conversation_id', 'created_at'),
        db.Index('idx_group_messages', 'group_id', 'created_at'),
    )
    
    def get_reactions(self) -> dict:
        """Récupère les réactions JSON"""
        return json.loads(self.reactions) if self.reactions else {}
    
    def set_reactions(self, reactions: dict):
        """Définit les réactions JSON"""
        self.reactions = json.dumps(reactions)
    
    def add_reaction(self, emoji: str, user_id: int):
        """Ajoute une réaction"""
        reactions = self.get_reactions()
        if emoji not in reactions:
            reactions[emoji] = []
        if user_id not in reactions[emoji]:
            reactions[emoji].append(user_id)
        self.set_reactions(reactions)
    
    def remove_reaction(self, emoji: str, user_id: int):
        """Retire une réaction"""
        reactions = self.get_reactions()
        if emoji in reactions and user_id in reactions[emoji]:
            reactions[emoji].remove(user_id)
            if not reactions[emoji]:
                del reactions[emoji]
        self.set_reactions(reactions)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'group_id': self.group_id,
            'sender': {
                'id': self.sender.id,
                'username': self.sender.username,
                'full_name': self.sender.get_full_name()
            },
            'content': self.content,
            'message_type': self.message_type,
            'file': self.file.to_dict() if self.file else None,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_deleted': self.is_deleted,
            'reactions': self.get_reactions(),
            'reply_to_id': self.reply_to_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'


class ChatFile(db.Model):
    """Fichier partagé dans le chat"""
    
    __tablename__ = 'chat_files'
    
    id = db.Column(db.Integer, primary_key=True)
    
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # En bytes
    mime_type = db.Column(db.String(100))
    
    # Contexte
    conversation_id = db.Column(db.Integer, db.ForeignKey('chat_conversations.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('chat_groups.id'))
    
    # Audit
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relations
    uploaded_by = db.relationship('User', backref='chat_files')
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat(),
            'uploaded_by': {
                'id': self.uploaded_by.id,
                'username': self.uploaded_by.username,
                'full_name': self.uploaded_by.get_full_name()
            }
        }
    
    def __repr__(self):
        return f'<ChatFile {self.filename}>'