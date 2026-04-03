from django.views.decorators.cache import cache_page as django_cache_page

from aligulac import settings


def cache_page(view):
    """
    Disabled Aligulac cache wrapper.
    Returning the original view directly to rely on edge/browser caching.
    """
    return view
