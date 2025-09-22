// filepath: /home/ncaba/Desktop/SwaziCore Innovations/LusitoHub/lusito_app/static/js/notifications.js
document.addEventListener('DOMContentLoaded', function() {
    const notificationItems = document.querySelectorAll('.dropdown-item');

    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.dataset.notificationId;

            fetch(`/mark_notification_as_read/${notificationId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })

            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.classList.add('read');
                }
            })
            .catch(error => {
                console.error('Error marking notification as read:', error);
            });
        });
    });
});