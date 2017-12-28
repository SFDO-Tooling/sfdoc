'''
Test settings

- Used to run tests fast on the continuous integration server and locally
'''

from .base import *  # noqa
from .utils import gen_private_key


# DEBUG
# ------------------------------------------------------------------------------
# Turn debug off so tests run faster
DEBUG = False
TEMPLATES[0]['OPTIONS']['debug'] = False

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env('DJANGO_SECRET_KEY', default='CHANGEME!!!')

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025

# In-memory email backend stores messages in django.core.mail.outbox
# for unit testing purposes
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# CACHING
# ------------------------------------------------------------------------------
# Speed advantages of in-memory caching without having to run Memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'


# PASSWORD HASHING
# ------------------------------------------------------------------------------
# Use fast password hasher so tests run faster
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# TEMPLATE LOADERS
# ------------------------------------------------------------------------------
# Keep templates in memory so tests run faster
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ['django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ], ],
]

EASYDITA_INSTANCE_URL = 'https://test.easydita.com'
EASYDITA_USERNAME = 'testuser'
EASYDITA_PASSWORD = 'testpass'

IMAGES_URL_PLACEHOLDER = 'ARTICLE_IMAGES_URL'
IMAGES_URL_ROOT = 'http://example.com/images'

# mail
FROM_EMAIL = 'admin@example.com'
TO_EMAILS = ['beatrice@example.com', 'john@example.com', 'susan@example.com']

# Salesforce
SALESFORCE_CLIENT_ID = 'abc123'
SALESFORCE_CLIENT_ID_REVIEW = 'zyx098'
SALESFORCE_SANDBOX = False
SALESFORCE_SANDBOX_REVIEW = True
SALESFORCE_JWT_PRIVATE_KEY = gen_private_key()
SALESFORCE_JWT_PRIVATE_KEY_REVIEW = gen_private_key()
SALESFORCE_USERNAME = 'test@example.com'
SALESFORCE_USERNAME_REVIEW = 'test@example-review.com'
SALESFORCE_ARTICLE_TYPE = 'Knowledge__kav'
SALESFORCE_ARTICLE_BODY_FIELD = 'ArticleBody__c'
SALESFORCE_API_VERSION = '41.0'

# AWS
AWS_ACCESS_KEY_ID = 'ABC123'
AWS_SECRET_ACCESS_KEY = 'XYZ789'
AWS_STORAGE_BUCKET_NAME = 'sfdoc-test'

HTML_WHITELIST = {
    'a': ['href'],
    'body': [],
    'br': [],
    'div': ['class'],
    'h1': [],
    'h2': [],
    'h3': [],
    'h4': [],
    'h5': [],
    'h6': [],
    'head': [],
    'html': [],
    'img': ['src'],
    'li': [],
    'meta': ['content', 'name'],
    'p': [],
    'ul': []
}
LINK_WHITELIST = []

HEROKU_APP_NAME = 'sfdoc.example.com'
