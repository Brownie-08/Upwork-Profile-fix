"""Synthetic sample records for a public, read-only portfolio demonstration."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from profiles.models import Profile, Document, DocumentReview

user, created = get_user_model().objects.get_or_create(username='demo_reviewer', defaults={'email': 'reviewer@example.invalid', 'first_name': 'Demo', 'last_name': 'Reviewer', 'is_staff': True, 'is_active': True})
user.set_unusable_password()
user.is_staff = True
user.is_superuser = False
user.save()
user.user_permissions.set(Permission.objects.filter(codename__startswith='view_'))
profile, _ = Profile.objects.get_or_create(user=user)
profile.first_name = 'Demo'
profile.last_name = 'Reviewer'
profile.title = 'Sample Transport Service Provider'
profile.bio = 'Synthetic portfolio profile demonstrating authentication, profile management, and document-review features. No real identity documents or customer information are shown.'
profile.skills = 'Transport coordination, Customer support'
profile.location = 'Demo location'
profile.profile_picture = 'avatar.svg'
profile.save()
for doc_type in ('ID_CARD', 'FACE_PHOTO', 'PROOF_OF_RESIDENCE'):
    document, _ = Document.objects.get_or_create(user=user, doc_type=doc_type, vehicle=None, defaults={'file': 'sample-document.svg'})
    DocumentReview.objects.get_or_create(document=document, defaults={'status': 'PENDING'})
print('Synthetic profile and document-review examples ready.')
