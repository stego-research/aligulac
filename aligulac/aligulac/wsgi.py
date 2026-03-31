"""
WSGI config for aligulac project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""

import os
import sys

# Monkey patch for django.utils.six which was removed in Django 3.0+
# and causes issues in Python 3.12 even with Django 2.2+
try:
    import six
    # Use getattr for lazy attributes to avoid static analysis issues in IDEs
    sys.modules['django.utils.six'] = six
    moves = getattr(six, 'moves')
    sys.modules['django.utils.six.moves'] = moves
    urllib = getattr(moves, 'urllib')
    sys.modules['django.utils.six.moves.urllib'] = urllib
    sys.modules['django.utils.six.moves.urllib.parse'] = getattr(urllib, 'parse')
    sys.modules['django.utils.six.moves.urllib.request'] = getattr(urllib, 'request')
    sys.modules['django.utils.six.moves.urllib.error'] = getattr(urllib, 'error')
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
