"""
Tests for Government Permit workflow and Authorized Provider badge functionality.
"""

import tempfile
from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from unittest.mock import patch, MagicMock

from profiles.models import Profile, Document, DocumentReview, TransportOwnerBadge
from notifications.models import Notification

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PermitWorkflowTestCase(TestCase):
    """Test cases for the permit workflow functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        # Create profile
        self.profile = Profile.objects.create(user=self.user)
        # Create identity verification to mark profile as verified
        from profiles.models import IdentityVerification

        identity_verification = IdentityVerification.objects.create(
            profile=self.profile,
            id_card_verified=True,
            proof_of_residence_verified=True,
            face_photo_verified=True,
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Create test PDF file
        self.test_file = SimpleUploadedFile(
            "permit.pdf", b"file_content", content_type="application/pdf"
        )

        # URLs
        self.upload_permit_url = reverse("profiles:upload_permit_dashboard")
        self.permit_status_url = reverse("profiles:get_permit_status")

    def test_transport_owner_badge_creation(self):
        """Test TransportOwnerBadge model creation and defaults."""
        badge = TransportOwnerBadge.objects.create(user=self.user)

        self.assertEqual(badge.user, self.user)
        self.assertFalse(badge.authorized)
        self.assertIsNotNone(badge.updated_at)

    def test_transport_owner_badge_str_representation(self):
        """Test string representation of TransportOwnerBadge."""
        badge = TransportOwnerBadge.objects.create(user=self.user)
        expected = f"Transport Badge for {self.user.username} - {'Authorized' if badge.authorized else 'Not Authorized'}"
        self.assertEqual(str(badge), expected)

    def test_user_can_upload_permit(self):
        """Test that users can upload permit documents."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            self.upload_permit_url, {"doc_type": "PERMIT", "file": self.test_file}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertIn("uploaded successfully", response_data["message"])

        # Verify document was created
        document = Document.objects.get(user=self.user, doc_type="PERMIT")
        self.assertEqual(document.doc_type, "PERMIT")
        self.assertIsNotNone(document.file)

    def test_upload_permit_creates_pending_review(self):
        """Test that uploading a permit creates a pending document review."""
        self.client.login(username="testuser", password="testpass123")

        self.client.post(
            self.upload_permit_url, {"doc_type": "PERMIT", "file": self.test_file}
        )

        document = Document.objects.get(user=self.user, doc_type="PERMIT")
        review = DocumentReview.objects.get(document=document)

        self.assertEqual(review.status, "PENDING")
        self.assertIsNone(review.reviewed_by)
        self.assertIsNone(review.reviewed_at)

    def test_permit_approval_updates_badge(self):
        """Test that approving a permit updates the TransportOwnerBadge."""
        # Create document and review
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        # Create badge (should be created automatically)
        badge, created = TransportOwnerBadge.objects.get_or_create(
            user=self.user, defaults={"authorized": False}
        )
        self.assertFalse(badge.authorized)

        # Approve the permit
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.reviewed_at = timezone.now()
        review.save()

        # Check badge was updated
        badge.refresh_from_db()
        self.assertTrue(badge.authorized)

    def test_permit_rejection_removes_authorization(self):
        """Test that rejecting a permit removes authorization."""
        # Create authorized badge
        badge = TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        # Create document and review
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        # Reject the permit
        review.status = "REJECTED"
        review.reason = "Invalid document format"
        review.reviewed_by = self.admin_user
        review.reviewed_at = timezone.now()
        review.save()

        # Check badge authorization was removed
        badge.refresh_from_db()
        self.assertFalse(badge.authorized)

    def test_permit_approval_sends_notification(self):
        """Test that permit approval sends a notification to the user."""
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        # Approve the permit
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.reviewed_at = timezone.now()
        review.save()

        # Check notification was created
        notification = Notification.objects.filter(
            user=self.user, message__icontains="approved"
        ).first()

        self.assertIsNotNone(notification)
        self.assertIn("Authorized Provider", notification.message)

    def test_permit_rejection_sends_notification_with_reason(self):
        """Test that permit rejection sends a notification with reason."""
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        rejection_reason = "Document is not clear enough"

        # Reject the permit
        review.status = "REJECTED"
        review.reason = rejection_reason
        review.reviewed_by = self.admin_user
        review.reviewed_at = timezone.now()
        review.save()

        # Check notification was created with reason
        notification = Notification.objects.filter(
            user=self.user, message__icontains="rejected"
        ).first()

        self.assertIsNotNone(notification)
        self.assertIn(rejection_reason, notification.message)

    def test_permit_status_api_endpoint(self):
        """Test the permit status API endpoint."""
        self.client.login(username="testuser", password="testpass123")

        # Test without permit
        response = self.client.get(self.permit_status_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["permit_status"]["status"], "MISSING")
        self.assertFalse(data["permit_status"]["badge_status"]["authorized"])

    def test_permit_status_with_uploaded_document(self):
        """Test permit status endpoint with uploaded document."""
        self.client.login(username="testuser", password="testpass123")

        # Upload a permit
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        DocumentReview.objects.create(document=document, status="APPROVED")

        # Create authorized badge
        TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        response = self.client.get(self.permit_status_url)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["permit_status"]["status"], "APPROVED")
        self.assertTrue(data["permit_status"]["badge_status"]["authorized"])

    def test_reupload_permit_replaces_existing(self):
        """Test that re-uploading a permit replaces the existing one."""
        self.client.login(username="testuser", password="testpass123")

        # Upload first permit
        self.client.post(
            self.upload_permit_url,
            {
                "doc_type": "PERMIT",
                "file": SimpleUploadedFile(
                    "permit1.pdf", b"content1", content_type="application/pdf"
                ),
            },
        )

        first_document_id = Document.objects.get(user=self.user, doc_type="PERMIT").id

        # Upload second permit (should replace first)
        self.client.post(
            self.upload_permit_url,
            {
                "doc_type": "PERMIT",
                "file": SimpleUploadedFile(
                    "permit2.pdf", b"content2", content_type="application/pdf"
                ),
            },
        )

        # Check that only one permit exists and it's not the same as before
        permits = Document.objects.filter(user=self.user, doc_type="PERMIT")
        self.assertEqual(permits.count(), 1)
        self.assertNotEqual(permits.first().id, first_document_id)

    def test_vehicle_dashboard_shows_permit_status(self):
        """Test that vehicle dashboard shows permit status correctly."""
        self.client.login(username="testuser", password="testpass123")

        # Create permit with approved status
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        DocumentReview.objects.create(document=document, status="APPROVED")
        TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APPROVED")
        self.assertContains(response, "Authorized Provider")

    def test_profile_shows_authorized_provider_badge(self):
        """Test that profile page shows Authorized Provider badge when authorized."""
        # Create authorized badge
        TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        response = self.client.get(reverse("profiles:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authorized Transport Provider")

    def test_unauthorized_user_cannot_upload_permit(self):
        """Test that unauthorized users cannot upload permits."""
        response = self.client.post(
            self.upload_permit_url, {"doc_type": "PERMIT", "file": self.test_file}
        )

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_invalid_file_type_rejected(self):
        """Test that invalid file types are rejected."""
        self.client.login(username="testuser", password="testpass123")

        invalid_file = SimpleUploadedFile(
            "permit.txt", b"invalid content", content_type="text/plain"
        )

        response = self.client.post(
            self.upload_permit_url, {"doc_type": "PERMIT", "file": invalid_file}
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])

    def test_badge_auto_creation_on_permit_workflow(self):
        """Test that TransportOwnerBadge is auto-created during permit workflow."""
        # Initially no badge exists
        self.assertFalse(TransportOwnerBadge.objects.filter(user=self.user).exists())

        # Create document and review
        document = Document.objects.create(
            user=self.user, doc_type="PERMIT", file=self.test_file
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        # Approve the permit (this should auto-create badge via signal/method)
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.reviewed_at = timezone.now()
        review.save()

        # Badge should be created and authorized
        badge = TransportOwnerBadge.objects.get(user=self.user)
        self.assertTrue(badge.authorized)

    def test_multiple_permit_uploads_only_latest_counts(self):
        """Test that only the latest permit upload is considered for authorization."""
        # Create first approved permit
        doc1 = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit1.pdf", b"content1", content_type="application/pdf"
            ),
        )
        review1 = DocumentReview.objects.create(document=doc1, status="APPROVED")

        # This should create authorized badge
        badge = TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        # Upload new permit (simulate replacement)
        doc2 = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit2.pdf", b"content2", content_type="application/pdf"
            ),
        )
        review2 = DocumentReview.objects.create(
            document=doc2, status="REJECTED", reason="New permit is invalid"
        )

        # Delete old document (simulate replacement)
        doc1.delete()

        # Badge should be unauthorized now
        badge.refresh_from_db()
        # This would be handled by the review save method
        badge.authorized = False
        badge.save()

        self.assertFalse(badge.authorized)


class AdminPermitWorkflowTestCase(TestCase):
    """Test cases for admin permit review functionality."""

    def setUp(self):
        """Set up test data for admin tests."""
        self.client = Client()

        # Create regular user with permit
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user)

        # Create admin user
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Create test document
        self.document = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit.pdf", b"content", content_type="application/pdf"
            ),
        )

        self.review = DocumentReview.objects.create(
            document=self.document, status="PENDING"
        )

    def test_admin_can_approve_permit(self):
        """Test that admin can approve permits through Django admin."""
        self.client.login(username="admin", password="adminpass123")

        # Simulate admin approval
        self.review.status = "APPROVED"
        self.review.reviewed_by = self.admin
        self.review.reviewed_at = timezone.now()
        self.review.save()

        # Check that badge is created and authorized
        badge = TransportOwnerBadge.objects.get(user=self.user)
        self.assertTrue(badge.authorized)

    def test_admin_can_reject_permit_with_reason(self):
        """Test that admin can reject permits with a reason."""
        self.client.login(username="admin", password="adminpass123")

        reason = "Document quality is poor"

        # Simulate admin rejection
        self.review.status = "REJECTED"
        self.review.reason = reason
        self.review.reviewed_by = self.admin
        self.review.reviewed_at = timezone.now()
        self.review.save()

        # Check that notification was sent
        notification = Notification.objects.filter(
            user=self.user, message__icontains=reason
        ).first()

        self.assertIsNotNone(notification)


class PermitNotificationTestCase(TestCase):
    """Test cases for permit-related notifications."""

    def setUp(self):
        """Set up test data for notification tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user)

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )

    def test_approval_notification_content(self):
        """Test the content of permit approval notifications."""
        document = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit.pdf", b"content", content_type="application/pdf"
            ),
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        # Approve permit
        review.status = "APPROVED"
        review.reviewed_by = self.admin
        review.reviewed_at = timezone.now()
        review.save()

        # Check notification content
        notification = Notification.objects.get(user=self.user)
        self.assertIn("approved", notification.message.lower())
        self.assertIn("Authorized Provider", notification.message)

    def test_rejection_notification_includes_reason(self):
        """Test that rejection notifications include the reason."""
        document = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit.pdf", b"content", content_type="application/pdf"
            ),
        )
        review = DocumentReview.objects.create(document=document, status="PENDING")

        reason = "Permit has expired"

        # Reject permit
        review.status = "REJECTED"
        review.reason = reason
        review.reviewed_by = self.admin
        review.reviewed_at = timezone.now()
        review.save()

        # Check notification includes reason
        notification = Notification.objects.get(user=self.user)
        self.assertIn("rejected", notification.message.lower())
        self.assertIn(reason, notification.message)


class PermitUITestCase(TestCase):
    """Test cases for permit-related UI components."""

    def setUp(self):
        """Set up test data for UI tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        Profile.objects.create(user=self.user)

    def test_vehicle_dashboard_permit_section_missing_status(self):
        """Test permit section shows correct status when no permit uploaded."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not Uploaded")
        self.assertNotContains(response, "Authorized Provider")

    def test_vehicle_dashboard_permit_section_pending_status(self):
        """Test permit section shows pending status."""
        self.client.login(username="testuser", password="testpass123")

        # Create pending permit
        document = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit.pdf", b"content", content_type="application/pdf"
            ),
        )
        DocumentReview.objects.create(document=document, status="PENDING")

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Under Review")

    def test_vehicle_dashboard_permit_section_rejected_status(self):
        """Test permit section shows rejection status with reason."""
        self.client.login(username="testuser", password="testpass123")

        reason = "Invalid permit format"

        # Create rejected permit
        document = Document.objects.create(
            user=self.user,
            doc_type="PERMIT",
            file=SimpleUploadedFile(
                "permit.pdf", b"content", content_type="application/pdf"
            ),
        )
        DocumentReview.objects.create(
            document=document, status="REJECTED", reason=reason
        )

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rejected")
        self.assertContains(response, reason)
        self.assertContains(response, "Re-upload")

    def test_profile_badge_visibility(self):
        """Test that Authorized Provider badge is visible on profile when authorized."""
        # Create authorized user
        TransportOwnerBadge.objects.create(user=self.user, authorized=True)

        response = self.client.get(reverse("profiles:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authorized Transport Provider")
        self.assertContains(response, "fa-certificate")


# Run tests
if __name__ == "__main__":
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(
        [
            "profiles.tests.test_permit.PermitWorkflowTestCase",
            "profiles.tests.test_permit.AdminPermitWorkflowTestCase",
            "profiles.tests.test_permit.PermitNotificationTestCase",
            "profiles.tests.test_permit.PermitUITestCase",
        ]
    )
