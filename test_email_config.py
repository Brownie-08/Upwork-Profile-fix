#!/usr/bin/env python
"""
Test script to verify email configuration for OTP delivery
Run this to check if your Railway email credentials are working

Usage:
python test_email_config.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User


def test_email_configuration():
    """Test email configuration and send a test email"""
    
    print("🔧 Testing Email Configuration")
    print("=" * 50)
    
    # Check environment variables
    print(f"📧 Email Backend: {settings.EMAIL_BACKEND}")
    print(f"📫 Email Host: {settings.EMAIL_HOST}")
    print(f"🔌 Email Port: {settings.EMAIL_PORT}")
    print(f"👤 Email User: {settings.EMAIL_HOST_USER}")
    print(f"🔐 Email Password: {'*' * 16 if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"📤 Default From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"🔒 Use TLS: {settings.EMAIL_USE_TLS}")
    
    # Check production environment detection
    is_production = (
        'RAILWAY_ENVIRONMENT' in os.environ or 
        'RAILWAY_SERVICE_NAME' in os.environ or
        'RAILWAY_DOMAIN' in os.environ or
        os.environ.get('DEBUG', '').lower() == 'false'
    )
    
    print(f"🌍 Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    
    print("\n" + "-" * 50)
    print("🔍 RAILWAY ENVIRONMENT VARIABLES CHECK")
    print("-" * 50)
    
    railway_vars = [
        'RAILWAY_ENVIRONMENT', 
        'RAILWAY_SERVICE_NAME', 
        'RAILWAY_DOMAIN',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL',
        'DEBUG'
    ]
    
    for var in railway_vars:
        value = os.environ.get(var, 'NOT SET')
        if 'PASSWORD' in var and value != 'NOT SET':
            value = '*' * 16
        print(f"{var}: {value}")
    
    # Test email sending if credentials are available
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        print(f"\n📨 Attempting to send test email...")
        
        try:
            send_mail(
                subject='🧪 LusitoHub Email Test - OTP System',
                message='This is a test email to verify your email configuration for OTP delivery.\n\nIf you receive this, your email setup is working correctly!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # Send to yourself
                fail_silently=False,
            )
            
            print("✅ TEST EMAIL SENT SUCCESSFULLY!")
            print(f"📬 Check your inbox: {settings.EMAIL_HOST_USER}")
            print("🎉 Your email configuration is working!")
            return True
            
        except Exception as e:
            print(f"❌ FAILED TO SEND TEST EMAIL: {str(e)}")
            print("🚨 This means users will NOT receive OTP codes!")
            
            # Common error diagnosis
            if "Network is unreachable" in str(e):
                print("🔧 FIX: This is likely a network connectivity issue in Railway")
                print("   - Check if Railway allows SMTP connections")
                print("   - Try using port 465 with SSL instead of 587 with TLS")
            elif "authentication failed" in str(e).lower():
                print("🔧 FIX: Authentication failed - check your Gmail credentials")
                print("   - Make sure you're using an App Password, not your regular Gmail password")
                print("   - Verify 2FA is enabled on your Gmail account")
            elif "timeout" in str(e).lower():
                print("🔧 FIX: Connection timeout")
                print("   - Railway may be blocking SMTP connections")
                print("   - Consider using a different email service like SendGrid")
                
            return False
    else:
        print(f"\n⚠️  Cannot test email - missing credentials")
        print("🔧 Set these Railway environment variables:")
        print("   EMAIL_HOST_USER=your-email@gmail.com")
        print("   EMAIL_HOST_PASSWORD=your-16-char-app-password")  
        print("   DEFAULT_FROM_EMAIL=your-email@gmail.com")
        return False


def test_otp_service():
    """Test the OTP service specifically"""
    print(f"\n🔐 Testing OTP Service")
    print("=" * 50)
    
    try:
        from profiles.services.otp import OTPService
        
        # Try to get or create a test user
        test_user, created = User.objects.get_or_create(
            username='email_test_user',
            defaults={
                'email': settings.EMAIL_HOST_USER if settings.EMAIL_HOST_USER else 'test@example.com',
                'is_active': False
            }
        )
        
        print(f"📝 Test user: {test_user.username} ({test_user.email})")
        
        # Test OTP creation
        print(f"🎲 Creating test OTP...")
        otp = OTPService.create_otp(test_user, 'VERIFY', 'EMAIL')
        
        if otp:
            print(f"✅ OTP created successfully: {otp.code}")
            print(f"📧 Channel: {otp.channel}")
            print(f"🎯 Purpose: {otp.purpose}")
            print(f"⏰ Expires: {otp.expires_at}")
            
            # Clean up test OTP
            otp.delete()
            print("🧹 Test OTP cleaned up")
            
        else:
            print("❌ Failed to create OTP")
            print("🚨 This means user registration will fail!")
            
        # Clean up test user if we created it
        if created:
            test_user.delete()
            print("🧹 Test user cleaned up")
            
    except Exception as e:
        print(f"❌ OTP Service test failed: {str(e)}")
        return False
        
    return otp is not None


if __name__ == "__main__":
    print("🚀 LusitoHub Email & OTP Configuration Test")
    print("=" * 60)
    
    email_success = test_email_configuration()
    otp_success = test_otp_service()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"📧 Email Configuration: {'✅ PASS' if email_success else '❌ FAIL'}")
    print(f"🔐 OTP Service: {'✅ PASS' if otp_success else '❌ FAIL'}")
    
    if email_success and otp_success:
        print("🎉 ALL TESTS PASSED - Users will receive OTP emails!")
    else:
        print("🚨 TESTS FAILED - Users will NOT receive OTP emails!")
        print("🔧 Fix the issues above and run this test again")
        
    print("=" * 60)