"""
Custom middleware for handling Railway deployment issues
"""

from django.http import HttpResponseRedirect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class FixMediaUrlsMiddleware:
    """
    Middleware to fix malformed media URLs in Railway deployment
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a malformed media request
        if request.path.startswith('/web-production-') and '/media/' in request.path:
            logger.warning(f"Fixing malformed media URL: {request.path}")
            
            # Extract the media part of the path
            media_start = request.path.find('/media/')
            if media_start != -1:
                media_path = request.path[media_start:]
                
                # Special cases for common media files
                if media_path == '/media/user-avatar.svg':
                    return HttpResponseRedirect('/static/media/user-avatar.svg')
                elif media_path == '/media/default.jpg':
                    return HttpResponseRedirect('/media/default.svg')
                
                # For other media files, redirect to static version
                filename = media_path.replace('/media/', '')
                return HttpResponseRedirect(f'/static/media/{filename}')
        
        response = self.get_response(request)
        return response