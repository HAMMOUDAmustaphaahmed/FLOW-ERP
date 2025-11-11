from flask import Blueprint, request, jsonify, session, render_template
from models.user import User, db
from models.company import Company, Department, DepartmentField, DepartmentItem
from utils.security import SecurityValidator, require_login, require_admin, AuditLogger
from datetime import datetime

try:
    from models.department_table import DepartmentTable, TableRow
except ImportError:
    DepartmentTable = None
    TableRow = None
    print("Warning: DepartmentTable models not found")

company_bp = Blueprint('company', __name__, url_prefix='/company')


@company_bp.route('/create', methods=['POST'])
@require_admin
def create_company():
    """Créer une nouvelle entreprise (Admin uniquement)"""
    data = request.get_json()
    
    # Validation des données
    name = SecurityValidator.sanitize_input(data.get('name', ''))
    if not name:
        return jsonify({'error': 'Le nom de l\'entreprise est requis'}), 400
    
    # Vérifier l'unicité
    if Company.query.filter_by(name=name).first():
        return jsonify({'error': 'Une entreprise avec ce nom existe déjà'}), 400
    
    tax_id = SecurityValidator.sanitize_input(data.get('tax_id', ''))
    if tax_id and Company.query.filter_by(tax_id=tax_id).first():
        return jsonify({'error': 'Ce matricule fiscale est déjà utilisé'}), 400
    
    try:
        company = Company(
            name=name,
            legal_name=SecurityValidator.sanitize_input(data.get('legal_name', name)),
            tax_id=tax_id,
            registration_number=SecurityValidator.sanitize_input(data.get('registration_number', '')),
            address=SecurityValidator.sanitize_input(data.get('address', '')),
            city=SecurityValidator.sanitize_input(data.get('city', '')),
            state=SecurityValidator.sanitize_input(data.get('state', '')),
            postal_code=SecurityValidator.sanitize_input(data.get('postal_code', '')),
            country=SecurityValidator.sanitize_input(data.get('country', 'Tunisie')),
            phone=SecurityValidator.sanitize_input(data.get('phone', '')),
            email=SecurityValidator.sanitize_input(data.get('email', '')),
            website=SecurityValidator.sanitize_input(data.get('website', '')),
            industry=SecurityValidator.sanitize_input(data.get('industry', '')),
            currency=data.get('currency', 'TND'),
            timezone=data.get('timezone', 'Africa/Tunis'),
            language=data.get('language', 'fr'),
            created_by_id=session['user_id']
        )
        
        # Date de fondation
        if data.get('founded_date'):
            try:
                company.founded_date = datetime.fromisoformat(data['founded_date']).date()
            except:
                pass
        
        db.session.add(company)
        db.session.commit()
        
        # Associer l'admin à l'entreprise
        user = User.query.get(session['user_id'])
        user.company_id = company.id
        db.session.commit()
        
        # Mettre à jour la session
        session['company_id'] = company.id
        
        # Logger dans la blockchain
        AuditLogger.log_action(
            session['user_id'], 
            'company_created', 
            'company', 
            company.id,
            {'name': name, 'tax_id': tax_id}
        )
        
        return jsonify({
            'success': True,
            'message': 'Entreprise créée avec succès',
            'company': company.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500


@company_bp.route('/get/<int:company_id>', methods=['GET'])
@require_login
def get_company(company_id):
    """Récupérer les informations d'une entreprise"""
    company = Company.query.get_or_404(company_id)
    
    # Vérifier les permissions
    user = User.query.get(session['user_id'])
    if not user.is_admin and user.company_id != company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    return jsonify({
        'success': True,
        'company': company.to_dict()
    }), 200


@company_bp.route('/update/<int:company_id>', methods=['PUT'])
@require_admin
def update_company(company_id):
    """Mettre à jour une entreprise"""
    company = Company.query.get_or_404(company_id)
    data = request.get_json()
    
    try:
        # Mise à jour des champs
        if 'name' in data:
            company.name = SecurityValidator.sanitize_input(data['name'])
        if 'legal_name' in data:
            company.legal_name = SecurityValidator.sanitize_input(data['legal_name'])
        if 'address' in data:
            company.address = SecurityValidator.sanitize_input(data['address'])
        if 'city' in data:
            company.city = SecurityValidator.sanitize_input(data['city'])
        if 'state' in data:
            company.state = SecurityValidator.sanitize_input(data['state'])
        if 'postal_code' in data:
            company.postal_code = SecurityValidator.sanitize_input(data['postal_code'])
        if 'country' in data:
            company.country = SecurityValidator.sanitize_input(data['country'])
        if 'phone' in data:
            company.phone = SecurityValidator.sanitize_input(data['phone'])
        if 'email' in data:
            email = SecurityValidator.sanitize_input(data['email'])
            valid, error = SecurityValidator.validate_email(email)
            if valid:
                company.email = email
        if 'website' in data:
            company.website = SecurityValidator.sanitize_input(data['website'])
        if 'industry' in data:
            company.industry = SecurityValidator.sanitize_input(data['industry'])
        if 'employee_count' in data:
            company.employee_count = int(data['employee_count'])
        
        company.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Logger
        AuditLogger.log_action(
            session['user_id'],
            'company_updated',
            'company',
            company_id,
            data
        )
        
        return jsonify({
            'success': True,
            'message': 'Entreprise mise à jour',
            'company': company.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la mise à jour: {str(e)}'}), 500


@company_bp.route('/list', methods=['GET'])
@require_admin
def list_companies():
    """Lister toutes les entreprises (Admin uniquement)"""
    companies = Company.query.all()
    return jsonify({
        'success': True,
        'companies': [company.to_dict() for company in companies]
    }), 200


@company_bp.route('/delete/<int:company_id>', methods=['DELETE'])
@require_admin
def delete_company(company_id):
    """Supprimer une entreprise"""
    company = Company.query.get_or_404(company_id)
    
    try:
        # Logger avant suppression
        AuditLogger.log_action(
            session['user_id'],
            'company_deleted',
            'company',
            company_id,
            {'name': company.name}
        )
        
        db.session.delete(company)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Entreprise supprimée'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500


# Routes pour les templates
@company_bp.route('/setup-page', methods=['GET'])
@require_admin
def company_setup_page():
    """Page de configuration de l'entreprise"""
    return render_template('company_setup.html')


@company_bp.route('/stats/<int:company_id>', methods=['GET'])
@require_login
def company_stats(company_id):
    """Obtenir les statistiques d'une entreprise"""
    user = User.query.get(session['user_id'])
    
    # Vérifier les permissions
    if not user.is_admin and user.company_id != company_id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    company = Company.query.get_or_404(company_id)
    
    try:
        # Compter les départements actifs (non supprimés)
        departments = Department.query.filter_by(
            company_id=company_id,
            deleted_at=None
        ).all()
        departments_count = len(departments)
        
        # Compter les utilisateurs actifs
        users_count = User.query.filter_by(
            company_id=company_id,
            is_active=True
        ).count()
        
        # Compter les tables personnalisées (si le module existe)
        tables_count = 0
        total_entries = 0
        
        if DepartmentTable is not None and TableRow is not None:
            tables_count = db.session.query(DepartmentTable).join(
                Department
            ).filter(
                Department.company_id == company_id,
                Department.deleted_at == None
            ).count()
            
            # Compter les entrées totales dans toutes les tables
            total_entries = db.session.query(TableRow).join(
                DepartmentTable
            ).join(
                Department
            ).filter(
                Department.company_id == company_id,
                Department.deleted_at == None
            ).count()
        
        # Statistiques détaillées par département
        dept_stats = []
        for dept in departments:
            # Compter les employés du département
            employees_count = User.query.filter_by(
                department_id=dept.id,
                is_active=True
            ).count()
            
            # Compter les tables du département
            dept_tables_count = 0
            dept_entries = 0
            
            if DepartmentTable is not None and TableRow is not None:
                dept_tables_count = DepartmentTable.query.filter_by(
                    department_id=dept.id
                ).count()
                
                # Compter les entrées du département
                dept_entries = db.session.query(TableRow).join(
                    DepartmentTable
                ).filter(
                    DepartmentTable.department_id == dept.id
                ).count()
            
            dept_stats.append({
                'id': dept.id,
                'name': dept.name,
                'employees_count': employees_count,
                'tables_count': dept_tables_count,
                'entries_count': dept_entries,
                'budget': float(dept.budget) if dept.budget else 0,
                'budget_spent': float(dept.budget_spent) if dept.budget_spent else 0
            })
        
        # Statistiques par période (7 derniers jours)
        from datetime import timedelta
        today = datetime.utcnow()
        week_ago = today - timedelta(days=7)
        
        # Activité des 7 derniers jours
        daily_activity = []
        for i in range(7):
            day = week_ago + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Compter les entrées créées ce jour (si le module existe)
            entries_count = 0
            if DepartmentTable is not None and TableRow is not None:
                entries_count = db.session.query(TableRow).join(
                    DepartmentTable
                ).join(
                    Department
                ).filter(
                    Department.company_id == company_id,
                    TableRow.created_at >= day_start,
                    TableRow.created_at <= day_end
                ).count()
            
            # Utilisateurs actifs (placeholder - nécessite une table de logs)
            active_users = users_count // 7 if users_count > 0 else 0
            
            daily_activity.append({
                'date': day.strftime('%Y-%m-%d'),
                'day_name': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][day.weekday()],
                'entries': entries_count,
                'active_users': active_users
            })
        
        # Statistiques par rôle
        role_stats = {}
        for role in ['admin', 'department_manager', 'employee', 'technician']:
            count = User.query.filter_by(
                company_id=company_id,
                role=role,
                is_active=True
            ).count()
            role_stats[role] = count
        
        stats = {
            'departments_count': departments_count,
            'users_count': users_count,
            'tables_count': tables_count,
            'total_entries': total_entries,
            'departments': dept_stats,
            'daily_activity': daily_activity,
            'role_distribution': role_stats,
            'company': {
                'name': company.name,
                'created_at': company.created_at.isoformat() if company.created_at else None
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la récupération des statistiques: {str(e)}'
        }), 500