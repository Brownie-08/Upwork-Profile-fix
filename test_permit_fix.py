#!/usr/bin/env python
import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from profiles.forms import GovernmentPermitForm
from profiles.models import GovernmentPermit
from django.contrib.auth.models import User
from datetime import date

# Test the form validation
form_data = {
    "permit_type": "Government Permit",  # Human readable label
    "permit_number": "GP-12345",
    "issue_date": "2025-01-01",
    "expiry_date": "2026-12-31",
}

form = GovernmentPermitForm(data=form_data)
print("Form validation result:", form.is_valid())
if form.is_valid():
    print("Cleaned permit_type:", form.cleaned_data["permit_type"])
else:
    print("Form errors:", form.errors)

# Test with machine value
form_data2 = {
    "permit_type": "TRANSPORT",  # Machine value
    "permit_number": "GP-12346",
    "issue_date": "2025-01-01",
    "expiry_date": "2026-12-31",
}

form2 = GovernmentPermitForm(data=form_data2)
print("\nForm validation result (machine value):", form2.is_valid())
if form2.is_valid():
    print("Cleaned permit_type:", form2.cleaned_data["permit_type"])
else:
    print("Form errors:", form2.errors)

# Test with invalid value
form_data3 = {
    "permit_type": "Invalid Type",
    "permit_number": "GP-12347",
    "issue_date": "2025-01-01",
    "expiry_date": "2026-12-31",
}

form3 = GovernmentPermitForm(data=form_data3)
print("\nForm validation result (invalid):", form3.is_valid())
if form3.is_valid():
    print("Cleaned permit_type:", form3.cleaned_data["permit_type"])
else:
    print("Form errors:", form3.errors)

print("\nModel choices:")
for choice in GovernmentPermit._meta.get_field("permit_type").choices:
    print(f"  {choice[0]} -> {choice[1]}")
