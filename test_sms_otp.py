#!/usr/bin/env python
"""
Test script for SMS OTP functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")
django.setup()

from django.contrib.auth.models import User
from profiles.models import Profile, LoginOTP
from profiles.services.otp import OTPService


def test_sms_otp():
    print("🧪 Testing SMS OTP Functionality")
    print("=" * 50)

    # Clean up any existing test user
    try:
        test_user = User.objects.get(username="smstest")
        test_user.delete()
        print("✅ Cleaned up existing test user")
    except User.DoesNotExist:
        pass

    # Create test user with phone number
    user = User.objects.create(
        username="smstest", email="sms@test.com", first_name="SMS", last_name="Test"
    )

    # Create profile with phone number
    profile = Profile.objects.create(user=user, phone_number="+26812345678")

    print(f"✅ Created test user: {user.username}")
    print(f"✅ Phone number: {profile.phone_number}")

    # Test available channels
    channels = OTPService.get_available_channels(user)
    print(f"✅ Available channels: {channels}")

    # Test SMS OTP creation
    print("\n📱 Testing SMS OTP creation...")
    sms_otp = OTPService.create_otp(user, "VERIFY", "SMS")
    if sms_otp:
        print(f"✅ SMS OTP created: {sms_otp.code}")
        print(f"   Channel: {sms_otp.channel}")
        print(f"   Purpose: {sms_otp.purpose}")
    else:
        print("❌ Failed to create SMS OTP")

    # Test BOTH channel OTP creation
    print("\n📧📱 Testing BOTH channels OTP creation...")
    both_otp = OTPService.create_otp(user, "RESET", "BOTH")
    if both_otp:
        print(f"✅ BOTH channels OTP created: {both_otp.code}")
        print(f"   Channel: {both_otp.channel}")
        print(f"   Purpose: {both_otp.purpose}")
    else:
        print("❌ Failed to create BOTH channels OTP")

    # Test verification
    if sms_otp:
        print(f"\n🔐 Testing OTP verification...")
        success, message = OTPService.verify_otp(user, sms_otp.code, "VERIFY")
        if success:
            print(f"✅ OTP verified successfully: {message}")
        else:
            print(f"❌ OTP verification failed: {message}")

    # Show all OTPs for user
    otps = LoginOTP.objects.filter(user=user)
    print(f"\n📋 All OTPs for {user.username}:")
    for otp in otps:
        print(
            f"   Code: {otp.code}, Channel: {otp.channel}, Purpose: {otp.purpose}, Verified: {otp.verified}"
        )

    # Cleanup
    user.delete()
    print(f"\n🧹 Cleaned up test user")
    print("✅ SMS OTP test completed!")


if __name__ == "__main__":
    test_sms_otp()
