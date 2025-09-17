from django.contrib import admin
from projects.models import Project


@admin.register(Project)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "freelancer",
        "client",
        "status",
        "budget",
        "start_date",
        "deadline",
        "completion_date",
    ]
    list_filter = ["status", "created_at", "freelancer"]
    search_fields = ["title", "description", "user__username"]
    readonly_fields = [
        "title",
        "freelancer",
        "client",
        "status",
        "budget",
        "start_date",
        "deadline",
        "completion_date",
    ]
    fieldsets = (
        (None, {"fields": ("title", "description", "freelancer", "client", "status")}),
        ("Financial Details", {"fields": ("budget", "final_payment")}),
        ("Dates", {"fields": ("start_date", "deadline", "completion_date")}),
        ("Additional Info", {"fields": ("rating", "created_at")}),
    )
