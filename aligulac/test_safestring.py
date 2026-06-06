import os
import django
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import SafeString

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")
django.setup()

s = render_to_string("messages.djhtml", {'m': {'text': 'abc'}})
print("Is SafeString in django?", isinstance(s, SafeString))
