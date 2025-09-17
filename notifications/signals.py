from django.db.models.signals import post_save
from django.dispatch import receiver
from profiles.models import Profile
from .models import Notification


@receiver(post_save, sender=Profile)
def check_profile_completion(sender, instance, created, **kwargs):
    user = instance.user
    profile = instance
    # Check for incomplete profile fields
    missing_fields = []
    if not profile.experiences.exists():
        missing_fields.append("experience")
    if not profile.education.exists():
        missing_fields.append("education")
    # Assume Portfolio model exists; adjust if not
    if not hasattr(profile, "portfolio") or not profile.portfolio.exists():
        missing_fields.append("portfolio")
    if missing_fields:
        message = f"Your profile is incomplete. Please add your {', '.join(missing_fields)} to enhance your visibility."
        Notification.objects.get_or_create(
            user=user,
            title="Complete Your Profile",
            message=message,
            notification_type="profile_completion",
        )
