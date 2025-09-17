from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser for production deployment'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Starting admin user creation process...')
        
        # Debug: Check Railway environment
        railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
        self.stdout.write(f'Railway Environment: {railway_env}')
        
        # Only run this in production/Railway environment
        if not railway_env:
            self.stdout.write(
                self.style.WARNING('❌ This command should only be run in production (Railway environment)')
            )
            self.stdout.write('Set RAILWAY_ENVIRONMENT=production in Railway variables')
            return

        # Get credentials from environment variables (REQUIRED)
        username = os.environ.get('ADMIN_USERNAME')
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        
        # Debug: Show what we found (without showing password)
        self.stdout.write(f'Found ADMIN_USERNAME: {"{}".format(username) if username else "❌ NOT SET"}')
        self.stdout.write(f'Found ADMIN_EMAIL: {"{}".format(email) if email else "❌ NOT SET"}')
        self.stdout.write(f'Found ADMIN_PASSWORD: {"✅ SET" if password else "❌ NOT SET"}')
        
        # Validate that all required credentials are provided
        if not username or not email or not password:
            self.stdout.write(
                self.style.ERROR('❌ Missing required environment variables:')
            )
            self.stdout.write('Required: ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD')
            self.stdout.write('Please set these in your Railway environment variables.')
            return

        # Check if superuser already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists')
            )
            return

        # Create the superuser
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created superuser "{username}"')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Email: {email}')
        )
        self.stdout.write(
            self.style.WARNING('Please change the password after first login!')
        )