from django.shortcuts import render
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods


def home(request):
    return render(request, "core/home")


def pricing_view(request):
    return render(request, "core/pricing.html")


def terms_view(request):
    return render(request, "core/terms.html")


def cookie_view(request):
    return render(request, "core/cookie.html")


def privacy_view(request):
    return render(request, "core/privacy.html")


def support_view(request):
    return render(request, "core/support.html")


def trust_safety_view(request):
    return render(request, "core/trust_safety.html")


@require_http_methods(["GET"])
def refresh_csrf_token(request):
    """
    Refresh CSRF token endpoint for AJAX requests.
    Returns a new CSRF token in JSON format.
    """
    token = get_token(request)
    return JsonResponse({"csrf_token": token, "status": "success"})
