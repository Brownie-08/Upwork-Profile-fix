#!/usr/bin/env python3
"""
Manual Admin User Creation Script for Railway
Run this script in Railway terminal if automatic admin creation fails
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/app')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')

# Setup Django
django.setup()

from django.contrib.auth import get_user_model
from django.core.management.color import make_style

User = get_user_model()
style = make_style()

def create_admin():
    print("🔐 Manual Admin User Creation")
    print("=" * 50)
    
    # Check if running in Railway
    if 'RAILWAY_ENVIRONMENT' not in os.environ:
        print("❌ This script should only be run in Railway environment")
        return
    
    # Get admin credentials from environment or use defaults
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    email = os.environ.get('ADMIN_EMAIL', 'admin@lusitohub.com')  
    password = os.environ.get('ADMIN_PASSWORD')
    
    if not password:
        print("❌ ADMIN_PASSWORD environment variable not set")
        print("Please set ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD in Railway")
        return
    
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {'✅ SET' if password else '❌ NOT SET'}")
    print()
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"⚠️  User '{username}' already exists")
        
        # Ask if we should update password
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.email = email
        user.save()
        
        print(f"✅ Updated existing user '{username}' with new password and admin privileges")
        return
    
    # Create new superuser
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        print(f"✅ Successfully created superuser '{username}'")
        print(f"📧 Email: {email}")
        print("⚠️  Please change the password after first login")
        print()
        print(f"🌐 Admin URL: https://your-railway-app.railway.app/admin/")
        print(f"👤 Login: {username}")
        
    except Exception as e:
        print(f"❌ Error creating superuser: {str(e)}")
        return

if __name__ == "__main__":
    create_admin()