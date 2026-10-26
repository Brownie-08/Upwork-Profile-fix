"""Public sample-data viewing only, including view-only admin access."""
import re
from html import escape
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpResponse, HttpResponseRedirect


class PortfolioDemoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def page(self, message='', status=200):
        links = ''.join('<a href="%s">%s &rarr;</a>' % (escape(url), escape(label)) for url, label in settings.DEMO_LINKS)
        return HttpResponse('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s | Portfolio Demo</title><style>body{margin:0;background:#101828;color:#f8fafc;font:17px/1.6 system-ui,sans-serif}main{max-width:780px;margin:10vh auto;padding:32px}small{color:#83d5b4;letter-spacing:.14em}h1{font-size:clamp(32px,6vw,56px);line-height:1.1}p{color:#cbd5e1}nav{display:grid;gap:12px;margin-top:32px}a{color:#fff;text-decoration:none;border:1px solid #475569;border-radius:12px;padding:16px 20px}a:hover{background:#243449}.notice{background:#243449;padding:18px;border-radius:12px}</style><main><small>UDOH PETER EMMANUEL · PROJECT DEMO</small><h1>%s</h1><p>Explore the original Django application using synthetic sample data.</p><p class="notice">Read-only portfolio demo. Payments, outbound messages, account registration, edits, and identity-document uploads are disabled. No real customer information is used. Sample data resets when the free service restarts.</p><p>%s</p><nav>%s</nav></main></html>''' % (escape(settings.DEMO_TITLE), escape(settings.DEMO_TITLE), escape(message), links), status=status)

    def __call__(self, request):
        path = request.path
        if path == '/demo/':
            return self.page()
        if path in ('/demo/start/', '/demo/admin/'):
            user = get_user_model().objects.get(username='demo_reviewer')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return HttpResponseRedirect('/admin/' if path == '/demo/admin/' else settings.DEMO_PROFILE_PATH)
        # Some original views perform writes on GET. Block those routes as well.
        unsafe_path = re.search(r'(delete|remove|deactivat|approv|reject|verify-email|resend|reset|like|debug|csrf-test|create|register|signup|logout|accept|confirm|submit|send|payment|transfer|withdraw|deposit|fund|mark-|assign|cancel|save|update|upload|edit|add-|/api/)', path, re.I)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') or unsafe_path:
            return self.page('This action is disabled in the public demo. Use the links below to continue browsing.', 403)
        response = self.get_response(request)
        if response.status_code == 200 and 'text/html' in response.get('Content-Type', '') and not response.streaming:
            body = response.content.decode(response.charset)
            banner = '<aside style="position:relative;z-index:99999;background:#102b23;color:white;padding:10px 16px;font:14px/1.5 system-ui;text-align:center">Portfolio demo · Sample data · Read-only · <a style="color:#a7f3d0" href="/demo/">Demo guide</a></aside>'
            body = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + banner, body, count=1, flags=re.I)
            response.content = body.encode(response.charset)
            if response.has_header('Content-Length'):
                response['Content-Length'] = str(len(response.content))
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
