from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import (
    Profile,
    OperatorAssignment,
    Document,
    DocumentReview,
    GovernmentPermit,
)
from wallets.models import Wallet
from notifications.models import Notification
import logging
from django.utils import timezone

# Try to import channels for real-time notifications
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False

logger = logging.getLogger(__name__)


def send_admin_notification(message, notification_type, object_id=None, user=None):
    """Send notification to all admin users and real-time via channels."""
    try:
        # Create notifications for all admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title="Admin Notification",
                message=message,
                notification_type=notification_type,
            )

        # Send real-time notification via channels if available
        if CHANNELS_AVAILABLE:
            channel_layer = get_channel_layer()
            if channel_layer:
                payload = {
                    "type": "admin_notification",
                    "message": message,
                    "notification_type": notification_type,
                    "object_id": object_id,
                    "user": user.username if user else None,
                    "created_at": timezone.now().isoformat(),
                }
                async_to_sync(channel_layer.group_send)(
                    "admins", {"type": "notification_message", "payload": payload}
                )

        logger.info(f"Admin notification sent: {notification_type} - {message}")
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a Profile when a new User is created.

    Args:
        sender: The model class (User)
        instance: The actual instance being saved
        created: Boolean; True if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """
    Signal handler to save the Profile whenever the User is saved.

    Args:
        sender: The model class (User)
        instance: The actual instance being saved
        **kwargs: Additional keyword arguments
    """
    instance.profile.save()


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=OperatorAssignment)
def notify_operator_assignment(sender, instance, created, **kwargs):
    """
    Send notification when operator is assigned to a vehicle.
    """
    if created and instance.active:
        try:
            # Notify the operator about assignment
            Notification.objects.create(
                user=instance.operator,
                title="Vehicle Assignment",
                message=f"You have been assigned as operator for vehicle {instance.vehicle.plate_number}",
                notification_type="operator_assigned",
            )
            logger.info(
                f"Assignment notification sent to {instance.operator.username} "
                f"for vehicle {instance.vehicle.plate_number}"
            )

            # Send admin notification
            send_admin_notification(
                message=f"Operator {instance.operator.username} assigned to vehicle {instance.vehicle.plate_number} by {instance.assigned_by.username}",
                notification_type="operator_assignment_created",
                object_id=instance.id,
                user=instance.assigned_by,
            )

        except Exception as e:
            logger.error(f"Error sending assignment notification: {str(e)}")


@receiver(pre_save, sender=OperatorAssignment)
def notify_operator_removal(sender, instance, **kwargs):
    """
    Send notification when operator assignment is deactivated.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = OperatorAssignment.objects.get(pk=instance.pk)
            # Check if assignment is being deactivated
            if old_instance.active and not instance.active:
                # Notify the operator about removal
                Notification.objects.create(
                    user=instance.operator,
                    title="Vehicle Assignment Removed",
                    message=f"You have been removed as operator for vehicle {instance.vehicle.plate_number}",
                    notification_type="operator_removed",
                )
                logger.info(
                    f"Removal notification sent to {instance.operator.username} "
                    f"for vehicle {instance.vehicle.plate_number}"
                )

                # Send admin notification
                deactivated_by = getattr(instance, "deactivated_by", None) or "System"
                send_admin_notification(
                    message=f"Operator {instance.operator.username} removed from vehicle {instance.vehicle.plate_number} by {deactivated_by}",
                    notification_type="operator_assignment_removed",
                    object_id=instance.id,
                    user=(
                        deactivated_by if hasattr(deactivated_by, "username") else None
                    ),
                )

        except OperatorAssignment.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error sending removal notification: {str(e)}")


@receiver(post_save, sender=Document)
def create_document_review(sender, instance, created, **kwargs):
    """
    Automatically create a DocumentReview when a Document is uploaded.
    """
    if created:
        try:
            # Create or get existing review to prevent UNIQUE constraint violations
            review, created = DocumentReview.objects.get_or_create(
                document=instance, defaults={"status": "PENDING"}
            )
            if created:
                logger.info(
                    f"DocumentReview auto-created for {instance.get_doc_type_display()} "
                    f"uploaded by {instance.user.username}"
                )
            else:
                logger.debug(
                    f"DocumentReview already exists for {instance.get_doc_type_display()} "
                    f"uploaded by {instance.user.username}"
                )

            # Send admin notification for document upload
            doc_type = instance.get_doc_type_display()
            if instance.vehicle:
                message = f"New {doc_type} uploaded by {instance.user.username} for vehicle {instance.vehicle}"
            else:
                message = f"New {doc_type} uploaded by {instance.user.username}"

            send_admin_notification(
                message=message,
                notification_type="document_uploaded",
                object_id=instance.id,
                user=instance.user,
            )

        except Exception as e:
            logger.error(
                f"Error creating DocumentReview for document {instance.id}: {str(e)}"
            )


@receiver(post_save, sender=DocumentReview)
def update_transport_owner_tag_on_review(sender, instance, **kwargs):
    """
    Update Transport Owner tag when document review status changes.
    """
    try:
        if instance.document.user:
            instance.document.user.profile.update_transport_owner_tag()
            logger.debug(
                f"Updated transport owner tag for {instance.document.user.username} "
                f"after document review change"
            )
    except Exception as e:
        logger.error(f"Error updating transport owner tag on review: {str(e)}")


@receiver(post_save, sender=GovernmentPermit)
def notify_permit_created(sender, instance, created, **kwargs):
    """
    Send admin notification when a government permit is created.
    """
    if created:
        try:
            # Send admin notification
            send_admin_notification(
                message=f"New {instance.get_permit_type_display()} permit {instance.permit_number} created by {instance.profile.user.username}",
                notification_type="permit_created",
                object_id=instance.id,
                user=instance.profile.user,
            )
        except Exception as e:
            logger.error(f"Error sending permit creation notification: {str(e)}")
