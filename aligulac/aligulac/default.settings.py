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

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

import aligulac.local as local

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = local.DEBUG
DEBUG_TOOLBAR = local.DEBUG_TOOLBAR

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = local.ALLOWED_HOSTS

LOCALE_PATHS = local.LOCALE_PATHS
LANGUAGE_CODE = 'en_US'

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
    ('pl', 'Polski'),
    ('da', 'Dansk'),
    ('nb', 'Norsk (bokmål)'),
    ('zh', '中文(简体)'),
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
S3_STATIC_BUCKET = getattr(local, 'S3_STATIC_BUCKET', getattr(local, 'S3_BUCKET_STATIC', ''))
S3_STATIC_ACCESS_KEY = getattr(local, 'S3_STATIC_ACCESS_KEY', getattr(local, 'S3_ACCESS_KEY', None))
S3_STATIC_SECRET_KEY = getattr(local, 'S3_STATIC_SECRET_KEY', getattr(local, 'S3_SECRET_KEY', None))
S3_STATIC_REGION = getattr(local, 'S3_STATIC_REGION', getattr(local, 'S3_REGION', 'us-east-1'))
S3_STATIC_ENDPOINT_URL = getattr(local, 'S3_STATIC_ENDPOINT_URL', getattr(local, 'S3_ENDPOINT_URL', None))
S3_STATIC_CUSTOM_DOMAIN = getattr(local, 'S3_STATIC_CUSTOM_DOMAIN', getattr(local, 'S3_CUSTOM_DOMAIN', None))
S3_STATIC_DEFAULT_ACL = getattr(local, 'S3_STATIC_DEFAULT_ACL', getattr(local, 'S3_DEFAULT_ACL', None))

CACHES = {
    'default': {
        'BACKEND': local.CACHE_BACKEND,
        'LOCATION': local.CACHE_LOCATION,
    }
}

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
        'NAME': 'aligulac',
        'USER': local.DB_USER,
        'PASSWORD': local.DB_PASSWORD,
        'HOST': 'localhost',
    }
}

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': local.ERROR_LOG_FILE
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': True
        }
    }
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
if S3_STATIC_CUSTOM_DOMAIN:
    STATIC_URL = f'https://{S3_STATIC_CUSTOM_DOMAIN}/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '..', 'resources'),
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
AWS_QUERYSTRING_AUTH = False

# Storage Configuration
if S3_STATIC_BUCKET:
    from storages.backends.s3boto3 import S3Boto3Storage
    from django.contrib.staticfiles.storage import ManifestFilesMixin

    class StaticS3Storage(ManifestFilesMixin, S3Boto3Storage):
        file_overwrite = True
        querystring_auth = False

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
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
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
            ]
            # ... some options here ...
        },
    },
]

SHOW_PER_LIST_PAGE = 40
