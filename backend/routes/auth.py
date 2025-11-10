# auth.py
from flask import Blueprint, request, jsonify, session, render_template, redirect, current_app
from models.user import User
from database import db
from models.company import Company
from utils.security import (
    SecurityValidator, rate_limiter, AuditLogger,
    rate_limit, generate_csrf_token
)
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def get_blockchain():
    """Fonction helper pour obtenir blockchain sans import circulaire"""
    return current_app.extensions.get('blockchain') if current_app else None

@auth_bp.route('/check-first-run', methods=['GET'])
def check_first_run():
    """Vérifie si c'est le premier démarrage (aucun utilisateur)"""
    user_count = User.query.count()
    return jsonify({
        'is_first_run': user_count == 0,
        'needs_admin_setup': user_count == 0
    })

@auth_bp.route('/signup-admin', methods=['POST'])
def signup_admin():
    """Création du premier compte administrateur - VERSION CORRIGÉE"""
    # Vérifier qu'aucun utilisateur n'existe
    if User.query.count() > 0:
        return jsonify({'error': 'Admin already exists'}), 403
    
    data = request.get_json()
    
    # Validation des données
    username = SecurityValidator.sanitize_input(data.get('username', ''))
    email = SecurityValidator.sanitize_input(data.get('email', ''))
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    first_name = SecurityValidator.sanitize_input(data.get('first_name', ''))
    last_name = SecurityValidator.sanitize_input(data.get('last_name', ''))
    company_name = SecurityValidator.sanitize_input(data.get('company_name', ''))
    
    # Validation du nom d'utilisateur
    valid, error_msg = SecurityValidator.validate_username(username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Validation de l'email
    valid, error_msg = SecurityValidator.validate_email(email)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Validation du mot de passe
    if password != confirm_password:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400
    
    valid, error_msg = SecurityValidator.validate_password(password, username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
   
    
    # Vérification de la sécurité SQL
    if not SecurityValidator.validate_sql_safe(username):
        return jsonify({'error': 'Caractères invalides détectés'}), 400
    
    try:
        # CRÉATION DE L'ENTREPRISE EN PREMIER
        company = Company(
            name=company_name,
            legal_name=data.get('company_legal_name', company_name),
            email=email,
            phone=data.get('company_phone', ''),
            address=data.get('company_address', ''),
            city=data.get('company_city', ''),
            country=data.get('company_country', 'Tunisie'),
            industry=data.get('company_industry', '')
        )
        db.session.add(company)
        db.session.flush()  # Pour obtenir l'ID de la company sans commit
        
        # Créer l'utilisateur admin AVEC company_id
        admin_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_id=company.id,  # CORRIGÉ : association à l'entreprise
            is_admin=True,
            is_active=True,
            role='admin'
        )
        admin_user.set_password(password)
        
        db.session.add(admin_user)
        db.session.flush()  # Pour obtenir l'ID de l'user sans commit
        
        # Associer la company à l'admin
        company.created_by_id = admin_user.id
        
        db.session.commit()
        
        # Logger l'événement dans la blockchain (SANS IMPORT CIRCULAIRE)
        try:
            blockchain = get_blockchain()
            if blockchain:
                blockchain.add_transaction({
                    'type': 'admin_created',
                    'user_id': admin_user.id,
                    'username': username,
                    'email': email,
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Blockchain logging failed: {e}")
        
        # Connexion automatique
        session['user_id'] = admin_user.id
        session['username'] = admin_user.username
        session['is_admin'] = True
        session['company_id'] = company.id  # CORRIGÉ : stocker company_id dans la session
        session['csrf_token'] = generate_csrf_token()
        
        # Logger la connexion
        AuditLogger.log_login_attempt(username, request.remote_addr, True)
        
        return jsonify({
            'success': True,
            'message': 'Compte administrateur créé avec succès',
            'user': admin_user.to_dict(),
            'company': company.to_dict(),
            'csrf_token': session['csrf_token']
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création du compte: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15)
def login():
    """Connexion utilisateur avec sécurité renforcée"""
    data = request.get_json()
    
    username = SecurityValidator.sanitize_input(data.get('username', ''))
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Nom d\'utilisateur et mot de passe requis'}), 400
    
    # Vérification de la sécurité SQL
    if not SecurityValidator.validate_sql_safe(username):
        AuditLogger.log_login_attempt(username, request.remote_addr, False, 
                                      'sql_injection_attempt')
        return jsonify({'error': 'Caractères invalides détectés'}), 400
    
    # Rechercher l'utilisateur
    user = User.query.filter_by(username=username).first()
    
    if not user:
        AuditLogger.log_login_attempt(username, request.remote_addr, False, 
                                      'user_not_found')
        return jsonify({'error': 'Nom d\'utilisateur ou mot de passe incorrect'}), 401
    
    # Vérifier si le compte est verrouillé
    if user.is_account_locked():
        AuditLogger.log_login_attempt(username, request.remote_addr, False, 
                                      'account_locked')
        return jsonify({
            'error': 'Compte temporairement verrouillé',
            'locked_until': user.account_locked_until.isoformat()
        }), 403
    
    # Vérifier le compte actif
    if not user.is_active:
        AuditLogger.log_login_attempt(username, request.remote_addr, False, 
                                      'account_inactive')
        return jsonify({'error': 'Compte désactivé'}), 403
    
    # Vérifier le mot de passe
    if not user.check_password(password):
        user.increment_failed_login()
        AuditLogger.log_login_attempt(username, request.remote_addr, False, 
                                      'invalid_password')
        
        remaining_attempts = 5 - user.failed_login_attempts
        if remaining_attempts > 0:
            return jsonify({
                'error': 'Nom d\'utilisateur ou mot de passe incorrect',
                'remaining_attempts': remaining_attempts
            }), 401
        else:
            return jsonify({
                'error': 'Compte verrouillé pour 30 minutes après 5 tentatives échouées'
            }), 403
    
    # Connexion réussie
    user.reset_failed_login()
    user.last_ip = request.remote_addr
    db.session.commit()
    
    # Créer la session
    session['user_id'] = user.id
    session['username'] = user.username
    session['is_admin'] = user.is_admin
    session['company_id'] = user.company_id  # CORRIGÉ : toujours stocker company_id
    session['csrf_token'] = generate_csrf_token()
    session.permanent = True
    
    # Logger la connexion
    AuditLogger.log_login_attempt(username, request.remote_addr, True)
    
    # Réinitialiser le rate limiter pour cet utilisateur
    rate_limiter.reset(request.remote_addr)
    
    return jsonify({
        'success': True,
        'message': 'Connexion réussie',
        'user': user.to_dict(),
        'csrf_token': session['csrf_token']
    }), 200

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Déconnexion utilisateur"""
    user_id = session.get('user_id')
    
    if user_id:
        try:
            blockchain = get_blockchain()
            if blockchain:
                blockchain.add_transaction({
                    'type': 'logout',
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Blockchain logging failed: {e}")
    
    session.clear()

    # Si la requête vient d’un navigateur (non AJAX) → redirection
    if request.method == 'GET' or request.content_type != 'application/json':
        return redirect('/auth/login-page')

    # Si la requête vient d’un appel JS/AJAX → réponse JSON
    return jsonify({'success': True, 'message': 'Déconnexion réussie'}), 200


@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Vérifie si la session est valide"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_active:
        session.clear()
        return jsonify({'authenticated': False}), 401
    
    return jsonify({
        'authenticated': True,
        'user': user.to_dict(),
        'csrf_token': session.get('csrf_token')
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Changement de mot de passe"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    user = User.query.get(session['user_id'])
    
    # Vérifier le mot de passe actuel
    if not user.check_password(current_password):
        return jsonify({'error': 'Mot de passe actuel incorrect'}), 401
    
    # Vérifier que les nouveaux mots de passe correspondent
    if new_password != confirm_password:
        return jsonify({'error': 'Les nouveaux mots de passe ne correspondent pas'}), 400
    
    # Valider le nouveau mot de passe
    valid, error_msg = SecurityValidator.validate_password(new_password, user.username)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Vérifier que le nouveau mot de passe est différent
    if user.check_password(new_password):
        return jsonify({'error': 'Le nouveau mot de passe doit être différent'}), 400
    
    try:
        # Changer le mot de passe
        user.set_password(new_password)
        db.session.commit()
        
        # Logger dans la blockchain (SANS IMPORT CIRCULAIRE)
        try:
            blockchain = get_blockchain()
            if blockchain:
                blockchain.add_transaction({
                    'type': 'password_changed',
                    'user_id': user.id,
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Blockchain logging failed: {e}")
        
        # Logger l'action
        AuditLogger.log_action(user.id, 'password_changed', 'user', user.id)
        
        return jsonify({
            'success': True,
            'message': 'Mot de passe modifié avec succès'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors du changement de mot de passe: {str(e)}'}), 500

@auth_bp.route('/request-password-reset', methods=['POST'])
@rate_limit(max_attempts=3, window_minutes=60)
def request_password_reset():
    """Demande de réinitialisation de mot de passe"""
    data = request.get_json()
    email = SecurityValidator.sanitize_input(data.get('email', ''))
    
    # Validation
    valid, error_msg = SecurityValidator.validate_email(email)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    user = User.query.filter_by(email=email).first()
    
    # Ne pas révéler si l'email existe ou non (sécurité)
    if user and user.is_active:
        # TODO: Générer un token et envoyer un email
        # Pour l'instant, juste logger
        AuditLogger.log_action(user.id, 'password_reset_requested', 'user', user.id)
    
    return jsonify({
        'success': True,
        'message': 'Si cet email existe, un lien de réinitialisation a été envoyé'
    }), 200

# Routes pour les templates HTML
@auth_bp.route('/login-page', methods=['GET'])
def login_page():
    """Page de connexion"""
    return render_template('login.html')

@auth_bp.route('/signup-admin-page', methods=['GET'])
def signup_admin_page():
    """Page de création du compte admin"""
    # Vérifier qu'aucun utilisateur n'existe
    if User.query.count() > 0:
        return redirect('/auth/login-page')
    return render_template('signup_admin.html')