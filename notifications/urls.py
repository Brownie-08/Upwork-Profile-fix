from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("notifications/", views.notifications_page, name="notifications_page"),
    path(
        "notifications/unread/",
        views.get_unread_notifications,
        name="get_unread_notifications",
    ),
    path(
        "notifications/mark_read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-as-read/",
        views.mark_as_read,
        name="mark_as_read",
    ),
    path(
        "notifications/mark_all_read/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
    path(
        "notifications/<int:notification_id>/delete/",
        views.delete_notification,
        name="delete_notification",
    ),
    path(
        "notifications/clear_all/",
        views.clear_all_notifications,
        name="clear_all_notifications",
    ),
    # Handle legacy/incorrect notification URL patterns
    path(
        "mark_notification_as_read/<str:notification_id>/",
        views.handle_legacy_mark_read,
        name="legacy_mark_read",
    ),
]
