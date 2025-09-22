"""
Media file handling views for Railway deployment
"""

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.cache import cache_control
import os
import logging

logger = logging.getLogger(__name__)

@cache_control(max_age=3600)  # Cache for 1 hour
def serve_default_avatar(request):
    """Serve the default user avatar with proper headers"""
    try:
        # Path to the default avatar
        avatar_path = os.path.join(settings.STATIC_ROOT, 'media', 'user-avatar.svg')
        
        # Try static directory if static root doesn't exist
        if not os.path.exists(avatar_path):
            avatar_path = os.path.join(settings.BASE_DIR, 'static', 'media', 'user-avatar.svg')
        
        if os.path.exists(avatar_path):
            with open(avatar_path, 'rb') as f:
                content = f.read()
            
            response = HttpResponse(content, content_type='image/svg+xml')
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            # Generate a simple SVG if file doesn't exist
            svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="50" fill="#e9ecef"/>
  <g fill="#6c757d">
    <circle cx="50" cy="35" r="15"/>
    <path d="M50 55c-15 0-25 8-25 18v12a50 50 0 0050 0V73c0-10-10-18-25-18z"/>
  </g>
</svg>'''
            response = HttpResponse(svg_content, content_type='image/svg+xml')
            response['Cache-Control'] = 'public, max-age=3600'
            return response
            
    except Exception as e:
        logger.error(f"Error serving default avatar: {str(e)}")
        raise Http404("Avatar not found")

def serve_default_jpg(request):
    """Serve default.jpg as our default avatar SVG"""
    try:
        # Path to the default avatar SVG
        avatar_path = os.path.join(settings.BASE_DIR, 'media', 'default.svg')
        
        if os.path.exists(avatar_path):
            with open(avatar_path, 'rb') as f:
                content = f.read()
            
            response = HttpResponse(content, content_type='image/svg+xml')
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            # Generate a simple SVG if file doesn't exist
            svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <circle cx="100" cy="100" r="100" fill="#f8f9fa"/>
  <g fill="#6c757d">
    <circle cx="100" cy="75" r="30"/>
    <path d="M100 115c-30 0-50 16-50 36v24a100 100 0 00100 0v-24c0-20-20-36-50-36z"/>
  </g>
</svg>'''
            response = HttpResponse(svg_content, content_type='image/svg+xml')
            response['Cache-Control'] = 'public, max-age=3600'
            return response
            
    except Exception as e:
        logger.error(f"Error serving default.jpg: {str(e)}")
        raise Http404("Default avatar not found")

def debug_media_request(request, path):
    """Debug view to understand malformed media requests"""
    logger.warning(f"Malformed media request: {request.path}")
    logger.warning(f"HTTP_HOST: {request.META.get('HTTP_HOST', 'Unknown')}")
    logger.warning(f"REQUEST_URI: {request.META.get('REQUEST_URI', 'Unknown')}")
    logger.warning(f"Referer: {request.META.get('HTTP_REFERER', 'Unknown')}")
    
    # Extract filename from the malformed path
    if path.endswith('user-avatar.svg'):
        return HttpResponseRedirect('/static/media/user-avatar.svg')
    elif path.endswith('default.jpg'):
        return HttpResponseRedirect('/media/default.svg')
    
    # For other media files, try to redirect to the correct path
    filename = os.path.basename(path)
    return HttpResponseRedirect(f'/static/media/{filename}')
