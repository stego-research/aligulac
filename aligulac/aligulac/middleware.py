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

        # Only hash if the response has content (e.g. not a streaming response)
        if hasattr(response, 'content') and response.content:
            etag = '"%s"' % hashlib.md5(force_bytes(response.content)).hexdigest()
            response['ETag'] = etag
            
        return response
