// LusitoHub Admin Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // Add loading spinner to form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtns = form.querySelectorAll('input[type="submit"], button[type="submit"]');
            submitBtns.forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            });
        });
    });

    // Auto-refresh certain admin pages
    if (window.location.pathname.includes('/admin/')) {
        // Refresh dashboard statistics every 5 minutes
        if (window.location.pathname === '/admin/') {
            setInterval(() => {
                const statsCards = document.querySelectorAll('.stat-card');
                statsCards.forEach(card => {
                    card.style.opacity = '0.7';
                });
                
                setTimeout(() => {
                    statsCards.forEach(card => {
                        card.style.opacity = '1';
                    });
                }, 1000);
            }, 300000); // 5 minutes
        }
    }

    // Enhance table rows with hover effects
    const tableRows = document.querySelectorAll('.results tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8fafc';
        });
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });

    // Add confirmation dialogs for dangerous actions
    const deleteButtons = document.querySelectorAll('input[value="Delete"], .deletelink, [name="_delete"]');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Add success/error message auto-hide
    const messages = document.querySelectorAll('.alert, .messagelist li');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s ease-out';
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Dashboard statistics animation
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(stat => {
        const finalNumber = parseInt(stat.textContent);
        if (finalNumber > 0) {
            let currentNumber = 0;
            const increment = Math.ceil(finalNumber / 50);
            const timer = setInterval(() => {
                currentNumber += increment;
                if (currentNumber >= finalNumber) {
                    currentNumber = finalNumber;
                    clearInterval(timer);
                }
                stat.textContent = currentNumber;
            }, 20);
        }
    });

    // Add tooltips to action buttons
    const actionButtons = document.querySelectorAll('.btn, .button, input[type="submit"]');
    actionButtons.forEach(btn => {
        if (btn.title || btn.getAttribute('data-title')) {
            btn.style.position = 'relative';
            
            btn.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'custom-tooltip';
                tooltip.textContent = this.title || this.getAttribute('data-title');
                tooltip.style.cssText = `
                    position: absolute;
                    bottom: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #2563eb;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    white-space: nowrap;
                    z-index: 1000;
                    margin-bottom: 5px;
                `;
                this.appendChild(tooltip);
                this.title = ''; // Remove default tooltip
            });

            btn.addEventListener('mouseleave', function() {
                const tooltip = this.querySelector('.custom-tooltip');
                if (tooltip) {
                    tooltip.remove();
                }
            });
        }
    });

    // Enhance form field focus
    const formFields = document.querySelectorAll('input, textarea, select');
    formFields.forEach(field => {
        field.addEventListener('focus', function() {
            this.style.borderColor = '#2563eb';
            this.style.boxShadow = '0 0 0 0.2rem rgba(37, 99, 235, 0.25)';
        });

        field.addEventListener('blur', function() {
            this.style.borderColor = '';
            this.style.boxShadow = '';
        });
    });

    console.log('LusitoHub Admin customizations loaded successfully!');
});

// Utility functions
window.LusitoAdmin = {
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    },

    confirmAction: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },

    formatCurrency: function(amount, currency = 'SZL') {
        return new Intl.NumberFormat('en-SZ', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }
};
