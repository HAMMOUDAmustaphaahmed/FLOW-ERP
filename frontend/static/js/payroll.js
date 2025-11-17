// static/js/payroll.js
// Gestion de la paie - FlowERP

let currentPayslipId = null;
let salaryVisibility = {}; // Pour gérer la visibilité des salaires
let searchTimeout;

// Filtres actuels
let currentFilters = {
    month: new Date().getMonth() + 1,  // Mois actuel par défaut
    year: new Date().getFullYear(),
    status: '',
    search: ''
};

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    loadEmployees();
    loadLeaveRequests();
    loadAdvances();
    loadPayslips();
    initializeYearSelects();
    loadDepartments();
    setupSearchListeners();
    initializeDateFilters();
});

function highlightSearch(text, searchTerm) {
    if (!searchTerm || !text) return text;
    
    const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
    return text.replace(regex, '<mark style="background: #fef08a; padding: 0 2px; border-radius: 2px;">$1</mark>');
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function setupSearchListeners() {
    // Recherche congés
    const leaveSearchInput = document.getElementById('leaveSearchInput');
    if (leaveSearchInput) {
        leaveSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentFilters.search = this.value;
                loadLeaveRequests();
            }, 300); // Debounce de 300ms
        });
    }
    
    // Recherche avances
    const advanceSearchInput = document.getElementById('advanceSearchInput');
    if (advanceSearchInput) {
        advanceSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentFilters.search = this.value;
                loadAdvances();
            }, 300);
        });
    }
    
    // Recherche fiches de paie
    const payslipSearchInput = document.getElementById('payslipSearchInput');
    if (payslipSearchInput) {
        payslipSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentFilters.search = this.value;
                loadPayslips();
            }, 300);
        });
    }
}

function initializeDateFilters() {
    const now = new Date();
    const currentMonth = now.getMonth() + 1;
    const currentYear = now.getFullYear();
    
    // Set leave filters
    const leaveMonth = document.getElementById('leaveMonthFilter');
    const leaveYear = document.getElementById('leaveYearFilter');
    if (leaveMonth) leaveMonth.value = currentMonth;
    if (leaveYear) {
        // Populate year options
        for (let year = currentYear - 2; year <= currentYear + 1; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === currentYear) option.selected = true;
            leaveYear.appendChild(option);
        }
    }
    
    // Set advance filters
    const advanceMonth = document.getElementById('advanceMonthFilter');
    const advanceYear = document.getElementById('advanceYearFilter');
    if (advanceMonth) advanceMonth.value = currentMonth;
    if (advanceYear) {
        // Populate year options
        for (let year = currentYear - 2; year <= currentYear + 1; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === currentYear) option.selected = true;
            advanceYear.appendChild(option);
        }
    }}

// ==================== ONGLETS ====================



function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`button[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Réinitialiser les filtres et charger les données
    currentFilters.search = '';
    
    if (tabName === 'employees') {
        loadEmployees();
    } else if (tabName === 'salaries') {
        loadEmployeeSalaries();
    } else if (tabName === 'leaves') {
        loadLeaveRequests();
    } else if (tabName === 'advances') {
        loadAdvances();
    } else if (tabName === 'payslips') {
        loadPayslips();
    }
}

// ==================== EMPLOYÉS ====================

async function loadEmployees() {
    try {
        const response = await fetch('/users/list');
        const data = await response.json();
        
        if (data.success) {
            displayEmployees(data.users);
        }
    } catch (error) {
        console.error('Erreur chargement employés:', error);
        showNotification('Erreur lors du chargement des employés', 'error');
    }
}

function displayEmployees(users) {
    const tbody = document.getElementById('employeesBody');
    
    if (!tbody) return;
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">Aucun employé trouvé</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.first_name || '-'}</td>
            <td>${user.last_name || '-'}</td>
            <td>${user.phone || '-'}</td>
            <td>${user.email}</td>
            <td>${new Date(user.created_at).toLocaleDateString('fr-FR')}</td>
            <td>${user.department_name || 'Sans département'}</td>
        </tr>
    `).join('');
}

// ==================== CONFIGURATION ====================

async function loadConfig() {
    try {
        const response = await fetch('/payroll/config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            document.getElementById('workingDaysPerWeek').value = config.working_days_per_week;
            document.getElementById('workingHoursPerDay').value = config.working_hours_per_day;
            document.getElementById('workingDaysPerMonth').value = config.working_days_per_month;
            document.getElementById('cnssRate').value = config.cnss_rate;
            document.getElementById('cnssEmployerRate').value = config.cnss_employer_rate;
            document.getElementById('irppRate').value = config.irpp_rate;
            document.getElementById('annualLeaveDays').value = config.annual_leave_days;
            document.getElementById('sickLeaveDays').value = config.sick_leave_days;
            document.getElementById('absencePenaltyRate').value = config.absence_penalty_rate;
            document.getElementById('latePenaltyRate').value = config.late_penalty_rate || 50;
        }
    } catch (error) {
        console.error('Erreur chargement config:', error);
        showNotification('Erreur lors du chargement de la configuration', 'error');
    }
}

async function saveConfig() {
    const configData = {
        working_days_per_week: parseInt(document.getElementById('workingDaysPerWeek').value),
        working_hours_per_day: parseFloat(document.getElementById('workingHoursPerDay').value),
        working_days_per_month: parseInt(document.getElementById('workingDaysPerMonth').value),
        cnss_rate: parseFloat(document.getElementById('cnssRate').value),
        cnss_employer_rate: parseFloat(document.getElementById('cnssEmployerRate').value),
        irpp_rate: parseFloat(document.getElementById('irppRate').value),
        annual_leave_days: parseInt(document.getElementById('annualLeaveDays').value),
        sick_leave_days: parseInt(document.getElementById('sickLeaveDays').value),
        absence_penalty_rate: parseFloat(document.getElementById('absencePenaltyRate').value),
        late_penalty_rate: parseFloat(document.getElementById('latePenaltyRate').value)
    };
    
    try {
        const response = await fetch('/payroll/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Configuration enregistrée avec succès', 'success');
        } else {
            showNotification(data.error || 'Erreur lors de l\'enregistrement', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion au serveur', 'error');
        console.error('Erreur:', error);
    }
}

// ==================== SALAIRES ====================

async function loadEmployeeSalaries() {
    try {
        console.log('🔄 Chargement des salaires...');
        const response = await fetch('/users/list');
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ ${data.users.length} employés chargés`);
            displayEmployeeSalaries(data.users);
        }
    } catch (error) {
        console.error('❌ Erreur chargement salaires:', error);
        showNotification('Erreur lors du chargement des salaires', 'error');
    }
}

async function displayEmployeeSalaries(users) {
    const container = document.getElementById('employeeSalaryList');
    
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 2rem;">Aucun employé trouvé</p>';
        return;
    }
    
    // Charger les salaires de chaque employé
    const salariesPromises = users.map(user => 
        fetch(`/payroll/salary/${user.id}`)
            .then(res => res.json())
            .then(data => ({ user, salary: data.success ? data.salary : null }))
            .catch(() => ({ user, salary: null }))
    );
    
    const employeesWithSalaries = await Promise.all(salariesPromises);
    
    container.innerHTML = employeesWithSalaries.map(({ user, salary }) => {
        const initials = (user.first_name?.[0] || '') + (user.last_name?.[0] || user.username[0]);
        const baseSalary = salary ? salary.base_salary : 0;
        const grossSalary = salary ? salary.gross_salary : 0;
        const allowancesTotal = salary ? salary.allowances.total : 0;
        
        // IMPORTANT: Initialiser TOUS les salaires à FALSE (masqués) par défaut
        if (!(user.id in salaryVisibility)) {
            salaryVisibility[user.id] = false;
        }
        
        const isVisible = salaryVisibility[user.id];
        
        return `
            <div class="employee-card" data-user-id="${user.id}">
                <div class="employee-header">
                    <div class="employee-info">
                        <div class="employee-avatar">${initials.toUpperCase()}</div>
                        <div>
                            <h4>${user.full_name}</h4>
                            <p class="text-secondary">${user.role_display} - ${user.department_name || 'Sans département'}</p>
                        </div>
                    </div>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-secondary" onclick="toggleSalaryVisibility(${user.id})" title="${isVisible ? 'Masquer' : 'Afficher'}" data-user-id="${user.id}">
                            <i class="fas fa-eye${isVisible ? '-slash' : ''}"></i>
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="editSalary(${user.id})">
                            <i class="fas fa-edit"></i> Modifier
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="openGeneratePayslipModalFor(${user.id})">
                            <i class="fas fa-file-invoice"></i> Fiche
                        </button>
                    </div>
                </div>
                <div class="salary-details salary-blur" id="salary-${user.id}">
                    <div class="salary-item">
                        <label>Salaire de Base</label>
                        <div class="value">${baseSalary.toFixed(3)} TND</div>
                    </div>
                    <div class="salary-item">
                        <label>Primes</label>
                        <div class="value">${allowancesTotal.toFixed(3)} TND</div>
                    </div>
                    <div class="salary-item">
                        <label>Salaire Brut</label>
                        <div class="value">${grossSalary.toFixed(3)} TND</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    console.log('🔒 Tous les salaires affichés avec blur par défaut');
    console.log('État de visibilité:', salaryVisibility);
}

function toggleSalaryVisibility(userId) {
    // Toggle l'état de visibilité
    salaryVisibility[userId] = !salaryVisibility[userId];
    
    console.log(`Toggle salary for user ${userId}: ${salaryVisibility[userId]}`);
    
    // Mettre à jour l'élément - Sélecteur CORRIGÉ
    const salaryElement = document.getElementById(`salary-${userId}`);
    // Trouver le bouton dans la card parent
    const employeeCard = document.querySelector(`[data-user-id="${userId}"]`);
    const button = employeeCard ? employeeCard.querySelector('button[onclick*="toggleSalaryVisibility"]') : null;
    
    if (!salaryElement) {
        console.error(`Salary element not found for user ${userId}`);
        return;
    }
    
    if (salaryVisibility[userId]) {
        // Afficher : retirer le blur
        salaryElement.classList.remove('salary-blur');
        if (button) {
            const icon = button.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-eye-slash';
            }
            button.title = 'Masquer';
        }
        console.log(`✅ Salaire affiché pour user ${userId}`);
    } else {
        // Masquer : ajouter le blur
        salaryElement.classList.add('salary-blur');
        if (button) {
            const icon = button.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-eye';
            }
            button.title = 'Afficher';
        }
        console.log(`🔒 Salaire masqué pour user ${userId}`);
    }
}

function toggleAllSalaries() {
    // Vérifier si au moins un salaire est visible
    const hasVisibleSalary = Object.values(salaryVisibility).some(v => v === true);
    
    // Si au moins un est visible, on masque tout. Sinon, on affiche tout
    const newState = !hasVisibleSalary;
    
    // Appliquer à tous les salaires
    Object.keys(salaryVisibility).forEach(userId => {
        salaryVisibility[userId] = newState;
        
        const salaryElement = document.getElementById(`salary-${userId}`);
        const buttonIcon = document.querySelector(`[data-user-id="${userId}"] button[onclick*="toggleSalaryVisibility"] i`);
        
        if (salaryElement && buttonIcon) {
            if (newState) {
                salaryElement.classList.remove('salary-blur');
                buttonIcon.className = 'fas fa-eye-slash';
            } else {
                salaryElement.classList.add('salary-blur');
                buttonIcon.className = 'fas fa-eye';
            }
        }
    });
    
    // Mettre à jour le texte du bouton
    const toggleButton = document.querySelector('button[onclick="toggleAllSalaries()"]');
    if (toggleButton) {
        if (newState) {
            toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i> Masquer tout';
        } else {
            toggleButton.innerHTML = '<i class="fas fa-eye"></i> Afficher tout';
        }
    }
}

async function editSalary(userId) {
    try {
        const response = await fetch(`/payroll/salary/${userId}`);
        const data = await response.json();
        
        document.getElementById('salaryUserId').value = userId;
        
        if (data.success) {
            const salary = data.salary;
            document.getElementById('baseSalary').value = salary.base_salary;
            document.getElementById('transportAllowance').value = salary.allowances.transport;
            document.getElementById('foodAllowance').value = salary.allowances.food;
            document.getElementById('housingAllowance').value = salary.allowances.housing;
            document.getElementById('responsibilityBonus').value = salary.allowances.responsibility;
        } else {
            // Nouveau salaire
            document.getElementById('baseSalary').value = 0;
            document.getElementById('transportAllowance').value = 0;
            document.getElementById('foodAllowance').value = 0;
            document.getElementById('housingAllowance').value = 0;
            document.getElementById('responsibilityBonus').value = 0;
        }
        
        openModal('salaryModal');
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur lors du chargement du salaire', 'error');
    }
}

async function saveSalary() {
    const userId = document.getElementById('salaryUserId').value;
    
    const salaryData = {
        base_salary: parseFloat(document.getElementById('baseSalary').value),
        transport_allowance: parseFloat(document.getElementById('transportAllowance').value),
        food_allowance: parseFloat(document.getElementById('foodAllowance').value),
        housing_allowance: parseFloat(document.getElementById('housingAllowance').value),
        responsibility_bonus: parseFloat(document.getElementById('responsibilityBonus').value)
    };
    
    try {
        const response = await fetch(`/payroll/salary/${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(salaryData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Salaire mis à jour avec succès', 'success');
            closeSalaryModal();
            loadEmployeeSalaries();
        } else {
            showNotification(data.error || 'Erreur lors de la mise à jour', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
        console.error('Erreur:', error);
    }
}

function closeSalaryModal() {
    closeModal('salaryModal');
}

// ==================== CONGÉS ====================

async function loadLeaveRequests() {
    // Récupérer les filtres
    const status = document.getElementById('leaveStatusFilter')?.value || '';
    const leaveType = document.getElementById('leaveTypeFilter')?.value || '';
    const month = document.getElementById('leaveMonthFilter')?.value || currentFilters.month;
    const year = document.getElementById('leaveYearFilter')?.value || currentFilters.year;
    const search = document.getElementById('leaveSearchInput')?.value || currentFilters.search;
    
    // Construire l'URL avec paramètres
    let url = '/payroll/leave-requests?';
    if (status) url += `status=${status}&`;
    if (leaveType) url += `leave_type=${leaveType}&`;
    if (month) url += `month=${month}&`;
    if (year) url += `year=${year}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayLeaveRequests(data.leave_requests);
        }
    } catch (error) {
        console.error('Erreur chargement congés:', error);
    }
}

function displayLeaveRequests(requests) {
    const tbody = document.getElementById('leaveRequestsBody');
    
    if (!tbody) return;
    
    if (requests.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">
            ${currentFilters.search ? 'Aucun résultat pour cette recherche' : 'Aucune demande de congé'}
        </td></tr>`;
        return;
    }
    
    const typeLabels = {
        'annual': 'Annuel',
        'sick': 'Maladie',
        'unpaid': 'Sans solde',
        'maternity': 'Maternité'
    };
    
    tbody.innerHTML = requests.map(req => {
        // Mettre en surbrillance les termes de recherche
        const userName = highlightSearch(req.user_name, currentFilters.search);
        
        return `
        <tr>
            <td>${userName}</td>
            <td><span class="badge ${req.leave_type}">${typeLabels[req.leave_type]}</span></td>
            <td>${formatDate(req.start_date)} - ${formatDate(req.end_date)}</td>
            <td>${req.days_count} jour(s)</td>
            <td><span class="badge ${req.status}">${req.status === 'pending' ? 'En attente' : req.status === 'approved' ? 'Approuvé' : 'Rejeté'}</span></td>
            <td>${req.deduction_amount > 0 ? req.deduction_amount.toFixed(3) + ' TND' : req.is_paid ? 'Payé' : 'Non payé'}</td>
            <td>
                ${req.status === 'pending' ? `
                    <button class="btn btn-sm btn-primary" onclick="openLeaveReviewModal(${req.id})">
                        <i class="fas fa-eye"></i> Traiter
                    </button>
                ` : `
                    <span class="text-secondary">Traité par ${req.reviewed_by || 'Admin'}</span>
                `}
            </td>
        </tr>
    `;
    }).join('');
}

async function openLeaveReviewModal(requestId) {
    try {
        const response = await fetch('/payroll/leave-requests');
        const data = await response.json();
        
        if (data.success) {
            const request = data.leave_requests.find(r => r.id === requestId);
            
            if (request) {
                document.getElementById('leaveRequestId').value = requestId;
                document.getElementById('leaveRequestDetails').innerHTML = `
                    <div class="salary-details">
                        <div class="salary-item">
                            <label>Employé</label>
                            <div class="value">${request.user_name}</div>
                        </div>
                        <div class="salary-item">
                            <label>Type</label>
                            <div class="value">${request.leave_type}</div>
                        </div>
                        <div class="salary-item">
                            <label>Période</label>
                            <div class="value">${formatDate(request.start_date)} - ${formatDate(request.end_date)}</div>
                        </div>
                        <div class="salary-item">
                            <label>Jours</label>
                            <div class="value">${request.days_count}</div>
                        </div>
                    </div>
                    ${request.reason ? `<p><strong>Raison:</strong> ${request.reason}</p>` : ''}
                `;
                
                openModal('leaveReviewModal');
            }
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function reviewLeaveRequest(status) {
    const requestId = document.getElementById('leaveRequestId').value;
    const comment = document.getElementById('leaveReviewComment').value;
    
    try {
        const response = await fetch(`/payroll/leave-request/${requestId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, review_comment: comment })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`Demande ${status === 'approved' ? 'approuvée' : 'rejetée'}`, 'success');
            closeLeaveReviewModal();
            loadLeaveRequests();
        } else {
            showNotification(data.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
        console.error('Erreur:', error);
    }
}

function closeLeaveReviewModal() {
    closeModal('leaveReviewModal');
}

// ==================== AVANCES ====================

async function loadAdvances() {
    const status = document.getElementById('advanceStatusFilter')?.value || '';
    const month = document.getElementById('advanceMonthFilter')?.value || currentFilters.month;
    const year = document.getElementById('advanceYearFilter')?.value || currentFilters.year;
    const search = document.getElementById('advanceSearchInput')?.value || currentFilters.search;
    
    let url = '/payroll/advances?';
    if (status) url += `status=${status}&`;
    if (month) url += `month=${month}&`;
    if (year) url += `year=${year}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayAdvances(data.advances);
        }
    } catch (error) {
        console.error('Erreur chargement avances:', error);
    }
}

function displayAdvances(advances) {
    const tbody = document.getElementById('advancesBody');
    
    if (!tbody) return;
    
    if (advances.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">
            ${currentFilters.search ? 'Aucun résultat pour cette recherche' : 'Aucune demande d\'avance'}
        </td></tr>`;
        return;
    }
    
    tbody.innerHTML = advances.map(adv => {
        const userName = highlightSearch(adv.user_name, currentFilters.search);
        
        return `
        <tr>
            <td>${userName}</td>
            <td>${adv.amount.toFixed(3)} TND</td>
            <td>${adv.monthly_deduction.toFixed(3)} TND × ${adv.repayment_months} mois</td>
            <td>${adv.remaining_amount.toFixed(3)} TND</td>
            <td><span class="badge ${adv.status}">${adv.status === 'pending' ? 'En attente' : adv.status === 'approved' ? 'Approuvé' : adv.status === 'repaid' ? 'Remboursé' : 'Rejeté'}</span></td>
            <td>${formatDate(adv.request_date)}</td>
            <td>
                ${adv.status === 'pending' ? `
                    <button class="btn btn-sm btn-primary" onclick="openAdvanceReviewModal(${adv.id})">
                        <i class="fas fa-eye"></i> Traiter
                    </button>
                ` : `
                    <span class="text-secondary">Traité</span>
                `}
            </td>
        </tr>
    `;
    }).join('');
}

async function loadPayslips() {
    const month = document.getElementById('payslipMonth')?.value || currentFilters.month;
    const year = document.getElementById('payslipYear')?.value || currentFilters.year;
    const status = document.getElementById('payslipStatusFilter')?.value || '';
    const search = document.getElementById('payslipSearchInput')?.value || currentFilters.search;
    
    let url = '/payroll/payslips?';
    if (month) url += `month=${month}&`;
    if (year) url += `year=${year}&`;
    if (status) url += `status=${status}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayPayslips(data.payslips);
        }
    } catch (error) {
        console.error('Erreur chargement fiches de paie:', error);
    }
}

async function reviewAdvance(status) {
    const advanceId = document.getElementById('advanceId').value;
    const disbursementDate = document.getElementById('disbursementDate').value;
    
    try {
        const response = await fetch(`/payroll/advance/${advanceId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, disbursement_date: disbursementDate })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`Avance ${status === 'approved' ? 'approuvée' : 'rejetée'}`, 'success');
            closeAdvanceReviewModal();
            loadAdvances();
        } else {
            showNotification(data.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
        console.error('Erreur:', error);
    }
}

function closeAdvanceReviewModal() {
    closeModal('advanceReviewModal');
}

// ==================== FICHES DE PAIE ====================

async function loadPayslips() {
    const month = document.getElementById('payslipMonth').value;
    const year = document.getElementById('payslipYear').value;
    const status = document.getElementById('payslipStatusFilter').value;
    
    let url = '/payroll/payslips?';
    if (month) url += `month=${month}&`;
    if (year) url += `year=${year}&`;
    if (status) url += `status=${status}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayPayslips(data.payslips);
        }
    } catch (error) {
        console.error('Erreur chargement fiches de paie:', error);
    }
}

function displayPayslips(payslips) {
    const tbody = document.getElementById('payslipsBody');
    
    if (!tbody) return;
    
    if (payslips.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">
            ${currentFilters.search ? 'Aucun résultat pour cette recherche' : 'Aucune fiche de paie'}
        </td></tr>`;
        return;
    }
    
    tbody.innerHTML = payslips.map(pay => {
        const userName = highlightSearch(pay.user_name, currentFilters.search);
        
        return `
        <tr>
            <td>${userName}</td>
            <td>${pay.period}</td>
            <td>${pay.gross_salary.toFixed(3)} TND</td>
            <td>${pay.deductions.total.toFixed(3)} TND</td>
            <td><strong>${pay.net_salary.toFixed(3)} TND</strong></td>
            <td><span class="badge ${pay.status}">${pay.status === 'draft' ? 'Brouillon' : pay.status === 'validated' ? 'Validé' : 'Payé'}</span></td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-secondary" onclick="viewPayslip(${pay.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${pay.status === 'draft' ? `
                        <button class="btn btn-sm btn-success" onclick="validatePayslip(${pay.id})">
                            <i class="fas fa-check"></i> Valider
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `;
    }).join('');
}

function openGeneratePayslipModalFor(userId) {
    document.getElementById('generateUserId').value = userId;
    
    const now = new Date();
    document.getElementById('generateMonth').value = now.getMonth() + 1;
    document.getElementById('generateYear').value = now.getFullYear();
    
    openModal('generatePayslipModal');
}

async function generatePayslip() {
    const userId = document.getElementById('generateUserId').value;
    const month = parseInt(document.getElementById('generateMonth').value);
    const year = parseInt(document.getElementById('generateYear').value);
    
    try {
        const response = await fetch(`/payroll/generate-payslip/${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ month, year })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Fiche de paie générée avec succès', 'success');
            closeGeneratePayslipModal();
            loadPayslips();
        } else {
            showNotification(data.error || 'Erreur lors de la génération', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
        console.error('Erreur:', error);
    }
}

function closeGeneratePayslipModal() {
    closeModal('generatePayslipModal');
}

async function viewPayslip(payslipId) {
    try {
        const response = await fetch('/payroll/payslips');
        const data = await response.json();
        
        if (data.success) {
            const payslip = data.payslips.find(p => p.id === payslipId);
            
            if (payslip) {
                currentPayslipId = payslipId;
                displayPayslipPreview(payslip);
                openModal('payslipPreviewModal');
            }
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

function displayPayslipPreview(payslip) {
    const monthNames = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
    
    document.getElementById('payslipPreviewContent').innerHTML = `
        <div class="payslip-preview">
            <div class="payslip-header">
                <h2>FICHE DE PAIE</h2>
                <p>${monthNames[payslip.month - 1]} ${payslip.year}</p>
            </div>
            
            <div class="payslip-section">
                <h3>Employé</h3>
                <p><strong>${payslip.user_name}</strong></p>
            </div>
            
            <div class="payslip-section">
                <h3>Rémunération</h3>
                <table class="payslip-table">
                    <tr>
                        <td>Salaire de Base</td>
                        <td>${payslip.base_salary.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Prime Transport</td>
                        <td>${payslip.allowances.transport.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Prime Panier</td>
                        <td>${payslip.allowances.food.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Prime Logement</td>
                        <td>${payslip.allowances.housing.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Prime Responsabilité</td>
                        <td>${payslip.allowances.responsibility.toFixed(3)} TND</td>
                    </tr>
                    <tr class="payslip-total">
                        <td>SALAIRE BRUT</td>
                        <td>${payslip.gross_salary.toFixed(3)} TND</td>
                    </tr>
                </table>
            </div>
            
            <div class="payslip-section">
                <h3>Déductions</h3>
                <table class="payslip-table">
                    <tr>
                        <td>Congés non payés</td>
                        <td>-${payslip.deductions.leave.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Absences</td>
                        <td>-${payslip.deductions.absence.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>Avances</td>
                        <td>-${payslip.deductions.advance.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>CNSS (9.18%)</td>
                        <td>-${payslip.deductions.cnss.toFixed(3)} TND</td>
                    </tr>
                    <tr>
                        <td>IRPP</td>
                        <td>-${payslip.deductions.irpp.toFixed(3)} TND</td>
                    </tr>
                    <tr class="payslip-total">
                        <td>TOTAL DÉDUCTIONS</td>
                        <td>-${payslip.deductions.total.toFixed(3)} TND</td>
                    </tr>
                </table>
            </div>
            
            <div class="payslip-section">
                <table class="payslip-table">
                    <tr class="payslip-total" style="background: #4CAF50; color: white;">
                        <td>SALAIRE NET À PAYER</td>
                        <td>${payslip.net_salary.toFixed(3)} TND</td>
                    </tr>
                </table>
            </div>
            
            <div class="payslip-section">
                <h3>Informations</h3>
                <p>Jours travaillés: ${payslip.days.worked} / ${payslip.days.working}</p>
                <p>Congés: ${payslip.days.leave} jour(s)</p>
                <p>Absences: ${payslip.days.absence} jour(s)</p>
            </div>
        </div>
    `;
}

async function validatePayslip(payslipId) {
    if (!confirm('Confirmer la validation de cette fiche de paie ?')) return;
    
    try {
        const response = await fetch(`/payroll/payslip/${payslipId}/validate`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Fiche de paie validée', 'success');
            loadPayslips();
        } else {
            showNotification(data.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
        console.error('Erreur:', error);
    }
}

function downloadPayslipPDF() {
    if (currentPayslipId) {
        window.open(`/payroll/payslip/${currentPayslipId}/pdf`, '_blank');
    }
}

function closePayslipPreviewModal() {
    closeModal('payslipPreviewModal');
    currentPayslipId = null;
}

// ==================== UTILITAIRES ====================

async function loadDepartments() {
    try {
        const response = await fetch('/department/list');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('salaryDepartmentFilter');
            if (select) {
                data.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.id;
                    option.textContent = dept.name;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Erreur chargement départements:', error);
    }
}

function initializeYearSelects() {
    const currentYear = new Date().getFullYear();
    const years = [];
    
    for (let i = currentYear - 2; i <= currentYear + 1; i++) {
        years.push(i);
    }
    
    const selects = ['payslipYear', 'generateYear'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                if (year === currentYear) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function showNotification(message, type = 'info') {
    if (window.FlowERP && window.FlowERP.showNotification) {
        window.FlowERP.showNotification(message, type);
    } else {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}       

function openGenerateAllPayslipsModal() {
    showNotification('Fonctionnalité en développement', 'info');
}