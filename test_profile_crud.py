#!/usr/bin/env python
"""
Test script to check Profile CRUD functionality (Skills, Experience, Education, Portfolio).

This script tests the specific issues mentioned:
1. Document Status Sync (already tested in vehicle workflow)
2. Profile CRUD operations not saving
3. Ajax requests with proper CSRF and content types

Usage: python test_profile_crud.py
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, "/user/main_project")  # Adjust path as needed

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import JsonResponse
import json

from profiles.models import (
    Profile,
    Experience,
    Education,
    Portfolio,
    Skill,
    ProfileSkill,
)


class ProfileCRUDTestCase(TestCase):
    """Test Profile CRUD operations work correctly"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = self.user.profile  # Created automatically by signal
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_add_experience_ajax(self):
        """Test adding experience via AJAX"""
        experience_data = {
            "title": "Software Developer",
            "company": "Test Company",
            "location": "Mbabane, Eswatini",
            "start_date": "2022-01-01",
            "end_date": "2023-12-31",
            "current": False,
            "description": "Developed web applications using Django",
        }

        response = self.client.post(
            reverse("profiles:add_experience"),
            data=experience_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that experience was saved
        experience = Experience.objects.filter(profile=self.profile).first()
        self.assertIsNotNone(experience)
        self.assertEqual(experience.title, "Software Developer")
        self.assertEqual(experience.company, "Test Company")

    def test_add_education_ajax(self):
        """Test adding education via AJAX"""
        education_data = {
            "institution": "University of Eswatini",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "start_date": "2018-08-01",
            "end_date": "2022-05-31",
            "current": False,
            "description": "Studied computer science fundamentals",
        }

        response = self.client.post(
            reverse("profiles:add_education"),
            data=education_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that education was saved
        education = Education.objects.filter(profile=self.profile).first()
        self.assertIsNotNone(education)
        self.assertEqual(education.institution, "University of Eswatini")
        self.assertEqual(education.degree, "Bachelor of Science")

    def test_add_skill_ajax(self):
        """Test adding skill via AJAX"""
        skill_data = {
            "skill_name": "Python",
            "skill_category": "Programming Languages",
            "proficiency": "ADV",
            "years_of_experience": 5,
        }

        response = self.client.post(
            reverse("profiles:add_skill"),
            data=skill_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that skill was saved
        profile_skill = ProfileSkill.objects.filter(profile=self.profile).first()
        self.assertIsNotNone(profile_skill)
        self.assertEqual(profile_skill.skill.name, "Python")
        self.assertEqual(profile_skill.proficiency, "ADV")

    def test_add_portfolio_ajax(self):
        """Test adding portfolio via AJAX"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a simple image file for testing
        image_file = SimpleUploadedFile(
            "test_image.jpg", b"fake image content", content_type="image/jpeg"
        )

        portfolio_data = {
            "title": "Web Application",
            "role": "Full Stack Developer",
            "description": "Built a complete web application using Django and React",
            "skills": "Python, Django, React, JavaScript",
            "related_job": "Freelance Project",
            "completion_date": "2023-06-01",
        }

        response = self.client.post(
            reverse("profiles:add_portfolio"),
            data=portfolio_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that portfolio was saved
        portfolio = Portfolio.objects.filter(user=self.user).first()
        self.assertIsNotNone(portfolio)
        self.assertEqual(portfolio.title, "Web Application")
        self.assertEqual(portfolio.role, "Full Stack Developer")

    def test_update_experience_ajax(self):
        """Test updating existing experience"""
        # First create an experience
        experience = Experience.objects.create(
            profile=self.profile,
            title="Junior Developer",
            company="Old Company",
            start_date="2021-01-01",
            description="Initial role",
        )

        # Now update it
        update_data = {
            "id": experience.id,
            "title": "Senior Developer",
            "company": "New Company",
            "location": "Manzini, Eswatini",
            "start_date": "2021-01-01",
            "end_date": "2023-12-31",
            "current": False,
            "description": "Updated role with more responsibilities",
        }

        response = self.client.post(
            reverse("profiles:update_experience"),
            data=update_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that experience was updated
        experience.refresh_from_db()
        self.assertEqual(experience.title, "Senior Developer")
        self.assertEqual(experience.company, "New Company")

    def test_csrf_token_handling(self):
        """Test that AJAX requests handle CSRF tokens properly"""
        # Get CSRF token
        csrf_response = self.client.get(reverse("profiles:profile"))
        csrf_token = csrf_response.cookies["csrftoken"].value

        skill_data = {
            "skill_name": "Django",
            "skill_category": "Web Frameworks",
            "proficiency": "EXP",
            "years_of_experience": 3,
            "csrfmiddlewaretoken": csrf_token,
        }

        response = self.client.post(
            reverse("profiles:add_skill"),
            data=skill_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should succeed even with explicit CSRF token
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

    def test_error_handling(self):
        """Test that validation errors are properly handled"""
        # Try to add experience with missing required fields
        experience_data = {
            "title": "",  # Missing required field
            "company": "Test Company",
            "start_date": "invalid-date",  # Invalid date format
        }

        response = self.client.post(
            reverse("profiles:add_experience"),
            data=experience_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertIn("errors", response_data)

    def test_content_types(self):
        """Test different content types are handled correctly"""
        # Test with form data
        skill_data = {
            "skill_name": "JavaScript",
            "proficiency": "INT",
        }

        response = self.client.post(
            reverse("profiles:add_skill"),
            data=skill_data,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])


def run_tests():
    """Run the tests"""
    from django.test.runner import DiscoverRunner
    from django.conf import settings

    # Configure test settings
    settings.DEBUG = True
    settings.TESTING = True

    runner = DiscoverRunner(verbosity=2, interactive=False)
    failures = runner.run_tests(["__main__"])

    if failures:
        print("❌ Some tests failed!")
        return False
    else:
        print("✅ All tests passed!")
        return True


if __name__ == "__main__":
    print("Testing Profile CRUD functionality...")
    print("=" * 50)

    try:
        # Import test classes and run them
        suite = django.test.TestSuite()

        # Add all test methods
        suite.addTest(ProfileCRUDTestCase("test_add_experience_ajax"))
        suite.addTest(ProfileCRUDTestCase("test_add_education_ajax"))
        suite.addTest(ProfileCRUDTestCase("test_add_skill_ajax"))
        suite.addTest(ProfileCRUDTestCase("test_add_portfolio_ajax"))
        suite.addTest(ProfileCRUDTestCase("test_update_experience_ajax"))
        suite.addTest(ProfileCRUDTestCase("test_csrf_token_handling"))
        suite.addTest(ProfileCRUDTestCase("test_error_handling"))
        suite.addTest(ProfileCRUDTestCase("test_content_types"))

        # Run the tests
        runner = django.test.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if result.wasSuccessful():
            print("\n✅ All Profile CRUD tests passed!")
            print(
                "Skills, Experience, Education, and Portfolio operations are working correctly."
            )
        else:
            print(
                f"\n❌ {len(result.failures)} tests failed, {len(result.errors)} errors"
            )
            for test, traceback in result.failures + result.errors:
                print(f"FAILED: {test}")
                print(f"ERROR: {traceback}\n")

    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        sys.exit(1)
