document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('notificationsDropdown')) {
        initializeNotifications();
    }
});

function initializeNotifications() {
    const notificationsList = document.getElementById('notificationsList');
    const notificationCount = document.getElementById('notificationCount');
    // WebSocket temporarily disabled for Render deployment
    // TODO: Configure Django Channels + ASGI for WebSocket support
    // const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // const ws = new WebSocket(
    //     `${protocol}//${window.location.host}/ws/notifications/`
    // );
    // 
    // ws.onmessage = function(e) {
    //     const data = JSON.parse(e.data);
    //     if (data.type === 'notification_update') {
    //         updateNotifications(data.notifications);
    //     }
    // };

    // Initial load
    fetchNotifications();

    // Mark all as read handler
    document.querySelector('.mark-all-read').addEventListener('click', function(e) {
        e.preventDefault();
        fetch('/chat/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateNotifications([]);
            }
        });
    });

    function fetchNotifications() {
        fetch('/notifications/unread/')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch notifications');
                }
                return response.json();
            })
            .then(data => {
                updateNotifications(data.notifications);
            })
            .catch(error => {
                console.error('Error fetching notifications:', error);
                // Show fallback message
                updateNotifications([]);
            });
    }

    function updateNotifications(notifications) {
        const totalCount = notifications.length;
        
        if (totalCount > 0) {
            notificationCount.textContent = totalCount;
            notificationCount.style.display = 'inline';
        } else {
            notificationCount.style.display = 'none';
        }

        notificationsList.innerHTML = notifications.length ? 
            notifications.map(notification => `
                <a href="${notification.url || '/notifications/'}" class="dropdown-item notification-item" 
                   onclick="markAsRead(${notification.id})">
                    <div class="notification-content">
                        <strong>${notification.title}</strong><br>
                        ${notification.message}
                    </div>
                    <div class="notification-meta">
                        ${formatTimeAgo(new Date(notification.created_at))}
                    </div>
                </a>
            `).join('') :
            '<div class="dropdown-item">No new notifications</div>';
    }
    
    // Mark notification as read when clicked
    function markAsRead(notificationId) {
        fetch('/notifications/mark_read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value || getCookie('csrftoken'),
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `notification_id=${notificationId}`
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }

    function formatTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }
}