from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth.models import User
from notifications.models import Notification
from .models import Transaction, MomoPayment, ProjectFund, CommissionTransaction
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def notify_transaction(sender, instance, created, update_fields, **kwargs):
    """
    Notify user when a transaction is completed or failed, only on status change.
    """
    if update_fields and "status" not in update_fields and not created:
        return  # Skip if status hasn't changed and not a new transaction

    try:
        user = instance.wallet.user
        if instance.status == "COMPLETED":
            Notification.objects.create(
                user=user,
                title=f"{instance.transaction_type.title()} Completed",
                message=f"Your {instance.transaction_type.lower()} of E{instance.amount} has been completed.",
                notification_type="wallet_transaction",
                link=reverse(
                    "wallets:transaction_status",
                    kwargs={"transaction_id": instance.reference_id},
                ),
            )
        elif instance.status == "FAILED":
            Notification.objects.create(
                user=user,
                title=f"{instance.transaction_type.title()} Failed",
                message=f"Your {instance.transaction_type.lower()} of E{instance.amount} failed: {instance.notes or 'Unknown error'}.",
                notification_type="wallet_transaction",
                link=reverse(
                    "wallets:transaction_status",
                    kwargs={"transaction_id": instance.reference_id},
                ),
            )
    except Exception as e:
        logger.error(
            f"Error in notify_transaction for transaction {instance.reference_id}: {str(e)}"
        )


@receiver(post_save, sender=MomoPayment)
def notify_momo_payment(sender, instance, update_fields, **kwargs):
    """
    Notify user of MoMo payment status changes, only if no Transaction notification.
    Skips if the linked Transaction will notify (e.g., DEPOSIT completion).
    """
    if update_fields and "payment_status" not in update_fields:
        return  # Skip if payment_status hasn't changed

    try:
        transaction = instance.transaction
        # Skip if Transaction will notify (e.g., DEPOSIT or WITHDRAWAL)
        if transaction.transaction_type in ["DEPOSIT", "WITHDRAWAL"]:
            return

        user = transaction.wallet.user
        phone_display = (
            instance.phone_number
            if instance.phone_number.startswith("+268")
            else f'+268{instance.phone_number.lstrip("0")}'
        )

        if instance.payment_status == "COMPLETED":
            Notification.objects.create(
                user=user,
                title="Mobile Money Payment Completed",
                message=f"Your MoMo payment of E{transaction.amount} from {phone_display} was successful.",
                notification_type="wallet_transaction",
                link=reverse(
                    "wallets:transaction_status",
                    kwargs={"transaction_id": transaction.reference_id},
                ),
            )
        elif instance.payment_status == "FAILED":
            Notification.objects.create(
                user=user,
                title="Mobile Money Payment Failed",
                message=f"Your MoMo payment of E{transaction.amount} from {phone_display} failed: {instance.error_message or 'Unknown error'}.",
                notification_type="wallet_transaction",
                link=reverse(
                    "wallets:transaction_status",
                    kwargs={"transaction_id": transaction.reference_id},
                ),
            )
    except Exception as e:
        logger.error(
            f"Error in notify_momo_payment for payment {instance.momo_transaction_id}: {str(e)}"
        )


@receiver(post_save, sender=ProjectFund)
def notify_project_fund(sender, instance, update_fields, **kwargs):
    """
    Notify freelancer and client when project funds are released.
    """
    if update_fields and "status" not in update_fields:
        return  # Skip if status hasn't changed

    try:
        if instance.status == "RELEASED":
            project = instance.project
            if not (project.freelancer and project.client):
                logger.warning(f"Missing freelancer or client for project {project.id}")
                return

            # Notify freelancer
            Notification.objects.create(
                user=project.freelancer,
                title="Project Funds Released",
                message=f"Funds of E{instance.amount - instance.commission_amount} for '{project.title}' have been released to your wallet.",
                notification_type="wallet_transaction",
                project=project,
                link=reverse("projects:project-detail", kwargs={"pk": project.id}),
            )
            # Notify client
            Notification.objects.create(
                user=project.client,
                title="Project Funds Released",
                message=f"Funds of E{instance.amount} for '{project.title}' have been released to the freelancer.",
                notification_type="wallet_transaction",
                project=project,
                link=reverse("projects:project-detail", kwargs={"pk": project.id}),
            )
    except Exception as e:
        logger.error(
            f"Error in notify_project_fund for project fund {instance.id}: {str(e)}"
        )


@receiver(post_save, sender=CommissionTransaction)
def notify_commission(sender, instance, created, **kwargs):
    """
    Notify all staff users when a commission is received.
    """
    if not created:
        return  # Only notify on creation

    try:
        staff_users = User.objects.filter(is_staff=True)
        if not staff_users.exists():
            logger.warning("No staff users found for commission notification")
            return

        for staff_user in staff_users:
            Notification.objects.create(
                user=staff_user,
                title="Commission Received",
                message=f"Commission of E{instance.amount} received for '{instance.project.title}' at {instance.rate*100}% rate.",
                notification_type="wallet_transaction",
                project=instance.project,
                link=reverse(
                    "projects:project-detail", kwargs={"pk": instance.project.id}
                ),
            )
    except Exception as e:
        logger.error(
            f"Error in notify_commission for commission {instance.id}: {str(e)}"
        )
