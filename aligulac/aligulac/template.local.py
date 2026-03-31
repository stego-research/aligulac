import os

# Helper to get env or default
def get_env(name, default=None):
    return os.environ.get(name, default)

# Path of the folder where manage.py is located
PROJECT_PATH = get_env('PROJECT_PATH', '/app/aligulac/')

# Path of folder where database dumps are saved
DUMP_PATH = get_env('DUMP_PATH', '/app/aligulac/untracked/')

# Path of folder where the locales are stored
LOCALE_PATHS = (get_env('LOCALE_PATHS', '/app/aligulac/locale/'),)

# Secret Key
SECRET_KEY = get_env('SECRET_KEY', '')

# API key to openexchangerates.org
EXCHANGE_ID = get_env('EXCHANGE_ID', '')

# Database name, host, port, username and password
DB_NAME = get_env('DB_NAME', 'aligulac')
DB_HOST = get_env('DB_HOST', '127.0.0.1')
DB_PORT = get_env('DB_PORT', '5432')
DB_SSLMODE = get_env('DB_SSLMODE', 'prefer')
DB_USER = get_env('DB_USER', '')
DB_PASSWORD = get_env('DB_PASSWORD', '')

# Folder where the templates are stored
TEMPLATE_DIRS = (get_env('TEMPLATE_DIRS', '/app/aligulac/templates/'),)

# Host names this server accepts connections to
ALLOWED_HOSTS = get_env('ALLOWED_HOSTS', '.aligulac.com,localhost').split(',')

# Necessary for django debug toolbar to work
INTERNAL_IPS = get_env('INTERNAL_IPS', '127.0.0.1').split(',')

# Cache backend
CACHE_BACKEND = get_env('CACHE_BACKEND', 'django.core.cache.backends.dummy.DummyCache')
CACHE_LOCATION = get_env('CACHE_LOCATION', '/app/aligulac/untracked/cache/')

# Debug mode
DEBUG = get_env('DEBUG', 'True').lower() == 'true'
DEBUG_TOOLBAR = get_env('DEBUG_TOOLBAR', 'True').lower() == 'true'

# Log file for errors
ERROR_LOG_FILE = get_env('ERROR_LOG_FILE', '/var/log/aligulac/error.log')
