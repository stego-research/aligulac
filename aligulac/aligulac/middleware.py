import hashlib
from django.utils.encoding import force_bytes

class ETagMiddleware:
    """
    Middleware that adds an ETag header to all 200 OK responses that don't already have one.
    This works by hashing the response content.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # 1. Skip API endpoints entirely to maintain the existing API contract.
        # 2. Only process successful GET/HEAD requests for web pages.
        if (request.path.startswith('/api/') or 
            request.method not in ('GET', 'HEAD') or 
            response.status_code != 200):
            return response

        # Don't overwrite existing ETag
        if response.has_header('ETag'):
            return response

        # Explicitly skip streaming responses (they don't have .content)
        if getattr(response, 'streaming', False):
            return response

        # Hash the content (even if it's an empty byte string)
        # We use usedforsecurity=False to avoid issues in FIPS environments
        content = getattr(response, 'content', b'')
        
        # Use a Weak ETag (W/") which is more likely to survive intermediary transcoding
        etag = 'W/"%s"' % hashlib.md5(force_bytes(content), usedforsecurity=False).hexdigest()
        response['ETag'] = etag
        # Project-specific debug header
        response['X-Aligulac-ETag'] = 'active; %s' % etag

        # Tell downstream caches and browsers to cache this, but always revalidate.
        # Since Aligulac uses cookie-based language switching, we use 'private' 
        # to ensure that shared proxies (like corporate firewalls) do not 
        # cache one user's language for another.
        # We use 'no-transform' to prevent intermediaries from stripping the ETag 
        # during compression transcoding or minification.
        if not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'private, no-cache, must-revalidate'
            
        return response
