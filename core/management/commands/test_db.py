from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Test database connection'

    def handle(self, *args, **options):
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            self.stdout.write(
                self.style.SUCCESS('✅ Database connection successful!')
            )
            self.stdout.write(f'Database backend: {settings.DATABASES["default"]["ENGINE"]}')
            
            if 'postgresql' in settings.DATABASES["default"]["ENGINE"]:
                self.stdout.write('🐘 Using PostgreSQL')
            elif 'sqlite' in settings.DATABASES["default"]["ENGINE"]:
                self.stdout.write('📱 Using SQLite')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database connection failed: {str(e)}')
            )