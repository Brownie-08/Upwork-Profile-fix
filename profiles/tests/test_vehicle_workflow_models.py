"""
Test cases for the vehicle workflow models (VehicleOwnership, Document, DocumentReview).
"""

import os
import tempfile
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import datetime

from profiles.models import Profile, VehicleOwnership, Document, DocumentReview
from notifications.models import Notification


class VehicleOwnershipModelTests(TestCase):
    """Test cases for VehicleOwnership model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_vehicle_ownership_creation(self):
        """Test creating a VehicleOwnership instance."""
        vehicle = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
        )

        self.assertEqual(vehicle.owner, self.user)
        self.assertEqual(vehicle.plate_number, "JSD 123 AM")
        self.assertEqual(vehicle.make, "Toyota")
        self.assertEqual(vehicle.model, "Camry")
        self.assertEqual(vehicle.year, 2020)
        self.assertEqual(vehicle.vehicle_type, "CAR")
        self.assertTrue(vehicle.created_at)

    def test_vehicle_ownership_str_method(self):
        """Test __str__ method for VehicleOwnership."""
        vehicle = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
        )
        self.assertEqual(str(vehicle), "2020 Toyota Camry (JSD 123 AM)")

        # Test with minimal info
        vehicle_minimal = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 456 BC"
        )
        self.assertEqual(str(vehicle_minimal), "Vehicle (JSD 456 BC)")

    def test_plate_number_validation(self):
        """Test license plate number validation."""
        # Valid plate number
        vehicle = VehicleOwnership(owner=self.user, plate_number="JSD 123 AM")
        vehicle.full_clean()  # Should not raise ValidationError

        # Invalid plate numbers
        invalid_plates = [
            "invalid",
            "123 ABC",
            "JSD123AM",
            "JSD 12 AM",
            "JSD 1234 AM",
            "jsd 123 am",  # lowercase
        ]

        for invalid_plate in invalid_plates:
            with self.assertRaises(ValidationError):
                vehicle = VehicleOwnership(owner=self.user, plate_number=invalid_plate)
                vehicle.full_clean()

    def test_unique_plate_number(self):
        """Test that plate numbers must be unique."""
        VehicleOwnership.objects.create(owner=self.user, plate_number="JSD 123 AM")

        user2 = User.objects.create_user(username="testuser2", password="pass")

        # Attempting to create another vehicle with the same plate should fail
        with self.assertRaises(ValidationError):
            vehicle = VehicleOwnership(owner=user2, plate_number="JSD 123 AM")
            vehicle.full_clean()

    def test_get_required_documents(self):
        """Test get_required_documents method."""
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        required_docs = vehicle.get_required_documents()
        self.assertEqual(set(required_docs), {"ROADWORTHY", "BLUEBOOK"})

    def test_get_document_status(self):
        """Test get_document_status method."""
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # No document uploaded - should return 'MISSING'
        status = vehicle.get_document_status("ROADWORTHY")
        self.assertEqual(status, "MISSING")

        # Create a document
        document = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

        # No review yet - should return 'PENDING'
        status = vehicle.get_document_status("ROADWORTHY")
        self.assertEqual(status, "PENDING")

        # Create a review
        DocumentReview.objects.create(document=document, status="APPROVED")

        # Should return review status
        status = vehicle.get_document_status("ROADWORTHY")
        self.assertEqual(status, "APPROVED")

    def test_is_fully_documented(self):
        """Test is_fully_documented method."""
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # No documents - should return False
        self.assertFalse(vehicle.is_fully_documented())

        # Create and approve roadworthy certificate
        roadworthy_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("roadworthy.pdf", b"content"),
        )
        DocumentReview.objects.create(document=roadworthy_doc, status="APPROVED")

        # Still missing blue book - should return False
        self.assertFalse(vehicle.is_fully_documented())

        # Create and approve blue book
        bluebook_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="BLUEBOOK",
            file=SimpleUploadedFile("bluebook.pdf", b"content"),
        )
        DocumentReview.objects.create(document=bluebook_doc, status="APPROVED")

        # Now should return True
        self.assertTrue(vehicle.is_fully_documented())


class DocumentModelTests(TestCase):
    """Test cases for Document model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

    def test_document_creation_vehicle_document(self):
        """Test creating a vehicle-specific document."""
        document = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile(
                "test.pdf", b"file content", content_type="application/pdf"
            ),
        )

        self.assertEqual(document.user, self.user)
        self.assertEqual(document.vehicle, self.vehicle)
        self.assertEqual(document.doc_type, "ROADWORTHY")
        self.assertTrue(document.file)
        self.assertTrue(document.uploaded_at)

    def test_document_creation_user_document(self):
        """Test creating a user-only document (driver's license)."""
        document = Document.objects.create(
            user=self.user,
            vehicle=None,
            doc_type="DRIVER_LICENSE",
            file=SimpleUploadedFile(
                "license.pdf", b"file content", content_type="application/pdf"
            ),
        )

        self.assertEqual(document.user, self.user)
        self.assertIsNone(document.vehicle)
        self.assertEqual(document.doc_type, "DRIVER_LICENSE")

    def test_document_str_method(self):
        """Test __str__ method for Document."""
        # Vehicle document
        document = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )
        expected = f"Roadworthiness Certificate for {self.vehicle.plate_number} - {self.user.username}"
        self.assertEqual(str(document), expected)

        # User-only document
        user_document = Document.objects.create(
            user=self.user,
            doc_type="DRIVER_LICENSE",
            file=SimpleUploadedFile("license.pdf", b"content"),
        )
        expected = f"Driver's License - {self.user.username}"
        self.assertEqual(str(user_document), expected)

    def test_document_file_path(self):
        """Test document file path generation."""
        document = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

        # Check that file path contains expected components
        file_path = document.file.name
        self.assertIn(f"user_{self.user.id}", file_path)
        self.assertIn(f"vehicle_{self.vehicle.id}", file_path)
        self.assertIn("roadworthy", file_path.lower())

    def test_unique_constraint(self):
        """Test unique constraint for user-vehicle-doc_type combination."""
        Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test1.pdf", b"content"),
        )

        # Attempting to create another document with same user, vehicle, and doc_type should fail
        with self.assertRaises(ValidationError):
            duplicate_doc = Document(
                user=self.user,
                vehicle=self.vehicle,
                doc_type="ROADWORTHY",
                file=SimpleUploadedFile("test2.pdf", b"content"),
            )
            duplicate_doc.full_clean()


class DocumentReviewModelTests(TestCase):
    """Test cases for DocumentReview model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )
        self.document = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

    def test_document_review_creation(self):
        """Test creating a DocumentReview instance."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")

        self.assertEqual(review.document, self.document)
        self.assertEqual(review.status, "PENDING")
        self.assertTrue(review.created_at)
        self.assertIsNone(review.reviewed_at)
        self.assertIsNone(review.reviewed_by)

    def test_document_review_str_method(self):
        """Test __str__ method for DocumentReview."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")
        expected = f"{self.document} - Pending Review"
        self.assertEqual(str(review), expected)

    def test_review_approval(self):
        """Test document review approval."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")

        # Approve the review
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.save()

        # Check that reviewed_at is set automatically
        self.assertIsNotNone(review.reviewed_at)
        self.assertEqual(review.reviewed_by, self.admin_user)

    def test_review_rejection(self):
        """Test document review rejection."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")

        # Reject the review
        review.status = "REJECTED"
        review.reason = "Document is unclear"
        review.reviewed_by = self.admin_user
        review.save()

        # Check fields are set correctly
        self.assertEqual(review.status, "REJECTED")
        self.assertEqual(review.reason, "Document is unclear")
        self.assertIsNotNone(review.reviewed_at)
        self.assertEqual(review.reviewed_by, self.admin_user)

    def test_notification_creation_on_approval(self):
        """Test that notification is created when document is approved."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")

        # Approve the review
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.save()

        # Check that notification was created
        notification = Notification.objects.filter(user=self.user).first()
        self.assertIsNotNone(notification)
        self.assertIn("approved", notification.message.lower())

    def test_notification_creation_on_rejection(self):
        """Test that notification is created when document is rejected."""
        review = DocumentReview.objects.create(document=self.document, status="PENDING")

        # Reject the review
        review.status = "REJECTED"
        review.reason = "Document is unclear"
        review.reviewed_by = self.admin_user
        review.save()

        # Check that notification was created
        notification = Notification.objects.filter(user=self.user).first()
        self.assertIsNotNone(notification)
        self.assertIn("rejected", notification.message.lower())
        self.assertIn("Document is unclear", notification.message)

    def test_no_duplicate_notifications(self):
        """Test that duplicate notifications are not created."""
        review = DocumentReview.objects.create(
            document=self.document, status="APPROVED", reviewed_by=self.admin_user
        )

        initial_count = Notification.objects.filter(user=self.user).count()

        # Save again without changes
        review.save()

        # Should not create another notification
        final_count = Notification.objects.filter(user=self.user).count()
        self.assertEqual(initial_count, final_count)


class ModelIntegrationTests(TestCase):
    """Integration tests for the vehicle workflow models."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_complete_vehicle_document_workflow(self):
        """Test complete workflow from vehicle creation to document approval."""
        # Step 1: Create vehicle
        vehicle = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
        )

        # Check initial state
        self.assertFalse(vehicle.is_fully_documented())

        # Step 2: Upload required documents
        roadworthy_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("roadworthy.pdf", b"content"),
        )

        bluebook_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="BLUEBOOK",
            file=SimpleUploadedFile("bluebook.pdf", b"content"),
        )

        # Step 3: Create reviews (automatic creation would happen in real workflow)
        roadworthy_review = DocumentReview.objects.create(
            document=roadworthy_doc, status="PENDING"
        )

        bluebook_review = DocumentReview.objects.create(
            document=bluebook_doc, status="PENDING"
        )

        # Still not fully documented
        self.assertFalse(vehicle.is_fully_documented())

        # Step 4: Approve documents
        roadworthy_review.status = "APPROVED"
        roadworthy_review.reviewed_by = self.admin_user
        roadworthy_review.save()

        bluebook_review.status = "APPROVED"
        bluebook_review.reviewed_by = self.admin_user
        bluebook_review.save()

        # Now should be fully documented
        self.assertTrue(vehicle.is_fully_documented())

        # Check notifications were created
        notifications = Notification.objects.filter(user=self.user)
        self.assertEqual(notifications.count(), 2)  # One for each approved document

    def test_document_replacement_workflow(self):
        """Test workflow when a document is replaced (re-uploaded)."""
        # Create vehicle and initial document
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        original_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("original.pdf", b"content"),
        )

        # Reject the original document
        review = DocumentReview.objects.create(
            document=original_doc,
            status="REJECTED",
            reason="Document is blurry",
            reviewed_by=self.admin_user,
        )

        # Check rejection notification was created
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, message__icontains="rejected"
            ).exists()
        )

        # In real workflow, user would upload a new document
        # For this test, we'll simulate the replacement
        original_doc.delete()  # Old document is deleted

        new_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("new.pdf", b"better content"),
        )

        # New review is created (would happen automatically in real workflow)
        new_review = DocumentReview.objects.create(document=new_doc, status="PENDING")

        # Approve the new document
        new_review.status = "APPROVED"
        new_review.reviewed_by = self.admin_user
        new_review.save()

        # Check approval notification was created
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, message__icontains="approved"
            ).exists()
        )
