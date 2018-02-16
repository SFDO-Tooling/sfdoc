"""
Local settings

- Run in Debug mode

- Use console backend for emails

- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .base import *  # noqa
from .utils import process_key


# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool('DJANGO_DEBUG', default=True)
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env('DJANGO_SECRET_KEY', default='RPr%].dHP4VLcU}SW(5o4;cH(]4i7?noV.q5*.%16!@#TYO/ku')

# Mail settings
# ------------------------------------------------------------------------------

EMAIL_PORT = 1025

EMAIL_HOST = 'localhost'
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND',
                    default='django.core.mail.backends.console.EmailBackend')


# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# django-debug-toolbar
# ------------------------------------------------------------------------------
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]
INSTALLED_APPS += ['debug_toolbar', ]

INTERNAL_IPS = ['127.0.0.1', '10.0.2.2', ]

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
}

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ['django_extensions', ]

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

# article related
ARTICLE_AUTHOR = env('ARTICLE_AUTHOR')
ARTICLE_AUTHOR_OVERRIDE = env('ARTICLE_AUTHOR_OVERRIDE')
ARTICLE_BODY_CLASS = env('ARTICLE_BODY_CLASS')
IMAGES_URL_PLACEHOLDER = env('IMAGES_URL_PLACEHOLDER')

# AWS
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
S3_IMAGES_DRAFT_DIR = env('S3_IMAGES_DRAFT_DIR')
if S3_IMAGES_DRAFT_DIR[-1] != '/':
    S3_IMAGES_DRAFT_DIR += '/'

# Salesforce
SALESFORCE_CLIENT_ID = env('SALESFORCE_CLIENT_ID')
SALESFORCE_JWT_PRIVATE_KEY = process_key(env('SALESFORCE_JWT_PRIVATE_KEY'))
SALESFORCE_SANDBOX = env.bool('SALESFORCE_SANDBOX')
SALESFORCE_USERNAME = env('SALESFORCE_USERNAME')
SALESFORCE_ARTICLE_AUTHOR_FIELD = env('SALESFORCE_ARTICLE_AUTHOR_FIELD')
SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD = env('SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD')
SALESFORCE_ARTICLE_TYPE = env('SALESFORCE_ARTICLE_TYPE')
SALESFORCE_ARTICLE_BODY_FIELD = env('SALESFORCE_ARTICLE_BODY_FIELD')
SALESFORCE_API_VERSION = env('SALESFORCE_API_VERSION')

# whitelists
HTML_WHITELIST = env.json('HTML_WHITELIST')
URL_WHITELIST = env.json('URL_WHITELIST')

# easyDITA
EASYDITA_INSTANCE_URL = env('EASYDITA_INSTANCE_URL')
EASYDITA_USERNAME = env('EASYDITA_USERNAME')
EASYDITA_PASSWORD = env('EASYDITA_PASSWORD')

HEROKU_APP_NAME = 'localhost:8000'
