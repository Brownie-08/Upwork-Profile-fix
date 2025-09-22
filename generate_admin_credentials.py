#!/usr/bin/env python3
"""
Secure Admin Credentials Generator for Railway Deployment
Run this locally to generate secure admin credentials for your production environment.
"""

import secrets
import string

def generate_secure_password(length=16):
    """Generate a cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def main():
    print("🔐 Secure Admin Credentials Generator")
    print("=" * 50)
    print()
    
    # Get username
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    
    # Get email
    while True:
        email = input("Enter admin email: ").strip()
        if "@" in email and "." in email:
            break
        print("Please enter a valid email address.")
    
    # Generate secure password
    password = generate_secure_password()
    
    print("\n🎯 Generated Admin Credentials:")
    print("=" * 50)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print()
    
    print("📱 Railway Environment Variables:")
    print("=" * 50)
    print("Add these to your Railway project's environment variables:")
    print()
    print(f"ADMIN_USERNAME={username}")
    print(f"ADMIN_EMAIL={email}")
    print(f"ADMIN_PASSWORD={password}")
    print()
    
    print("⚠️  SECURITY REMINDERS:")
    print("- Keep these credentials secure")
    print("- Don't commit them to git")
    print("- Change them after first login if desired")
    print("- Only set them in Railway's environment variables")
    print()
    
    input("Press Enter to close...")

if __name__ == "__main__":
    main()