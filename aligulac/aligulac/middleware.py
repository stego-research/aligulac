import hashlib
from django.utils.encoding import force_bytes

class RealIPMiddleware:
    """
    Middleware that updates request.META['REMOTE_ADDR'] with the true origin IP 
    from Cloudflare's 'CF-Connecting-IP' header if present.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Cloudflare provides the original visitor IP address in the 'CF-Connecting-IP' header.
        # This is the most reliable header when using Cloudflare as it cannot be easily spoofed 
        # (if we only allow traffic through Cloudflare).
        real_ip = request.META.get('HTTP_CF_CONNECTING_IP')

        # 2. Fallback to 'X-Forwarded-For' if 'CF-Connecting-IP' is not present.
        # This is useful for other proxies or if Cloudflare is bypassed.
        if not real_ip:
            forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if forwarded_for:
                # X-Forwarded-For can be a comma-separated list (e.g., "client, proxy1, proxy2").
                # The first entry is generally the original client IP.
                real_ip = forwarded_for.split(',')[0].strip()

        # Update REMOTE_ADDR if we found a better candidate for the real client IP.
        # This ensures that Django's request logging, Sentry, and other tools 
        # see the correct origin IP.
        if real_ip:
            request.META['REMOTE_ADDR'] = real_ip
            
            # Update Sentry user context if Sentry is configured
            from django.conf import settings
            if getattr(settings, 'SENTRY_DSN', None):
                try:
                    import sentry_sdk
                    sentry_sdk.set_user({"ip_address": real_ip})
                except (ImportError, Exception):
                    pass
            
        return self.get_response(request)

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
        if not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'private, no-cache, must-revalidate'
            
        return response
