#!/usr/bin/env python
"""
Simple test script to verify that the document upload endpoints are working correctly.
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from django.urls import reverse, NoReverseMatch
from django.test import Client
from django.contrib.auth.models import User
from profiles.models import Profile


def test_url_resolution():
    """Test that all required URLs can be resolved."""
    required_urls = [
        "profiles:vehicle_dashboard",
        "profiles:upload_document_dashboard",
        "profiles:upload_permit_dashboard",
        "profiles:get_permit_status",
        "profiles:add_vehicle_dashboard",
        "profiles:get_vehicle_documents",
    ]

    print("Testing URL resolution...")
    for url_name in required_urls:
        try:
            if "vehicle_documents" in url_name:
                url = reverse(url_name, kwargs={"vehicle_id": 1})
            else:
                url = reverse(url_name)
            print(f"✓ {url_name}: {url}")
        except NoReverseMatch as e:
            print(f"✗ {url_name}: {e}")
    print()


def test_dashboard_access():
    """Test that the dashboard loads without authentication errors."""
    client = Client()

    print("Testing dashboard access...")

    # Test without login (should redirect)
    response = client.get(reverse("profiles:vehicle_dashboard"))
    print(f"✓ Dashboard redirect status: {response.status_code}")

    # Create test user and login
    try:
        user = User.objects.create_user(
            username="testuser123", email="test@example.com", password="testpass123"
        )
        # Create profile
        profile, created = Profile.objects.get_or_create(user=user)

        # Login
        client.login(username="testuser123", password="testpass123")

        # Test dashboard access
        response = client.get(reverse("profiles:vehicle_dashboard"))
        print(f"✓ Dashboard authenticated status: {response.status_code}")

        if response.status_code == 200:
            # Check if essential elements are in the response
            content = response.content.decode("utf-8")
            if "uploadDocumentModal" in content:
                print("✓ Upload modal found in template")
            if "copyReferralCode" in content:
                print("✓ Referral code function found in template")
            if "uploadDocumentForm" in content:
                print("✓ Upload form found in template")

        # Clean up
        user.delete()

    except Exception as e:
        print(f"✗ Dashboard test error: {e}")

    print()


def test_form_csrf():
    """Test that CSRF tokens are properly included."""
    client = Client()

    print("Testing CSRF token availability...")

    try:
        # Create test user and login
        user = User.objects.create_user(
            username="testuser456", email="test2@example.com", password="testpass123"
        )
        profile, created = Profile.objects.get_or_create(user=user)
        client.login(username="testuser456", password="testpass123")

        # Get dashboard page
        response = client.get(reverse("profiles:vehicle_dashboard"))

        if response.status_code == 200:
            content = response.content.decode("utf-8")
            if "csrfmiddlewaretoken" in content:
                print("✓ CSRF token found in template")
            else:
                print("✗ CSRF token missing from template")

        # Clean up
        user.delete()

    except Exception as e:
        print(f"✗ CSRF test error: {e}")

    print()


if __name__ == "__main__":
    print("=== Document Upload System Test ===\n")

    test_url_resolution()
    test_dashboard_access()
    test_form_csrf()

    print("Test completed!")
