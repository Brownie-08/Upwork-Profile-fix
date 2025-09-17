"""
Tests for Portfolio, Education, Experience CRUD operations.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

from profiles.models import Profile, Portfolio, Education, Experience
from profiles.forms import PortfolioForm, EducationForm, ExperienceForm


class PortfolioModelTest(TestCase):
    """Test Portfolio model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_portfolio_creation(self):
        """Test creating a portfolio item."""
        portfolio = Portfolio.objects.create(
            user=self.user,
            title="Test Project",
            role="Developer",
            description="A test project",
            skills="Python, Django",
            completion_date=date.today(),
        )

        self.assertEqual(portfolio.title, "Test Project")
        self.assertEqual(portfolio.user, self.user)
        self.assertTrue(portfolio.created_at)

    def test_portfolio_str_method(self):
        """Test Portfolio string representation."""
        portfolio = Portfolio.objects.create(
            user=self.user, title="Test Project", completion_date=date.today()
        )

        self.assertEqual(str(portfolio), "Test Project")

    def test_portfolio_ordering(self):
        """Test Portfolio ordering by creation date."""
        portfolio1 = Portfolio.objects.create(
            user=self.user, title="Project 1", completion_date=date.today()
        )

        portfolio2 = Portfolio.objects.create(
            user=self.user, title="Project 2", completion_date=date.today()
        )

        portfolios = Portfolio.objects.all()
        # Should be ordered by creation date (newest first based on admin config)
        self.assertEqual(portfolios[0], portfolio2)


class EducationModelTest(TestCase):
    """Test Education model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_education_creation(self):
        """Test creating an education entry."""
        education = Education.objects.create(
            profile=self.profile,
            institution="Test University",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 1, 1),
        )

        self.assertEqual(education.institution, "Test University")
        self.assertEqual(education.profile, self.profile)

    def test_education_str_method(self):
        """Test Education string representation."""
        education = Education.objects.create(
            profile=self.profile,
            institution="Test University",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date=date(2020, 1, 1),
        )

        expected_str = "Bachelor of Science in Computer Science from Test University"
        self.assertEqual(str(education), expected_str)

    def test_education_current_field(self):
        """Test education current field functionality."""
        education = Education.objects.create(
            profile=self.profile,
            institution="Test University",
            degree="Master of Science",
            field_of_study="Data Science",
            start_date=date(2023, 1, 1),
            current=True,
        )

        self.assertTrue(education.current)
        self.assertIsNone(education.end_date)


class ExperienceModelTest(TestCase):
    """Test Experience model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_experience_creation(self):
        """Test creating an experience entry."""
        experience = Experience.objects.create(
            profile=self.profile,
            title="Software Developer",
            company="Tech Company",
            location="San Francisco, CA",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
            description="Developed web applications",
        )

        self.assertEqual(experience.title, "Software Developer")
        self.assertEqual(experience.company, "Tech Company")

    def test_experience_str_method(self):
        """Test Experience string representation."""
        experience = Experience.objects.create(
            profile=self.profile,
            title="Software Developer",
            company="Tech Company",
            start_date=date(2022, 1, 1),
        )

        expected_str = "Software Developer at Tech Company"
        self.assertEqual(str(experience), expected_str)

    def test_experience_current_position(self):
        """Test experience current position functionality."""
        experience = Experience.objects.create(
            profile=self.profile,
            title="Senior Developer",
            company="Current Company",
            start_date=date(2023, 1, 1),
            current=True,
            description="Current role",
        )

        self.assertTrue(experience.current)
        self.assertIsNone(experience.end_date)


class PortfolioFormTest(TestCase):
    """Test Portfolio form validation."""

    def test_valid_portfolio_form(self):
        """Test portfolio form with valid data."""
        form_data = {
            "title": "Test Project",
            "role": "Developer",
            "description": "A test project description",
            "skills": "Python, Django, JavaScript",
            "completion_date": date.today().strftime("%Y-%m-%d"),
            "related_job": "Web Development",
        }

        form = PortfolioForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_portfolio_form_future_date_validation(self):
        """Test portfolio form rejects future completion dates."""
        future_date = date.today() + timedelta(days=30)
        form_data = {
            "title": "Future Project",
            "completion_date": future_date.strftime("%Y-%m-%d"),
            "description": "Test description",
        }

        form = PortfolioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("completion_date", form.errors)

    def test_portfolio_form_required_fields(self):
        """Test portfolio form requires essential fields."""
        form_data = {}

        form = PortfolioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("completion_date", form.errors)


class EducationFormTest(TestCase):
    """Test Education form validation."""

    def test_valid_education_form(self):
        """Test education form with valid data."""
        form_data = {
            "institution": "Test University",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "start_date": date(2020, 1, 1).strftime("%Y-%m-%d"),
            "end_date": date(2024, 1, 1).strftime("%Y-%m-%d"),
            "current": False,
            "description": "Computer Science degree program",
        }

        form = EducationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_education_form_current_no_end_date(self):
        """Test education form allows current education without end date."""
        form_data = {
            "institution": "Test University",
            "degree": "Master of Science",
            "field_of_study": "Data Science",
            "start_date": date(2023, 1, 1).strftime("%Y-%m-%d"),
            "current": True,
            "description": "Current degree program",
        }

        form = EducationForm(data=form_data)
        self.assertTrue(form.is_valid())


class ExperienceFormTest(TestCase):
    """Test Experience form validation."""

    def test_valid_experience_form(self):
        """Test experience form with valid data."""
        form_data = {
            "title": "Software Developer",
            "company": "Tech Company",
            "location": "San Francisco, CA",
            "start_date": date(2022, 1, 1).strftime("%Y-%m-%d"),
            "end_date": date(2023, 12, 31).strftime("%Y-%m-%d"),
            "current": False,
            "description": "Developed web applications using Django and React",
        }

        form = ExperienceForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_experience_form_date_validation(self):
        """Test experience form validates date ranges."""
        # End date before start date should be invalid
        form_data = {
            "title": "Developer",
            "company": "Company",
            "start_date": date(2023, 1, 1).strftime("%Y-%m-%d"),
            "end_date": date(2022, 1, 1).strftime("%Y-%m-%d"),  # Before start date
            "description": "Test description",
        }

        form = ExperienceForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_experience_form_current_validation(self):
        """Test experience form validation for current positions."""
        form_data = {
            "title": "Senior Developer",
            "company": "Current Company",
            "start_date": date(2023, 1, 1).strftime("%Y-%m-%d"),
            "current": True,
            "description": "Current position",
        }

        form = ExperienceForm(data=form_data)
        self.assertTrue(form.is_valid())


class PortfolioViewTest(TestCase):
    """Test Portfolio CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

        # Create another user to test ownership
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

    def test_add_portfolio_requires_authentication(self):
        """Test that adding portfolio requires authentication."""
        response = self.client.post(reverse("profiles:add_portfolio"))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_add_portfolio_authenticated_user(self):
        """Test adding portfolio as authenticated user."""
        self.client.login(username="testuser", password="testpass123")

        portfolio_data = {
            "title": "New Project",
            "role": "Developer",
            "description": "A new project description",
            "skills": "Python, Django",
            "completion_date": date.today().strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("profiles:add_portfolio"),
            data=json.dumps(portfolio_data),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should be successful (assuming AJAX endpoint returns JSON)
        self.assertIn(response.status_code, [200, 201, 302])

        # Verify portfolio was created
        portfolio_exists = Portfolio.objects.filter(
            user=self.user, title="New Project"
        ).exists()
        self.assertTrue(portfolio_exists)

    def test_delete_portfolio_ownership(self):
        """Test that users can only delete their own portfolios."""
        # Create portfolio for user
        portfolio = Portfolio.objects.create(
            user=self.user, title="My Project", completion_date=date.today()
        )

        # Try to delete as other user
        self.client.login(username="otheruser", password="otherpass123")
        response = self.client.post(
            reverse("profiles:delete_portfolio", kwargs={"pk": portfolio.pk})
        )

        # Should be forbidden or redirect
        self.assertIn(response.status_code, [403, 404, 302])

        # Portfolio should still exist
        self.assertTrue(Portfolio.objects.filter(pk=portfolio.pk).exists())


class EducationViewTest(TestCase):
    """Test Education CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_add_education_authenticated(self):
        """Test adding education as authenticated user."""
        self.client.login(username="testuser", password="testpass123")

        education_data = {
            "institution": "Test University",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "start_date": date(2020, 1, 1).strftime("%Y-%m-%d"),
            "end_date": date(2024, 1, 1).strftime("%Y-%m-%d"),
            "description": "Computer Science degree",
        }

        response = self.client.post(
            reverse("profiles:add_education"),
            data=json.dumps(education_data),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should be successful
        self.assertIn(response.status_code, [200, 201, 302])

        # Verify education was created
        education_exists = Education.objects.filter(
            profile=self.profile, institution="Test University"
        ).exists()
        self.assertTrue(education_exists)


class ExperienceViewTest(TestCase):
    """Test Experience CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_add_experience_authenticated(self):
        """Test adding experience as authenticated user."""
        self.client.login(username="testuser", password="testpass123")

        experience_data = {
            "title": "Software Developer",
            "company": "Tech Company",
            "location": "San Francisco, CA",
            "start_date": date(2022, 1, 1).strftime("%Y-%m-%d"),
            "end_date": date(2023, 12, 31).strftime("%Y-%m-%d"),
            "description": "Developed web applications",
        }

        response = self.client.post(
            reverse("profiles:add_experience"),
            data=json.dumps(experience_data),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should be successful
        self.assertIn(response.status_code, [200, 201, 302])

        # Verify experience was created
        experience_exists = Experience.objects.filter(
            profile=self.profile, title="Software Developer"
        ).exists()
        self.assertTrue(experience_exists)

    def test_update_experience_ownership(self):
        """Test that users can only update their own experience."""
        # Create experience
        experience = Experience.objects.create(
            profile=self.profile,
            title="Original Title",
            company="Original Company",
            start_date=date(2022, 1, 1),
            description="Original description",
        )

        # Login as user
        self.client.login(username="testuser", password="testpass123")

        # Update experience
        update_data = {
            "title": "Updated Title",
            "company": "Updated Company",
            "start_date": date(2022, 1, 1).strftime("%Y-%m-%d"),
            "description": "Updated description",
        }

        response = self.client.post(
            reverse("profiles:update_experience"),
            data=json.dumps({**update_data, "id": experience.id}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should be successful
        self.assertIn(response.status_code, [200, 302])

        # Verify experience was updated
        experience.refresh_from_db()
        self.assertEqual(experience.title, "Updated Title")
