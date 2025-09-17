from django.contrib import admin
from .models import ChatRoom, Message, ProjectMilestone


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("client", "freelancer", "project", "project_status", "created_at")
    readonly_fields = (
        "client",
        "freelancer",
        "project",
        "project_status",
        "created_at",
    )
    list_filter = ("project_status", "is_active")
    search_fields = ("client__username", "freelancer__username", "project__title")


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "chatroom", "due_date", "amount", "is_completed")
    readonly_fields = ("title", "chatroom", "due_date", "amount", "is_completed")
    list_filter = ("is_completed", "due_date")
    search_fields = ("title", "description")


class MessageInline(admin.TabularInline):
    model = Message
    readonly_fields = ("sender", "content", "timestamp", "is_read")
    can_delete = False
    extra = 0
