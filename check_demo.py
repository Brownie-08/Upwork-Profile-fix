import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_settings')
os.environ.setdefault('SECRET_KEY', 'local-check-only-not-a-deployment-secret')
import django
django.setup()
from django.test import Client
from profiles.models import Document, DocumentReview

client = Client()
for path in ('/demo/', '/demo/health/', '/', '/demo/start/', '/profile/', '/public-profile/demo_reviewer/', '/demo/admin/', '/admin/', '/admin/profiles/documentreview/'):
    response = client.get(path)
    assert response.status_code in (200, 302), (path, response.status_code)
    print(path, response.status_code)
before = Document.objects.count()
assert before == 3
assert DocumentReview.objects.count() == 3
assert client.post('/upload-identity-document/id_card/').status_code == 403
assert client.get('/delete-education/1/').status_code == 403
assert client.get('/register/').status_code == 403
assert client.get('/bid/1/accept/').status_code == 403
assert client.get('/csrf-debug/').status_code == 403
assert Document.objects.count() == before
print('Profile/admin demo routes work; uploads and writes blocked.')
