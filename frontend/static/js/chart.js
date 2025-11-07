/**
 * Chart.js utilities for FlowERP Dashboard
 * Provides functions to create and manage charts
 */

class DashboardCharts {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: '#667eea',
            success: '#48bb78',
            warning: '#ed8936',
            danger: '#f56565',
            info: '#4299e1',
            secondary: '#718096'
        };
    }

    /**
     * Create a budget chart
     */
    createBudgetChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // Destroy existing chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const labels = data.map(d => d.department_name);
        const budgets = data.map(d => d.budget);
        const spent = data.map(d => d.spent);

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Budget Total',
                        data: budgets,
                        backgroundColor: this.colors.primary + '40',
                        borderColor: this.colors.primary,
                        borderWidth: 2
                    },
                    {
                        label: 'Dépensé',
                        data: spent,
                        backgroundColor: this.colors.warning + '40',
                        borderColor: this.colors.warning,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + 
                                       context.parsed.y.toFixed(2) + ' TND';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(0) + ' TND';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create an employee distribution pie chart
     */
    createEmployeeChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const labels = data.map(d => d.department_name);
        const counts = data.map(d => d.employee_count);
        const colors = this.generateColors(data.length);

        this.charts[canvasId] = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors.background,
                    borderColor: colors.border,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return context.label + ': ' + context.parsed + 
                                       ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a line chart for activity trends
     */
    createActivityChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Activité',
                    data: data.values,
                    backgroundColor: this.colors.info + '20',
                    borderColor: this.colors.info,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a doughnut chart for budget status
     */
    createBudgetStatusChart(canvasId, budgetData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const spent = budgetData.total_spent || 0;
        const remaining = budgetData.budget_remaining || 0;

        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Dépensé', 'Restant'],
                datasets: [{
                    data: [spent, remaining],
                    backgroundColor: [
                        this.colors.warning + '80',
                        this.colors.success + '80'
                    ],
                    borderColor: [
                        this.colors.warning,
                        this.colors.success
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = spent + remaining;
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return context.label + ': ' + context.parsed.toFixed(2) + 
                                       ' TND (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a horizontal bar chart for department comparison
     */
    createDepartmentComparisonChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const labels = data.map(d => d.name);
        const values = data.map(d => d.value);
        const backgroundColors = data.map((d, i) => {
            if (d.status === 'critical') return this.colors.danger + '60';
            if (d.status === 'warning') return this.colors.warning + '60';
            return this.colors.success + '60';
        });

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Utilisation',
                    data: values,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(c => c.replace('60', '')),
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Generate color palette
     */
    generateColors(count) {
        const baseColors = [
            this.colors.primary,
            this.colors.success,
            this.colors.warning,
            this.colors.danger,
            this.colors.info,
            this.colors.secondary
        ];

        const background = [];
        const border = [];

        for (let i = 0; i < count; i++) {
            const color = baseColors[i % baseColors.length];
            background.push(color + '60');
            border.push(color);
        }

        return { background, border };
    }

    /**
     * Destroy all charts
     */
    destroyAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    /**
     * Destroy specific chart
     */
    destroy(canvasId) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
            delete this.charts[canvasId];
        }
    }
}

// Initialize charts manager
const dashboardCharts = new DashboardCharts();

/**
 * Load and display all dashboard charts
 */
async function loadDashboardCharts() {
    try {
        // Load budget analysis
        const budgetResponse = await fetch('/api/dashboard/budget/analysis');
        if (budgetResponse.ok) {
            const budgetData = await budgetResponse.json();
            if (budgetData.success && budgetData.analysis.length > 0) {
                dashboardCharts.createBudgetChart('budgetChart', budgetData.analysis);
                
                // Create comparison chart
                const comparisonData = budgetData.analysis.map(d => ({
                    name: d.department_name,
                    value: d.percentage,
                    status: d.status
                }));
                dashboardCharts.createDepartmentComparisonChart('comparisonChart', comparisonData);
            }
        }

        // Load employee distribution
        const employeeResponse = await fetch('/api/dashboard/employees/distribution');
        if (employeeResponse.ok) {
            const employeeData = await employeeResponse.json();
            if (employeeData.success && employeeData.distribution.length > 0) {
                dashboardCharts.createEmployeeChart('employeeChart', employeeData.distribution);
            }
        }

        // Load main stats for budget status
        const statsResponse = await fetch('/api/dashboard/stats');
        if (statsResponse.ok) {
            const statsData = await statsResponse.json();
            if (statsData.success) {
                dashboardCharts.createBudgetStatusChart('budgetStatusChart', statsData.stats);
            }
        }

    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardCharts, loadDashboardCharts };
}