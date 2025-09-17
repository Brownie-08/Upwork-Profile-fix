function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(document).ready(function() {
    // Fetch unread notifications on page load
    function fetchNotifications() {
        $.ajax({
            url: '/notifications/unread/',
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(data) {
                const notifications = data.notifications;
                const count = notifications.length;
                $('#notificationCount').text(count).toggle(count > 0);
                const $list = $('#notificationsList').empty();
                if (notifications.length > 0) {
                    notifications.forEach(notification => {
                        // Validate notification data
                        if (!notification.id || !notification.title || !notification.message) {
                            console.error('Invalid notification data:', notification);
                            return; // Skip this notification
                        }
                        
                        const item = `
                            <li class="list-group-item notification-item ${notification.is_read ? '' : 'notification-unread'}">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="mb-1">${notification.title}</h6>
                                        <p class="mb-1 small">${notification.message.substring(0, 30)}${notification.message.length > 30 ? '...' : ''}</p>
                                        <small class="text-muted">${new Date(notification.created_at).toLocaleString()}</small>
                                    </div>
                                    <div class="action-buttons">
                                        ${!notification.is_read ? `<button class="btn btn-primary btn-sm mark-read-btn" data-notification-id="${notification.id}">Mark as Read</button>` : ''}
                                        <button class="btn btn-danger btn-sm delete-btn" data-notification-id="${notification.id}">Delete</button>
                                    </div>
                                </div>
                            </li>
                        `;
                        $list.append(item);
                    });
                } else {
                    $list.append('<li class="dropdown-item text-center text-muted">No unread notifications</li>');
                }
            },
            error: function(error) {
                console.error('Error fetching notifications:', error);
                if (error.status === 0) {
                    alert('Network error: Please check your internet connection or server status.');
                } else {
                    alert('Failed to fetch notifications. Please try again later.');
                }
            }
        });
    }

    // Initial fetch
    fetchNotifications();

    // Handle Mark as Read with redirect
    $(document).on('click', '.mark-read-btn', function() {
        const $button = $(this);
        const notificationId = $button.data('notification-id');
        
        // Check for undefined notification ID
        if (!notificationId || notificationId === 'undefined') {
            console.error('Notification ID is undefined:', notificationId);
            alert('Error: Unable to identify notification. Please refresh the page and try again.');
            return;
        }
        
        // Disable button during request
        $button.prop('disabled', true).text('Marking...');
        
        $.ajax({
            url: '/notifications/mark-as-read/',
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            data: JSON.stringify({ 
                id: notificationId,
                redirect_url: '/notifications/'
            }),
            success: function(data) {
                if (data.success) {
                    // Update the notification count if provided
                    if (typeof data.unread_count !== 'undefined') {
                        $('#notificationCount').text(data.unread_count).toggle(data.unread_count > 0);
                    }
                    
                    // Remove the notification from the UI
                    $button.closest('.notification-item').fadeOut(300, function() {
                        $(this).remove();
                    });
                    
                    // Optionally refresh the list to show updated state
                    setTimeout(fetchNotifications, 500);
                } else {
                    console.error('Server error:', data.error);
                    alert(data.error || 'Failed to mark notification as read.');
                    $button.prop('disabled', false).text('Mark as Read');
                }
            },
            error: function(xhr, status, error) {
                console.error('AJAX Error:', { xhr, status, error });
                let errorMessage = 'An error occurred while marking the notification as read.';
                
                if (xhr.status === 0) {
                    errorMessage = 'Network error: Please check your internet connection or server status.';
                } else if (xhr.status === 404) {
                    errorMessage = 'Notification not found. It may have already been processed.';
                } else if (xhr.status === 403) {
                    errorMessage = 'You do not have permission to mark this notification as read.';
                } else if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                }
                
                alert(errorMessage);
                $button.prop('disabled', false).text('Mark as Read');
            }
        });
    });

    // Handle Delete
    $(document).on('click', '.delete-btn', function() {
        if (!confirm('Are you sure you want to delete this notification?')) return;
        const $button = $(this);
        const notificationId = $button.data('notification-id');
        
        // Check for undefined notification ID
        if (!notificationId || notificationId === 'undefined') {
            console.error('Notification ID is undefined:', notificationId);
            alert('Error: Unable to identify notification. Please refresh the page and try again.');
            return;
        }
        
        $.ajax({
            url: `/notifications/${notificationId}/delete/`,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(data) {
                $button.closest('.notification-item').remove();
                fetchNotifications(); // Refresh count and list
            },
            error: function(error) {
                console.error('Error:', error);
                if (error.status === 0) {
                    alert('Network error: Please check your internet connection or server status.');
                } else {
                    alert('An error occurred while deleting the notification.');
                }
            }
        });
    });

    // Handle Mark All as Read
    window.markAllNotificationsAsRead = function() {
        $.ajax({
            url: '/notifications/mark_all_read/',
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(data) {
                if (data.success) {
                    fetchNotifications();
                } else {
                    alert('Failed to mark all notifications as read.');
                }
            },
            error: function(error) {
                console.error('Error:', error);
                if (error.status === 0) {
                    alert('Network error: Please check your internet connection or server status.');
                } else {
                    alert('An error occurred while marking all notifications as read.');
                }
            }
        });
    };

    // Handle Clear All Notifications
    window.clearAllNotifications = function() {
        if (!confirm('Are you sure you want to delete all notifications?')) return;
        $.ajax({
            url: '/notifications/clear_all/',
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(data) {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Failed to clear notifications.');
                }
            },
            error: function(error) {
                console.error('Error:', error);
                if (error.status === 0) {
                    alert('Network error: Please check your internet connection or server status.');
                } else {
                    alert('An error occurred while clearing notifications.');
                }
            }
        });
    };

    // Poll for new notifications every 30 seconds
    setInterval(fetchNotifications, 30000);
});