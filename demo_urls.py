from django.urls import path, include
from django.http import JsonResponse
urlpatterns = [path('demo/health/', lambda request: JsonResponse({'status': 'ok', 'mode': 'read-only portfolio demo'})), path('', include('lusitohub.urls'))]
