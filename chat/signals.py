from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from notifications.models import Notification
from .models import Message, MessageAttachment, ProjectMilestone
from django.utils import timezone
from datetime import timedelta


@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        recipient = (
            instance.chatroom.client
            if instance.sender == instance.chatroom.freelancer
            else instance.chatroom.freelancer
        )
        Notification.objects.create(
            user=recipient,
            title="New Chat Message",
            message=f"{instance.sender.profile.get_full_name()} sent a message in '{instance.chatroom.project.title}': {instance.content[:50]}...",
            notification_type="chat_message",
            project=instance.chatroom.project,
            chat_message=instance,
            link=reverse("chats:chatroom", args=[instance.chatroom.id]),
        )
        if instance.message_type == "STATUS_CHANGE":
            Notification.objects.create(
                user=recipient,
                title="Project Status Changed",
                message=f"The project '{instance.chatroom.project.title}' status changed: {instance.content[:50]}...",
                notification_type="status_change",
                project=instance.chatroom.project,
                chat_message=instance,
                link=reverse("chats:chatroom", args=[instance.chatroom.id]),
            )
        elif instance.message_type == "PROPOSAL" and instance.related_proposal:
            Notification.objects.create(
                user=recipient,
                title="Proposal Updated",
                message=f"{instance.sender.profile.get_full_name()} updated a proposal for '{instance.chatroom.project.title}'.",
                notification_type="proposal_update",
                project=instance.chatroom.project,
                chat_message=instance,
                link=reverse("chats:chatroom", args=[instance.chatroom.id]),
            )
        elif instance.message_type == "DELIVERY":
            Notification.objects.create(
                user=recipient,
                title="Review Requested",
                message=f"{instance.sender.profile.get_full_name()} requested a review for '{instance.chatroom.project.title}'.",
                notification_type="review_requested",
                project=instance.chatroom.project,
                chat_message=instance,
                link=reverse("chats:chatroom", args=[instance.chatroom.id]),
            )


@receiver(post_save, sender=MessageAttachment)
def notify_file_uploaded(sender, instance, created, **kwargs):
    if created:
        recipient = (
            instance.message.chatroom.client
            if instance.message.sender == instance.message.chatroom.freelancer
            else instance.message.chatroom.freelancer
        )
        Notification.objects.create(
            user=recipient,
            title="File Uploaded",
            message=f"{instance.message.sender.profile.get_full_name()} uploaded a file ({instance.file_name}) in '{instance.message.chatroom.project.title}'.",
            notification_type="file_uploaded",
            project=instance.message.chatroom.project,
            chat_message=instance.message,
            link=reverse("chats:chatroom", args=[instance.message.chatroom.id]),
        )


@receiver(post_save, sender=ProjectMilestone)
def notify_milestone_update(sender, instance, created, **kwargs):
    if not created and instance.is_completed:
        recipients = [instance.chatroom.client, instance.chatroom.freelancer]
        for recipient in recipients:
            Notification.objects.create(
                user=recipient,
                title="Milestone Completed",
                message=f"Milestone '{instance.title}' in '{instance.chatroom.project.title}' has been completed.",
                notification_type="milestone_due",
                project=instance.chatroom.project,
                link=reverse("chats:chatroom", args=[instance.chatroom.id]),
            )


@receiver(post_save, sender=ProjectMilestone)
def notify_milestone_due_soon(sender, instance, created, **kwargs):
    if created and instance.due_date:
        now = timezone.now()
        due_soon = instance.due_date - timedelta(days=1)
        if now.date() >= due_soon.date() and not instance.is_completed:
            recipients = [instance.chatroom.client, instance.chatroom.freelancer]
            for recipient in recipients:
                Notification.objects.create(
                    user=recipient,
                    title="Milestone Due Soon",
                    message=f"Milestone '{instance.title}' in '{instance.chatroom.project.title}' is due on {instance.due_date.strftime('%Y-%m-%d')}.",
                    notification_type="milestone_due",
                    project=instance.chatroom.project,
                    link=reverse("chats:chatroom", args=[instance.chatroom.id]),
                )
