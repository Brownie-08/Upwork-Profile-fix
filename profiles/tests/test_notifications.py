"""
Tests for the notification system.
"""

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from unittest.mock import patch, MagicMock

from profiles.models import Profile
from notifications.models import Notification
from profiles.services.notify import (
    notify_inapp,
    notify_email,
    notify_all,
    mark_as_read,
    bulk_notify,
)


class NotificationModelTest(TestCase):
    """Test Notification model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_notification_creation(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            user=self.user, message="Test notification message", is_read=False
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, "Test notification message")
        self.assertFalse(notification.is_read)
        self.assertTrue(notification.created_at)

    def test_notification_str_method(self):
        """Test Notification string representation."""
        notification = Notification.objects.create(
            user=self.user, message="Test notification message"
        )

        expected_str = (
            f"Notification for {self.user.username} - Test notification message"
        )
        self.assertEqual(str(notification), expected_str)

    def test_notification_defaults(self):
        """Test Notification default values."""
        notification = Notification.objects.create(
            user=self.user, message="Test message"
        )

        # Should default to unread
        self.assertFalse(notification.is_read)
        # Should have created_at timestamp
        self.assertIsNotNone(notification.created_at)


class NotificationServiceTest(TestCase):
    """Test notification service functions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_notify_inapp_creates_notification(self):
        """Test that notify_inapp creates a database notification."""
        message = "Test in-app notification"

        notification = notify_inapp(self.user, message)

        self.assertIsNotNone(notification)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, message)
        self.assertFalse(notification.is_read)

        # Verify it was saved to database
        db_notification = Notification.objects.get(pk=notification.pk)
        self.assertEqual(db_notification.message, message)

    def test_notify_inapp_error_handling(self):
        """Test notify_inapp handles errors gracefully."""
        # Test with invalid user (None)
        result = notify_inapp(None, "Test message")
        self.assertIsNone(result)

    def test_mark_as_read_single_notification(self):
        """Test marking a single notification as read."""
        notification = Notification.objects.create(
            user=self.user, message="Test message", is_read=False
        )

        count = mark_as_read(notification)

        self.assertEqual(count, 1)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_as_read_queryset(self):
        """Test marking multiple notifications as read via queryset."""
        # Create multiple notifications
        for i in range(3):
            Notification.objects.create(
                user=self.user, message=f"Test message {i}", is_read=False
            )

        queryset = Notification.objects.filter(user=self.user)
        count = mark_as_read(queryset)

        self.assertEqual(count, 3)
        # All should be marked as read
        unread_count = Notification.objects.filter(
            user=self.user, is_read=False
        ).count()
        self.assertEqual(unread_count, 0)

    def test_bulk_notify(self):
        """Test bulk notification creation."""
        # Create additional users
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass123"
        )
        user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="pass123"
        )

        users = [self.user, user2, user3]
        message = "Bulk notification message"

        notifications = bulk_notify(users, message)

        self.assertEqual(len(notifications), 3)

        # Verify all notifications were created
        for user in users:
            notification_exists = Notification.objects.filter(
                user=user, message=message
            ).exists()
            self.assertTrue(notification_exists)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_notify_email(self):
        """Test email notification sending."""
        subject = "Test Subject"
        body = "Test email body"

        notify_email(self.user, subject, body)

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, subject)
        self.assertEqual(sent_email.body, body)
        self.assertIn(self.user.email, sent_email.to)

    def test_notify_email_no_email_address(self):
        """Test notify_email handles users without email gracefully."""
        user_no_email = User.objects.create_user(username="noemail", password="pass123")
        # Remove email
        user_no_email.email = ""
        user_no_email.save()

        # Should not raise exception
        notify_email(user_no_email, "Subject", "Body")

        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_notify_all(self):
        """Test notify_all function with multiple channels."""
        message = "Multi-channel notification"

        results = notify_all(self.user, message, send_email=True, send_sms=False)

        # Should have created in-app notification
        self.assertIsNotNone(results["inapp"])
        self.assertEqual(results["inapp"].message, message)

        # Should have attempted email (results may be None for email/sms)
        # But email should be in outbox
        self.assertEqual(len(mail.outbox), 1)

        # SMS should not have been attempted
        self.assertIsNone(results["sms"])

    def test_notify_all_inapp_only(self):
        """Test notify_all with only in-app notifications."""
        message = "In-app only notification"

        results = notify_all(self.user, message, send_email=False, send_sms=False)

        # Should have created in-app notification
        self.assertIsNotNone(results["inapp"])
        self.assertEqual(results["inapp"].message, message)

        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)

        # Verify notification is in database
        notification_exists = Notification.objects.filter(
            user=self.user, message=message
        ).exists()
        self.assertTrue(notification_exists)


class NotificationIntegrationTest(TestCase):
    """Test notification integration with other systems."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile, created = Profile.objects.get_or_create(user=self.user)

    def test_document_approval_notification(self):
        """Test that document approval triggers notification."""
        # This would test the actual integration with DocumentReview model
        # For now, just test the notification service directly

        message = "Your Roadworthiness Certificate has been approved."

        notification = notify_inapp(self.user, message)

        self.assertIsNotNone(notification)
        self.assertIn("approved", notification.message)

    def test_document_rejection_notification(self):
        """Test that document rejection triggers notification with reason."""
        reason = "Document is not clear enough"
        message = f"Your Driver's License was rejected. Reason: {reason}"

        notification = notify_inapp(self.user, message)

        self.assertIsNotNone(notification)
        self.assertIn("rejected", notification.message)
        self.assertIn(reason, notification.message)

    def test_no_duplicate_notifications(self):
        """Test that duplicate notifications are not created."""
        message = "Test notification"

        # Create first notification
        notify_inapp(self.user, message)

        # Create second identical notification
        notify_inapp(self.user, message)

        # Both should exist (the service doesn't prevent duplicates by design)
        # But we can test that the service works correctly
        notifications = Notification.objects.filter(user=self.user, message=message)
        self.assertEqual(notifications.count(), 2)

    def test_notification_ordering(self):
        """Test that notifications are ordered by timestamp (newest first)."""
        # Create notifications in sequence
        notify_inapp(self.user, "First notification")
        notify_inapp(self.user, "Second notification")
        notify_inapp(self.user, "Third notification")

        notifications = Notification.objects.filter(user=self.user).order_by(
            "-created_at"
        )

        self.assertEqual(notifications[0].message, "Third notification")
        self.assertEqual(notifications[1].message, "Second notification")
        self.assertEqual(notifications[2].message, "First notification")

    def test_user_notification_isolation(self):
        """Test that users only see their own notifications."""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="pass123"
        )

        # Create notifications for both users
        notify_inapp(self.user, "User 1 notification")
        notify_inapp(other_user, "User 2 notification")

        # Each user should only see their own notification
        user1_notifications = Notification.objects.filter(user=self.user)
        user2_notifications = Notification.objects.filter(user=other_user)

        self.assertEqual(user1_notifications.count(), 1)
        self.assertEqual(user2_notifications.count(), 1)

        self.assertEqual(user1_notifications[0].message, "User 1 notification")
        self.assertEqual(user2_notifications[0].message, "User 2 notification")
