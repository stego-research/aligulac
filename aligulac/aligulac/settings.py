# -*- coding: utf-8 -*-

"""
Django settings for aligulac project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.core.files.storage import FileSystemStorage

# BASE_DIR is the Django project root (containing manage.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# REPO_ROOT is the repository root (containing resources/ and static_root/)
REPO_ROOT = os.path.dirname(BASE_DIR)


# Helper to get env or default, normalizing 'None' and 'null' to None.
# Empty strings are kept as '' to avoid breaking downstream .split()/.lower() calls.
def get_env(name, default=None):
    if name not in os.environ:
        return default
    val = os.environ[name]
    if val.lower() in ('none', 'null'):
        return None
    return val


from django.utils.translation import gettext_lazy as _

from . import local as local

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local.SECRET_KEY
SENTRY_DSN = getattr(local, 'SENTRY_DSN', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = local.DEBUG
DEBUG_TOOLBAR = local.DEBUG_TOOLBAR

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = local.ALLOWED_HOSTS

CSRF_TRUSTED_ORIGINS = get_env('CSRF_TRUSTED_ORIGINS', '').split(',')
# Clean up empty strings if no origins provided
CSRF_TRUSTED_ORIGINS = [o for o in CSRF_TRUSTED_ORIGINS if o]

LOCALE_PATHS = local.LOCALE_PATHS
LANGUAGE_CODE = 'en_US'

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
    ('pl', 'Polski'),
    ('da', 'Dansk'),
    ('nb', 'Norsk (bokmål)'),
    ('zh-hans', '中文(简体)'),
]

if DEBUG:
    LANGUAGES += [
        ('ru', 'Русский'),
        ('es', 'Español'),
        ('de', 'Deutsch'),
        ('se', 'Svenska'),
        ('pt', 'Português'),
    ]

# CUSTOM

PROJECT_PATH = local.PROJECT_PATH
DUMP_PATH = local.DUMP_PATH
INTERNAL_IPS = local.INTERNAL_IPS
EXCHANGE_ID = local.EXCHANGE_ID

# S3/R2 Configuration
# Database Dumps (AWS S3)
S3_DB_BUCKET = getattr(local, 'S3_DB_BUCKET', getattr(local, 'S3_BUCKET', ''))
S3_DB_ACCESS_KEY = getattr(local, 'S3_DB_ACCESS_KEY', getattr(local, 'S3_ACCESS_KEY', None))
S3_DB_SECRET_KEY = getattr(local, 'S3_DB_SECRET_KEY', getattr(local, 'S3_SECRET_KEY', None))
S3_DB_REGION = getattr(local, 'S3_DB_REGION', getattr(local, 'S3_REGION', 'us-east-1'))
S3_DB_ENDPOINT_URL = getattr(local, 'S3_DB_ENDPOINT_URL', getattr(local, 'S3_ENDPOINT_URL', None))

# Static Assets (Cloudflare R2)
S3_STATIC_BUCKET = get_env('S3_STATIC_BUCKET', getattr(local, 'S3_STATIC_BUCKET', get_env('S3_BUCKET_STATIC', getattr(local, 'S3_BUCKET_STATIC', ''))))
S3_STATIC_ACCESS_KEY = get_env('S3_STATIC_ACCESS_KEY', getattr(local, 'S3_STATIC_ACCESS_KEY', None))
S3_STATIC_SECRET_KEY = get_env('S3_STATIC_SECRET_KEY', getattr(local, 'S3_STATIC_SECRET_KEY', None))
S3_STATIC_REGION = get_env('S3_STATIC_REGION', getattr(local, 'S3_STATIC_REGION', 'us-east-1'))
S3_STATIC_ENDPOINT_URL = get_env('S3_STATIC_ENDPOINT_URL', getattr(local, 'S3_STATIC_ENDPOINT_URL', None))
S3_STATIC_CUSTOM_DOMAIN = get_env('S3_STATIC_CUSTOM_DOMAIN', getattr(local, 'S3_STATIC_CUSTOM_DOMAIN', get_env('S3_CUSTOM_DOMAIN', getattr(local, 'S3_CUSTOM_DOMAIN', None))))
S3_STATIC_DEFAULT_ACL = get_env('S3_STATIC_DEFAULT_ACL', getattr(local, 'S3_STATIC_DEFAULT_ACL', None))

CACHES = {
    'default': {
        'BACKEND': local.CACHE_BACKEND,
        'LOCATION': local.CACHE_LOCATION,
    }
}

if local.CACHE_BACKEND == 'django_redis.cache.RedisCache':
    CACHES['default'].update({
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'DB': getattr(local, 'CACHE_DB', '1'),
            'PASSWORD': getattr(local, 'REDIS_PASSWORD', None) or getattr(local, 'VALKEY_PASSWORD', None),
        },
        'KEY_PREFIX': getattr(local, 'CACHE_PREFIX', 'aligulac'),
    })
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

CACHE_TIMES = {
    # Trivially constant pages, one day
    'aligulac.views.h404': 24 * 60 * 60,
    'aligulac.views.h500': 24 * 60 * 60,
    'ratings.inference_views.predict': 24 * 60 * 60,

    # Views that change only after the quad-daily update can have fifteen minutes cache times
    # These typically depend on ratings, but not on specific results
    'aligulac.views.home': 15 * 60,
    'ratings.inference_views.dual': 15 * 60,
    'ratings.inference_views.sebracket': 15 * 60,
    'ratings.inference_views.rrgroup': 15 * 60,
    'ratings.inference_views.proleague': 15 * 60,
    'ratings.player_views.historical': 15 * 60,
    'ratings.ranking_views.periods': 15 * 60,
    'ratings.ranking_views.period': 15 * 60,
    'ratings.records_views.history': 15 * 60,
    'ratings.records_views.hof': 15 * 60,
    'ratings.records_views.race': 15 * 60,
    'ratings.report_views.balance': 15 * 60,
    'blog.views.blog': 15 * 60,

    # Depends on results but not urgent
    'ratings.misc_views.clocks': 30 * 60,

    # Set until the queries have been improved
    'ratings.results_views.results': 10 * 60
}

# RATINGS

INACTIVE_THRESHOLD = 4
INIT_DEV = 0.16
DECAY_DEV = 0.065
MIN_DEV = 0.04
OFFLINE_WEIGHT = 1.5
PRF_NA = -1000
PRF_INF = -2000
PRF_MININF = -3000


def start_rating(country, period):
    return 0.2 if country == 'KR' else 0.0


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tastypie',
    'sniplates',
    'blog',
    'faq',
    'miniURL',
    'ratings',
]

if DEBUG and DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG and DEBUG_TOOLBAR:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'aligulac.urls'

WSGI_APPLICATION = 'aligulac.wsgi.application'

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': local.DB_NAME,
        'USER': local.DB_USER,
        'PASSWORD': local.DB_PASSWORD,
        'HOST': local.DB_HOST,
        'PORT': local.DB_PORT,
        'OPTIONS': {
            'sslmode': getattr(local, 'DB_SSLMODE', 'prefer'),
        }
    }
}

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': get_env('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'
if S3_STATIC_CUSTOM_DOMAIN and not DEBUG:
    STATIC_URL = f'//{S3_STATIC_CUSTOM_DOMAIN}/'

# Static root is in the Repo folder, consistent with global asset location
STATIC_ROOT = os.path.join(REPO_ROOT, 'static_root')

# Only include the compiled assets in collectstatic.
# This explicitly skips js-src and node_modules, reducing file count by 1000+.
STATICFILES_DIRS = [
    ('css', os.path.join(REPO_ROOT, 'resources', 'css')),
    ('fonts', os.path.join(REPO_ROOT, 'resources', 'fonts')),
    ('img', os.path.join(REPO_ROOT, 'resources', 'img')),
    ('js', os.path.join(REPO_ROOT, 'resources', 'js')),
]

# AWS/R2 Storage Settings for Static Files
AWS_ACCESS_KEY_ID = S3_STATIC_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = S3_STATIC_SECRET_KEY
AWS_STORAGE_BUCKET_NAME = S3_STATIC_BUCKET
AWS_S3_REGION_NAME = S3_STATIC_REGION
AWS_S3_ENDPOINT_URL = S3_STATIC_ENDPOINT_URL
AWS_S3_CUSTOM_DOMAIN = S3_STATIC_CUSTOM_DOMAIN
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=31536000, public, immutable',
}
AWS_LOCATION = ''
AWS_DEFAULT_ACL = S3_STATIC_DEFAULT_ACL
AWS_S3_FILE_OVERWRITE = True
AWS_S3_GZIP = True
AWS_QUERYSTRING_AUTH = False
# Optimization: Increase memory buffer and reduce redundant metadata calls
AWS_S3_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB
AWS_S3_PRELOAD_METADATA = False
AWS_S3_CHECKSUM_MODE = None
AWS_S3_USE_THREADS = True

# Storage Configuration
if S3_STATIC_BUCKET:
    from storages.backends.s3boto3 import S3Boto3Storage
    from django.contrib.staticfiles.storage import ManifestFilesMixin

    class StaticS3Storage(ManifestFilesMixin, S3Boto3Storage):
        file_overwrite = True
        querystring_auth = False
        manifest_strict = False

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Ensure the manifest is ALWAYS stored locally in the container
            # so WhiteNoise and Django can find it at runtime.
            self.manifest_storage = FileSystemStorage(location=STATIC_ROOT)
else:
    from whitenoise.storage import CompressedManifestStaticFilesStorage

    class SafeWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
        def __init__(self, *args, **kwargs):
            # Ensure consistency with the S3 storage manifest location
            self.manifest_storage = FileSystemStorage(location=STATIC_ROOT)
            super().__init__(*args, **kwargs)

        manifest_strict = False
        def hashed_name(self, name, content=None, filename=None):
            try:
                return super().hashed_name(name, content, filename)
            except (ValueError, Exception):
                return name
        @property
        def base_url(self):
            if S3_STATIC_CUSTOM_DOMAIN and not DEBUG:
                return f'//{S3_STATIC_CUSTOM_DOMAIN}/'
            return super().base_url
        def url(self, name, force=False):
            url = super().url(name, force)
            if S3_STATIC_CUSTOM_DOMAIN and not DEBUG:
                # If it's already an absolute URL (from CDN), return it
                if url.startswith('http') or url.startswith('//'):
                    return url
                # Otherwise, ensure it starts with our CDN domain
                path = url[7:] if url.startswith('/static/') else url
                if path.startswith('/'):
                    path = path[1:]
                return f'//{S3_STATIC_CUSTOM_DOMAIN}/{path}'
            return url

WHITENOISE_USE_FINDERS = False
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

if S3_STATIC_BUCKET:
    STORAGES["staticfiles"] = {
        "BACKEND": "aligulac.settings.StaticS3Storage",
    }
else:
    STORAGES["staticfiles"] = {
        "BACKEND": "aligulac.settings.SafeWhiteNoiseStorage",
    }
    WHITENOISE_KEEP_ONLY_HASHED_FILES = False
    # Max age for non-hashed files (fallback). Hashed files still get 1 year.
    WHITENOISE_MAX_AGE = 600

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': local.TEMPLATE_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ]
            # ... some options here ...
        },
    },
]

SHOW_PER_LIST_PAGE = 40
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Sentry Configuration
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    # Default to 1% in production, 100% in debug/dev
    default_sample_rate = 0.01 if not DEBUG else 1.0
    
    # Safely parse and validate the sample rate
    try:
        raw_sample_rate = getattr(local, 'SENTRY_TRACES_SAMPLE_RATE', None)
        if raw_sample_rate is not None:
            sample_rate = float(raw_sample_rate)
            # Clamp between 0.0 and 1.0
            sample_rate = max(0.0, min(1.0, sample_rate))
        else:
            sample_rate = default_sample_rate
    except (ValueError, TypeError):
        sample_rate = default_sample_rate

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        # Add data like request headers and IP for users
        send_default_pii=True,
        # Set traces_sample_rate to capture transactions for performance monitoring.
        traces_sample_rate=sample_rate,
    )
