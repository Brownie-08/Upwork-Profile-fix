from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth.models import User
from notifications.models import Notification
from .models import Project, Proposal, Review, Rating


@receiver(post_save, sender=Project)
def notify_project_created(sender, instance, created, **kwargs):
    if created and instance.service_type != "TAXI":  # Exclude taxi projects
        # Notify freelancers with matching service types
        freelancers = User.objects.filter(
            profile__account_type=instance.service_type, profile__is_verified=True
        )
        for freelancer in freelancers:
            Notification.objects.create(
                user=freelancer,
                title="New Project Available",
                message=f"A new {instance.get_service_type_display()} project '{instance.title}' has been posted.",
                notification_type="project_created",
                project=instance,
                link=reverse("project-detail", args=[instance.id]),
            )


@receiver(post_save, sender=Proposal)
def notify_project_proposal(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.project.client,
            title="New Proposal Received",
            message=f"{instance.freelancer.profile.get_full_name()} submitted a proposal for '{instance.project.title}'.",
            notification_type="project_proposal",
            project=instance.project,
            link=reverse("project-detail", args=[instance.project.id]),
        )


@receiver(post_save, sender=Proposal)
def notify_proposal_accepted(sender, instance, **kwargs):
    if instance.accepted and instance.project.status == "IN_PROGRESS":
        Notification.objects.create(
            user=instance.freelancer,
            title="Proposal Accepted",
            message=f"Your proposal for '{instance.project.title}' was accepted!",
            notification_type="project_proposal_accepted",
            project=instance.project,
            link=reverse("project-detail", args=[instance.project.id]),
        )
        Notification.objects.create(
            user=instance.project.client,
            title="Proposal Accepted",
            message=f"You accepted {instance.freelancer.profile.get_full_name()}'s proposal for '{instance.project.title}'.",
            notification_type="project_proposal_accepted",
            project=instance.project,
            link=reverse("project-detail", args=[instance.project.id]),
        )


@receiver(post_save, sender=Project)
def notify_project_status_update(sender, instance, **kwargs):
    if instance.status in ["IN_PROGRESS", "REVIEW", "COMPLETED", "DISPUTED"]:
        recipients = [instance.client]
        if instance.freelancer:
            recipients.append(instance.freelancer)
        for user in recipients:
            Notification.objects.create(
                user=user,
                title=f"Project {instance.status.title()}",
                message=f"The project '{instance.title}' is now {instance.status.lower()}.",
                notification_type="project_status_update",
                project=instance,
                link=reverse("project-detail", args=[instance.id]),
            )


@receiver(post_save, sender=Review)
def notify_project_review(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.recipient,
            title="New Review Received",
            message=f"{instance.reviewer.profile.get_full_name()} left a review for '{instance.project.title}'.",
            notification_type="project_review",
            project=instance.project,
            link=reverse("project-detail", args=[instance.project.id]),
        )


@receiver(post_save, sender=Rating)
def notify_project_rating(sender, instance, created, **kwargs):
    if created:
        recipient = (
            instance.project.freelancer
            if instance.rater_type == "CLIENT"
            else instance.project.client
        )
        Notification.objects.create(
            user=recipient,
            title="New Rating Received",
            message=f"{instance.rated_by.profile.get_full_name()} rated the project '{instance.project.title}' {instance.rating} stars.",
            notification_type="project_rating",
            project=instance.project,
            link=reverse("project-detail", args=[instance.project.id]),
        )
