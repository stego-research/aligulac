import hashlib
import logging

from django.conf import settings
from django.db.backends.signals import connection_created
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)

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
        # This ensures that Django's request logging, Sentry (with send_default_pii=True),
        # and other tools see the correct origin IP.
        if real_ip:
            request.META['REMOTE_ADDR'] = real_ip
            
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


class StatementTimeoutMiddleware:
    """
    Caps Postgres ``statement_timeout`` on web-request DB connections so a runaway query
    is cancelled by the database (surfacing as a clean HTTP 500) instead of blocking a
    gunicorn worker until the arbiter SIGABRTs it -- the failure mode behind ALIGULAC-1E
    (SystemExit:1 raised from gunicorn's handle_abort). The timeout
    (settings.DB_STATEMENT_TIMEOUT_MS, default 25s) is kept below the gunicorn --timeout
    (30s) so the DB cancels first and the worker survives.

    Scope is the whole point. The timeout is applied via the ``connection_created`` signal,
    which we connect in ``__init__``. Middleware is only instantiated by the request-handling
    stack, so this signal is never connected in management/batch processes (e.g. rating
    recalcs) -- their legitimately long-running queries are left uncapped. And because the
    signal fires only when a connection is actually opened, fully cache-served requests that
    touch no DB pay nothing.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_ms = getattr(settings, 'DB_STATEMENT_TIMEOUT_MS', 25000)
        if self.timeout_ms and self.timeout_ms > 0:
            connection_created.connect(
                self._apply_statement_timeout,
                dispatch_uid='aligulac.statement_timeout',
            )

    def _apply_statement_timeout(self, sender, connection, **kwargs):
        # Postgres-only; ignore sqlite (tests) or any other backend.
        if connection.vendor != 'postgresql':
            return
        try:
            with connection.cursor() as cursor:
                # set_config() rather than a bare SET so the value binds as a parameter under
                # both psycopg2 and psycopg3 (SET does not accept bind parameters). is_local
                # is false so it holds for the life of this (per-request) connection.
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, false)",
                    [str(self.timeout_ms)],
                )
        except Exception:
            # Fail open: a defensive guard that cannot arm itself must not 500 every request.
            logger.warning('Could not set per-request statement_timeout', exc_info=True)

    def __call__(self, request):
        return self.get_response(request)
