#!/usr/bin/env python
"""
Simple test to verify Profile CRUD functionality works.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
import json
from profiles.models import Experience, Education, ProfileSkill, Portfolio


def test_profile_crud():
    """Test Profile CRUD operations"""

    # Create test user
    try:
        User.objects.get(username="testuser").delete()
    except User.DoesNotExist:
        pass

    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )

    # Create test client and login
    client = Client()
    client.login(username="testuser", password="testpass123")

    print("✅ User created and logged in successfully")

    # Test 1: Add Experience
    print("\n📝 Testing add experience...")
    experience_data = {
        "title": "Software Developer",
        "company": "Test Company",
        "location": "Mbabane, Eswatini",
        "start_date": "2022-01-01",
        "end_date": "2023-12-31",
        "current": False,
        "description": "Developed web applications using Django",
    }

    response = client.post(
        reverse("profiles:add_experience"),
        data=experience_data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    if response.status_code == 200:
        try:
            response_data = json.loads(response.content)
            if response_data.get("success"):
                experience = Experience.objects.filter(profile=user.profile).first()
                if experience and experience.title == "Software Developer":
                    print("✅ Experience added successfully")
                else:
                    print("❌ Experience not saved properly")
            else:
                print(f"❌ Experience add failed: {response_data}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.content}")
    else:
        print(f"❌ Add experience failed with status {response.status_code}")

    # Test 2: Add Education
    print("\n🎓 Testing add education...")
    education_data = {
        "institution": "University of Eswatini",
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "start_date": "2018-08-01",
        "end_date": "2022-05-31",
        "current": False,
        "description": "Studied computer science fundamentals",
    }

    response = client.post(
        reverse("profiles:add_education"),
        data=education_data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    if response.status_code == 200:
        try:
            response_data = json.loads(response.content)
            if response_data.get("success"):
                education = Education.objects.filter(profile=user.profile).first()
                if education and education.institution == "University of Eswatini":
                    print("✅ Education added successfully")
                else:
                    print("❌ Education not saved properly")
            else:
                print(f"❌ Education add failed: {response_data}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.content}")
    else:
        print(f"❌ Add education failed with status {response.status_code}")

    # Test 3: Add Skill
    print("\n🔧 Testing add skill...")
    skill_data = {
        "skill_name": "Python",
        "skill_category": "Programming Languages",
        "proficiency": "ADV",
        "years_of_experience": 5,
    }

    response = client.post(
        reverse("profiles:add_skill"),
        data=skill_data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    if response.status_code == 200:
        try:
            response_data = json.loads(response.content)
            if response_data.get("success"):
                skill = ProfileSkill.objects.filter(profile=user.profile).first()
                if skill and skill.skill.name == "Python":
                    print("✅ Skill added successfully")
                else:
                    print("❌ Skill not saved properly")
            else:
                print(f"❌ Skill add failed: {response_data}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.content}")
    else:
        print(f"❌ Add skill failed with status {response.status_code}")

    # Test 4: Add Portfolio
    print("\n💼 Testing add portfolio...")
    portfolio_data = {
        "title": "Web Application",
        "role": "Full Stack Developer",
        "description": "Built a complete web application using Django and React",
        "skills": "Python, Django, React, JavaScript",
        "related_job": "Freelance Project",
        "completion_date": "2023-06-01",
    }

    response = client.post(
        reverse("profiles:add_portfolio"),
        data=portfolio_data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    if response.status_code == 200:
        try:
            response_data = json.loads(response.content)
            if response_data.get("success"):
                portfolio = Portfolio.objects.filter(user=user).first()
                if portfolio and portfolio.title == "Web Application":
                    print("✅ Portfolio added successfully")
                else:
                    print("❌ Portfolio not saved properly")
            else:
                print(f"❌ Portfolio add failed: {response_data}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.content}")
    else:
        print(f"❌ Add portfolio failed with status {response.status_code}")

    # Summary
    exp_count = Experience.objects.filter(profile=user.profile).count()
    edu_count = Education.objects.filter(profile=user.profile).count()
    skill_count = ProfileSkill.objects.filter(profile=user.profile).count()
    port_count = Portfolio.objects.filter(user=user).count()

    print(f"\n📊 Summary:")
    print(f"   Experiences: {exp_count}")
    print(f"   Education: {edu_count}")
    print(f"   Skills: {skill_count}")
    print(f"   Portfolio: {port_count}")

    all_working = exp_count > 0 and edu_count > 0 and skill_count > 0 and port_count > 0

    if all_working:
        print("\n✅ ALL PROFILE CRUD OPERATIONS WORKING!")
        print(
            "✅ Skills, Experience, Education, and Portfolio can be added successfully"
        )
    else:
        print("\n❌ SOME PROFILE CRUD OPERATIONS FAILED")
        print("❌ Check the specific errors above")

    return all_working


if __name__ == "__main__":
    print("Testing Profile CRUD Functionality")
    print("=" * 50)

    try:
        success = test_profile_crud()
        if success:
            print("\n🎉 All tests passed! Profile CRUD is working correctly.")
        else:
            print("\n💥 Some tests failed. Profile CRUD needs fixing.")
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        import traceback

        traceback.print_exc()
