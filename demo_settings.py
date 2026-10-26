"""Isolated read-only portfolio demo; no client services or data."""
from lusitohub.settings import *

DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
CSRF_TRUSTED_ORIGINS = ['https://' + h for h in ALLOWED_HOSTS if h.endswith('.onrender.com')]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'portfolio_demo.sqlite3'}}
ROOT_URLCONF = 'demo_urls'
WSGI_APPLICATION = 'demo_wsgi.application'
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'core.middleware.FixMediaUrlsMiddleware']
MIDDLEWARE.insert(MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1, 'demo_middleware.PortfolioDemoMiddleware')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static', BASE_DIR / 'demo_static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/static/demo/'
MEDIA_ROOT = BASE_DIR / 'demo_static' / 'demo'
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
RESEND_API_KEY = ''
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_NAME = 'lusitohub_demo_session'
SESSION_COOKIE_SECURE = bool(os.environ.get('RENDER'))
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = bool(os.environ.get('RENDER'))
SECURE_HSTS_SECONDS = 3600
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
FILE_UPLOAD_MAX_MEMORY_SIZE = 65536
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'handlers': {'console': {'class': 'logging.StreamHandler'}}, 'root': {'handlers': ['console'], 'level': 'WARNING'}}
GOOGLE_MAPS_SERVER_API_KEY = {'API_KEY': ''}
GOOGLE_MAPS_CLIENT_API_KEY = {'API_KEY': ''}
DEMO_TITLE = 'LusitoHub'
DEMO_LINKS = [('/', 'Home'), ('/demo/start/', 'Explore sample profile'), ('/demo/admin/', 'View document-review admin'), ('/public-profile/demo_reviewer/', 'View public profile')]
DEMO_PROFILE_PATH = '/profile/'
