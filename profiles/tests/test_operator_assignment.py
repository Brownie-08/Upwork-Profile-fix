"""
Regression tests for the operator assignment functionality.

This module tests the fix for the "ERROR OCCURRED" issue when assigning verified users as vehicle operators.
It covers both AJAX and non-AJAX flows, legacy and new vehicle models, and various validation scenarios.
"""

import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages

from profiles.models import (
    Profile,
    Vehicle,
    VehicleOwnership,
    OperatorAssignment,
    Document,
    DocumentReview,
)


class OperatorAssignmentTestCase(TestCase):
    """Test cases for the operator assignment functionality."""

    def setUp(self):
        """Set up test data for each test case."""
        self.client = Client()

        # Create test users
        self.vehicle_owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.operator_user = User.objects.create_user(
            username="operator", email="operator@example.com", password="testpass123"
        )
        self.unverified_user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="testpass123",
        )

        # Create profiles using get_or_create to handle potential conflicts
        self.owner_profile, _ = Profile.objects.get_or_create(user=self.vehicle_owner)
        self.operator_profile, _ = Profile.objects.get_or_create(
            user=self.operator_user
        )
        self.unverified_profile, _ = Profile.objects.get_or_create(
            user=self.unverified_user
        )

        # Set up identity verification for owner and operator
        self._setup_identity_verification(self.vehicle_owner)
        self._setup_identity_verification(self.operator_user)
        # Unverified user has no identity verification

        # Create test vehicles
        self.legacy_vehicle = Vehicle.objects.create(
            profile=self.owner_profile,
            license_plate="TEST123",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
            is_verified=True,
        )

        self.new_vehicle = VehicleOwnership.objects.create(
            owner=self.vehicle_owner,
            plate_number="NEW456",
            make="Honda",
            model="Civic",
            year=2021,
            vehicle_type="CAR",
        )

    def _setup_identity_verification(self, user):
        """Set up identity verification for a user."""
        # Create identity documents
        for doc_type in ["ID_CARD", "FACE_PHOTO", "PROOF_OF_RESIDENCE"]:
            document, created = Document.objects.get_or_create(
                user=user, doc_type=doc_type, defaults={"file": "dummy/path.jpg"}
            )
            # Create or update DocumentReview to ensure APPROVED status
            review, review_created = DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "APPROVED", "reviewed_by": None}
            )
            if not review_created and review.status != "APPROVED":
                review.status = "APPROVED"
                review.save()

        # Refresh profile to update is_identity_verified
        user.profile.refresh_from_db()

    def test_ajax_success_path_new_vehicle(self):
        """Test successful AJAX operator assignment to new vehicle."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("successfully assigned", response_data["message"])
        self.assertIn("redirect_url", response_data)

        # Check database
        assignment = OperatorAssignment.objects.filter(
            vehicle=self.new_vehicle, operator=self.operator_user, active=True
        ).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.assigned_by, self.vehicle_owner)

    def test_ajax_success_path_legacy_vehicle(self):
        """Test successful AJAX operator assignment to legacy vehicle."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.legacy_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("successfully assigned", response_data["message"])

        # Check database - legacy vehicle should have operator in many-to-many relationship
        self.assertIn(self.operator_user, self.legacy_vehicle.operators.all())

        # For legacy vehicles, OperatorAssignment should NOT be created (as per fix)
        assignment = OperatorAssignment.objects.filter(
            operator=self.operator_user
        ).first()
        self.assertIsNone(
            assignment, "OperatorAssignment should not be created for legacy vehicles"
        )

    def test_ajax_missing_operator_username(self):
        """Test AJAX request with missing operator_username."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {}  # No operator_username
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("select an operator", response_data["message"])

    def test_ajax_unverified_operator(self):
        """Test AJAX request with unverified operator."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "unverified"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("verify their identity first", response_data["message"])
        self.assertIn(
            "ID card, face photo, and proof of residence", response_data["message"]
        )

    def test_ajax_self_assignment(self):
        """Test AJAX request trying to assign self as operator."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "owner"}  # Same as logged in user
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("cannot assign yourself", response_data["message"])

    def test_ajax_duplicate_assignment(self):
        """Test AJAX request for duplicate assignment."""
        # First create an assignment
        OperatorAssignment.objects.create(
            vehicle=self.new_vehicle,
            operator=self.operator_user,
            assigned_by=self.vehicle_owner,
            active=True,
        )

        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("already has an active operator", response_data["message"])

    def test_ajax_nonexistent_operator(self):
        """Test AJAX request with non-existent operator username."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "nonexistent"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["content-type"], "application/json")

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("user not found", response_data["message"])

    def test_non_ajax_success_path(self):
        """Test successful non-AJAX operator assignment (should redirect)."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}

        # No AJAX headers
        response = self.client.post(url, data)

        # Check response - should be a redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profiles:profile"))

        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("successfully assigned", str(messages[0]))

        # Check database
        assignment = OperatorAssignment.objects.filter(
            vehicle=self.new_vehicle, operator=self.operator_user, active=True
        ).first()
        self.assertIsNotNone(assignment)

    def test_non_ajax_validation_error(self):
        """Test non-AJAX validation error (should redirect with error message)."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "unverified"}

        # No AJAX headers
        response = self.client.post(url, data)

        # Check response - should be a redirect back to same page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url)

        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("verify their identity first", str(messages[0]))

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot assign operators."""
        # Login as different user
        self.client.login(username="operator", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Should get redirect to profile page (via exception handling)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profiles:profile"))

    def test_nonexistent_vehicle(self):
        """Test assignment to non-existent vehicle."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[99999])  # Non-existent ID
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Should get redirect to profile page (via exception handling)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profiles:profile"))

    @patch("profiles.views.logger")
    def test_exception_handling_ajax(self, mock_logger):
        """Test exception handling in AJAX requests."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        # Mock User.objects.get to raise an exception
        with patch("profiles.views.User.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database error")

            response = self.client.post(url, data, **headers)

            # Check response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response["content-type"], "application/json")

            response_data = json.loads(response.content)
            self.assertFalse(response_data["success"])
            self.assertIn("error occurred", response_data["message"])

            # Check that logger.exception was called (not logger.error)
            mock_logger.exception.assert_called_once()

    def test_get_request_renders_template(self):
        """Test that GET request renders the assignment template."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profiles/add_vehicle_operator.html")

        # Check context
        self.assertIn("vehicle", response.context)
        self.assertIn("verified_users", response.context)
        self.assertEqual(response.context["vehicle"], self.new_vehicle)

        # Verified users should only include identity-verified users (excluding owner)
        verified_users = response.context["verified_users"]
        self.assertIn(self.operator_user, verified_users)
        self.assertNotIn(self.unverified_user, verified_users)
        self.assertNotIn(self.vehicle_owner, verified_users)  # Owner excluded

    def test_transport_status_upgrade(self):
        """Test that both owner and operator get TRANSPORT status after assignment."""
        # Initially both should be REGULAR
        self.assertEqual(self.owner_profile.account_type, "REGULAR")
        self.assertEqual(self.operator_profile.account_type, "REGULAR")

        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)
        self.assertEqual(response.status_code, 200)

        # Refresh from database
        self.owner_profile.refresh_from_db()
        self.operator_profile.refresh_from_db()

        # Both should now have TRANSPORT status
        self.assertEqual(self.owner_profile.account_type, "TRANSPORT")
        self.assertEqual(self.operator_profile.account_type, "TRANSPORT")

    @patch("notifications.models.Notification.objects.create")
    def test_notification_sent_to_operator(self, mock_notification):
        """Test that notification is sent to operator after successful assignment."""
        self.client.login(username="owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.new_vehicle.id])
        data = {"operator_username": "operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)
        self.assertEqual(response.status_code, 200)

        # Check that notification was created
        mock_notification.assert_called_once()
        call_args = mock_notification.call_args[1]  # kwargs

        self.assertEqual(call_args["user"], self.operator_user)
        self.assertEqual(call_args["title"], "Vehicle Operator Assignment")
        self.assertIn("Vehicle NEW456", call_args["message"])
        self.assertIn("Transport Service Provider status", call_args["message"])
        self.assertEqual(call_args["notification_type"], "operator_assigned")


class LegacyVehicleSpecificTests(TestCase):
    """Specific tests for legacy vehicle behavior."""

    def setUp(self):
        """Set up test data for legacy vehicle tests."""
        self.client = Client()

        # Create test users with unique usernames to avoid conflicts with OperatorAssignmentTestCase
        self.vehicle_owner = User.objects.create_user(
            username="legacy_owner",
            email="legacy_owner@example.com",
            password="testpass123",
        )
        self.operator_user = User.objects.create_user(
            username="legacy_operator",
            email="legacy_operator@example.com",
            password="testpass123",
        )

        # Create profiles with identity verification using get_or_create to handle potential conflicts
        self.owner_profile, _ = Profile.objects.get_or_create(user=self.vehicle_owner)
        self.operator_profile, _ = Profile.objects.get_or_create(
            user=self.operator_user
        )

        self._setup_identity_verification(self.vehicle_owner)
        self._setup_identity_verification(self.operator_user)

        # Create legacy vehicle
        self.legacy_vehicle = Vehicle.objects.create(
            profile=self.owner_profile,
            license_plate="LEGACY123",
            make="Ford",
            model="Focus",
            year=2019,
            vehicle_type="CAR",
            is_verified=True,
        )

    def _setup_identity_verification(self, user):
        """Set up identity verification for a user."""
        for doc_type in ["ID_CARD", "FACE_PHOTO", "PROOF_OF_RESIDENCE"]:
            document, created = Document.objects.get_or_create(
                user=user, doc_type=doc_type, defaults={"file": "dummy/path.jpg"}
            )
            # Create or update DocumentReview to ensure APPROVED status
            review, review_created = DocumentReview.objects.get_or_create(
                document=document, defaults={"status": "APPROVED", "reviewed_by": None}
            )
            if not review_created and review.status != "APPROVED":
                review.status = "APPROVED"
                review.save()
        user.profile.refresh_from_db()

    def test_legacy_vehicle_no_operator_assignment_created(self):
        """Test that OperatorAssignment is NOT created for legacy vehicles."""
        self.client.login(username="legacy_owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.legacy_vehicle.id])
        data = {"operator_username": "legacy_operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        # Ensure no existing assignments
        initial_count = OperatorAssignment.objects.count()

        response = self.client.post(url, data, **headers)

        # Check successful response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that operator was added to legacy vehicle
        self.assertIn(self.operator_user, self.legacy_vehicle.operators.all())

        # Confirm that NO OperatorAssignment was created
        final_count = OperatorAssignment.objects.count()
        self.assertEqual(
            initial_count,
            final_count,
            "No OperatorAssignment should be created for legacy vehicles",
        )

    def test_legacy_vehicle_duplicate_check(self):
        """Test duplicate assignment check for legacy vehicles."""
        # Add operator to legacy vehicle
        self.legacy_vehicle.operators.add(self.operator_user)

        self.client.login(username="legacy_owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.legacy_vehicle.id])
        data = {"operator_username": "legacy_operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        response = self.client.post(url, data, **headers)

        # Should get error for duplicate assignment
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("already assigned", response_data["message"])

    def test_robust_vehicle_info_building(self):
        """Test that vehicle info is built robustly for legacy vehicles."""
        self.client.login(username="legacy_owner", password="testpass123")

        url = reverse("profiles:add_vehicle_operator", args=[self.legacy_vehicle.id])
        data = {"operator_username": "legacy_operator"}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

        # Mock Notification.objects.create to capture the message
        with patch(
            "notifications.models.Notification.objects.create"
        ) as mock_notification:
            response = self.client.post(url, data, **headers)

            self.assertEqual(response.status_code, 200)

            # Check that notification was created with proper vehicle info
            mock_notification.assert_called_once()
            call_args = mock_notification.call_args[1]  # kwargs

            # Should contain plate number from license_plate field (legacy)
            message = call_args["message"]
            self.assertIn("LEGACY123", message)  # Using license_plate, not plate_number
            self.assertIn("2019 Ford Focus", message)


if __name__ == "__main__":
    # Run tests with: python manage.py test profiles.tests.test_operator_assignment
    pass
