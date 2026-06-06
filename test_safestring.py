import django
from django.conf import settings
from django.template.loader import render_to_string
settings.configure(TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': []}])
django.setup()
try:
    s = render_to_string("messages.djhtml", {}) # just any template
except Exception as e:
    pass # might fail without full setup
from django.utils.safestring import SafeString
print("Is SafeString in django?", SafeString)
