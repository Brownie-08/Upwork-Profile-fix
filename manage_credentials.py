#!/usr/bin/env python3
"""
LusitoHub Credential Management Script
This script helps you generate and manage credentials for your environment.
"""

import secrets
import string
import os
from pathlib import Path

def generate_django_secret_key():
    """Generate a secure Django secret key."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(50))

def create_env_file():
    """Create .env file from template with prompts for credentials."""
    print("🔧 LusitoHub Environment Setup")
    print("=" * 40)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        overwrite = input("📄 .env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("❌ Setup cancelled.")
            return
    
    print("\n📋 I'll help you set up your environment variables.")
    print("Press Enter to use default values where available.\n")
    
    # Django Core
    print("🔐 Django Configuration:")
    secret_key = input("Secret Key (press Enter to generate new): ").strip()
    if not secret_key:
        secret_key = generate_django_secret_key()
        print(f"✅ Generated new secret key: {secret_key[:20]}...")
    
    debug = input("Debug mode (True/False) [True]: ").strip() or "True"
    allowed_hosts = input("Allowed hosts [127.0.0.1,localhost]: ").strip() or "127.0.0.1,localhost"
    site_url = input("Site URL [http://127.0.0.1:8000]: ").strip() or "http://127.0.0.1:8000"
    
    # Database
    print("\n💾 Database Configuration:")
    db_choice = input("Database type (1=SQLite, 2=PostgreSQL) [1]: ").strip() or "1"
    if db_choice == "2":
        db_url = input("PostgreSQL URL [postgres://user:pass@localhost:5432/lusitohub]: ").strip()
        if not db_url:
            db_url = "postgres://user:pass@localhost:5432/lusitohub"
    else:
        db_url = "sqlite:///db.sqlite3"
    
    # Email Configuration
    print("\n📧 Email Configuration (Gmail):")
    email_backend = input("Email backend (1=Console, 2=SMTP) [1]: ").strip() or "1"
    if email_backend == "2":
        email_backend = "django.core.mail.backends.smtp.EmailBackend"
        email_user = input("Gmail address [ncabamatse@gmail.com]: ").strip() or "ncabamatse@gmail.com"
        print("📝 To get Gmail app password:")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Generate app password for 'LusitoHub Django App'")
        email_password = input("Gmail app password (16 characters): ").strip()
    else:
        email_backend = "django.core.mail.backends.console.EmailBackend"
        email_user = "ncabamatse@gmail.com"
        email_password = ""
    
    # Google Maps
    print("\n🗺️ Google Maps API (optional):")
    server_api_key = input("Server-side API key: ").strip()
    client_api_key = input("Client-side API key: ").strip()
    
    # MTN MoMo
    print("\n💰 MTN MoMo API (optional):")
    momo_sub_key = input("MoMo subscription key: ").strip()
    momo_api_user = input("MoMo API user ID: ").strip()
    momo_api_key = input("MoMo API key: ").strip()
    
    # Create .env content
    env_content = f"""# LusitoHub Environment Configuration
# Generated on: {os.popen('date').read().strip()}

# Django Core Settings
SECRET_KEY={secret_key}
DEBUG={debug}
ALLOWED_HOSTS={allowed_hosts}
SITE_URL={site_url}

# Database Configuration
DATABASE_URL={db_url}

# Email Configuration
EMAIL_BACKEND={email_backend}
DEFAULT_FROM_EMAIL={email_user}
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER={email_user}
EMAIL_HOST_PASSWORD={email_password}
EMAIL_USE_TLS=True

# Google Maps API Keys
Server-Side_API_KEY={server_api_key}
Client_API_KEY={client_api_key}

# MTN MoMo Configuration
MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
MOMO_SUBSCRIPTION_KEY={momo_sub_key}
MOMO_API_USER_ID={momo_api_user}
MOMO_API_KEY={momo_api_key}
MOMO_CALLBACK_URL=https://lusitohub.com/momo/callback/
MOMO_PROVIDER_CALLBACK_HOST=https://lusitohub.com
MOMO_ENVIRONMENT=sandbox
MOMO_CURRENCY=SZL

# SMS Configuration (when ready)
SMS_API_KEY=
SMS_SENDER=LusitoHub

# Media Configuration
MEDIA_URL=/media/

# Redis Configuration (for production)
REDIS_URL=redis://127.0.0.1:6379/1
"""
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Environment file created: .env")
    print("\n🔒 Security Reminders:")
    print("   • Never commit .env to version control")
    print("   • Use different credentials for production")
    print("   • Rotate credentials regularly")
    
    if email_backend == "django.core.mail.backends.smtp.EmailBackend" and not email_password:
        print("\n⚠️  Gmail app password not set!")
        print("   Email functionality will not work until you add the password.")
    
    print("\n📚 Next Steps:")
    print("   1. Test your configuration: python manage.py runserver")
    print("   2. Create superuser: python manage.py createsuperuser")
    print("   3. Run migrations: python manage.py migrate")
    print("   4. Check ENVIRONMENT_SETUP.md for detailed guides")

def test_configuration():
    """Test the current environment configuration."""
    print("🧪 Testing Environment Configuration")
    print("=" * 40)
    
    if not os.path.exists('.env'):
        print("❌ No .env file found. Run setup first.")
        return
    
    # Test Django settings
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')
        import django
        django.setup()
        
        from django.conf import settings
        print("✅ Django settings loaded successfully")
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
        
        # Test email configuration
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
            if settings.EMAIL_HOST_PASSWORD:
                print("✅ Email SMTP configuration appears complete")
            else:
                print("⚠️  Email SMTP configured but no password set")
        else:
            print("ℹ️  Email using console backend (development mode)")
        
        # Test API keys
        if hasattr(settings, 'GOOGLE_MAPS_SERVER_API_KEY'):
            if settings.GOOGLE_MAPS_SERVER_API_KEY.get('API_KEY'):
                print("✅ Google Maps server key configured")
            else:
                print("⚠️  Google Maps server key not configured")
        
        print("\n🎉 Configuration test completed!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        print("   Check your .env file and try again.")

def main():
    """Main menu for credential management."""
    while True:
        print("\n🔧 LusitoHub Credential Manager")
        print("=" * 40)
        print("1. Create/Update .env file")
        print("2. Test current configuration")
        print("3. Generate new Django secret key")
        print("4. Show environment setup guide")
        print("5. Exit")
        
        choice = input("\nSelect an option (1-5): ").strip()
        
        if choice == '1':
            create_env_file()
        elif choice == '2':
            test_configuration()
        elif choice == '3':
            key = generate_django_secret_key()
            print(f"\n🔑 New Django secret key:\n{key}")
            print("\n📝 Add this to your .env file:")
            print(f"SECRET_KEY={key}")
        elif choice == '4':
            print("\n📚 Environment Setup Guide:")
            print("   • Check ENVIRONMENT_SETUP.md for detailed instructions")
            print("   • Use .env.template as reference")
            print("   • Follow security best practices")
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid option. Please try again.")

if __name__ == '__main__':
    main()
