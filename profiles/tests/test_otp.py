"""
Tests for OTP (One-Time Password) functionality including account verification 
and password reset flows.
"""

import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core import mail

from profiles.models import LoginOTP, Profile
from profiles.services.otp import OTPService


class OTPServiceTestCase(TestCase):
    """Test the OTP service functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_active=False,
        )
        self.profile, created = Profile.objects.get_or_create(user=self.user)

    def test_generate_otp_code(self):
        """Test OTP code generation."""
        code = LoginOTP.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    @patch("profiles.services.otp.OTPService._send_email_otp")
    def test_create_otp_success(self, mock_email):
        """Test successful OTP creation."""
        mock_email.return_value = True

        otp = OTPService.create_otp(self.user, "VERIFY", "EMAIL")

        self.assertIsNotNone(otp)
        self.assertEqual(otp.user, self.user)
        self.assertEqual(otp.purpose, "VERIFY")
        self.assertEqual(otp.channel, "EMAIL")
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.verified)
        self.assertEqual(otp.attempts, 0)

        # Check expiry time (should be ~5 minutes from now)
        now = timezone.now()
        self.assertTrue(otp.expires_at > now)
        self.assertTrue(otp.expires_at <= now + timedelta(minutes=6))

        mock_email.assert_called_once()

    @patch("profiles.services.otp.OTPService._send_email_otp")
    def test_create_otp_email_failure(self, mock_email):
        """Test OTP creation when email sending fails."""
        mock_email.return_value = False

        otp = OTPService.create_otp(self.user, "VERIFY", "EMAIL")

        self.assertIsNone(otp)
        mock_email.assert_called_once()
        # Ensure no OTP record was saved
        self.assertEqual(LoginOTP.objects.count(), 0)

    @patch("profiles.services.otp.OTPService._send_email_otp")
    def test_create_otp_cooldown_active(self, mock_email):
        """Test OTP creation during cooldown period."""
        mock_email.return_value = True

        # Create first OTP
        otp1 = OTPService.create_otp(self.user, "VERIFY", "EMAIL")
        self.assertIsNotNone(otp1)

        # Try to create another immediately (should be blocked by cooldown)
        otp2 = OTPService.create_otp(self.user, "VERIFY", "EMAIL")
        self.assertIsNone(otp2)

        # Should only have called email once
        self.assertEqual(mock_email.call_count, 1)

    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        # Create OTP manually to control the code
        otp = LoginOTP.objects.create(
            user=self.user,
            code="123456",
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        success, message = OTPService.verify_otp(self.user, "123456", "VERIFY")

        self.assertTrue(success)
        self.assertEqual(message, "OTP verified successfully.")

        # Check OTP is marked as verified
        otp.refresh_from_db()
        self.assertTrue(otp.verified)
        self.assertEqual(otp.attempts, 1)

        # Check user is activated for VERIFY purpose
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_verify_otp_incorrect_code(self):
        """Test OTP verification with incorrect code."""
        otp = LoginOTP.objects.create(
            user=self.user,
            code="123456",
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        success, message = OTPService.verify_otp(self.user, "654321", "VERIFY")

        self.assertFalse(success)
        self.assertIn("Invalid OTP", message)
        self.assertIn("4 attempts remaining", message)

        otp.refresh_from_db()
        self.assertFalse(otp.verified)
        self.assertEqual(otp.attempts, 1)

    def test_verify_otp_expired(self):
        """Test OTP verification with expired code."""
        otp = LoginOTP.objects.create(
            user=self.user,
            code="123456",
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() - timedelta(minutes=1),  # Expired
        )

        success, message = OTPService.verify_otp(self.user, "123456", "VERIFY")

        self.assertFalse(success)
        self.assertEqual(message, "OTP has expired. Please request a new one.")

        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)

    def test_verify_otp_max_attempts_exceeded(self):
        """Test OTP verification when max attempts exceeded."""
        otp = LoginOTP.objects.create(
            user=self.user,
            code="123456",
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=5,  # Already at max
        )

        success, message = OTPService.verify_otp(self.user, "123456", "VERIFY")

        self.assertFalse(success)
        self.assertEqual(
            message, "Maximum attempts exceeded. Please request a new OTP."
        )

        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 6)

    def test_verify_otp_no_otp_found(self):
        """Test OTP verification when no OTP exists."""
        success, message = OTPService.verify_otp(self.user, "123456", "VERIFY")

        self.assertFalse(success)
        self.assertEqual(message, "No valid OTP found. Please request a new one.")

    def test_can_resend_otp_true(self):
        """Test can_resend_otp returns True when enough time passed."""
        # Create OTP more than 60 seconds ago
        old_time = timezone.now() - timedelta(seconds=70)
        with patch("django.utils.timezone.now", return_value=old_time):
            LoginOTP.objects.create(
                user=self.user,
                code="123456",
                purpose="VERIFY",
                channel="EMAIL",
                expires_at=old_time + timedelta(minutes=5),
            )

        can_resend, cooldown = OTPService.can_resend_otp(self.user, "VERIFY")

        self.assertTrue(can_resend)
        self.assertEqual(cooldown, 0)

    def test_can_resend_otp_false(self):
        """Test can_resend_otp returns False during cooldown."""
        # Create OTP 30 seconds ago (within cooldown)
        recent_time = timezone.now() - timedelta(seconds=30)
        with patch("django.utils.timezone.now", return_value=recent_time):
            LoginOTP.objects.create(
                user=self.user,
                code="123456",
                purpose="VERIFY",
                channel="EMAIL",
                expires_at=recent_time + timedelta(minutes=5),
            )

        can_resend, cooldown = OTPService.can_resend_otp(self.user, "VERIFY")

        self.assertFalse(can_resend)
        self.assertIn(cooldown, [29, 30])  # Allow for timing differences

    def test_can_resend_otp_no_previous(self):
        """Test can_resend_otp returns True when no previous OTP."""
        can_resend, cooldown = OTPService.can_resend_otp(self.user, "VERIFY")

        self.assertTrue(can_resend)
        self.assertEqual(cooldown, 0)

    def test_cleanup_expired_otps(self):
        """Test cleanup of expired OTP records."""
        # Create expired and valid OTPs
        expired_otp = LoginOTP.objects.create(
            user=self.user,
            code="111111",
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        valid_otp = LoginOTP.objects.create(
            user=self.user,
            code="222222",
            purpose="RESET",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        deleted_count = OTPService.cleanup_expired_otps()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(LoginOTP.objects.filter(id=expired_otp.id).exists())
        self.assertTrue(LoginOTP.objects.filter(id=valid_otp.id).exists())


class OTPViewsTestCase(TestCase):
    """Test OTP-related views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_active=False,
        )
        self.profile, created = Profile.objects.get_or_create(user=self.user)

    @patch("profiles.views.OTPService.create_otp")
    def test_register_creates_otp(self, mock_create_otp):
        """Test registration creates OTP and redirects to verification."""
        mock_otp = MagicMock()
        mock_otp.code = "123456"
        mock_create_otp.return_value = mock_otp

        response = self.client.post(
            reverse("profiles:register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:verify_account"))

        # Check OTP creation was called
        mock_create_otp.assert_called_once()
        args = mock_create_otp.call_args[0]
        self.assertEqual(args[1], "VERIFY")
        self.assertEqual(args[2], "EMAIL")

        # Check user was created as inactive
        new_user = User.objects.get(username="newuser")
        self.assertFalse(new_user.is_active)

    def test_verify_account_get(self):
        """Test GET request to verify account page."""
        # Set up session
        session = self.client.session
        session["otp_user_id"] = self.user.id
        session.save()

        response = self.client.get(reverse("profiles:verify_account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify Your Account")
        self.assertContains(response, "te**@example.com")  # Masked email

    def test_verify_account_no_session(self):
        """Test verify account without valid session."""
        response = self.client.get(reverse("profiles:verify_account"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:register"))

    @patch("profiles.views.OTPService.verify_otp")
    def test_verify_account_success(self, mock_verify):
        """Test successful account verification."""
        mock_verify.return_value = (True, "OTP verified successfully.")

        # Set up session
        session = self.client.session
        session["otp_user_id"] = self.user.id
        session.save()

        response = self.client.post(
            reverse("profiles:verify_account"), {"otp_code": "123456"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:profile"))

        # Check user is authenticated
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

        # Check session was cleaned up
        self.assertNotIn("otp_user_id", self.client.session)

    @patch("profiles.views.OTPService.verify_otp")
    def test_verify_account_failure(self, mock_verify):
        """Test failed account verification."""
        mock_verify.return_value = (False, "Invalid OTP code.")

        session = self.client.session
        session["otp_user_id"] = self.user.id
        session.save()

        response = self.client.post(
            reverse("profiles:verify_account"), {"otp_code": "123456"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid OTP code.")

    @patch("profiles.views.OTPService.can_resend_otp")
    @patch("profiles.views.OTPService.create_otp")
    def test_resend_account_otp_success(self, mock_create_otp, mock_can_resend):
        """Test successful OTP resend."""
        mock_can_resend.return_value = (True, 0)
        mock_otp = MagicMock()
        mock_create_otp.return_value = mock_otp

        session = self.client.session
        session["otp_user_id"] = self.user.id
        session.save()

        response = self.client.post(reverse("profiles:resend_account_otp"))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["cooldown_remaining"], 60)

        mock_create_otp.assert_called_once()

    @patch("profiles.views.OTPService.can_resend_otp")
    def test_resend_account_otp_cooldown(self, mock_can_resend):
        """Test OTP resend during cooldown."""
        mock_can_resend.return_value = (False, 45)

        session = self.client.session
        session["otp_user_id"] = self.user.id
        session.save()

        response = self.client.post(reverse("profiles:resend_account_otp"))

        self.assertEqual(response.status_code, 429)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["cooldown_remaining"], 45)

    def test_reset_request_get(self):
        """Test GET request to password reset page."""
        response = self.client.get(reverse("profiles:reset_request"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset Your Password")

    @patch("profiles.views.OTPService.can_resend_otp")
    @patch("profiles.views.OTPService.create_otp")
    def test_reset_request_success(self, mock_create_otp, mock_can_resend):
        """Test successful password reset request."""
        self.user.is_active = True
        self.user.save()

        mock_can_resend.return_value = (True, 0)
        mock_otp = MagicMock()
        mock_create_otp.return_value = mock_otp

        response = self.client.post(
            reverse("profiles:reset_request"), {"email_or_username": "test@example.com"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:reset_verify"))

        # Check session was set
        self.assertEqual(self.client.session["reset_user_id"], self.user.id)

        mock_create_otp.assert_called_once()

    def test_reset_request_nonexistent_user(self):
        """Test password reset request for nonexistent user."""
        response = self.client.post(
            reverse("profiles:reset_request"),
            {"email_or_username": "nonexistent@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If an account with that email/username exists")

    @patch("profiles.views.OTPService.verify_otp")
    def test_reset_verify_success(self, mock_verify):
        """Test successful password reset verification."""
        self.user.is_active = True
        self.user.save()

        mock_verify.return_value = (True, "OTP verified successfully.")

        session = self.client.session
        session["reset_user_id"] = self.user.id
        session.save()

        response = self.client.post(
            reverse("profiles:reset_verify"), {"otp_code": "123456"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:reset_new_password"))

        # Check reset verified flag was set
        self.assertTrue(self.client.session["reset_verified"])

    def test_reset_new_password_get(self):
        """Test GET request to new password page."""
        self.user.is_active = True
        self.user.save()

        session = self.client.session
        session["reset_user_id"] = self.user.id
        session["reset_verified"] = True
        session.save()

        response = self.client.get(reverse("profiles:reset_new_password"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set New Password")

    def test_reset_new_password_success(self):
        """Test successful password reset completion."""
        self.user.is_active = True
        self.user.save()
        old_password = self.user.password

        session = self.client.session
        session["reset_user_id"] = self.user.id
        session["reset_verified"] = True
        session.save()

        response = self.client.post(
            reverse("profiles:reset_new_password"),
            {"password1": "newpassword123", "password2": "newpassword123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))

        # Check password was changed
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old_password)
        self.assertTrue(self.user.check_password("newpassword123"))

        # Check session was cleaned up
        self.assertNotIn("reset_user_id", self.client.session)
        self.assertNotIn("reset_verified", self.client.session)

    def test_reset_new_password_mismatch(self):
        """Test password reset with mismatched passwords."""
        self.user.is_active = True
        self.user.save()

        session = self.client.session
        session["reset_user_id"] = self.user.id
        session["reset_verified"] = True
        session.save()

        response = self.client.post(
            reverse("profiles:reset_new_password"),
            {"password1": "newpassword123", "password2": "differentpassword"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")

    def test_reset_new_password_invalid_session(self):
        """Test new password page without valid session."""
        response = self.client.get(reverse("profiles:reset_new_password"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profiles:reset_request"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OTPEmailTestCase(TestCase):
    """Test OTP email functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        mail.outbox = []  # Clear any existing emails

    def test_verification_email_sent(self):
        """Test verification OTP email is sent correctly."""
        otp = OTPService.create_otp(self.user, "VERIFY", "EMAIL")

        self.assertIsNotNone(otp)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertIn("Verify Your Account", email.subject)
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(otp.code, email.body)

    def test_reset_email_sent(self):
        """Test password reset OTP email is sent correctly."""
        otp = OTPService.create_otp(self.user, "RESET", "EMAIL")

        self.assertIsNotNone(otp)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertIn("Password Reset Code", email.subject)
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(otp.code, email.body)


class OTPModelTestCase(TestCase):
    """Test the LoginOTP model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_otp_auto_expiry(self):
        """Test OTP automatically sets expiry time on creation."""
        otp = LoginOTP.objects.create(user=self.user, purpose="VERIFY", channel="EMAIL")

        self.assertIsNotNone(otp.expires_at)
        self.assertIsNotNone(otp.code)
        self.assertEqual(len(otp.code), 6)

        # Check expiry is approximately 5 minutes from now
        now = timezone.now()
        self.assertTrue(otp.expires_at > now)
        self.assertTrue(otp.expires_at <= now + timedelta(minutes=6))

    def test_otp_is_expired(self):
        """Test OTP expiry detection."""
        # Create expired OTP
        expired_otp = LoginOTP.objects.create(
            user=self.user,
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(expired_otp.is_expired())

        # Create valid OTP
        valid_otp = LoginOTP.objects.create(
            user=self.user,
            purpose="RESET",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertFalse(valid_otp.is_expired())

    def test_otp_is_valid(self):
        """Test OTP validity check."""
        # Create valid OTP
        valid_otp = LoginOTP.objects.create(
            user=self.user,
            purpose="VERIFY",
            channel="EMAIL",
            expires_at=timezone.now() + timedelta(minutes=5),
            verified=False,
            attempts=2,
        )

        self.assertTrue(valid_otp.is_valid())

        # Test invalid scenarios
        valid_otp.verified = True
        self.assertFalse(valid_otp.is_valid())

        valid_otp.verified = False
        valid_otp.attempts = 5
        self.assertFalse(valid_otp.is_valid())

        valid_otp.attempts = 0
        valid_otp.expires_at = timezone.now() - timedelta(minutes=1)
        self.assertFalse(valid_otp.is_valid())

    def test_otp_string_representation(self):
        """Test OTP string representation."""
        otp = LoginOTP.objects.create(
            user=self.user, code="123456", purpose="VERIFY", channel="EMAIL"
        )

        expected = f"OTP 123456 for testuser (Account Verification)"
        self.assertEqual(str(otp), expected)
