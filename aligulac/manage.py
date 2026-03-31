#!/usr/bin/env python3
import os
import sys

# Add the project directory to the path
# This must happen before any django imports or settings access
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

if __name__ == "__main__":
    # Monkey patch for django.utils.six which was removed in Django 3.0+
    # and causes issues in Python 3.12 even with Django 2.2
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

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

    # Default runserver to 0.0.0.0:8000 for remote access
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver' and len(sys.argv) == 2:
        sys.argv.append('0.0.0.0:8000')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
