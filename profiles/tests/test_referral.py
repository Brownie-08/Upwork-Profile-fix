"""
Tests for referral system functionality
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock
from profiles.models import Referral, Profile
from profiles.services.referral import ReferralService


class ReferralModelTestCase(TestCase):
    """Test the Referral model"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user1)
        Profile.objects.create(user=self.user2)

    def test_referral_creation(self):
        """Test that referral is created with auto-generated code"""
        referral = Referral.objects.create(user=self.user1)

        self.assertIsNotNone(referral.code)
        self.assertEqual(len(referral.code), 8)
        self.assertTrue(referral.code.isupper())
        self.assertIsNone(referral.referred_by)
        self.assertEqual(referral.total_referrals, 0)

    def test_referral_with_referrer(self):
        """Test creating referral with a referrer"""
        referrer_referral = Referral.objects.create(user=self.user1)
        referred_referral = Referral.objects.create(
            user=self.user2, referred_by=self.user1
        )

        self.assertEqual(referred_referral.referred_by, self.user1)
        self.assertEqual(referrer_referral.total_referrals, 1)

    def test_unique_referral_code(self):
        """Test that referral codes are unique"""
        referral1 = Referral.objects.create(user=self.user1)
        referral2 = Referral.objects.create(user=self.user2)

        self.assertNotEqual(referral1.code, referral2.code)

    def test_string_representation(self):
        """Test the string representation of Referral"""
        referral = Referral.objects.create(user=self.user1)
        expected = f"Referral code {referral.code} for {self.user1.username}"
        self.assertEqual(str(referral), expected)

    def test_total_referrals_property(self):
        """Test the total_referrals property"""
        referrer_referral = Referral.objects.create(user=self.user1)

        # Create some referred users
        for i in range(3):
            user = User.objects.create_user(
                username=f"referred_user_{i}",
                email=f"referred{i}@example.com",
                password="testpass123",
            )
            Profile.objects.create(user=user)
            Referral.objects.create(user=user, referred_by=self.user1)

        self.assertEqual(referrer_referral.total_referrals, 3)


class ReferralServiceTestCase(TestCase):
    """Test the ReferralService class"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user1)
        Profile.objects.create(user=self.user2)

    def test_generate_code(self):
        """Test code generation"""
        code = ReferralService.generate_code()

        self.assertEqual(len(code), 8)
        self.assertTrue(code.isupper())
        self.assertTrue(all(c.isalnum() for c in code))

    def test_generate_unique_codes(self):
        """Test that generated codes are unique"""
        codes = [ReferralService.generate_code() for _ in range(10)]
        self.assertEqual(len(codes), len(set(codes)))

    def test_create_referral(self):
        """Test creating a referral for a user"""
        referral = ReferralService.create_referral(self.user1)

        self.assertIsNotNone(referral)
        self.assertEqual(referral.user, self.user1)
        self.assertIsNotNone(referral.code)
        self.assertIsNone(referral.referred_by)

    def test_create_referral_idempotent(self):
        """Test that creating referral for same user returns existing"""
        referral1 = ReferralService.create_referral(self.user1)
        referral2 = ReferralService.create_referral(self.user1)

        self.assertEqual(referral1, referral2)
        self.assertEqual(Referral.objects.filter(user=self.user1).count(), 1)

    def test_assign_referrer_success(self):
        """Test successful referrer assignment"""
        referrer_referral = Referral.objects.create(user=self.user1)

        success, message, referrer = ReferralService.assign_referrer(
            self.user2, referrer_referral.code
        )

        self.assertTrue(success)
        self.assertEqual(referrer, self.user1)
        self.assertIn("Successfully linked", message)

        # Check that referral was created with referrer
        user2_referral = Referral.objects.get(user=self.user2)
        self.assertEqual(user2_referral.referred_by, self.user1)

    def test_assign_referrer_invalid_code(self):
        """Test assignment with invalid referral code"""
        success, message, referrer = ReferralService.assign_referrer(
            self.user2, "INVALID123"
        )

        self.assertFalse(success)
        self.assertIsNone(referrer)
        self.assertIn("Invalid referral code", message)

    def test_assign_referrer_self_referral(self):
        """Test that users cannot refer themselves"""
        referral = Referral.objects.create(user=self.user1)

        success, message, referrer = ReferralService.assign_referrer(
            self.user1, referral.code
        )

        self.assertFalse(success)
        self.assertIsNone(referrer)
        self.assertIn("Cannot use your own referral code", message)

    def test_assign_referrer_empty_code(self):
        """Test assignment with empty referral code"""
        success, message, referrer = ReferralService.assign_referrer(self.user2, "")

        self.assertTrue(success)  # Empty code is allowed
        self.assertIsNone(referrer)
        self.assertEqual(message, "No referral code provided")

    def test_get_referral_stats(self):
        """Test getting referral statistics for a user"""
        referrer_referral = Referral.objects.create(user=self.user1)

        # Create some referred users
        for i in range(2):
            user = User.objects.create_user(
                username=f"referred_user_{i}",
                email=f"referred{i}@example.com",
                password="testpass123",
            )
            Profile.objects.create(user=user)
            Referral.objects.create(user=user, referred_by=self.user1)

        stats = ReferralService.get_referral_stats(self.user1)

        self.assertEqual(stats["referral_code"], referrer_referral.code)
        self.assertEqual(stats["total_referrals"], 2)
        self.assertIsNone(stats["referred_by"])
        self.assertEqual(stats["referred_users"].count(), 2)

    def test_get_referral_stats_for_referred_user(self):
        """Test getting stats for a user who was referred"""
        referrer_referral = Referral.objects.create(user=self.user1)
        referred_referral = Referral.objects.create(
            user=self.user2, referred_by=self.user1
        )

        stats = ReferralService.get_referral_stats(self.user2)

        self.assertEqual(stats["referral_code"], referred_referral.code)
        self.assertEqual(stats["total_referrals"], 0)
        self.assertEqual(stats["referred_by"], self.user1)

    def test_validate_referral_code(self):
        """Test referral code validation"""
        referral = Referral.objects.create(user=self.user1)

        # Valid code
        is_valid, referrer = ReferralService.validate_referral_code(referral.code)
        self.assertTrue(is_valid)
        self.assertEqual(referrer, self.user1)

        # Invalid code
        is_valid, referrer = ReferralService.validate_referral_code("INVALID123")
        self.assertFalse(is_valid)
        self.assertIsNone(referrer)

        # Empty code
        is_valid, referrer = ReferralService.validate_referral_code("")
        self.assertFalse(is_valid)
        self.assertIsNone(referrer)

    def test_get_user_referrals(self):
        """Test getting all users referred by a specific user"""
        referrer_referral = Referral.objects.create(user=self.user1)

        # Create referred users
        referred_users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"referred_user_{i}",
                email=f"referred{i}@example.com",
                password="testpass123",
            )
            Profile.objects.create(user=user)
            Referral.objects.create(user=user, referred_by=self.user1)
            referred_users.append(user)

        user_referrals = ReferralService.get_user_referrals(self.user1)

        self.assertEqual(user_referrals.count(), 3)
        for user in referred_users:
            self.assertIn(user, user_referrals)


class ReferralRegistrationTestCase(TestCase):
    """Test referral functionality during user registration"""

    def setUp(self):
        self.client = Client()
        self.referrer_user = User.objects.create_user(
            username="referrer", email="referrer@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.referrer_user)
        self.referrer_referral = Referral.objects.create(user=self.referrer_user)

    def test_registration_with_valid_referral_code(self):
        """Test registration using a valid referral code"""
        with patch("profiles.views.OTPService.create_otp") as mock_create_otp:
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
                    "referral_code": self.referrer_referral.code,
                },
            )

            self.assertEqual(response.status_code, 302)

            # Check user was created
            new_user = User.objects.get(username="newuser")
            self.assertFalse(
                new_user.is_active
            )  # Should be inactive until OTP verification

            # Check referral was assigned
            new_user_referral = Referral.objects.get(user=new_user)
            self.assertEqual(new_user_referral.referred_by, self.referrer_user)

    def test_registration_with_invalid_referral_code(self):
        """Test registration with invalid referral code"""
        with patch("profiles.views.OTPService.create_otp") as mock_create_otp:
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
                    "referral_code": "INVALID123",
                },
            )

            self.assertEqual(response.status_code, 302)

            # Check user was still created
            new_user = User.objects.get(username="newuser")

            # Check referral was created but without referrer
            new_user_referral = Referral.objects.get(user=new_user)
            self.assertIsNone(new_user_referral.referred_by)

    def test_registration_with_phone_number(self):
        """Test registration with phone number"""
        with patch("profiles.views.OTPService.create_otp") as mock_create_otp:
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
                    "phone_number": "+26876543210",
                },
            )

            self.assertEqual(response.status_code, 302)

            # Check user was created
            new_user = User.objects.get(username="newuser")

            # Check phone number was saved
            self.assertEqual(new_user.profile.phone_number, "+26876543210")

            # Check OTP was created with BOTH channel
            mock_create_otp.assert_called_once()
            args = mock_create_otp.call_args[0]
            self.assertEqual(args[2], "BOTH")  # channel parameter

    def test_registration_without_referral_code(self):
        """Test normal registration without referral code"""
        with patch("profiles.views.OTPService.create_otp") as mock_create_otp:
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

            # Check user was created
            new_user = User.objects.get(username="newuser")

            # Check referral was created but without referrer
            new_user_referral = Referral.objects.get(user=new_user)
            self.assertIsNone(new_user_referral.referred_by)
            self.assertIsNotNone(new_user_referral.code)

    @patch("profiles.views.OTPService.create_otp")
    def test_auto_referral_creation(self, mock_create_otp):
        """Test that referral is automatically created for new users"""
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

        # Check user was created
        new_user = User.objects.get(username="newuser")

        # Check referral was auto-created
        self.assertTrue(Referral.objects.filter(user=new_user).exists())
        referral = Referral.objects.get(user=new_user)
        self.assertIsNotNone(referral.code)
        self.assertEqual(len(referral.code), 8)


class ReferralStatsTestCase(TestCase):
    """Test referral statistics functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user)
        self.client = Client()

    def test_referral_stats_in_profile_view(self):
        """Test that referral stats are included in profile view"""
        # Create referral for user
        referral = Referral.objects.create(user=self.user)

        # Login user
        self.client.force_login(self.user)

        response = self.client.get(reverse("profiles:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("referral_stats", response.context)

        referral_stats = response.context["referral_stats"]
        self.assertEqual(referral_stats["referral_code"], referral.code)
        self.assertEqual(referral_stats["total_referrals"], 0)
        self.assertIsNone(referral_stats["referred_by"])

    def test_referral_stats_auto_creation(self):
        """Test that referral is auto-created when getting stats"""
        # Login user
        self.client.force_login(self.user)

        # User doesn't have referral yet
        self.assertFalse(Referral.objects.filter(user=self.user).exists())

        response = self.client.get(reverse("profiles:profile"))

        # Referral should be auto-created
        self.assertTrue(Referral.objects.filter(user=self.user).exists())

        referral_stats = response.context["referral_stats"]
        self.assertIsNotNone(referral_stats["referral_code"])


class ReferralEdgeCasesTestCase(TestCase):
    """Test edge cases and error handling for referral system"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user1)
        Profile.objects.create(user=self.user2)

    def test_case_insensitive_referral_codes(self):
        """Test that referral codes are case-insensitive"""
        referral = Referral.objects.create(user=self.user1)
        original_code = referral.code

        # Test with lowercase
        success, message, referrer = ReferralService.assign_referrer(
            self.user2, original_code.lower()
        )

        self.assertTrue(success)
        self.assertEqual(referrer, self.user1)

    def test_whitespace_handling(self):
        """Test that whitespace is handled properly"""
        referral = Referral.objects.create(user=self.user1)
        code_with_whitespace = f"  {referral.code}  "

        success, message, referrer = ReferralService.assign_referrer(
            self.user2, code_with_whitespace
        )

        self.assertTrue(success)
        self.assertEqual(referrer, self.user1)

    def test_already_has_referrer(self):
        """Test assigning referrer to user who already has one"""
        referrer1_referral = Referral.objects.create(user=self.user1)

        # Create another potential referrer
        user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="testpass123"
        )
        Profile.objects.create(user=user3)
        referrer2_referral = Referral.objects.create(user=user3)

        # First assignment should succeed
        success1, message1, referrer1 = ReferralService.assign_referrer(
            self.user2, referrer1_referral.code
        )
        self.assertTrue(success1)

        # Second assignment should fail
        success2, message2, referrer2 = ReferralService.assign_referrer(
            self.user2, referrer2_referral.code
        )
        self.assertFalse(success2)
        self.assertIn("already has a referrer", message2)

    @patch("profiles.services.referral.ReferralService.generate_code")
    def test_code_generation_collision_handling(self, mock_generate):
        """Test handling of code generation collisions"""
        # Simulate collision by returning same code twice, then unique code
        mock_generate.side_effect = ["TESTCODE", "TESTCODE", "UNIQUE12"]

        # Create first referral with 'TESTCODE'
        referral1 = Referral.objects.create(user=self.user1)

        # Try to create second referral - should get different code due to collision
        referral2 = Referral.objects.create(user=self.user2)

        self.assertNotEqual(referral1.code, referral2.code)
