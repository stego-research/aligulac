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

# Helper to get env or default
def get_env(name, default=None):
    return os.environ.get(name, default)

from django.utils.translation import gettext_lazy as _

from . import local as local

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local.SECRET_KEY

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

S3_BUCKET = getattr(local, 'S3_BUCKET', '')
S3_ACCESS_KEY = getattr(local, 'S3_ACCESS_KEY', None)
S3_SECRET_KEY = getattr(local, 'S3_SECRET_KEY', None)
S3_REGION = getattr(local, 'S3_REGION', 'us-east-1')
S3_ENDPOINT_URL = getattr(local, 'S3_ENDPOINT_URL', None)

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

    # Views that change only after the quad-daily update can have six hours cache times
    # These typically depend on ratings, but not on specific results
    'aligulac.views.home': 6 * 60 * 60,
    'ratings.inference_views.dual': 6 * 60 * 60,
    'ratings.inference_views.sebracket': 6 * 60 * 60,
    'ratings.inference_views.rrgroup': 6 * 60 * 60,
    'ratings.inference_views.proleague': 6 * 60 * 60,
    'ratings.player_views.historical': 6 * 60 * 60,
    'ratings.ranking_views.periods': 6 * 60 * 60,
    'ratings.ranking_views.period': 6 * 60 * 60,
    'ratings.records_views.history': 6 * 60 * 60,
    'ratings.records_views.hof': 6 * 60 * 60,
    'ratings.records_views.race': 6 * 60 * 60,
    'ratings.report_views.balance': 6 * 60 * 60,

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
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '..', 'resources'),
]

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
