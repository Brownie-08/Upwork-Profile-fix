"""
CSRF Debug utilities for troubleshooting CSRF token issues
"""

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


def csrf_debug_view(request):
    """Debug view to check CSRF token generation and settings"""
    
    # Get CSRF token
    csrf_token = get_token(request)
    
    debug_info = {
        'csrf_token': csrf_token,
        'method': request.method,
        'secure': request.is_secure(),
        'host': request.get_host(),
        'headers': {
            'referer': request.META.get('HTTP_REFERER', 'Not provided'),
            'origin': request.META.get('HTTP_ORIGIN', 'Not provided'),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Not provided'),
        },
        'cookies': {
            'csrftoken': request.COOKIES.get('csrftoken', 'Not found'),
            'sessionid': request.COOKIES.get('sessionid', 'Not found'),
        }
    }
    
    # Log the debug info
    logger.info(f"CSRF Debug Info: {debug_info}")
    
    if request.method == 'GET':
        return render(request, 'profiles/csrf_debug.html', {
            'debug_info': debug_info,
            'csrf_token': csrf_token
        })
    else:
        return JsonResponse(debug_info)


@csrf_exempt
def csrf_test_endpoint(request):
    """Test endpoint to verify CSRF token submission"""
    
    if request.method == 'POST':
        csrf_token_from_post = request.POST.get('csrfmiddlewaretoken', '')
        csrf_token_from_header = request.META.get('HTTP_X_CSRFTOKEN', '')
        
        result = {
            'success': True,
            'message': 'CSRF test successful!',
            'data': {
                'csrf_from_post': csrf_token_from_post[:10] + '...' if csrf_token_from_post else 'Not provided',
                'csrf_from_header': csrf_token_from_header[:10] + '...' if csrf_token_from_header else 'Not provided',
                'method': request.method,
                'host': request.get_host(),
                'secure': request.is_secure(),
            }
        }
        
        logger.info(f"CSRF Test Result: {result}")
        return JsonResponse(result)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)