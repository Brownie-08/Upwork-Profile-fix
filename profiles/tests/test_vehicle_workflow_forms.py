"""
Test cases for the vehicle workflow forms (VehicleOwnershipForm, DocumentForm, DocumentReviewForm).
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from profiles.models import (
    Profile,
    VehicleOwnership,
    Document,
    DocumentReview,
)
from profiles.forms import (
    VehicleOwnershipForm,
    DocumentForm,
    DocumentReviewForm,
)


class VehicleOwnershipFormTests(TestCase):
    """Test cases for VehicleOwnershipForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_valid_form_with_all_fields(self):
        """Test form with all fields filled correctly."""
        form_data = {
            "plate_number": "JSD 123 AM",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": "CAR",
        }

        form = VehicleOwnershipForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_form_with_minimal_fields(self):
        """Test form with only required fields."""
        form_data = {"plate_number": "JSD 123 AM"}

        form = VehicleOwnershipForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_plate_number_format(self):
        """Test form validation for invalid plate number format."""
        invalid_plates = [
            "invalid",
            "123 ABC",
            "JSD123AM",
            "JSD 12 AM",
            "JSD 1234 AM",
            "jsd 123 am",  # lowercase
        ]

        for invalid_plate in invalid_plates:
            form_data = {"plate_number": invalid_plate}
            form = VehicleOwnershipForm(data=form_data)
            self.assertFalse(form.is_valid())
            self.assertIn("plate_number", form.errors)

    def test_missing_required_field(self):
        """Test form validation when required field is missing."""
        form_data = {}  # Missing plate_number

        form = VehicleOwnershipForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("plate_number", form.errors)

    def test_year_validation(self):
        """Test year field validation."""
        # Valid year
        form_data = {"plate_number": "JSD 123 AM", "year": 2020}
        form = VehicleOwnershipForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Year too old
        form_data["year"] = 1899
        form = VehicleOwnershipForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)

        # Year in future
        form_data["year"] = 2030
        form = VehicleOwnershipForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)

    def test_form_save(self):
        """Test form save functionality."""
        form_data = {
            "plate_number": "JSD 123 AM",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": "CAR",
        }

        form = VehicleOwnershipForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Save form (commit=False to set owner manually)
        vehicle = form.save(commit=False)
        vehicle.owner = self.user
        vehicle.save()

        # Check that vehicle was created correctly
        self.assertEqual(vehicle.plate_number, "JSD 123 AM")
        self.assertEqual(vehicle.make, "Toyota")
        self.assertEqual(vehicle.model, "Camry")
        self.assertEqual(vehicle.year, 2020)
        self.assertEqual(vehicle.vehicle_type, "CAR")
        self.assertEqual(vehicle.owner, self.user)


class DocumentFormTests(TestCase):
    """Test cases for DocumentForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # Create test files
        self.valid_pdf = SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"
        )

        self.valid_image = SimpleUploadedFile(
            "test.jpg", b"fake image content", content_type="image/jpeg"
        )

    def test_vehicle_document_form_choices(self):
        """Test form choices for vehicle documents."""
        form = DocumentForm(vehicle=self.vehicle)

        # Check that only vehicle document types are available
        doc_type_choices = [choice[0] for choice in form.fields["doc_type"].choices]
        self.assertIn("ROADWORTHY", doc_type_choices)
        self.assertIn("BLUEBOOK", doc_type_choices)
        self.assertNotIn("DRIVER_LICENSE", doc_type_choices)
        self.assertNotIn("PERMIT", doc_type_choices)

    def test_user_document_form_choices(self):
        """Test form choices for user-only documents."""
        form = DocumentForm(vehicle=None)

        # Check that only user document types are available
        doc_type_choices = [choice[0] for choice in form.fields["doc_type"].choices]
        self.assertIn("DRIVER_LICENSE", doc_type_choices)
        self.assertIn("PERMIT", doc_type_choices)
        self.assertNotIn("ROADWORTHY", doc_type_choices)
        self.assertNotIn("BLUEBOOK", doc_type_choices)

    def test_valid_vehicle_document_form(self):
        """Test valid vehicle document form submission."""
        form_data = {"doc_type": "ROADWORTHY"}

        form_files = {"file": self.valid_pdf}

        form = DocumentForm(data=form_data, files=form_files, vehicle=self.vehicle)
        self.assertTrue(form.is_valid())

    def test_valid_user_document_form(self):
        """Test valid user document form submission."""
        form_data = {"doc_type": "DRIVER_LICENSE"}

        form_files = {"file": self.valid_pdf}

        form = DocumentForm(data=form_data, files=form_files, vehicle=None)
        self.assertTrue(form.is_valid())

    def test_missing_file(self):
        """Test form validation when file is missing."""
        form_data = {"doc_type": "ROADWORTHY"}

        form = DocumentForm(data=form_data, vehicle=self.vehicle)
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_missing_doc_type(self):
        """Test form validation when doc_type is missing."""
        form_files = {"file": self.valid_pdf}

        form = DocumentForm(files=form_files, vehicle=self.vehicle)
        self.assertFalse(form.is_valid())
        self.assertIn("doc_type", form.errors)

    def test_invalid_file_size(self):
        """Test form validation for oversized files."""
        # Create a file larger than 5MB
        large_file = SimpleUploadedFile(
            "large.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf"  # 6MB
        )

        form_data = {"doc_type": "ROADWORTHY"}

        form_files = {"file": large_file}

        form = DocumentForm(data=form_data, files=form_files, vehicle=self.vehicle)
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)
        self.assertIn("5MB", str(form.errors["file"]))

    def test_invalid_file_type(self):
        """Test form validation for invalid file types."""
        invalid_file = SimpleUploadedFile(
            "test.txt", b"plain text content", content_type="text/plain"
        )

        form_data = {"doc_type": "ROADWORTHY"}

        form_files = {"file": invalid_file}

        form = DocumentForm(data=form_data, files=form_files, vehicle=self.vehicle)
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_form_save_vehicle_document(self):
        """Test saving vehicle document form."""
        form_data = {"doc_type": "ROADWORTHY"}

        form_files = {"file": self.valid_pdf}

        form = DocumentForm(data=form_data, files=form_files, vehicle=self.vehicle)
        self.assertTrue(form.is_valid())

        document = form.save(user=self.user, vehicle=self.vehicle)

        self.assertEqual(document.user, self.user)
        self.assertEqual(document.vehicle, self.vehicle)
        self.assertEqual(document.doc_type, "ROADWORTHY")
        self.assertTrue(document.file)

        # Check that DocumentReview was created
        self.assertTrue(
            DocumentReview.objects.filter(document=document, status="PENDING").exists()
        )

    def test_form_save_user_document(self):
        """Test saving user document form."""
        form_data = {"doc_type": "DRIVER_LICENSE"}

        form_files = {"file": self.valid_pdf}

        form = DocumentForm(data=form_data, files=form_files, vehicle=None)
        self.assertTrue(form.is_valid())

        document = form.save(user=self.user, vehicle=None)

        self.assertEqual(document.user, self.user)
        self.assertIsNone(document.vehicle)
        self.assertEqual(document.doc_type, "DRIVER_LICENSE")
        self.assertTrue(document.file)

        # Check that DocumentReview was created
        self.assertTrue(
            DocumentReview.objects.filter(document=document, status="PENDING").exists()
        )


class DocumentReviewFormTests(TestCase):
    """Test cases for DocumentReviewForm."""

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
        self.review = DocumentReview.objects.create(
            document=self.document, status="PENDING"
        )

    def test_valid_approval_form(self):
        """Test valid form for approving a document."""
        form_data = {
            "status": "APPROVED",
            "reason": "",  # Reason not required for approval
        }

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

    def test_valid_rejection_form(self):
        """Test valid form for rejecting a document."""
        form_data = {"status": "REJECTED", "reason": "Document is too blurry to read"}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

    def test_rejection_without_reason(self):
        """Test form validation when rejecting without providing reason."""
        form_data = {"status": "REJECTED", "reason": ""}  # Missing reason for rejection

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertFalse(form.is_valid())
        self.assertIn("reason", form.errors)

    def test_approval_with_reason(self):
        """Test that reason is optional when approving."""
        form_data = {"status": "APPROVED", "reason": "Document looks good"}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

    def test_pending_status(self):
        """Test form with pending status."""
        form_data = {"status": "PENDING", "reason": ""}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

    def test_form_save_approval(self):
        """Test saving form with approval status."""
        form_data = {"status": "APPROVED", "reason": ""}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

        review = form.save(reviewed_by=self.admin_user)

        self.assertEqual(review.status, "APPROVED")
        self.assertEqual(review.reviewed_by, self.admin_user)
        self.assertIsNotNone(review.reviewed_at)
        self.assertEqual(review.reason, "")

    def test_form_save_rejection(self):
        """Test saving form with rejection status."""
        form_data = {"status": "REJECTED", "reason": "Poor image quality"}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertTrue(form.is_valid())

        review = form.save(reviewed_by=self.admin_user)

        self.assertEqual(review.status, "REJECTED")
        self.assertEqual(review.reviewed_by, self.admin_user)
        self.assertIsNotNone(review.reviewed_at)
        self.assertEqual(review.reason, "Poor image quality")

    def test_missing_status(self):
        """Test form validation when status is missing."""
        form_data = {"reason": "Some reason"}

        form = DocumentReviewForm(data=form_data, instance=self.review)
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)


class FormIntegrationTests(TestCase):
    """Integration tests for the vehicle workflow forms."""

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

    def test_complete_form_workflow(self):
        """Test complete workflow using forms."""
        # Step 1: Create vehicle using form
        vehicle_data = {
            "plate_number": "JSD 123 AM",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": "CAR",
        }

        vehicle_form = VehicleOwnershipForm(data=vehicle_data)
        self.assertTrue(vehicle_form.is_valid())

        vehicle = vehicle_form.save(commit=False)
        vehicle.owner = self.user
        vehicle.save()

        # Step 2: Upload document using form
        document_data = {"doc_type": "ROADWORTHY"}

        document_files = {"file": SimpleUploadedFile("roadworthy.pdf", b"pdf content")}

        document_form = DocumentForm(
            data=document_data, files=document_files, vehicle=vehicle
        )
        self.assertTrue(document_form.is_valid())

        document = document_form.save(user=self.user, vehicle=vehicle)

        # Check that review was created automatically
        review = DocumentReview.objects.get(document=document)
        self.assertEqual(review.status, "PENDING")

        # Step 3: Review document using form
        review_data = {"status": "APPROVED", "reason": ""}

        review_form = DocumentReviewForm(data=review_data, instance=review)
        self.assertTrue(review_form.is_valid())

        updated_review = review_form.save(reviewed_by=self.admin_user)

        # Check final state
        self.assertEqual(updated_review.status, "APPROVED")
        self.assertEqual(updated_review.reviewed_by, self.admin_user)
        self.assertIsNotNone(updated_review.reviewed_at)

    def test_document_replacement_with_forms(self):
        """Test document replacement workflow using forms."""
        # Create vehicle
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # Upload initial document
        document_data = {"doc_type": "ROADWORTHY"}

        document_files = {"file": SimpleUploadedFile("original.pdf", b"pdf content")}

        document_form = DocumentForm(
            data=document_data, files=document_files, vehicle=vehicle
        )
        self.assertTrue(document_form.is_valid())

        original_document = document_form.save(user=self.user, vehicle=vehicle)
        original_review = DocumentReview.objects.get(document=original_document)

        # Reject the document
        review_data = {"status": "REJECTED", "reason": "Document is unclear"}

        review_form = DocumentReviewForm(data=review_data, instance=original_review)
        self.assertTrue(review_form.is_valid())

        rejected_review = review_form.save(reviewed_by=self.admin_user)
        self.assertEqual(rejected_review.status, "REJECTED")

        # Simulate document replacement (delete old, upload new)
        original_document.delete()

        # Upload new document
        new_document_files = {
            "file": SimpleUploadedFile("new.pdf", b"better pdf content")
        }

        new_document_form = DocumentForm(
            data=document_data, files=new_document_files, vehicle=vehicle
        )
        self.assertTrue(new_document_form.is_valid())

        new_document = new_document_form.save(user=self.user, vehicle=vehicle)

        # Check that new review was created
        new_review = DocumentReview.objects.get(document=new_document)
        self.assertEqual(new_review.status, "PENDING")

        # Approve the new document
        approval_data = {"status": "APPROVED", "reason": ""}

        approval_form = DocumentReviewForm(data=approval_data, instance=new_review)
        self.assertTrue(approval_form.is_valid())

        approved_review = approval_form.save(reviewed_by=self.admin_user)
        self.assertEqual(approved_review.status, "APPROVED")
