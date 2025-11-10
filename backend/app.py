# app.py
from flask import Flask, render_template, session, redirect, url_for, current_app
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import timedelta
from config import config
from database import db

# Import des routes
from routes.auth import auth_bp
from routes.company import company_bp
from routes.department import department_bp
from routes.dashboard import dashboard_bp
from routes.users import users_bp
from routes.department_tables import dept_tables_bp
from routes.department_managers import dept_managers_bp

def get_blockchain():
    """Fonction pour obtenir l'instance blockchain sans import circulaire"""
    from models.blockchain import Blockchain
    return current_app.extensions.get('blockchain')

def create_app(config_name='development'):
    """Factory pour créer l'application Flask"""
    app = Flask(__name__, 
                template_folder='../frontend/templates',
                static_folder='../frontend/static')
    
    # Charger la configuration
    app.config.from_object(config[config_name])
    
    # Initialiser les extensions AVEC LA MÊME INSTANCE
    db.init_app(app)
    CORS(app, supports_credentials=True)
    Session(app)
    
    # Initialiser la blockchain après la création de l'app
    with app.app_context():
        from models.blockchain import Blockchain
        blockchain = Blockchain(difficulty=4)
        if len(blockchain.chain) == 0:
            blockchain.create_genesis_block()
        
        # Stocker blockchain dans les extensions de l'app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['blockchain'] = blockchain
    
    # Enregistrer les blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(dept_tables_bp)
    app.register_blueprint(dept_managers_bp)
    
    # Créer les tables
    with app.app_context():
        db.create_all()
    
    # Route principale
    @app.route('/')
    def index():
        """Route d'accueil - redirige selon l'état"""
        from models.user import User
        
        # Vérifier si c'est le premier démarrage
        user_count = User.query.count()
        if user_count == 0:
            return redirect(url_for('auth.signup_admin_page'))
        
        # Vérifier si l'utilisateur est connecté
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        # Vérifier si l'utilisateur a une entreprise
        user = User.query.get(session['user_id'])
        if not user.company_id:
            return redirect(url_for('company.company_setup_page'))
        
        # Rediriger vers le dashboard
        return redirect(url_for('dashboard'))
    
    @app.route('/dashboard')
    def dashboard():
        """Page du dashboard principal"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        return render_template('dashboard.html', user=user)
    
    @app.route('/departments')
    def departments_page():
        """Page de gestion des départements"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        return render_template('department.html')
    @app.route('/department-settings/<int:dept_id>')
    def department_settings_page(dept_id):
        """Page de configuration du département avec gestion des tables"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.company import Department
        
        user = User.query.get(session['user_id'])
        department = Department.query.get_or_404(dept_id)
        
        # Vérifier les permissions
        if not user.is_admin and user.company_id != department.company_id:
            return redirect(url_for('dashboard'))
        
        return render_template('department_settings.html', department=department)
    
    @app.route('/department-table/<int:table_id>')
    def department_table_page(table_id):
        """Page de visualisation/édition d'une table"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.department_table import DepartmentTable
        
        user = User.query.get(session['user_id'])
        table = DepartmentTable.query.get_or_404(table_id)
        
        # Vérifier les permissions
        if not user.is_admin and user.company_id != table.department.company_id:
            return redirect(url_for('dashboard'))
        
        return render_template('department_table.html', table=table)

    @app.route('/department/delete/<int:dept_id>', methods=['POST'])
    def delete_department_page(dept_id):
        """Route pour la suppression via l'interface web"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.company import Department
        from flask import jsonify
        from datetime import datetime
        
        user = User.query.get(session['user_id'])
        department = Department.query.get_or_404(dept_id)
        
        # Vérifier les permissions
        if not user.is_admin:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        if user.company_id != department.company_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        try:
            # SOFT DELETE avec deleted_at
            department.deleted_at = datetime.utcnow()
            db.session.commit()
            
            # Rediriger vers la liste des départements
            return redirect(url_for('departments_page'))
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

    @app.route('/api/blockchain/stats', methods=['GET'])
    def blockchain_stats():
        """Statistiques de la blockchain"""
        from flask import jsonify
        try:
            blockchain = get_blockchain()
            if blockchain:
                stats = blockchain.get_blockchain_stats()
                return jsonify(stats)
            return jsonify({'error': 'Blockchain non disponible'}), 500
        except Exception as e:
            return jsonify({
                'error': f'Erreur lors de la récupération des stats: {str(e)}'
            }), 500
    
    @app.route('/api/blockchain/chain', methods=['GET'])
    def get_chain():
        """Récupérer toute la chaîne"""
        from flask import jsonify
        blockchain = get_blockchain()
        if blockchain:
            return jsonify({
                'chain': blockchain.get_chain(),
                'length': len(blockchain.chain)
            })
        return jsonify({'error': 'Blockchain non disponible'}), 500
    
    @app.route('/api/blockchain/mine', methods=['POST'])
    def mine_block():
        """Miner les transactions en attente"""
        from flask import jsonify
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        blockchain = get_blockchain()
        if not blockchain:
            return jsonify({'error': 'Blockchain non disponible'}), 500
        
        miner_address = f"user_{session['user_id']}"
        success = blockchain.mine_pending_transactions(miner_address)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Bloc miné avec succès',
                'block': blockchain.get_latest_block()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Aucune transaction en attente'
            })
    
    @app.route('/api/blockchain/validate', methods=['GET'])
    def validate_chain():
        """Valider l'intégrité de la blockchain"""
        from flask import jsonify
        blockchain = get_blockchain()
        if blockchain:
            is_valid = blockchain.is_chain_valid()
            return jsonify({
                'is_valid': is_valid,
                'message': 'Blockchain valide' if is_valid else 'Blockchain corrompue'
            })
        return jsonify({'error': 'Blockchain non disponible'}), 500
    
    @app.route('/api/blockchain/history/<entity_type>/<int:entity_id>', methods=['GET'])
    def get_history(entity_type, entity_id):
        """Récupérer l'historique d'une entité"""
        from flask import jsonify
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        blockchain = get_blockchain()
        if blockchain:
            history = blockchain.get_transaction_history(entity_type, str(entity_id))
            return jsonify({
                'success': True,
                'history': history
            })
        return jsonify({'error': 'Blockchain non disponible'}), 500
    
    # Gestionnaire d'erreurs
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('403.html'), 403
    
    # Context processor pour les templates
    @app.context_processor
    def inject_user():
        """Injecter l'utilisateur dans tous les templates"""
        if 'user_id' in session:
            from models.user import User
            user = User.query.get(session['user_id'])
            return dict(current_user=user)
        return dict(current_user=None)
    
    # Commande CLI pour initialiser la base de données
    @app.cli.command()
    def init_db():
        """Initialiser la base de données"""
        db.create_all()
        print('Base de données initialisée!')
    
    @app.cli.command()
    def create_admin():
        """Créer un utilisateur admin via CLI"""
        from models.user import User
        import getpass
        
        username = input('Nom d\'utilisateur: ')
        email = input('Email: ')
        password = getpass.getpass('Mot de passe: ')
        
        admin = User(
            username=username,
            email=email,
            is_admin=True,
            role='admin'
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        print(f'Administrateur {username} créé avec succès!')
    
    return app

# Point d'entrée pour le serveur de développement
if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5002, debug=True)