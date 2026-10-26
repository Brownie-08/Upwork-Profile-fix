# LusitoHub public portfolio demo

Separate read-only demo using the original project templates and Django views with synthetic profile/document-review records. No client database, media, API credentials, or live payment/email providers are used. Document uploads, registration, edits, and payments are disabled.

Render configuration:
- Python 3.12
- Build: `pip install -r requirements-demo.txt && python manage.py collectstatic --noinput`
- Start: `bash start-demo.sh`
- Environment: `DJANGO_SETTINGS_MODULE=demo_settings` and a fresh generated `SECRET_KEY`.
- Entry point: `/demo/`

Sample SQLite data resets on service restart. A durable deployment requires a persistent database, private document storage, fresh service credentials, and a separate production permission review.
