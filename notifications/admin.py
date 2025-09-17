from django.contrib import admin
from .models import Notification, AdminReminder


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read"]
    search_fields = ["title", "message", "user__username"]


@admin.register(AdminReminder)
class AdminReminderAdmin(admin.ModelAdmin):
    list_display = ["title", "created_by", "sent_at", "send_to_all"]
    filter_horizontal = ["recipients"]
    search_fields = ["title", "message"]

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
