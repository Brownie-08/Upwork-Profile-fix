"""
Test cases for the vehicle workflow views (dashboard views and API endpoints).
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from profiles.models import Profile, VehicleOwnership, Document, DocumentReview
from notifications.models import Notification


class VehicleDashboardViewTests(TestCase):
    """Test cases for the vehicle dashboard view."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user."""
        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vehicle Dashboard")
        self.assertContains(response, "Driver's License")
        self.assertIn("vehicles", response.context)
        self.assertIn("driver_license_status", response.context)

    def test_dashboard_view_unauthenticated(self):
        """Test dashboard view redirects unauthenticated users."""
        self.client.logout()
        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_with_vehicles(self):
        """Test dashboard view with existing vehicles."""
        # Create test vehicles
        vehicle1 = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
            vehicle_type="CAR",
        )

        vehicle2 = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 456 BC",
            make="Honda",
            model="Civic",
            year=2019,
            vehicle_type="CAR",
        )

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JSD 123 AM")
        self.assertContains(response, "JSD 456 BC")
        self.assertContains(response, "Toyota Camry")
        self.assertContains(response, "Honda Civic")
        self.assertEqual(len(response.context["vehicles"]), 2)

    def test_dashboard_driver_license_status(self):
        """Test driver's license status display."""
        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        # Should show missing status initially
        self.assertEqual(response.context["driver_license_status"], "MISSING")

        # Upload driver's license
        Document.objects.create(
            user=self.user,
            doc_type="DRIVER_LICENSE",
            file=SimpleUploadedFile("license.pdf", b"content"),
        )

        response = self.client.get(reverse("profiles:vehicle_dashboard"))

        # Should show pending status
        self.assertEqual(response.context["driver_license_status"], "PENDING")


class AddVehicleViewTests(TestCase):
    """Test cases for the add vehicle API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_add_vehicle_success(self):
        """Test successful vehicle addition."""
        data = {
            "plate_number": "JSD 123 AM",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": "CAR",
        }

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("message", response_data)
        self.assertIn("vehicle", response_data)

        # Check vehicle was created
        self.assertTrue(
            VehicleOwnership.objects.filter(
                owner=self.user, plate_number="JSD 123 AM"
            ).exists()
        )

    def test_add_vehicle_minimal_data(self):
        """Test adding vehicle with minimal required data."""
        data = {"plate_number": "JSD 123 AM"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check vehicle was created
        vehicle = VehicleOwnership.objects.get(
            owner=self.user, plate_number="JSD 123 AM"
        )
        self.assertEqual(vehicle.plate_number, "JSD 123 AM")
        self.assertEqual(vehicle.make, "")  # Should be empty

    def test_add_vehicle_invalid_data(self):
        """Test adding vehicle with invalid data."""
        data = {"plate_number": "invalid-plate"}  # Invalid format

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("errors", response_data)

    def test_add_vehicle_duplicate_plate(self):
        """Test adding vehicle with duplicate plate number."""
        # Create first vehicle
        VehicleOwnership.objects.create(owner=self.user, plate_number="JSD 123 AM")

        # Try to create another with same plate
        data = {"plate_number": "JSD 123 AM"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])

    def test_add_vehicle_unauthenticated(self):
        """Test adding vehicle without authentication."""
        self.client.logout()

        data = {"plate_number": "JSD 123 AM"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"), data=data
        )

        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_add_vehicle_non_ajax(self):
        """Test adding vehicle via non-AJAX request."""
        data = {"plate_number": "JSD 123 AM"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=data,
            # No XMLHttpRequest header
        )

        self.assertEqual(response.status_code, 405)  # Method not allowed

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])


class UploadDocumentViewTests(TestCase):
    """Test cases for the upload document API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_upload_vehicle_document_success(self):
        """Test successful vehicle document upload."""
        test_file = SimpleUploadedFile(
            "roadworthy.pdf", b"PDF content", content_type="application/pdf"
        )

        data = {
            "vehicle_id": self.vehicle.id,
            "doc_type": "ROADWORTHY",
            "file": test_file,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("message", response_data)

        # Check document was created
        self.assertTrue(
            Document.objects.filter(
                user=self.user, vehicle=self.vehicle, doc_type="ROADWORTHY"
            ).exists()
        )

        # Check review was created
        document = Document.objects.get(
            user=self.user, vehicle=self.vehicle, doc_type="ROADWORTHY"
        )
        self.assertTrue(
            DocumentReview.objects.filter(document=document, status="PENDING").exists()
        )

    def test_upload_user_document_success(self):
        """Test successful user document upload."""
        test_file = SimpleUploadedFile(
            "license.pdf", b"PDF content", content_type="application/pdf"
        )

        data = {
            "vehicle_id": "",  # Empty for user document
            "doc_type": "DRIVER_LICENSE",
            "file": test_file,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check document was created
        self.assertTrue(
            Document.objects.filter(
                user=self.user, vehicle=None, doc_type="DRIVER_LICENSE"
            ).exists()
        )

    def test_upload_document_replace_existing(self):
        """Test uploading document replaces existing one."""
        # Create existing document
        existing_doc = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("old.pdf", b"old content"),
        )

        # Create review for existing document
        DocumentReview.objects.create(
            document=existing_doc, status="REJECTED", reason="Poor quality"
        )

        # Upload new document
        test_file = SimpleUploadedFile(
            "new.pdf", b"new content", content_type="application/pdf"
        )

        data = {
            "vehicle_id": self.vehicle.id,
            "doc_type": "ROADWORTHY",
            "file": test_file,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        # Check old document was deleted and new one created
        self.assertFalse(Document.objects.filter(id=existing_doc.id).exists())

        new_document = Document.objects.get(
            user=self.user, vehicle=self.vehicle, doc_type="ROADWORTHY"
        )

        # Check new review was created with PENDING status
        new_review = DocumentReview.objects.get(document=new_document)
        self.assertEqual(new_review.status, "PENDING")

    def test_upload_document_missing_file(self):
        """Test upload without file."""
        data = {
            "vehicle_id": self.vehicle.id,
            "doc_type": "ROADWORTHY",
            # Missing file
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])

    def test_upload_document_invalid_vehicle(self):
        """Test upload with invalid vehicle ID."""
        test_file = SimpleUploadedFile(
            "test.pdf", b"content", content_type="application/pdf"
        )

        data = {
            "vehicle_id": 99999,  # Non-existent vehicle
            "doc_type": "ROADWORTHY",
            "file": test_file,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("Vehicle not found", response_data["message"])


class GetVehicleDocumentsViewTests(TestCase):
    """Test cases for the get vehicle documents API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user,
            plate_number="JSD 123 AM",
            make="Toyota",
            model="Camry",
            year=2020,
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_get_vehicle_documents_success(self):
        """Test successful retrieval of vehicle documents."""
        # Create documents
        roadworthy_doc = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("roadworthy.pdf", b"content"),
        )

        bluebook_doc = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="BLUEBOOK",
            file=SimpleUploadedFile("bluebook.pdf", b"content"),
        )

        # Create reviews
        DocumentReview.objects.create(document=roadworthy_doc, status="APPROVED")

        DocumentReview.objects.create(document=bluebook_doc, status="PENDING")

        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[self.vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("vehicle", response_data)
        self.assertIn("documents", response_data)

        # Check vehicle info
        vehicle_data = response_data["vehicle"]
        self.assertEqual(vehicle_data["plate_number"], "JSD 123 AM")
        self.assertEqual(vehicle_data["display_name"], "2020 Toyota Camry (JSD 123 AM)")

        # Check documents
        documents = response_data["documents"]
        self.assertEqual(len(documents), 2)  # Should include both required docs

        # Find roadworthy document
        roadworthy = next(d for d in documents if d["doc_type"] == "ROADWORTHY")
        self.assertEqual(roadworthy["status"], "APPROVED")
        self.assertEqual(roadworthy["doc_type_display"], "Roadworthiness Certificate")

        # Find bluebook document
        bluebook = next(d for d in documents if d["doc_type"] == "BLUEBOOK")
        self.assertEqual(bluebook["status"], "PENDING")

    def test_get_vehicle_documents_no_documents(self):
        """Test retrieval when no documents are uploaded."""
        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[self.vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Should still return required document types with MISSING status
        documents = response_data["documents"]
        self.assertEqual(len(documents), 2)

        for doc in documents:
            self.assertEqual(doc["status"], "MISSING")

    def test_get_vehicle_documents_invalid_vehicle(self):
        """Test retrieval with invalid vehicle ID."""
        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[99999]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])

    def test_get_vehicle_documents_wrong_owner(self):
        """Test retrieval of another user's vehicle documents."""
        # Create another user and their vehicle
        other_user = User.objects.create_user(username="otheruser", password="pass")
        other_vehicle = VehicleOwnership.objects.create(
            owner=other_user, plate_number="JSD 456 BC"
        )

        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[other_vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)


class DeleteVehicleViewTests(TestCase):
    """Test cases for the delete vehicle API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)
        self.vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_delete_vehicle_success(self):
        """Test successful vehicle deletion."""
        response = self.client.delete(
            reverse("profiles:delete_vehicle_dashboard", args=[self.vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("message", response_data)

        # Check vehicle was deleted
        self.assertFalse(VehicleOwnership.objects.filter(id=self.vehicle.id).exists())

    def test_delete_vehicle_with_documents(self):
        """Test deleting vehicle with associated documents."""
        # Create documents for the vehicle
        doc = Document.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            doc_type="ROADWORTHY",
            file=SimpleUploadedFile("test.pdf", b"content"),
        )

        DocumentReview.objects.create(document=doc, status="PENDING")

        response = self.client.delete(
            reverse("profiles:delete_vehicle_dashboard", args=[self.vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)

        # Check vehicle and related documents were deleted
        self.assertFalse(VehicleOwnership.objects.filter(id=self.vehicle.id).exists())
        self.assertFalse(Document.objects.filter(vehicle=self.vehicle).exists())

    def test_delete_vehicle_invalid_id(self):
        """Test deleting vehicle with invalid ID."""
        response = self.client.delete(
            reverse("profiles:delete_vehicle_dashboard", args=[99999]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)

        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])

    def test_delete_vehicle_wrong_owner(self):
        """Test deleting another user's vehicle."""
        # Create another user and their vehicle
        other_user = User.objects.create_user(username="otheruser", password="pass")
        other_vehicle = VehicleOwnership.objects.create(
            owner=other_user, plate_number="JSD 456 BC"
        )

        response = self.client.delete(
            reverse("profiles:delete_vehicle_dashboard", args=[other_vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_vehicle_unauthenticated(self):
        """Test deleting vehicle without authentication."""
        self.client.logout()

        response = self.client.delete(
            reverse("profiles:delete_vehicle_dashboard", args=[self.vehicle.id])
        )

        self.assertEqual(response.status_code, 302)  # Redirect to login


class ViewIntegrationTests(TestCase):
    """Integration tests for the vehicle workflow views."""

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
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_complete_vehicle_workflow_via_views(self):
        """Test complete workflow using views."""
        # Step 1: Visit dashboard (initially empty)
        response = self.client.get(reverse("profiles:vehicle_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["vehicles"]), 0)

        # Step 2: Add vehicle
        add_data = {
            "plate_number": "JSD 123 AM",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "vehicle_type": "CAR",
        }

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=add_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Get the created vehicle
        vehicle = VehicleOwnership.objects.get(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # Step 3: Upload document
        test_file = SimpleUploadedFile(
            "roadworthy.pdf", b"PDF content", content_type="application/pdf"
        )

        upload_data = {
            "vehicle_id": vehicle.id,
            "doc_type": "ROADWORTHY",
            "file": test_file,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=upload_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Step 4: Check document status
        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        documents = response_data["documents"]

        # Find roadworthy document
        roadworthy = next(d for d in documents if d["doc_type"] == "ROADWORTHY")
        self.assertEqual(roadworthy["status"], "PENDING")

        # Step 5: Visit dashboard to see updated state
        response = self.client.get(reverse("profiles:vehicle_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["vehicles"]), 1)

        # Vehicle should show in dashboard with document status
        context_vehicle = response.context["vehicles"][0]
        self.assertEqual(context_vehicle.plate_number, "JSD 123 AM")

    def test_document_replacement_via_views(self):
        """Test document replacement workflow via views."""
        # Create vehicle
        vehicle = VehicleOwnership.objects.create(
            owner=self.user, plate_number="JSD 123 AM"
        )

        # Upload initial document
        test_file1 = SimpleUploadedFile(
            "original.pdf", b"Original PDF content", content_type="application/pdf"
        )

        upload_data = {
            "vehicle_id": vehicle.id,
            "doc_type": "ROADWORTHY",
            "file": test_file1,
        }

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=upload_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Get initial document
        initial_doc = Document.objects.get(
            user=self.user, vehicle=vehicle, doc_type="ROADWORTHY"
        )
        initial_doc_id = initial_doc.id

        # Upload replacement document
        test_file2 = SimpleUploadedFile(
            "replacement.pdf",
            b"Replacement PDF content",
            content_type="application/pdf",
        )

        upload_data["file"] = test_file2

        response = self.client.post(
            reverse("profiles:upload_document_dashboard"),
            data=upload_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Check that old document was replaced
        self.assertFalse(Document.objects.filter(id=initial_doc_id).exists())

        # Check that new document exists
        new_doc = Document.objects.get(
            user=self.user, vehicle=vehicle, doc_type="ROADWORTHY"
        )
        self.assertNotEqual(new_doc.id, initial_doc_id)

        # Check that new review was created with PENDING status
        new_review = DocumentReview.objects.get(document=new_doc)
        self.assertEqual(new_review.status, "PENDING")

        # Check document status via API
        response = self.client.get(
            reverse("profiles:get_vehicle_documents", args=[vehicle.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        documents = response_data["documents"]
        roadworthy = next(d for d in documents if d["doc_type"] == "ROADWORTHY")
        self.assertEqual(roadworthy["status"], "PENDING")

    def test_multiple_vehicles_workflow(self):
        """Test workflow with multiple vehicles."""
        # Add first vehicle
        add_data1 = {"plate_number": "JSD 123 AM", "make": "Toyota", "model": "Camry"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=add_data1,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Add second vehicle
        add_data2 = {"plate_number": "JSD 456 BC", "make": "Honda", "model": "Civic"}

        response = self.client.post(
            reverse("profiles:add_vehicle_dashboard"),
            data=add_data2,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        # Check both vehicles appear in dashboard
        response = self.client.get(reverse("profiles:vehicle_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["vehicles"]), 2)

        # Upload documents for both vehicles
        vehicles = VehicleOwnership.objects.filter(owner=self.user)

        for vehicle in vehicles:
            test_file = SimpleUploadedFile(
                f"doc_{vehicle.plate_number}.pdf",
                b"PDF content",
                content_type="application/pdf",
            )

            upload_data = {
                "vehicle_id": vehicle.id,
                "doc_type": "ROADWORTHY",
                "file": test_file,
            }

            response = self.client.post(
                reverse("profiles:upload_document_dashboard"),
                data=upload_data,
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)

        # Check that documents were uploaded for both vehicles
        self.assertEqual(
            Document.objects.filter(user=self.user, doc_type="ROADWORTHY").count(), 2
        )
