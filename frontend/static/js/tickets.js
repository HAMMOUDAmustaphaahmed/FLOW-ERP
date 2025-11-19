class TicketsManager {
    constructor() {
        this.currentTicket = null;
        this.createTicketModal = null;
        this.ticketDetailModal = null;
        this.assignTicketModal = null;
        this.departments = [];
        this.departmentUsers = [];
        this.isInitialized = false;
        
        if (typeof bootstrap !== 'undefined') {
            this.initialize();
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                this.initialize();
            });
        }
    }

initialize() {
    console.log('TicketsManager initializing...');
    
    try {
        this.initializeModals();
        this.initEventListeners();
        
        // Charger en parallèle pour plus de rapidité
        Promise.all([
            this.loadDepartments(),
            this.loadTickets(),
            this.loadStats()
        ]).then(() => {
            this.isInitialized = true;
            console.log('✓ TicketsManager fully initialized');
        }).catch(error => {
            console.error('Error during initialization:', error);
        });
        
    } catch (error) {
        console.error('Error during TicketsManager initialization:', error);
    }
}
    initializeModals() {
        console.log('Initializing modals...');
        
        const createModalElement = document.getElementById('createTicketModal');
        if (createModalElement) {
            this.createTicketModal = new bootstrap.Modal(createModalElement);
        }
        
        const detailModalElement = document.getElementById('ticketDetailModal');
        if (detailModalElement) {
            this.ticketDetailModal = new bootstrap.Modal(detailModalElement);
        }
        
        // Modal d'assignation
        this.createAssignModal();
    }

    createAssignModal() {
        // Créer dynamiquement le modal d'assignation s'il n'existe pas
        if (!document.getElementById('assignTicketModal')) {
            const modalHTML = `
                <div class="modal fade" id="assignTicketModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Assigner le Ticket</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label class="form-label">Assigner à</label>
                                    <select class="form-select" id="assignToUser">
                                        <option value="">Choisir un utilisateur...</option>
                                    </select>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                                <button type="button" class="btn btn-primary" id="confirmAssignBtn">Assigner</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
        
        const assignModalElement = document.getElementById('assignTicketModal');
        if (assignModalElement) {
            this.assignTicketModal = new bootstrap.Modal(assignModalElement);
        }
    }

    initEventListeners() {
        console.log('Initializing event listeners...');
        
        const newTicketBtn = document.getElementById('newTicketBtn');
        if (newTicketBtn) {
            newTicketBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openCreateTicketModal();
            });
        }

        const createTicketBtn = document.getElementById('createTicketBtn');
        if (createTicketBtn) {
            createTicketBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.createTicket();
            });
        }

        const confirmAssignBtn = document.getElementById('confirmAssignBtn');
        if (confirmAssignBtn) {
            confirmAssignBtn.addEventListener('click', () => {
                this.confirmAssign();
            });
        }

        const filters = ['statusFilter', 'priorityFilter', 'categoryFilter', 'viewType'];
        filters.forEach(filterId => {
            const filterElement = document.getElementById(filterId);
            if (filterElement) {
                filterElement.addEventListener('change', () => this.loadTickets());
            }
        });
    }

async loadDepartments() {
    // Éviter de recharger si déjà chargé
    if (this.departments && this.departments.length > 0) {
        this.populateDepartmentSelect();
        return;
    }
    
    try {
        const response = await fetch('/api/tickets/departments');
        const data = await response.json();
        
        if (data.success) {
            this.departments = data.departments;
            this.populateDepartmentSelect();
        }
    } catch (error) {
        console.error('Erreur chargement départements:', error);
    }
}

    populateDepartmentSelect() {
        const select = document.getElementById('ticketDepartment');
        if (!select) return;
        
        select.innerHTML = '<option value="">Choisir un département *</option>';
        this.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept.id;
            option.textContent = `${dept.name}${dept.code ? ' (' + dept.code + ')' : ''}`;
            select.appendChild(option);
        });
    }

    openCreateTicketModal() {
        console.log('Opening create ticket modal...');
        
        if (!this.createTicketModal) {
            const modalElement = document.getElementById('createTicketModal');
            if (modalElement) {
                this.createTicketModal = new bootstrap.Modal(modalElement);
            } else {
                alert('Erreur: Le formulaire de ticket n\'est pas disponible.');
                return;
            }
        }
        
        try {
            const form = document.getElementById('createTicketForm');
            if (form) form.reset();
            
            this.createTicketModal.show();
        } catch (error) {
            console.error('Error showing modal:', error);
            alert('Erreur lors de l\'ouverture du formulaire');
        }
    }

    async createTicket() {
        const formData = {
            title: document.getElementById('ticketTitle').value.trim(),
            description: document.getElementById('ticketDescription').value.trim(),
            category: document.getElementById('ticketCategory').value,
            priority: document.getElementById('ticketPriority').value,
            department_id: parseInt(document.getElementById('ticketDepartment').value),
            location: document.getElementById('ticketLocation').value.trim(),
            equipment: document.getElementById('ticketEquipment').value.trim(),
            tags: document.getElementById('ticketTags').value.split(',').map(tag => tag.trim()).filter(tag => tag)
        };

        // Validation
        if (!formData.title || !formData.description || !formData.category || !formData.department_id) {
            this.showError('Veuillez remplir tous les champs obligatoires (dont le département)');
            return;
        }

        try {
            const response = await fetch('/api/tickets/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(data.message || 'Ticket créé avec succès');
                this.createTicketModal.hide();
                document.getElementById('createTicketForm').reset();
                await this.loadTickets();
                await this.loadStats();
            } else {
                this.showError(data.error || 'Erreur lors de la création');
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/tickets/stats');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('totalTickets').textContent = data.stats.total || 0;
                document.getElementById('pendingTickets').textContent = data.stats.en_attente || 0;
                document.getElementById('overdueTickets').textContent = data.stats.overdue || 0;
                document.getElementById('resolvedTickets').textContent = data.stats.resolu || 0;
            }
        } catch (error) {
            console.error('Erreur chargement stats:', error);
        }
    }

getDepartmentColor(departmentName) {
    // Générer une couleur basée sur le nom du département
    const colors = [
        'bg-primary', 'bg-success', 'bg-warning', 'bg-info', 'bg-danger',
        'bg-secondary', 'bg-dark', 'bg-primary bg-opacity-75', 
        'bg-success bg-opacity-75', 'bg-warning bg-opacity-75'
    ];
    
    // Créer un hash simple à partir du nom
    let hash = 0;
    for (let i = 0; i < departmentName.length; i++) {
        hash = departmentName.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    // Utiliser le hash pour sélectionner une couleur
    const index = Math.abs(hash) % colors.length;
    return colors[index];
}

async loadTickets() {
    const status = document.getElementById('statusFilter')?.value || '';
    const priority = document.getElementById('priorityFilter')?.value || '';
    const category = document.getElementById('categoryFilter')?.value || '';
    const viewType = document.getElementById('viewType')?.value || 'my_tickets';

    let url = '/api/tickets/';
    switch(viewType) {
        case 'my_tickets':
            url += 'my-tickets';
            break;
        case 'assigned_to_me':
            url += 'assigned-to-me';
            break;
        case 'all':
            url += 'all';
            break;
    }

    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    if (category) params.append('category', category);

    if (params.toString()) {
        url += '?' + params.toString();
    }

    console.log(`Chargement des tickets: ${url}`); // Debug

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Réponse tickets:', data); // Debug
        
        if (data.success) {
            this.displayTickets(data.tickets);
        } else {
            this.showError(data.error || 'Erreur lors du chargement des tickets');
        }
    } catch (error) {
        console.error('Erreur:', error);
        this.showError('Erreur de connexion');
    }
}

    displayTickets(tickets) {
        const container = document.getElementById('ticketsList');
        if (!container) return;
        
        if (tickets.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Aucun ticket trouvé</p>
                </div>
            `;
            return;
        }

        let html = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Numéro</th>
                        <th>Titre</th>
                        <th>Département</th>
                        <th>Catégorie</th>
                        <th>Priorité</th>
                        <th>Statut</th>
                        <th>Assigné à</th>
                        <th>Créé le</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        tickets.forEach(ticket => {
            const priorityClass = this.getPriorityClass(ticket.priority);
            const statusClass = this.getStatusClass(ticket.status);
            const createdDate = new Date(ticket.created_at).toLocaleDateString('fr-FR');
            
            html += `
                <tr class="ticket-item ${ticket.is_overdue ? 'ticket-overdue' : ''}">
                    <td>
                        <strong>${ticket.ticket_number}</strong>
                        ${ticket.is_overdue ? '<i class="fas fa-exclamation-triangle text-warning ms-1" title="En retard"></i>' : ''}
                    </td>
                    <td>${this.escapeHtml(ticket.title)}</td>
                    <td><span class="badge ${this.getDepartmentColor(ticket.department)}">${ticket.department || 'N/A'}</span></td>
                    <td><span class="badge badge-category">${this.getCategoryLabel(ticket.category)}</span></td>
                    <td><span class="badge ${priorityClass}">${this.getPriorityLabel(ticket.priority)}</span></td>
                    <td><span class="badge ${statusClass}">${this.getStatusLabel(ticket.status)}</span></td>
                    <td>${ticket.assigned_to ? ticket.assigned_to.name : '<em class="text-muted">Non assigné</em>'}</td>
                    <td>${createdDate}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary view-ticket-btn" data-ticket-id="${ticket.id}" title="Voir les détails">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;

        container.querySelectorAll('.view-ticket-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ticketId = parseInt(e.currentTarget.getAttribute('data-ticket-id'));
                this.viewTicket(ticketId);
            });
        });
    }

    async viewTicket(ticketId) {
        try {
            const response = await fetch(`/api/tickets/${ticketId}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentTicket = data.ticket;
                this.showTicketDetail(data.ticket, data.can_modify);
            } else {
                this.showError('Erreur lors du chargement du ticket');
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    showTicketDetail(ticket, canModify) {
        if (!this.ticketDetailModal) return;

        const title = document.getElementById('ticketDetailTitle');
        const content = document.getElementById('ticketDetailContent');

        if (!title || !content) return;

        title.textContent = `Ticket ${ticket.ticket_number} - ${ticket.title}`;
        
        const createdDate = new Date(ticket.created_at).toLocaleString('fr-FR');
        const slaDeadline = ticket.sla_deadline ? new Date(ticket.sla_deadline).toLocaleString('fr-FR') : 'Non défini';

        let actionsHTML = '';
        if (canModify) {
            if (ticket.status !== 'resolu' && ticket.status !== 'ferme') {
                actionsHTML = `
                    <div class="mb-3">
                        <button class="btn btn-primary me-2" id="assignTicketBtn">
                            <i class="fas fa-user-plus"></i> ${ticket.assigned_to ? 'Réassigner' : 'Assigner'}
                        </button>
                        ${ticket.assigned_to ? `
                            <button class="btn btn-success" id="resolveTicketBtn">
                                <i class="fas fa-check"></i> Marquer comme résolu
                            </button>
                        ` : ''}
                    </div>
                `;
            } else if (ticket.status === 'resolu') {
                actionsHTML = `
                    <div class="mb-3">
                        <button class="btn btn-warning" id="reopenTicketBtn">
                            <i class="fas fa-redo"></i> Réouvrir le ticket
                        </button>
                    </div>
                `;
            }
        }

        content.innerHTML = `
            ${actionsHTML}
            <div class="row">
                <div class="col-md-8">
                    <div class="card mb-3">
                        <div class="card-header"><h6>Description</h6></div>
                        <div class="card-body">
                            <p>${this.escapeHtml(ticket.description)}</p>
                            ${ticket.location ? `<p><strong>Localisation:</strong> ${this.escapeHtml(ticket.location)}</p>` : ''}
                            ${ticket.equipment ? `<p><strong>Équipement:</strong> ${this.escapeHtml(ticket.equipment)}</p>` : ''}
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header d-flex justify-content-between">
                            <h6>Commentaires</h6>
                            <span class="badge bg-primary">${ticket.comments_count || 0}</span>
                        </div>
                        <div class="card-body">
                            <div id="commentsList">${this.renderComments(ticket.comments || [])}</div>
                            <div class="mt-3">
                                <textarea class="form-control mb-2" id="newComment" rows="3" placeholder="Ajouter un commentaire..."></textarea>
                                <button class="btn btn-primary btn-sm" id="addCommentBtn">
                                    <i class="fas fa-paper-plane me-1"></i>Ajouter
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card mb-3">
                        <div class="card-header"><h6>Informations</h6></div>
                        <div class="card-body">
                            <p><strong>Département:</strong> <span class="badge bg-info">${ticket.department || 'N/A'}</span></p>
                            <p><strong>Créé par:</strong> ${ticket.creator.name}</p>
                            <p><strong>Assigné à:</strong> ${ticket.assigned_to ? ticket.assigned_to.name : '<em class="text-muted">Non assigné</em>'}</p>
                            ${ticket.resolved_by_id && ticket.resolution_comment ? `
                                <div class="alert alert-success mt-3">
                                    <strong>Résolu par:</strong> ${ticket.assigned_to ? ticket.assigned_to.name : 'N/A'}<br>
                                    <strong>Temps:</strong> ${ticket.resolution_time_minutes} min<br>
                                    <strong>Commentaire:</strong> ${this.escapeHtml(ticket.resolution_comment)}
                                </div>
                            ` : ''}
                            <p><strong>Date création:</strong> ${createdDate}</p>
                            <p><strong>Deadline SLA:</strong> ${slaDeadline}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        setTimeout(() => {
            const addCommentBtn = document.getElementById('addCommentBtn');
            if (addCommentBtn) {
                addCommentBtn.addEventListener('click', () => this.addComment());
            }

            const assignBtn = document.getElementById('assignTicketBtn');
            if (assignBtn) {
                assignBtn.addEventListener('click', () => this.openAssignModal());
            }

            const resolveBtn = document.getElementById('resolveTicketBtn');
            if (resolveBtn) {
                resolveBtn.addEventListener('click', () => this.openResolveDialog());
            }

            const reopenBtn = document.getElementById('reopenTicketBtn');
            if (reopenBtn) {
                reopenBtn.addEventListener('click', () => this.openReopenDialog());
            }
        }, 100);

        this.ticketDetailModal.show();
    }

    async openAssignModal() {
        // Vérifier que department_id est disponible
    if (!this.currentTicket.department_id) {
        this.showError('Impossible de déterminer le département du ticket');
        return;
    }

        try {
            // Charger les users du département
            const response = await fetch(`/api/tickets/department/${this.currentTicket.department_id}/users`);
            const data = await response.json();

            if (data.success) {
                this.departmentUsers = data.users;
                
                const select = document.getElementById('assignToUser');
                if (select) {
                    select.innerHTML = '<option value="">Choisir un utilisateur...</option>';
                    data.users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = `${user.full_name} (${user.role})`;
                        select.appendChild(option);
                    });
                }

                this.assignTicketModal.show();
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur lors du chargement des utilisateurs');
        }
    }

    async confirmAssign() {
        const userId = document.getElementById('assignToUser')?.value;
        if (!userId || !this.currentTicket) return;

        try {
            const response = await fetch(`/api/tickets/${this.currentTicket.id}/assign`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assigned_to_id: parseInt(userId) })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(data.message);
                this.assignTicketModal.hide();
                await this.viewTicket(this.currentTicket.id);
                await this.loadTickets();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    openResolveDialog() {
        const comment = prompt('Commentaire de résolution (obligatoire):');
        if (comment && comment.trim()) {
            this.resolveTicket(comment.trim());
        }
    }

    async resolveTicket(comment) {
        if (!this.currentTicket) return;

        try {
            const response = await fetch(`/api/tickets/${this.currentTicket.id}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ comment })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(data.message);
                await this.viewTicket(this.currentTicket.id);
                await this.loadTickets();
                await this.loadStats();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    openReopenDialog() {
        const reason = prompt('Raison de la réouverture:');
        if (reason && reason.trim()) {
            this.reopenTicket(reason.trim());
        }
    }

    async reopenTicket(reason) {
        if (!this.currentTicket) return;

        try {
            const response = await fetch(`/api/tickets/${this.currentTicket.id}/reopen`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Ticket réouvert avec succès');
                await this.viewTicket(this.currentTicket.id);
                await this.loadTickets();
                await this.loadStats();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    renderComments(comments) {
        if (comments.length === 0) {
            return '<p class="text-muted text-center">Aucun commentaire</p>';
        }

        return comments.map(comment => `
            <div class="comment mb-3 p-3 bg-light">
                <div class="d-flex justify-content-between mb-2">
                    <strong>${comment.user.name}</strong>
                    <small class="text-muted">${new Date(comment.created_at).toLocaleString('fr-FR')}</small>
                </div>
                <p class="mb-0">${this.escapeHtml(comment.comment)}</p>
            </div>
        `).join('');
    }

    async addComment() {
        if (!this.currentTicket) return;

        const comment = document.getElementById('newComment').value.trim();

        if (!comment) {
            this.showError('Veuillez saisir un commentaire');
            return;
        }

        try {
            const response = await fetch(`/api/tickets/${this.currentTicket.id}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ comment, is_internal: false })
            });

            const data = await response.json();

            if (data.success) {
                document.getElementById('newComment').value = '';
                this.viewTicket(this.currentTicket.id);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showError('Erreur de connexion');
        }
    }

    // Helper methods
    getPriorityClass(priority) {
        const classes = {
            'urgente': 'bg-danger',
            'critique': 'bg-danger',
            'haute': 'bg-warning',
            'normale': 'bg-primary',
            'basse': 'bg-secondary'
        };
        return classes[priority] || 'bg-primary';
    }

    getStatusClass(status) {
        const classes = {
            'en_attente': 'bg-warning',
            'en_cours': 'bg-info',
            'resolu': 'bg-success',
            'ferme': 'bg-secondary',
            'reouvert': 'bg-danger'
        };
        return classes[status] || 'bg-warning';
    }

    getPriorityLabel(priority) {
        const labels = {
            'urgente': 'Urgente',
            'critique': 'Critique',
            'haute': 'Haute',
            'normale': 'Normale',
            'basse': 'Basse'
        };
        return labels[priority] || priority;
    }

    getStatusLabel(status) {
        const labels = {
            'en_attente': 'En Attente',
            'en_cours': 'En Cours',
            'resolu': 'Résolu',
            'ferme': 'Fermé',
            'reouvert': 'Réouvert'
        };
        return labels[status] || status;
    }

    getCategoryLabel(category) {
        const labels = {
            'production': 'Production',
            'quality_control': 'Contrôle Qualité',
            'warehouse': 'Magasin',
            'it_support': 'IT/Informatique',
            'hr': 'RH',
            'maintenance': 'Maintenance',
            'security': 'Sécurité',
            'other': 'Autre'
        };
        return labels[category] || category;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'error');
    }

    showAlert(message, type) {
        if (window.FlowERP && window.FlowERP.showNotification) {
            window.FlowERP.showNotification(message, type);
        } else {
            alert(message);
        }
    }
}

// Initialisation
(function() {
    let initAttempts = 0;
    const maxAttempts = 10;
    
    function tryInitialize() {
        initAttempts++;
        
        if (typeof bootstrap === 'undefined') {
            if (initAttempts < maxAttempts) {
                setTimeout(tryInitialize, 500);
            }
            return;
        }
        
        if (!document.getElementById('createTicketModal')) {
            if (initAttempts < maxAttempts) {
                setTimeout(tryInitialize, 500);
            }
            return;
        }
        
        try {
            window.ticketsManager = new TicketsManager();
            console.log('✓ TicketsManager successfully initialized');
        } catch (error) {
            console.error('Error during initialization:', error);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInitialize);
    } else {
        tryInitialize();
    }
})();