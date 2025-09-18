#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if environment variables are provided
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lusitohub.settings')
django.setup()

from django.contrib.auth.models import User

# Get admin credentials from environment
admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

# Create superuser if it doesn't exist
if not User.objects.filter(username=admin_username).exists():
    User.objects.create_superuser(admin_username, admin_email, admin_password)
    print(f'Superuser {admin_username} created successfully')
else:
    print(f'Superuser {admin_username} already exists')
"
else
    echo "Skipping superuser creation (no credentials provided)"
fi

echo "✅ Build completed successfully!"
