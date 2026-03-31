"""
WSGI config for aligulac project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""

import os
import sys

# Add the project directory to the path
# This must happen before any django imports or settings access
# Structure: /app/aligulac/aligulac/wsgi.py -> project root is /app/aligulac
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

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

# We are INSIDE the aligulac package here. 
# To avoid ambiguity between the outer folder and inner package,
# we can set the settings module to just 'settings' if we add this folder to path,
# but the standard way is 'aligulac.settings'.
# Let's ensure the PARENT of the package is in path.
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
