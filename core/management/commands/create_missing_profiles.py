from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from freelanceApp.models import Profile


class Command(BaseCommand):
    help = "Create profiles for users who do not have one"

    def handle(self, *args, **options):
        users_without_profiles = User.objects.filter(profile__isnull=True)
        created_count = 0

        for user in users_without_profiles:
            Profile.objects.create(user=user)
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} profiles for existing users"
            )
        )
