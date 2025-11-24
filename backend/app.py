# app.py
from flask import Flask, render_template, session, redirect, url_for, current_app, request, jsonify
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import timedelta
from config import config
from database import db
from models.payroll import Payslip
import json
from models.dashboard import DashboardWidget, DashboardLayout
from models.department_table import DepartmentTable, TableRow
from sqlalchemy import func
from routes.dashboard_widgets import dashboard_widgets_bp

# Import des routes
from routes.auth import auth_bp
from routes.company import company_bp
from routes.department import department_bp
from routes.dashboard import dashboard_bp
from routes.users import users_bp
from routes.department_tables import dept_tables_bp
from routes.department_managers import dept_managers_bp
from routes.employee_requests import employee_requests_bp
from routes.payroll import payroll_bp
from routes.chat import chat_bp, init_socketio
from routes.tickets import tickets_bp
from routes.projects import projects_bp
from utils.project_scheduler import register_scheduler_routes
from routes.dashboard_custom import dashboard_custom_bp



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
    app.register_blueprint(employee_requests_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(dashboard_custom_bp)
    app.register_blueprint(dashboard_widgets_bp)

    register_scheduler_routes(app)
    # Initialiser SocketIO et le retourner
    socketio = init_socketio(app)

    
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
        """Page du dashboard personnalisé"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        # Utiliser le nouveau template dashboard_custom.html
        return render_template('dashboard.html', user=user)
    
    @app.route('/company/stats/<int:company_id>')
    def company_stats(company_id):
        """Statistiques détaillées de l'entreprise"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        from models.company import Company, Department
        from models.department_table import DepartmentTable
        from sqlalchemy import func
        
        user = User.query.get(session['user_id'])
        
        # Vérifier les permissions
        if not user.is_admin and user.company_id != company_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        try:
            company = Company.query.get_or_404(company_id)
            
            # Statistiques de base
            departments_count = Department.query.filter_by(
                company_id=company_id,
                is_active=True
            ).count()
            
            users_count = User.query.filter_by(
                company_id=company_id,
                is_active=True
            ).count()
            
            tables_count = db.session.query(func.count(DepartmentTable.id)).join(
                Department
            ).filter(
                Department.company_id == company_id,
                DepartmentTable.is_active == True
            ).scalar() or 0
            
            # Compter les entrées totales dans toutes les tables
            from models.department_table import TableRow
            total_entries = db.session.query(func.count(TableRow.id)).join(
                DepartmentTable
            ).join(
                Department
            ).filter(
                Department.company_id == company_id,
                TableRow.is_active == True
            ).scalar() or 0
            
            # Activité quotidienne des 7 derniers jours
            from datetime import datetime, timedelta
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            
            daily_activity = []
            day_names = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
            
            for i in range(7):
                day = seven_days_ago + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                entries = db.session.query(func.count(TableRow.id)).join(
                    DepartmentTable
                ).join(
                    Department
                ).filter(
                    Department.company_id == company_id,
                    TableRow.created_at >= day_start,
                    TableRow.created_at < day_end
                ).scalar() or 0
                
                active_users = db.session.query(func.count(func.distinct(TableRow.created_by_id))).join(
                    DepartmentTable
                ).join(
                    Department
                ).filter(
                    Department.company_id == company_id,
                    TableRow.created_at >= day_start,
                    TableRow.created_at < day_end
                ).scalar() or 0
                
                daily_activity.append({
                    'day_name': day_names[day.weekday()],
                    'entries': entries,
                    'active_users': active_users
                })
            
            # Statistiques par département
            departments = Department.query.filter_by(
                company_id=company_id,
                is_active=True
            ).all()
            
            departments_data = []
            for dept in departments:
                entries_count = db.session.query(func.count(TableRow.id)).join(
                    DepartmentTable
                ).filter(
                    DepartmentTable.department_id == dept.id,
                    TableRow.is_active == True
                ).scalar() or 0
                
                departments_data.append({
                    'id': dept.id,
                    'name': dept.name,
                    'entries_count': entries_count,
                    'users_count': len(dept.employees)
                })
            
            # Distribution des rôles
            role_distribution = {}
            roles = db.session.query(
                User.role,
                func.count(User.id).label('count')
            ).filter(
                User.company_id == company_id,
                User.is_active == True
            ).group_by(User.role).all()
            
            for role, count in roles:
                role_distribution[role] = count
            
            return jsonify({
                'success': True,
                'stats': {
                    'departments_count': departments_count,
                    'users_count': users_count,
                    'tables_count': tables_count,
                    'total_entries': total_entries,
                    'daily_activity': daily_activity,
                    'departments': departments_data,
                    'role_distribution': role_distribution
                }
            })
            
        except Exception as e:
            print(f"Erreur lors du chargement des stats: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    # Routes pour les widgets personnalisés (garder celles du dashboard_custom.py)

    @app.route('/api/dashboard/widgets/list', methods=['GET'])
    def list_user_widgets():
        """Liste des widgets personnalisés de l'utilisateur"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        from models.dashboard import DashboardWidget
        
        user = User.query.get(session['user_id'])
        
        widgets = DashboardWidget.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(DashboardWidget.position_order).all()
        
        return jsonify({
            'success': True,
            'widgets': [w.to_dict() for w in widgets]
        })


    @app.route('/api/dashboard/widgets/create', methods=['POST'])
    def create_widget():
        """Créer un nouveau widget personnalisé"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        from models.dashboard import DashboardWidget
        import json
        
        user = User.query.get(session['user_id'])
        data = request.json
        
        widget = DashboardWidget(
            user_id=user.id,
            title=data.get('title'),
            widget_type=data.get('widget_type'),
            chart_type=data.get('chart_type', 'bar'),
            data_source=data.get('data_source'),
            department_id=data.get('department_id'),
            filters=json.dumps(data.get('filters', {})),
            size=data.get('size', 'medium'),
            position_order=data.get('position_order', 0)
        )
        
        db.session.add(widget)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'widget': widget.to_dict()
        })


    @app.route('/api/dashboard/widgets/<int:widget_id>/data', methods=['GET'])
    def get_widget_data(widget_id):
        """Récupérer les données d'un widget"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        from models.dashboard import DashboardWidget
        
        user = User.query.get(session['user_id'])
        widget = DashboardWidget.query.get_or_404(widget_id)
        
        if widget.user_id != user.id:
            return jsonify({'error': 'Non autorisé'}), 403
        
        # Générer les données selon le type de widget
        # (utiliser la logique de dashboard_custom.py)
        data = generate_widget_data(widget, user)
        
        return jsonify({
            'success': True,
            'data': data
        })


    def generate_widget_data(widget, user):
        """Génère les données pour un widget selon son type"""
        import json
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        filters = json.loads(widget.filters) if widget.filters else {}
        date_range = filters.get('date_range', 'week')
        
        # Calculer les dates
        end_date = datetime.utcnow()
        if date_range == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0)
        elif date_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif date_range == 'quarter':
            start_date = end_date - timedelta(days=90)
        elif date_range == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)
        
        data_source = widget.data_source
        
        # Exemple pour les employés
        if data_source == 'employees':
            from models.user import User
            
            if widget.widget_type == 'count':
                count = User.query.filter(
                    User.company_id == user.company_id,
                    User.is_active == True,
                    User.created_at >= start_date
                ).count()
                
                return {
                    'value': count,
                    'label': 'Employés',
                    'type': 'single'
                }
            
            elif widget.widget_type == 'distribution':
                roles = db.session.query(
                    User.role,
                    func.count(User.id).label('count')
                ).filter(
                    User.company_id == user.company_id,
                    User.is_active == True
                ).group_by(User.role).all()
                
                role_labels = {
                    'admin': 'Administrateurs',
                    'directeur_rh': 'Directeurs RH',
                    'department_manager': 'Managers',
                    'employee': 'Employés',
                    'technician': 'Techniciens'
                }
                
                return {
                    'labels': [role_labels.get(r.role, r.role) for r in roles],
                    'datasets': [{
                        'label': 'Distribution des rôles',
                        'data': [r.count for r in roles]
                    }],
                    'type': 'chart'
                }
        
        # Retour par défaut
        return {
            'labels': [],
            'datasets': [],
            'type': 'chart'
        }


    @app.route('/api/dashboard/widgets/<int:widget_id>/delete', methods=['DELETE'])
    def delete_widget(widget_id):
        """Supprimer un widget"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        from models.dashboard import DashboardWidget
        
        user = User.query.get(session['user_id'])
        widget = DashboardWidget.query.get_or_404(widget_id)
        
        if widget.user_id != user.id:
            return jsonify({'error': 'Non autorisé'}), 403
        
        db.session.delete(widget)
        db.session.commit()
        
        return jsonify({'success': True})
        
    @app.route('/departments')
    def departments_page():
        """Page de gestion des départements"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        return render_template('departments.html', user=user)
    @app.route('/projects')
    def projects_page():
        """Page de gestion des départements"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        return render_template('projects_all.html', user=user)
    
    @app.route('/projects/<int:project_id>')
    def project_detail_page(project_id):
        """Page de détail d'un projet"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.project import Project
        
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Vérifier les permissions
        if not user.is_admin and project.company_id != user.company_id:
            return redirect(url_for('dashboard'))
        
        return render_template('project_detail.html', project=project, user=user)
    @app.route('/tickets')
    def tickets_page():
        """Page de gestion des tickets"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        return render_template('tickets.html', user=user)
    
    @app.route('/profile')
    def profile():
        """Page de profil utilisateur"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.employee_request import EmployeeRequest
        from datetime import datetime
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        days_in_company = (datetime.utcnow() - user.created_at).days
        pending_requests = EmployeeRequest.query.filter_by(user_id=user.id, status='pending').count()
        total_leave_days = 30
        used_leave_days = db.session.query(db.func.sum(EmployeeRequest.days)).filter(
            EmployeeRequest.user_id == user.id, EmployeeRequest.type == 'leave',
            EmployeeRequest.status == 'approved',
            EmployeeRequest.created_at >= datetime(datetime.utcnow().year, 1, 1)
        ).scalar() or 0
        remaining_leaves = total_leave_days - used_leave_days
        
        return render_template('profile.html', user=user, days_in_company=days_in_company,
                            pending_requests=pending_requests, remaining_leaves=remaining_leaves)

    @app.route('/admin/requests')
    def admin_requests_page():
        """Page admin pour gérer toutes les demandes"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        if not user.is_admin and user.role != 'department_manager':
            return redirect(url_for('dashboard'))
        
        return render_template('admin_requests.html', user=user)
    
    @app.route('/chat')
    def chat_page():
        """Page de chat/messagerie"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for('auth.login_page'))
        
        return render_template('internal_chat.html', user=user)
    


    @app.route('/chat/users/search', methods=['GET'])
    def chat_users_search():
        """Rechercher des utilisateurs pour le chat"""
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        
        from models.user import User
        
        user = User.query.get(session['user_id'])
        query = request.args.get('q', '').strip()
        
        # Chercher dans la même entreprise, exclure l'utilisateur actuel
        users_query = User.query.filter(
            User.company_id == user.company_id,
            User.id != user.id,
            User.is_active == True
        )
        
        if query:
            users_query = users_query.filter(
                db.or_(
                    User.username.ilike(f'%{query}%'),
                    User.first_name.ilike(f'%{query}%'),
                    User.last_name.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%')
                )
            )
        
        users = users_query.limit(20).all()
        
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
        
    @app.route('/department/<int:dept_id>')
    def department_page(dept_id):
        """Page d'un département"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        from models.user import User
        from models.company import Department
        
        user = User.query.get(session['user_id'])
        department = Department.query.get_or_404(dept_id)
        
        return render_template('department.html', department=department, user=user)
    
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
    
    @app.context_processor
    def inject_unread_messages():
        if 'user_id' in session:
            from models.chat import ChatMessage, ChatConversation
            user_id = session['user_id']
            
            # Compter messages non lus dans conversations 1-to-1
            conversations = ChatConversation.query.filter(
                db.or_(
                    ChatConversation.user1_id == user_id,
                    ChatConversation.user2_id == user_id
                )
            ).all()
            
            conv_ids = [c.id for c in conversations]
            
            unread_count = ChatMessage.query.filter(
                ChatMessage.conversation_id.in_(conv_ids),
                ChatMessage.sender_id != user_id,
                ChatMessage.is_read == False
            ).count()
            
            return dict(unread_messages_count=unread_count)
        return dict(unread_messages_count=0)
    
    
    # Context processor pour les templates
    @app.context_processor
    def inject_user():
        """Injecter l'utilisateur dans tous les templates"""
        if 'user_id' in session:
            from models.user import User
            user = User.query.get(session['user_id'])
            return dict(current_user=user)
        return dict(current_user=None)
    
    @app.context_processor
    def inject_pending_requests():
        if 'user_id' in session:
            from models.employee_request import EmployeeRequest
            count = EmployeeRequest.query.filter_by(status='pending').count()
            return dict(pending_requests_count=count)
        return dict(pending_requests_count=0)
    
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
    
    # Retourner app ET socketio
    return app, socketio


# Point d'entrée pour le serveur de développement
if __name__ == '__main__':
    app, socketio = create_app('development')
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)