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
        
        # Only process successful GET/HEAD requests
        if request.method not in ('GET', 'HEAD') or response.status_code != 200:
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
        etag = '"%s"' % hashlib.md5(force_bytes(content), usedforsecurity=False).hexdigest()
        response['ETag'] = etag
            
        return response
