import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

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
        request.META.get('HTTP_PRAGMA') == 'no-cache' or
        'no-cache' in request.META.get('HTTP_CACHE_CONTROL', '').lower()
    )

    if not force_refresh:
        try:
            data = cache.get(key)
            if data is not None:
                return data
        except Exception as e:
            logger.error(f"Failed to get from cache (key={key}): {str(e)}")

    data = query_func()
    
    # If it's a queryset or other iterable, evaluate it now
    if hasattr(data, '__iter__') and not isinstance(data, (list, dict, str, bytes)):
        data = list(data)

    # Synchronous persistence to cache provider (typically Redis/Valkey, which is fast)
    try:
        cache.set(key, data, timeout)
    except Exception as e:
        logger.error(f"Failed to set to cache (key={key}): {str(e)}")

    return data
