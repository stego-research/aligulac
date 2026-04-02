import os


# Helper to get env or default, normalizing 'None', 'null', and empty strings to None
# ONLY if the variable is actually set in the environment.
def get_env(name, default=None):
    if name not in os.environ:
        return default
    val = os.environ[name]
    if val.lower() in ('none', 'null', ''):
        return None
    return val


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

# S3/R2 settings
# Use S3_DB_* for database dumps (e.g. AWS S3)
S3_DB_BUCKET = get_env('S3_DB_BUCKET', get_env('S3_BUCKET', ''))
S3_DB_ACCESS_KEY = get_env('S3_DB_ACCESS_KEY', get_env('S3_ACCESS_KEY', None))
S3_DB_SECRET_KEY = get_env('S3_DB_SECRET_KEY', get_env('S3_SECRET_KEY', None))
S3_DB_REGION = get_env('S3_DB_REGION', get_env('S3_REGION', 'us-east-1'))
S3_DB_ENDPOINT_URL = get_env('S3_DB_ENDPOINT_URL', get_env('S3_ENDPOINT_URL', None))

# Use S3_STATIC_* for static assets (e.g. Cloudflare R2)
S3_STATIC_BUCKET = get_env('S3_STATIC_BUCKET', get_env('S3_BUCKET_STATIC', ''))
S3_STATIC_ACCESS_KEY = get_env('S3_STATIC_ACCESS_KEY', get_env('S3_ACCESS_KEY', None))
S3_STATIC_SECRET_KEY = get_env('S3_STATIC_SECRET_KEY', get_env('S3_SECRET_KEY', None))
S3_STATIC_REGION = get_env('S3_STATIC_REGION', get_env('S3_REGION', 'us-east-1'))
S3_STATIC_ENDPOINT_URL = get_env('S3_STATIC_ENDPOINT_URL', get_env('S3_ENDPOINT_URL', None))
S3_STATIC_CUSTOM_DOMAIN = get_env('S3_STATIC_CUSTOM_DOMAIN', get_env('S3_CUSTOM_DOMAIN', None))
S3_STATIC_DEFAULT_ACL = get_env('S3_STATIC_DEFAULT_ACL', get_env('S3_DEFAULT_ACL', None))

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
