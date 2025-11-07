/**
 * FlowERP - Main JavaScript
 * Fonctions globales et utilitaires
 */

// ========================================
// Configuration globale
// ========================================
const API_BASE_URL = '';
let currentUser = null;
let csrfToken = null;

// ========================================
// Initialisation
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    // Vérifier la session
    await checkSession();
    
    // Initialiser les event listeners globaux
    initializeGlobalListeners();
}

// ========================================
// Gestion de la session
// ========================================
async function checkSession() {
    try {
        const response = await fetch('/auth/check-session');
        if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
                currentUser = data.user;
                csrfToken = data.csrf_token;
            }
        }
    } catch (error) {
        console.error('Erreur lors de la vérification de la session:', error);
    }
}

// ========================================
// Gestion du menu utilisateur
// ========================================
function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    menu.classList.toggle('show');
}

// Fermer le menu en cliquant ailleurs
document.addEventListener('click', function(event) {
    const userDropdown = document.querySelector('.user-dropdown');
    const menu = document.getElementById('userMenu');
    
    if (userDropdown && menu && !userDropdown.contains(event.target)) {
        menu.classList.remove('show');
    }
});

// ========================================
// Déconnexion
// ========================================
async function logout() {
    if (!confirm('Voulez-vous vraiment vous déconnecter ?')) {
        return;
    }
    
    try {
        const response = await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showNotification('Déconnexion réussie', 'success');
            setTimeout(() => {
                window.location.href = '/auth/login-page';
            }, 1000);
        }
    } catch (error) {
        showNotification('Erreur lors de la déconnexion', 'error');
    }
}

// ========================================
// Système de notifications
// ========================================
function showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('flashMessages') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Auto-suppression
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, duration);
    }
}

function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'flashMessages';
    container.className = 'notification-container';
    document.body.appendChild(container);
    return container;
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

// ========================================
// Vérification du statut de la blockchain
// ========================================
async function checkBlockchainStatus() {
    try {
        const response = await fetch('/api/blockchain/stats');
        if (response.ok) {
            const data = await response.json();
            updateBlockchainUI(data);
        }
    } catch (error) {
        console.error('Erreur lors de la vérification de la blockchain:', error);
    }
}

function updateBlockchainUI(stats) {
    const statusIndicator = document.getElementById('blockchainStatus');
    const blockCount = document.getElementById('blockCount');
    
    if (statusIndicator) {
        statusIndicator.className = stats.is_valid ? 'status-indicator status-success' : 'status-indicator status-error';
    }
    
    if (blockCount) {
        blockCount.textContent = stats.total_blocks;
    }
}

// ========================================
// Modals
// ========================================
function openModal(title, content, actions = []) {
    const modalContainer = document.getElementById('modalContainer') || createModalContainer();
    
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-backdrop" onclick="closeModal(this.parentElement)"></div>
        <div class="modal-dialog">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="modal-close" onclick="closeModal(this.closest('.modal'))">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
            ${actions.length > 0 ? `
                <div class="modal-footer">
                    ${actions.map(action => `
                        <button class="btn ${action.class || 'btn-secondary'}" onclick="${action.onclick}">
                            ${action.label}
                        </button>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
    
    modalContainer.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

function closeModal(modal) {
    modal.classList.remove('show');
    setTimeout(() => modal.remove(), 300);
}

function createModalContainer() {
    const container = document.createElement('div');
    container.id = 'modalContainer';
    document.body.appendChild(container);
    return container;
}

// ========================================
// Modal de profil
// ========================================
async function openProfileModal() {
    if (!currentUser) {
        await checkSession();
    }

    if (!currentUser) {
        showNotification("Impossible de charger le profil. Veuillez actualiser la page.", "error");
        return;
    }

    
    const content = `
        <form id="profileForm" class="modal-form">
            <div class="form-group">
                <label for="profile_first_name">Prénom</label>
                <input type="text" id="profile_first_name" class="form-control" value="${currentUser.first_name || ''}" required>
            </div>
            <div class="form-group">
                <label for="profile_last_name">Nom</label>
                <input type="text" id="profile_last_name" class="form-control" value="${currentUser.last_name || ''}" required>
            </div>
            <div class="form-group">
                <label for="profile_email">Email</label>
                <input type="email" id="profile_email" class="form-control" value="${currentUser.email}" required>
            </div>
            <div class="form-group">
                <label for="profile_phone">Téléphone</label>
                <input type="tel" id="profile_phone" class="form-control" value="${currentUser.phone || ''}">
            </div>
        </form>
    `;
    
    const actions = [
        { label: 'Annuler', class: 'btn-secondary', onclick: 'closeModal(this.closest(".modal"))' },
        { label: 'Enregistrer', class: 'btn-primary', onclick: 'saveProfile()' }
    ];
    
    openModal('Mon Profil', content, actions);
}

async function saveProfile() {
    // TODO: Implémenter la sauvegarde du profil
    showNotification('Fonctionnalité en cours de développement', 'info');
}

// ========================================
// Modal de changement de mot de passe
// ========================================
function openPasswordModal() {
    const content = `
        <form id="passwordForm" class="modal-form">
            <div class="form-group">
                <label for="current_password">Mot de passe actuel</label>
                <input type="password" id="current_password" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="new_password">Nouveau mot de passe</label>
                <input type="password" id="new_password" class="form-control" required minlength="8">
            </div>
            <div class="form-group">
                <label for="confirm_new_password">Confirmer le nouveau mot de passe</label>
                <input type="password" id="confirm_new_password" class="form-control" required>
            </div>
            <div id="passwordError" class="alert alert-error" style="display: none;"></div>
        </form>
    `;
    
    const actions = [
        { label: 'Annuler', class: 'btn-secondary', onclick: 'closeModal(this.closest(".modal"))' },
        { label: 'Changer', class: 'btn-primary', onclick: 'changePassword()' }
    ];
    
    openModal('Changer le mot de passe', content, actions);
}

async function changePassword() {
    const currentPassword = document.getElementById('current_password').value;
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_new_password').value;
    const errorDiv = document.getElementById('passwordError');
    
    // Validation
    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'Les mots de passe ne correspondent pas';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch('/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            closeModal(document.querySelector('.modal'));
            showNotification('Mot de passe modifié avec succès', 'success');
        } else {
            errorDiv.textContent = data.error || 'Erreur lors du changement de mot de passe';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Erreur de connexion au serveur';
        errorDiv.style.display = 'block';
    }
}

// ========================================
// Utilitaires pour les requêtes API
// ========================================
async function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(API_BASE_URL + endpoint, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erreur lors de la requête');
        }
        
        return data;
    } catch (error) {
        console.error('Erreur API:', error);
        throw error;
    }
}

// ========================================
// Formatage des dates
// ========================================
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function formatDateShort(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(date);
}

// ========================================
// Formatage des nombres
// ========================================
function formatCurrency(amount, currency = 'TND') {
    return new Intl.NumberFormat('fr-TN', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatNumber(number) {
    return new Intl.NumberFormat('fr-FR').format(number);
}

// ========================================
// Validation côté client
// ========================================
function validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

function validatePhone(phone) {
    const regex = /^\+?[0-9]{8,15}$/;
    return regex.test(phone);
}

// ========================================
// Debounce pour les recherches
// ========================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ========================================
// Event Listeners globaux
// ========================================
function initializeGlobalListeners() {
    // Fermer les dropdowns en cliquant ailleurs
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
    
    // Empêcher la soumission des formulaires si invalides
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// ========================================
// Loading spinner
// ========================================
function showLoading() {
    const loader = document.createElement('div');
    loader.id = 'globalLoader';
    loader.className = 'loading-overlay';
    loader.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Chargement...</p>
        </div>
    `;
    document.body.appendChild(loader);
}

function hideLoading() {
    const loader = document.getElementById('globalLoader');
    if (loader) {
        loader.remove();
    }
}

// ========================================
// Confirmation dialog
// ========================================
function confirmDialog(message, onConfirm, onCancel) {
    const content = `
        <p class="confirm-message">${message}</p>
    `;
    
    const actions = [
        { 
            label: 'Annuler', 
            class: 'btn-secondary', 
            onclick: `closeModal(this.closest('.modal')); ${onCancel ? `(${onCancel})()` : ''}`
        },
        { 
            label: 'Confirmer', 
            class: 'btn-primary', 
            onclick: `closeModal(this.closest('.modal')); (${onConfirm})()`
        }
    ];
    
    openModal('Confirmation', content, actions);
}

// ========================================
// Export des fonctions globales
// ========================================
window.FlowERP = {
    checkSession,
    toggleUserMenu,
    logout,
    showNotification,
    checkBlockchainStatus,
    openModal,
    closeModal,
    openProfileModal,
    openPasswordModal,
    apiRequest,
    formatDate,
    formatDateShort,
    formatCurrency,
    formatNumber,
    validateEmail,
    validatePhone,
    debounce,
    showLoading,
    hideLoading,
    confirmDialog
};