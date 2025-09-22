"""
Comprehensive test suite for the Vehicle & Document Workflow system.

This file imports and runs all the vehicle workflow tests to ensure 
everything works together properly.

Usage:
    python manage.py test profiles.tests.test_vehicle_workflow
    
Or run specific test modules:
    python manage.py test profiles.tests.test_vehicle_workflow_models
    python manage.py test profiles.tests.test_vehicle_workflow_forms
    python manage.py test profiles.tests.test_vehicle_workflow_views
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from profiles.models import Profile, VehicleOwnership, Document, DocumentReview
from notifications.models import Notification

# Import all test modules to ensure they're discovered
from .test_vehicle_workflow_models import *
from .test_vehicle_workflow_forms import *
from .test_vehicle_workflow_views import *


class VehicleWorkflowSystemTests(TestCase):
    """
    System-level integration tests for the complete Vehicle & Document Workflow.

    These tests ensure that all components (models, forms, views, admin)
    work together seamlessly to provide the complete user experience.
    """

    def setUp(self):
        """Set up test data for system tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Profiles are created automatically via signal
        self.profile = self.user.profile
        self.admin_profile = self.admin_user.profile

    def test_complete_vehicle_lifecycle(self):
        """
        Test the complete lifecycle of a vehicle through the workflow system.

        This test covers:
        1. User creates a vehicle
        2. User uploads required documents
        3. Admin reviews and approves/rejects documents
        4. User receives notifications
        5. Vehicle status is updated accordingly
        """
        # Step 1: Create vehicle
        vehicle = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
        )

        self.assertFalse(vehicle.is_fully_documented())
        self.assertEqual(vehicle.get_document_status("ROADWORTHY"), "MISSING")
        self.assertEqual(vehicle.get_document_status("BLUEBOOK"), "MISSING")

        # Step 2: Upload roadworthy certificate
        roadworthy_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("roadworthy.pdf", b"pdf content"),
        )

        # Review is automatically created
        roadworthy_review = DocumentReview.objects.get(document=roadworthy_doc)
        self.assertEqual(roadworthy_review.status, "PENDING")

        # Vehicle status should be updated
        self.assertEqual(vehicle.get_document_status("ROADWORTHY"), "PENDING")
        self.assertFalse(vehicle.is_fully_documented())

        # Step 3: Upload blue book
        bluebook_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="BLUEBOOK",
            file=SimpleUploadedFile("bluebook.pdf", b"pdf content"),
        )

        bluebook_review = DocumentReview.objects.get(document=bluebook_doc)
        self.assertEqual(bluebook_review.status, "PENDING")
        self.assertEqual(vehicle.get_document_status("BLUEBOOK"), "PENDING")
        self.assertFalse(vehicle.is_fully_documented())

        # Step 4: Admin rejects roadworthy certificate
        roadworthy_review.status = "REJECTED"
        roadworthy_review.reason = "Document is too blurry"
        roadworthy_review.reviewed_by = self.admin_user
        roadworthy_review.save()

        # Check notification was sent
        rejection_notification = Notification.objects.filter(
            user=self.user, message__icontains="rejected"
        ).first()
        self.assertIsNotNone(rejection_notification)
        self.assertIn("too blurry", rejection_notification.message)

        # Vehicle should still not be fully documented
        self.assertEqual(vehicle.get_document_status("ROADWORTHY"), "REJECTED")
        self.assertFalse(vehicle.is_fully_documented())

        # Step 5: User re-uploads roadworthy certificate
        # First delete the old one (this happens in the view)
        roadworthy_doc.delete()

        # Upload new document
        new_roadworthy_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("new_roadworthy.pdf", b"better pdf content"),
        )

        new_roadworthy_review = DocumentReview.objects.get(document=new_roadworthy_doc)
        self.assertEqual(new_roadworthy_review.status, "PENDING")

        # Step 6: Admin approves both documents
        new_roadworthy_review.status = "APPROVED"
        new_roadworthy_review.reviewed_by = self.admin_user
        new_roadworthy_review.save()

        bluebook_review.status = "APPROVED"
        bluebook_review.reviewed_by = self.admin_user
        bluebook_review.save()

        # Check approval notifications were sent
        approval_notifications = Notification.objects.filter(
            user=self.user, message__icontains="approved"
        ).count()
        self.assertEqual(approval_notifications, 2)  # One for each document

        # Step 7: Vehicle should now be fully documented
        self.assertEqual(vehicle.get_document_status("ROADWORTHY"), "APPROVED")
        self.assertEqual(vehicle.get_document_status("BLUEBOOK"), "APPROVED")
        self.assertTrue(vehicle.is_fully_documented())

    def test_driver_license_workflow(self):
        """
        Test the driver's license workflow (user-only document).

        This test covers:
        1. User uploads driver's license
        2. Admin reviews the document
        3. User receives appropriate notifications
        """
        # Step 1: Upload driver's license
        license_doc = Document.objects.create(
            user=self.user,
            vehicle=None,  # User-only document
            doc_type="DRIVER_LICENSE",
            file=SimpleUploadedFile("license.pdf", b"license content"),
        )

        # Review is automatically created
        license_review = DocumentReview.objects.get(document=license_doc)
        self.assertEqual(license_review.status, "PENDING")

        # Step 2: Admin approves the license
        license_review.status = "APPROVED"
        license_review.reviewed_by = self.admin_user
        license_review.save()

        # Step 3: Check notification was sent
        approval_notification = Notification.objects.filter(
            user=self.user, message__icontains="approved"
        ).first()
        self.assertIsNotNone(approval_notification)
        self.assertIn("Driver's License", approval_notification.message)

    def test_notification_system(self):
        """
        Test that the notification system works correctly for all scenarios.
        """
        # Create a document
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        document = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

        review = DocumentReview.objects.get(document=document)

        # Test approval notification
        review.status = "APPROVED"
        review.reviewed_by = self.admin_user
        review.save()

        approval_notification = Notification.objects.filter(
            user=self.user, message__icontains="approved"
        ).first()
        self.assertIsNotNone(approval_notification)

        # Reset for rejection test
        review.status = "REJECTED"
        review.reason = "Test rejection reason"
        review.save()

        rejection_notification = Notification.objects.filter(
            user=self.user, message__icontains="rejected"
        ).first()
        self.assertIsNotNone(rejection_notification)
        self.assertIn("Test rejection reason", rejection_notification.message)

        # Test that multiple saves don't create duplicate notifications
        initial_count = Notification.objects.filter(user=self.user).count()
        review.save()  # Save without changes
        final_count = Notification.objects.filter(user=self.user).count()
        self.assertEqual(initial_count, final_count)

    def test_document_replacement_system(self):
        """
        Test the document replacement functionality across the system.
        """
        # Create vehicle and initial document
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # Upload and reject first document
        original_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("original.pdf", b"original content"),
        )

        original_review = DocumentReview.objects.get(document=original_doc)
        original_review.status = "REJECTED"
        original_review.reason = "Poor quality"
        original_review.reviewed_by = self.admin_user
        original_review.save()

        # Check rejection notification
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, message__icontains="rejected"
            ).exists()
        )

        # Replace document (simulate what happens in view)
        original_doc.delete()

        new_doc = Document.objects.create(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("new.pdf", b"new content"),
        )

        # New review should be created automatically
        new_review = DocumentReview.objects.get(document=new_doc)
        self.assertEqual(new_review.status, "PENDING")

        # Approve new document
        new_review.status = "APPROVED"
        new_review.reviewed_by = self.admin_user
        new_review.save()

        # Check approval notification
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, message__icontains="approved"
            ).exists()
        )

        # Check vehicle status
        self.assertEqual(vehicle.get_document_status("ROADWORTHY"), "APPROVED")

    def test_system_data_integrity(self):
        """
        Test that the system maintains data integrity across operations.
        """
        # Create multiple vehicles and documents
        vehicles = []
        for i in range(3):
            vehicle = VehicleOwnership.objects.create(
                owner=self.user, plate_number=f"JSD {i+100} AM"
            )
            vehicles.append(vehicle)

            # Upload documents for each vehicle
            for doc_type in ["ROADWORTHY", "BLUEBOOK"]:
                doc = Document.objects.create(
                    user=self.user,
                    vehicle=vehicle,
                    doc_type=doc_type,
                    file=SimpleUploadedFile(f"{doc_type.lower()}_{i}.pdf", b"content"),
                )

                # Approve some, reject others
                review = DocumentReview.objects.get(document=doc)
                if i % 2 == 0:  # Approve even numbered vehicles
                    review.status = "APPROVED"
                    review.reviewed_by = self.admin_user
                    review.save()

        # Check data integrity
        total_vehicles = VehicleOwnership.objects.filter(owner=self.user).count()
        self.assertEqual(total_vehicles, 3)

        total_documents = Document.objects.filter(user=self.user).count()
        self.assertEqual(total_documents, 6)  # 3 vehicles × 2 docs each

        total_reviews = DocumentReview.objects.filter(document__user=self.user).count()
        self.assertEqual(total_reviews, 6)

        # Check notifications were created for approved documents
        approved_docs = DocumentReview.objects.filter(
            document__user=self.user, status="APPROVED"
        ).count()

        approval_notifications = Notification.objects.filter(
            user=self.user, message__icontains="approved"
        ).count()

        self.assertEqual(approved_docs, approval_notifications)

        # Check vehicle statuses
        for i, vehicle in enumerate(vehicles):
            if i % 2 == 0:  # Even numbered vehicles should be fully documented
                self.assertTrue(vehicle.is_fully_documented())
            else:  # Odd numbered vehicles should not be
                self.assertFalse(vehicle.is_fully_documented())

    def test_error_handling(self):
        """
        Test that the system handles edge cases and errors gracefully.
        """
        # Test accessing non-existent vehicle
        try:
            vehicle = VehicleOwnership.objects.get(id=99999)
            self.fail("Should have raised DoesNotExist")
        except VehicleOwnership.DoesNotExist:
            pass  # Expected

        # Test document without review
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        document = Document(
            user=self.user,
            vehicle=vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

        # Save without creating review (to test error handling)
        document.save()

        # Should still be able to get status (returns PENDING if no review)
        status = vehicle.get_document_status("ROADWORTHY")
        self.assertEqual(status, "PENDING")  # Should handle missing review gracefully

    def test_performance_considerations(self):
        """
        Test that the system performs well with larger datasets.

        This is a basic performance test to ensure queries don't become
        problematic with more data.
        """
        # Create multiple users and vehicles
        users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f"user{i}", email=f"user{i}@example.com", password="password"
            )
            # Profile is created automatically via signal
            users.append(user)

            # Each user has multiple vehicles
            for j in range(5):
                vehicle = VehicleOwnership.objects.create(
                    owner=user, plate_number=f"JSD {i*10+j:03d} AM"
                )

                # Each vehicle has documents
                for doc_type in ["ROADWORTHY", "BLUEBOOK"]:
                    doc = Document.objects.create(
                        user=user,
                        vehicle=vehicle,
                        doc_type=doc_type,
                        file=SimpleUploadedFile(f"doc_{i}_{j}.pdf", b"content"),
                    )

        # Test that queries still perform reasonably
        from django.test.utils import override_settings
        from django.db import connection

        with override_settings(DEBUG=True):
            # Clear query log
            connection.queries.clear()

            # Perform some typical operations
            all_vehicles = list(VehicleOwnership.objects.all())
            self.assertEqual(len(all_vehicles), 50)  # 10 users × 5 vehicles

            # Check that we don't have an excessive number of queries
            query_count = len(connection.queries)
            self.assertLess(query_count, 100)  # Reasonable threshold

            # Test document status checking
            test_vehicle = all_vehicles[0]
            status = test_vehicle.get_document_status("ROADWORTHY")
            self.assertIn(status, ["MISSING", "PENDING", "APPROVED", "REJECTED"])


# Test discovery helper
def load_tests(loader, standard_tests, pattern):
    """
    Custom test loader to ensure all vehicle workflow tests are discovered.
    """
    # Load tests from all modules
    from . import test_vehicle_workflow_models
    from . import test_vehicle_workflow_forms
    from . import test_vehicle_workflow_views

    suite = standard_tests

    # Add tests from each module
    for module in [
        test_vehicle_workflow_models,
        test_vehicle_workflow_forms,
        test_vehicle_workflow_views,
    ]:
        module_tests = loader.loadTestsFromModule(module)
        suite.addTests(module_tests)

    return suite


if __name__ == "__main__":
    """
    Allow running tests directly with: python test_vehicle_workflow.py
    """
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    if not settings.configured:
        # Configure Django settings for standalone test execution
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "profiles",
            ],
        )
        django.setup()

    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])

    if failures:
        exit(1)
