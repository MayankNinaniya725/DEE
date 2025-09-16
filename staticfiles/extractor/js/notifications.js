/**
 * Notifications Utility for Extractor Project
 * This script provides standardized notification handling for all pages
 */

// Show a notification with auto-hide functionality
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    if (!container) {
        console.error('Notification container not found');
        return null;
    }
    
    let icon = 'ℹ';
    if (type === 'success') icon = '✓';
    else if (type === 'warning') icon = '⚠';
    else if (type === 'error') icon = '✗';
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.setAttribute('role', 'alert');
    notification.innerHTML = `
        <span class="notification-icon">${icon}</span>
        <span class="notification-text">${message}</span>
        <button type="button" class="notification-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.5s ease-out';
            setTimeout(() => notification.remove(), 500);
        }, duration);
    }
    
    return notification;
}

// Initialize notification system
document.addEventListener('DOMContentLoaded', function() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; width: 350px;';
        document.body.appendChild(container);
    }
    
    // Auto-hide all existing notifications
    const notifications = document.querySelectorAll('#notification-container .notification');
    notifications.forEach((notification, index) => {
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.5s ease-out';
            setTimeout(() => notification.remove(), 500);
        }, 5000 + (index * 500)); // Stagger the disappearance
    });
    
    // Add fade-out animation CSS if it doesn't exist
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes fadeOut {
                to { opacity: 0; transform: translateY(-10px); }
            }
        `;
        document.head.appendChild(style);
    }
});

// Handle form submissions to show loading notification
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[data-show-loading]');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            showNotification('Processing your request...', 'info', 0);
        });
    });
});
