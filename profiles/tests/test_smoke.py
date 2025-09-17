"""
Smoke tests to verify basic functionality and test setup.
"""

from django.test import TestCase
from django.contrib.auth.models import User


def test_smoke():
    """Basic smoke test to verify pytest is working."""
    assert 1 + 1 == 2


class SmokeTestCase(TestCase):
    """Django smoke tests to verify basic functionality."""

    def test_django_setup(self):
        """Test that Django is properly configured."""
        self.assertTrue(True)

    def test_user_creation(self):
        """Test that we can create a user."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")


def test_imports():
    """Test that our stub services can be imported without errors."""
    from profiles.services import otp, notify
    from profiles.integrations import sms

    # Test that the functions exist
    assert hasattr(otp, "create_otp")
    assert hasattr(otp, "verify_otp")
    assert hasattr(notify, "notify_email")
    assert hasattr(notify, "notify_sms")
    assert hasattr(notify, "notify_inapp")
    assert hasattr(sms, "send_sms")
