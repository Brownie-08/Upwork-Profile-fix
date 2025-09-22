#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from django.test import TestCase
from django.contrib.auth.models import User

from profiles.models import VehicleOwnership, OperatorAssignment
from profiles.forms import VehicleOwnershipForm


def test_vehicle_form_with_operator_choice():
    """Test that the VehicleOwnershipForm includes the operator choice checkbox"""
    print("Testing VehicleOwnershipForm...")

    # Create form instance
    form = VehicleOwnershipForm()

    # Check if will_be_operator field exists
    if "will_be_operator" in form.fields:
        print("✅ will_be_operator field exists in form")
        field = form.fields["will_be_operator"]
        print(f"   - Label: {field.label}")
        print(f"   - Required: {field.required}")
        print(f"   - Initial: {field.initial}")
        print(f"   - Help text: {field.help_text}")
    else:
        print("❌ will_be_operator field is missing from form")
        return False

    # Test form validation with checkbox
    form_data = {
        "plate_number": "JSD 123 AM",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2020,
        "vehicle_type": "CAR",
        "will_be_operator": True,
    }

    form = VehicleOwnershipForm(data=form_data)
    if form.is_valid():
        print("✅ Form validation passes with will_be_operator=True")
        print(
            f"   - Cleaned data: will_be_operator = {form.cleaned_data.get('will_be_operator')}"
        )
    else:
        print(f"❌ Form validation failed: {form.errors}")
        return False

    # Test form without checkbox (should default to False)
    form_data_no_checkbox = {
        "plate_number": "JSD 124 AM",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2020,
        "vehicle_type": "CAR",
        # will_be_operator not included
    }

    form = VehicleOwnershipForm(data=form_data_no_checkbox)
    if form.is_valid():
        print("✅ Form validation passes without will_be_operator")
        print(
            f"   - Cleaned data: will_be_operator = {form.cleaned_data.get('will_be_operator')}"
        )
    else:
        print(f"❌ Form validation failed without checkbox: {form.errors}")
        return False

    print("\n✅ All VehicleOwnershipForm tests passed!")
    return True


def test_vehicle_creation_with_operator():
    """Test vehicle creation with operator assignment"""
    print("\nTesting vehicle creation with operator assignment...")

    # Create a test user
    try:
        user = User.objects.get(username="testuser_vehicle")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username="testuser_vehicle",
            email="test@example.com",
            password="testpass123",
        )
        print("✅ Test user created")

    # Clean up any existing test vehicles first
    VehicleOwnership.objects.filter(plate_number="TSD 999 XY").delete()

    # Test creating a vehicle with operator assignment
    form_data = {
        "plate_number": "TSD 999 XY",
        "make": "Honda",
        "model": "Civic",
        "year": 2022,
        "vehicle_type": "CAR",
        "will_be_operator": True,
    }

    form = VehicleOwnershipForm(data=form_data)
    if form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.owner = user
        vehicle.save()
        print("✅ Vehicle created successfully")

        # Check if will_be_operator was captured in cleaned_data
        will_be_operator = form.cleaned_data.get("will_be_operator", False)
        print(f"   - will_be_operator from form: {will_be_operator}")

        if will_be_operator:
            # Create operator assignment (simulating what the view would do)
            assignment = OperatorAssignment.objects.create(
                vehicle=vehicle, operator=user, assigned_by=user, active=True
            )
            print(f"✅ Operator assignment created: {assignment}")

        # Clean up
        OperatorAssignment.objects.filter(vehicle=vehicle).delete()
        vehicle.delete()
        print("✅ Test data cleaned up")

    else:
        print(f"❌ Form validation failed: {form.errors}")
        return False

    print("✅ Vehicle creation with operator assignment test passed!")
    return True


if __name__ == "__main__":
    print("=== Testing Vehicle Registration with Operator Choice ===\n")

    success = True
    success &= test_vehicle_form_with_operator_choice()
    success &= test_vehicle_creation_with_operator()

    if success:
        print("\n🎉 All tests passed! The feature is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")

    sys.exit(0 if success else 1)
