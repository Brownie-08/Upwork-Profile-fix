from django.db import models
from django.contrib.auth.models import User
from projects.models import Project, Proposal
from django.utils import timezone


def message_attachment_path(instance, filename):
    return f"chat_attachments/{instance.message.chatroom.id}/{timezone.now().timestamp()}_{filename}"


class ChatRoom(models.Model):
    PROJECT_STATUS_CHOICES = [
        ("DISCUSSION", "In Discussion"),
        ("IN_PROGRESS", "Project In Progress"),
        ("REVIEW", "Under Review"),
        ("COMPLETED", "Completed"),
        ("DISPUTED", "In Dispute"),
    ]

    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="client_chats"
    )
    freelancer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="freelancer_chats"
    )
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="chat_room"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(auto_now=True)
    project_status = models.CharField(
        max_length=20, choices=PROJECT_STATUS_CHOICES, default="DISCUSSION"
    )
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at"]

    last_milestone_message = models.ForeignKey(
        "Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="latest_milestone_chat",
    )

    def sync_project_status(self):
        status_mapping = {
            "OPEN": "DISCUSSION",
            "IN_PROGRESS": "IN_PROGRESS",
            "COMPLETED": "COMPLETED",
            "DISPUTED": "DISPUTED",
        }
        self.project_status = status_mapping.get(self.project.status, "DISCUSSION")
        self.save()

    def __str__(self):
        return f"Chat: {self.client.username} - {self.freelancer.username} ({self.project.title})"


class Message(models.Model):
    MESSAGE_TYPES = [
        ("REGULAR", "Regular Message"),
        ("MILESTONE", "Milestone Update"),
        ("PAYMENT", "Payment Discussion"),
        ("DELIVERY", "Project Delivery"),
        ("REVISION", "Revision Request"),
        ("AGREEMENT", "Agreement/Terms"),
        ("STATUS_CHANGE", "Project Status Change"),
        ("FILE_SHARE", "File Shared"),
        ("PROPOSAL", "Proposal Discussion"),
    ]

    chatroom = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="REGULAR"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_by = models.ManyToManyField(User, related_name="read_messages", blank=True)
    has_attachment = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    related_milestone = models.ForeignKey(
        "ProjectMilestone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_messages",
    )

    related_proposal = models.ForeignKey(
        Proposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_messages",
    )

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"


class MessageAttachment(models.Model):
    ATTACHMENT_CATEGORIES = [
        ("PROPOSAL", "Project Proposal"),
        ("CONTRACT", "Contract/Agreement"),
        ("DELIVERABLE", "Project Deliverable"),
        ("REVISION", "Revision File"),
        ("REFERENCE", "Reference Material"),
        ("OTHER", "Other"),
    ]

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=message_attachment_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20, choices=ATTACHMENT_CATEGORIES, default="OTHER"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)


class ProjectMilestone(models.Model):
    chatroom = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="milestones"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    associated_files = models.ManyToManyField(
        MessageAttachment, related_name="milestone_files", blank=True
    )

    def mark_as_completed(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

        Message.objects.create(
            chatroom=self.chatroom,
            message_type="MILESTONE",
            content=f'Milestone "{self.title}" has been marked as completed.',
            sender=self.chatroom.freelancer,
            related_milestone=self,
        )

    def __str__(self):
        return f"{self.title} - {self.chatroom.project.title}"
