import os

# Helper to get env or default
def get_env(name, default=None):
    return os.environ.get(name, default)

# Dynamically determine base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Path of the folder where manage.py is located
PROJECT_PATH = get_env('PROJECT_PATH', os.path.join(BASE_DIR, 'aligulac/'))

# Path of folder where database dumps are saved
DUMP_PATH = get_env('DUMP_PATH', os.path.join(BASE_DIR, 'untracked/'))

# Path of folder where the locales are stored
LOCALE_PATHS = (get_env('LOCALE_PATHS', os.path.join(BASE_DIR, 'locale/')),)

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
TEMPLATE_DIRS = (get_env('TEMPLATE_DIRS', os.path.join(BASE_DIR, 'templates/')),)

# S3 settings
S3_BUCKET = get_env('S3_BUCKET', '')
S3_ACCESS_KEY = get_env('S3_ACCESS_KEY', None)
S3_SECRET_KEY = get_env('S3_SECRET_KEY', None)
S3_REGION = get_env('S3_REGION', 'us-east-1')
S3_ENDPOINT_URL = get_env('S3_ENDPOINT_URL', None)


# Host names this server accepts connections to
ALLOWED_HOSTS = get_env('ALLOWED_HOSTS', '.aligulac.com,localhost').split(',')

# Necessary for django debug toolbar to work
INTERNAL_IPS = get_env('INTERNAL_IPS', '127.0.0.1').split(',')

# Cache settings
CACHE_BACKEND = get_env('CACHE_BACKEND', 'django.core.cache.backends.dummy.DummyCache')
CACHE_LOCATION = get_env('CACHE_LOCATION', '/app/aligulac/untracked/cache/')
CACHE_DB = get_env('CACHE_DB', '1')
CACHE_PREFIX = get_env('CACHE_PREFIX', 'aligulac')
REDIS_PASSWORD = get_env('REDIS_PASSWORD', None)
VALKEY_PASSWORD = get_env('VALKEY_PASSWORD', None)

# Debug mode
DEBUG = get_env('DEBUG', 'True').lower() == 'true'
DEBUG_TOOLBAR = get_env('DEBUG_TOOLBAR', 'True').lower() == 'true'

# Log file for errors
ERROR_LOG_FILE = get_env('ERROR_LOG_FILE', '/var/log/aligulac/error.log')
