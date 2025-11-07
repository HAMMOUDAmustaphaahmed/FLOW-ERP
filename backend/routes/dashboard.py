from flask import Blueprint, jsonify, session, request
from models.user import User, db
from models.company import Company, Department, DepartmentItem
from utils.security import require_login
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
@require_login
def get_dashboard_stats():
    """Récupère les statistiques principales pour le dashboard"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    company = Company.query.get(user.company_id)
    
    # Statistiques de base
    total_departments = Department.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).count()
    
    total_employees = User.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).count()
    
    total_items = db.session.query(func.count(DepartmentItem.id)).join(
        Department
    ).filter(
        Department.company_id == user.company_id
    ).scalar()
    
    # Budget total et dépensé
    budget_data = db.session.query(
        func.sum(Department.budget),
        func.sum(Department.budget_spent)
    ).filter(
        Department.company_id == user.company_id,
        Department.is_active == True
    ).first()
    
    total_budget = float(budget_data[0]) if budget_data[0] else 0
    total_spent = float(budget_data[1]) if budget_data[1] else 0
    
    # Activité récente (7 derniers jours)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = DepartmentItem.query.join(
        Department
    ).filter(
        Department.company_id == user.company_id,
        DepartmentItem.created_at >= seven_days_ago
    ).count()
    
    return jsonify({
        'success': True,
        'stats': {
            'company_name': company.name,
            'total_departments': total_departments,
            'total_employees': total_employees,
            'total_items': total_items,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'budget_remaining': total_budget - total_spent,
            'budget_percentage': (total_spent / total_budget * 100) if total_budget > 0 else 0,
            'recent_activity': recent_activity
        }
    }), 200


@dashboard_bp.route('/departments/summary', methods=['GET'])
@require_login
def get_departments_summary():
    """Résumé des départements pour le dashboard"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    departments = Department.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).all()
    
    summary = []
    for dept in departments:
        summary.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'employees_count': len(dept.employees),
            'items_count': dept.items.count(),
            'budget': float(dept.budget) if dept.budget else 0,
            'budget_spent': float(dept.budget_spent) if dept.budget_spent else 0,
            'budget_remaining': float(dept.budget - dept.budget_spent) if dept.budget else 0,
            'manager': {
                'id': dept.manager.id,
                'name': f"{dept.manager.first_name} {dept.manager.last_name}".strip() or dept.manager.username
            } if dept.manager else None
        })
    
    return jsonify({
        'success': True,
        'departments': summary
    }), 200


@dashboard_bp.route('/recent-activity', methods=['GET'])
@require_login
def get_recent_activity():
    """Activité récente de l'entreprise"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    limit = request.args.get('limit', 10, type=int)
    
    # Items récemment créés
    recent_items = DepartmentItem.query.join(
        Department
    ).filter(
        Department.company_id == user.company_id
    ).order_by(
        DepartmentItem.created_at.desc()
    ).limit(limit).all()
    
    activity = []
    for item in recent_items:
        activity.append({
            'id': item.id,
            'type': 'item_created',
            'title': item.title,
            'department': item.department.name,
            'item_type': item.item_type,
            'created_at': item.created_at.isoformat(),
            'created_by': {
                'id': item.created_by.id,
                'username': item.created_by.username
            } if item.created_by else None
        })
    
    return jsonify({
        'success': True,
        'activity': activity
    }), 200


@dashboard_bp.route('/budget/analysis', methods=['GET'])
@require_login
def get_budget_analysis():
    """Analyse budgétaire par département"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    departments = Department.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).filter(
        Department.budget.isnot(None)
    ).all()
    
    budget_analysis = []
    for dept in departments:
        budget = float(dept.budget) if dept.budget else 0
        spent = float(dept.budget_spent) if dept.budget_spent else 0
        remaining = budget - spent
        percentage = (spent / budget * 100) if budget > 0 else 0
        
        status = 'healthy'
        if percentage >= 90:
            status = 'critical'
        elif percentage >= 75:
            status = 'warning'
        
        budget_analysis.append({
            'department_id': dept.id,
            'department_name': dept.name,
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'percentage': round(percentage, 2),
            'status': status
        })
    
    # Trier par pourcentage décroissant
    budget_analysis.sort(key=lambda x: x['percentage'], reverse=True)
    
    return jsonify({
        'success': True,
        'analysis': budget_analysis
    }), 200


@dashboard_bp.route('/employees/distribution', methods=['GET'])
@require_login
def get_employee_distribution():
    """Distribution des employés par département"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    # Compter les employés par département
    distribution = db.session.query(
        Department.id,
        Department.name,
        func.count(User.id).label('employee_count')
    ).outerjoin(
        User, Department.id == User.department_id
    ).filter(
        Department.company_id == user.company_id,
        Department.is_active == True
    ).group_by(
        Department.id,
        Department.name
    ).all()
    
    result = []
    total_employees = 0
    
    for dept_id, dept_name, count in distribution:
        result.append({
            'department_id': dept_id,
            'department_name': dept_name,
            'employee_count': count
        })
        total_employees += count
    
    # Ajouter les employés sans département
    no_dept_count = User.query.filter_by(
        company_id=user.company_id,
        department_id=None,
        is_active=True
    ).count()
    
    if no_dept_count > 0:
        result.append({
            'department_id': None,
            'department_name': 'Sans département',
            'employee_count': no_dept_count
        })
        total_employees += no_dept_count
    
    return jsonify({
        'success': True,
        'distribution': result,
        'total_employees': total_employees
    }), 200


@dashboard_bp.route('/items/by-type', methods=['GET'])
@require_login
def get_items_by_type():
    """Statistiques des items par type"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    # Compter les items par type
    items_by_type = db.session.query(
        DepartmentItem.item_type,
        func.count(DepartmentItem.id).label('count')
    ).join(
        Department
    ).filter(
        Department.company_id == user.company_id
    ).group_by(
        DepartmentItem.item_type
    ).all()
    
    result = []
    for item_type, count in items_by_type:
        result.append({
            'type': item_type,
            'count': count
        })
    
    return jsonify({
        'success': True,
        'items_by_type': result
    }), 200


@dashboard_bp.route('/performance/metrics', methods=['GET'])
@require_login
def get_performance_metrics():
    """Métriques de performance"""
    user = User.query.get(session['user_id'])
    
    if not user.company_id:
        return jsonify({'error': 'Aucune entreprise associée'}), 400
    
    # Calculer diverses métriques
    company = Company.query.get(user.company_id)
    
    # Nombre de jours depuis la création
    days_active = (datetime.utcnow() - company.created_at).days
    
    # Moyenne d'items par département
    total_depts = Department.query.filter_by(
        company_id=user.company_id,
        is_active=True
    ).count()
    
    total_items = db.session.query(func.count(DepartmentItem.id)).join(
        Department
    ).filter(
        Department.company_id == user.company_id
    ).scalar()
    
    avg_items_per_dept = (total_items / total_depts) if total_depts > 0 else 0
    
    # Taux d'utilisation du budget
    budget_data = db.session.query(
        func.sum(Department.budget),
        func.sum(Department.budget_spent)
    ).filter(
        Department.company_id == user.company_id,
        Department.is_active == True
    ).first()
    
    total_budget = float(budget_data[0]) if budget_data[0] else 0
    total_spent = float(budget_data[1]) if budget_data[1] else 0
    budget_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    return jsonify({
        'success': True,
        'metrics': {
            'days_active': days_active,
            'avg_items_per_department': round(avg_items_per_dept, 2),
            'budget_utilization_rate': round(budget_utilization, 2),
            'total_departments': total_depts,
            'total_items': total_items
        }
    }), 200