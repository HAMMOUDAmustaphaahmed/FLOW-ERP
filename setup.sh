# FlowERP - Enterprise Resource Planning with Blockchain

A modern, secure ERP system built with Flask and blockchain technology for complete traceability.

## 🚀 Features

- **Blockchain Integration**: Full transaction traceability with Proof of Work
- **Advanced Security**: SQL injection protection, XSS prevention, rate limiting, account locking
- **Dynamic Departments**: Customizable fields and flexible structure
- **User Management**: Role-based access control (Admin, Manager, User)
- **Company Management**: Multi-company support with complete information
- **Dashboard**: Real-time statistics and charts
- **Audit Trail**: Complete action logging in blockchain

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser

## 🛠️ Installation

### 1. Clone or create project structure

```bash
FlowERP/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── utils/
│   └── requirements.txt
├── frontend/
│   ├── static/
│   └── templates/
└── database/
    └── init_db.py
```

### 2. Install dependencies

```bash
cd FlowERP/backend
pip install -r requirements.txt
```

### 3. Initialize the database

#### Option A: With sample data (recommended for testing)
```bash
cd ../database
python init_db.py
# Answer 'yes' to both prompts
```

This will create:
- Admin user: username=`admin`, password=`Admin@123`
- Sample company: TechCorp Tunisia
- 4 departments (HR, IT, Finance, Marketing)
- 3 sample users: password=`User@123`

#### Option B: Empty database
```bash
cd ../database
python init_db.py
# Answer 'yes' to first prompt, 'no' to second
```

### 4. Run the application

```bash
cd ../backend
python app.py
```

The application will be available at: http://localhost:5000

## 🎯 First Time Setup

If you initialized an empty database:

1. Navigate to http://localhost:5000
2. Create the first admin account
3. Set up your company information
4. Start creating departments and users

## 📱 Usage

### Admin Features
- Create and manage companies
- Create departments with custom fields
- Manage users and permissions
- View blockchain statistics
- Access all audit logs

### Manager Features
- Manage their department
- Add items to department
- View department statistics
- Manage team members

### User Features
- View assigned department
- Add items (if permitted)
- View personal statistics

## 🔒 Security Features

### Password Requirements
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- Cannot contain username
- Cannot be common password

### Account Protection
- Rate limiting: 5 login attempts per 15 minutes
- Account lockout: 30 minutes after 5 failed attempts
- Session management with automatic expiration
- CSRF protection on all forms
- XSS protection with input sanitization
- SQL injection prevention

### Audit Trail
All actions are logged in the blockchain:
- User login/logout
- Company creation/modification
- Department creation/modification
- Item additions/changes
- Password changes

## 🔗 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/signup-admin` - First admin signup
- `GET /auth/check-session` - Verify session

### Company
- `POST /company/create` - Create company
- `GET /company/get/<id>` - Get company details
- `PUT /company/update/<id>` - Update company
- `GET /company/stats/<id>` - Company statistics

### Departments
- `POST /department/create` - Create department
- `GET /department/list` - List departments
- `GET /department/get/<id>` - Get department
- `PUT /department/update/<id>` - Update department
- `POST /department/<id>/items/add` - Add item

### Dashboard
- `GET /api/dashboard/stats` - Main statistics
- `GET /api/dashboard/departments/summary` - Departments summary
- `GET /api/dashboard/budget/analysis` - Budget analysis
- `GET /api/dashboard/employees/distribution` - Employee distribution

### Blockchain
- `GET /api/blockchain/stats` - Blockchain statistics
- `GET /api/blockchain/chain` - Get full chain
- `POST /api/blockchain/mine` - Mine pending transactions
- `GET /api/blockchain/validate` - Validate chain integrity
- `GET /api/blockchain/history/<type>/<id>` - Entity history

### Blockchain Sync (Multi-node)
- `POST /api/blockchain/nodes/register` - Register node
- `GET /api/blockchain/nodes/list` - List nodes
- `POST /api/blockchain/sync` - Manual sync
- `GET /api/blockchain/network/status` - Network status

## 🏗️ Project Structure

```
FlowERP/
├── backend/
│   ├── app.py                 # Application factory
│   ├── config.py              # Configuration settings
│   ├── requirements.txt       # Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── blockchain.py      # Blockchain implementation
│   │   ├── user.py            # User models
│   │   └── company.py         # Company & Department models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication routes
│   │   ├── company.py         # Company routes
│   │   ├── department.py      # Department routes
│   │   └── dashboard.py       # Dashboard API routes
│   └── utils/
│       ├── __init__.py
│       ├── security.py        # Security validators
│       └── blockchain_sync.py # Blockchain synchronization
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css      # Global styles
│   │   └── js/
│   │       ├── main.js        # Main JavaScript
│   │       └── chart.js       # Chart utilities
│   └── templates/
│       ├── base.html          # Base template
│       ├── login.html         # Login page
│       ├── signup_admin.html  # Admin signup
│       ├── dashboard.html     # Dashboard
│       ├── company_setup.html # Company setup
│       └── department.html    # Department management
└── database/
    └── init_db.py             # Database initialization script
```

## 🧪 Testing

To test the application with sample data:

1. Initialize database with sample data (see step 3)
2. Login as admin (admin / Admin@123)
3. Explore departments and statistics
4. Test blockchain features:
   - Add new items to departments
   - View blockchain at http://localhost:5000/api/blockchain/chain
   - Validate chain at http://localhost:5000/api/blockchain/validate

## 🔧 Configuration

Edit `backend/config.py` to customize:

- Database URL (SQLite by default, PostgreSQL for production)
- Session timeout (24 hours by default)
- Blockchain difficulty (4 by default)
- Password requirements
- Rate limiting settings

## 🚢 Production Deployment

For production deployment:

1. Change `config_name` to `'production'` in `app.py`
2. Set environment variables:
   ```bash
   export SECRET_KEY='your-secret-key-here'
   export DATABASE_URL='postgresql://user:pass@localhost/dbname'
   ```
3. Use a production WSGI server:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
   ```
4. Enable HTTPS and set secure cookies
5. Use Redis for session storage (recommended)

## 📊 Database Schema

- **users**: User accounts and authentication
- **companies**: Company information
- **departments**: Department structure
- **department_fields**: Custom fields for departments
- **department_items**: Items within departments
- **login_attempts**: Login audit trail
- **sessions**: Active user sessions

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guide
- All security features remain intact
- New features include proper validation
- Blockchain integrity is maintained

## 📝 License

This project is proprietary software for FlowERP.

## 🆘 Support

For issues or questions:
1. Check the console for error messages
2. Verify database initialization completed successfully
3. Ensure all dependencies are installed
4. Check that port 5000 is available

## 🎓 Credits

Built with:
- Flask (Python web framework)
- SQLAlchemy (ORM)
- Chart.js (Charts and graphs)
- Blockchain technology (Custom implementation)
- Modern CSS and JavaScript

---

**Version**: 1.0.0  
**Last Updated**: November 2025