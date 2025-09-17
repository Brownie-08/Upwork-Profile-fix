from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from transport.models import TransportRequest
from projects.models import Project
from wallets.models import Transaction
from chat.models import Message


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("profile_completion", "Profile Completion"),
        ("admin_reminder", "Admin Reminder"),
        ("chat_message", "Chat Message"),
        ("milestone_due", "Milestone Due Soon"),
        ("file_uploaded", "File Uploaded"),
        ("proposal_update", "Proposal Updated"),
        ("status_change", "Project Status Changed"),
        ("review_requested", "Review Requested"),
        ("project_update", "Project Update"),
        ("wallet_transaction", "Wallet Transaction"),
        ("project_fund", "Project Fund Update"),
        ("transport_bid_submitted", "Bid Submitted"),
        ("transport_bid_accepted", "Bid Accepted"),
        ("transport_contract_confirmed", "Contract Confirmed"),
        ("transport_job_status_updated", "Job Status Updated"),
        ("transport_job_deleted", "Job Deleted"),
        ("project_created", "Project Created"),
        ("project_proposal", "Project Proposal"),
        ("project_proposal_accepted", "Proposal Accepted"),
        ("project_status_update", "Project Status Update"),
        ("project_review", "Project Review"),
        ("project_rating", "Project Rating"),
        ("document_approved", "Document Approved"),
        ("document_rejected", "Document Rejected"),
        ("general", "General Notification"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_notifications"
    )
    title = models.CharField(max_length=255, blank=True, default="")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(
        max_length=50, choices=NOTIFICATION_TYPES, default="general"
    )
    link = models.URLField(blank=True, null=True)
    transport_request = models.ForeignKey(
        TransportRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    chat_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    @classmethod
    def create_simple(cls, user, message, notification_type="general", title=None):
        """
        Create a simple notification with minimal required fields.
        Compatible with profiles.Notification usage.
        """
        if not title:
            title = message[:50] + "..." if len(message) > 50 else message

        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
        )

    def __str__(self):
        if self.title:
            return f"{self.title} - {self.user.username}"
        else:
            return f"Notification for {self.user.username} - {self.message[:50]}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["notification_type"]),
        ]


class AdminReminder(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_reminders"
    )
    created_at = models.DateTimeField(default=timezone.now)
    recipients = models.ManyToManyField(
        User, related_name="received_reminders", blank=True
    )
    send_to_all = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} by {self.created_by}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.sent_at:
            self.sent_at = timezone.now()
            self.save()
            # Create notifications for recipients
            users = User.objects.all() if self.send_to_all else self.recipients.all()
            for user in users:
                Notification.objects.create(
                    user=user,
                    title=self.title,
                    message=self.message,
                    notification_type="admin_reminder",
                )
