import logging
from django.core.cache import cache
from django.db.models.query import QuerySet

logger = logging.getLogger(__name__)

# Unique sentinel to distinguish between a cache miss and a cached None value.
CACHE_MISS = object()

def cache_page(view):
    """
    Disabled Aligulac cache wrapper.
    Returning the original view directly to rely on edge/browser caching.
    """
    return view

def cached_query(request, key, query_func, timeout=None):
    """
    Caches the result of a query function.
    Supports force refresh via 'refresh=true' query param, 'Pragma: no-cache' header,
    or 'Cache-Control: no-cache' (case-insensitive substring match).
    """
    force_refresh = (
        request.GET.get('refresh') == 'true' or
        'no-cache' in request.META.get('HTTP_PRAGMA', '').lower() or
        'no-cache' in request.META.get('HTTP_CACHE_CONTROL', '').lower()
    )

    if not force_refresh:
        try:
            # Check the cache using a sentinel to distinguish between a cache miss 
            # and a found value. In this implementation, None is never a valid 
            # cached result and is treated as a miss to prevent transient 
            # database or logic errors from being persisted.
            data = cache.get(key, default=CACHE_MISS)
            if data is not CACHE_MISS and data is not None:
                return data
        except Exception:
            # logger.exception preserves the stack trace for production debugging.
            # A true cache miss (key not found) returns CACHE_MISS and doesn't trigger this.
            logger.exception(f"Cache backend error during get (key={key})")

    data = query_func()
    
    # Evaluate Django QuerySets into a list before caching to prevent pickling lazy objects.
    # We limit this to QuerySets to avoid subtle type breakages for tuples, sets, etc.
    if isinstance(data, QuerySet):
        data = list(data)

    # Synchronous persistence to cache provider (typically Redis/Valkey, which is fast).
    # We avoid caching None to prevent transient failures from being persisted.
    if data is not None:
        try:
            cache.set(key, data, timeout)
        except Exception:
            logger.exception(f"Cache backend error during set (key={key})")

    return data
