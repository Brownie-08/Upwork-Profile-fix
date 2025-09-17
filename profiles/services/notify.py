from django.core.mail import send_mail
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)


def notify_email(user, subject, body):
    """
    Send email notification to user.

    Args:
        user: Django User instance
        subject (str): Email subject
        body (str): Email body text
    """
    if not getattr(user, "email", None):
        print(f"[NOTIFY] User {user} has no email address")
        return

    try:
        send_mail(
            subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True
        )
        print(f"[EMAIL] Sent to {user.email}: {subject}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {user.email}: {e}")


def notify_sms(user, text):
    """
    Send SMS notification to user.

    Args:
        user: Django User instance
        text (str): SMS message text
    """
    # Try different possible phone number fields
    phone = (
        getattr(user, "phone_number", None)
        or getattr(user, "phone", None)
        or getattr(user, "mobile", None)
    )

    if not phone:
        print(f"[NOTIFY] User {user} has no phone number")
        return

    from profiles.integrations.sms import send_sms

    send_sms(phone, text)


def notify_inapp(user, message):
    """
    Send in-app notification to user.

    Args:
        user: Django User instance
        message (str): Notification message

    Returns:
        Notification: The created notification instance
    """
    try:
        from notifications.models import Notification
        from django.db import transaction

        # Create the notification
        notification = Notification.objects.create(
            user=user, message=message, is_read=False
        )

        print(f"[INAPP] Created notification for {user.username}: {message[:50]}...")
        return notification

    except Exception as e:
        print(f"[INAPP ERROR] Failed to create notification for {user}: {e}")
        return None


def mark_as_read(notification_or_queryset):
    """
    Mark notification(s) as read.

    Args:
        notification_or_queryset: Single Notification instance or QuerySet of notifications

    Returns:
        int: Number of notifications marked as read
    """
    try:
        from notifications.models import Notification

        if hasattr(notification_or_queryset, "update"):  # It's a QuerySet
            count = notification_or_queryset.update(is_read=True)
            print(f"[NOTIFY] Marked {count} notifications as read")
            return count
        else:  # It's a single notification
            notification_or_queryset.is_read = True
            notification_or_queryset.save()
            print(f"[NOTIFY] Marked notification {notification_or_queryset.id} as read")
            return 1

    except Exception as e:
        print(f"[NOTIFY ERROR] Failed to mark notifications as read: {e}")
        return 0


def bulk_notify(users, message, notification_type=None):
    """
    Send in-app notifications to multiple users.

    Args:
        users: Iterable of Django User instances
        message (str): Notification message
        notification_type (str): Optional type for categorization

    Returns:
        list: List of created Notification instances
    """
    notifications = []

    try:
        from notifications.models import Notification

        for user in users:
            try:
                notification = Notification.objects.create(
                    user=user, message=message, is_read=False
                )
                notifications.append(notification)
            except Exception as e:
                print(f"[BULK_NOTIFY ERROR] Failed to notify {user}: {e}")

        print(f"[BULK_NOTIFY] Created {len(notifications)} notifications")
        return notifications

    except Exception as e:
        print(f"[BULK_NOTIFY ERROR] Failed to bulk notify: {e}")
        return notifications


def notify_all(user, message, send_email=False, send_sms=False):
    """
    Send notifications via multiple channels.

    Args:
        user: Django User instance
        message (str): Notification message
        send_email (bool): Whether to send email notification
        send_sms (bool): Whether to send SMS notification

    Returns:
        dict: Results from each notification channel
    """
    results = {"inapp": None, "email": None, "sms": None}

    # Always send in-app notification
    results["inapp"] = notify_inapp(user, message)

    # Send email if requested
    if send_email:
        subject = "Notification from LusitoHub"
        try:
            results["email"] = notify_email(user, subject, message)
        except Exception as e:
            print(f"[NOTIFY_ALL ERROR] Email failed: {e}")

    # Send SMS if requested
    if send_sms:
        try:
            results["sms"] = notify_sms(user, message)
        except Exception as e:
            print(f"[NOTIFY_ALL ERROR] SMS failed: {e}")

    return results


def notify_admins(notification_type, message, payload=None):
    """
    Send real-time notification to all connected admin users via WebSocket.

    Args:
        notification_type (str): Type of notification (e.g., 'permit_created', 'document_uploaded')
        message (str): Human-readable notification message
        payload (dict, optional): Additional data to include in the notification

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    try:
        from datetime import datetime
        import json

        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("[ADMIN_NOTIFY] No channel layer configured")
            return False

        # Ensure payload is JSON-serializable and doesn't contain sensitive data
        safe_payload = {}
        if payload:
            try:
                # Test JSON serialization and filter out sensitive data
                for key, value in payload.items():
                    # Skip potentially sensitive fields
                    if key.lower() in ["password", "token", "secret", "key", "csrf"]:
                        continue
                    # Only include JSON-serializable values
                    try:
                        json.dumps(value)
                        safe_payload[key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable values to strings
                        safe_payload[key] = str(value)
            except Exception as e:
                logger.warning(f"[ADMIN_NOTIFY] Error processing payload: {e}")

        # Prepare the notification data with server-side timestamp
        data = {
            "type": "admin_notification",
            "notification_type": notification_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC ISO string
            **safe_payload,
        }

        # Send to the admins group
        async_to_sync(channel_layer.group_send)(
            "admins", {"type": "notification_message", "payload": data}
        )

        logger.debug(
            f"[ADMIN_NOTIFY] Sent {notification_type} notification: {message[:100]}..."
        )
        return True

    except Exception as e:
        logger.error(f"[ADMIN_NOTIFY ERROR] Failed to send notification: {e}")
        return False
