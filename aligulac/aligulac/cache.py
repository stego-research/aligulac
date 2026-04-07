from django.views.decorators.cache import cache_page as django_cache_page
from django.core.cache import cache
import threading
from django.conf import settings
import threading

def cache_page(view):
    """
    Disabled Aligulac cache wrapper.
    Returning the original view directly to rely on edge/browser caching.
    """
    return view

def cached_query(request, key, query_func, timeout=None):
    """
    Caches the result of a query function.
    Supports force refresh via 'refresh=true' query param or 'Pragma: no-cache' header.
    Persists to cache asynchronously.
    """
    force_refresh = (
        request.GET.get('refresh') == 'true' or
        request.META.get('HTTP_PRAGMA') == 'no-cache' or
        request.META.get('HTTP_CACHE_CONTROL') == 'no-cache'
    )


    if not force_refresh:
        data = cache.get(key)
        if data is not None:
            return data

    data = query_func()
    
    # If it's a queryset or other iterable, evaluate it now
    if hasattr(data, '__iter__') and not isinstance(data, (list, dict, str, bytes)):
        data = list(data)

    # Asynchronous persistence to cache provider
    def persist():
        try:
            cache.set(key, data, timeout)
        except Exception:
            # Best effort
            pass

    threading.Thread(target=persist, daemon=True).start()

    return data
