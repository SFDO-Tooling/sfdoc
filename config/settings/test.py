"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from .base import *  # noqa
from .utils import gen_private_key

# DEBUG
# ------------------------------------------------------------------------------
# Turn debug off so tests run faster
DEBUG = False
TEMPLATES[0]["OPTIONS"]["debug"] = False

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="CHANGEME!!!")

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025

# In-memory email backend stores messages in django.core.mail.outbox
# for unit testing purposes
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# CACHING
# ------------------------------------------------------------------------------
# Speed advantages of in-memory caching without having to run Memcached
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"


# PASSWORD HASHING
# ------------------------------------------------------------------------------
# Use fast password hasher so tests run faster
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# TEMPLATE LOADERS
# ------------------------------------------------------------------------------
# Keep templates in memory so tests run faster
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    [
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ]
]

EASYDITA_INSTANCE_URL = "https://test.easydita.com"
EASYDITA_USERNAME = "testuser"
EASYDITA_PASSWORD = "testpass"

# article related
ARTICLE_AUTHOR = "article-author"
ARTICLE_AUTHOR_OVERRIDE = "article-author-override"
ARTICLE_BODY_CLASS = "article-body-class"

# Salesforce
SALESFORCE_CLIENT_ID = "abc123"
SALESFORCE_SANDBOX = False
SALESFORCE_JWT_PRIVATE_KEY = gen_private_key()
SALESFORCE_USERNAME = "test@example.com"
SALESFORCE_ARTICLE_AUTHOR_FIELD = "ArticleAuthor__c"
SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD = "ArticleAuthorOverride__c"
SALESFORCE_ARTICLE_TYPE = "Resource__kav"
SALESFORCE_ARTICLE_BODY_FIELD = "ArticleBody__c"
SALESFORCE_ARTICLE_TEXT_INDEX_FIELD = "ArticleText__c"
SALESFORCE_ARTICLE_LINK_LIMIT = 100
SALESFORCE_ARTICLE_URL_PATH_PREFIX = "/articles/"
SALESFORCE_API_VERSION = "41.0"
SALESFORCE_COMMUNITY = "testcommunity"

SALESFORCE_DOCSET_TYPE = "Hub_Product_Description__c"
SALESFORCE_DOCSET_ID_FIELD = "EasyDITA_UUID__c"
SALESFORCE_DOCSET_STATUS_FIELD = "Status__c"
SALESFORCE_DOCSET_STATUS_INACTIVE = "Inactive"
SALESFORCE_DOCSET_RELATION_FIELD = SALESFORCE_DOCSET_TYPE

# AWS
AWS_ACCESS_KEY_ID = "ABC123"
AWS_SECRET_ACCESS_KEY = "XYZ789"
AWS_S3_BUCKET = "sfdoc-test"

WHITELIST_HTML = {
    "a": ["href"],
    "body": [],
    "br": [],
    "div": ["class"],
    "h1": [],
    "h2": [],
    "h3": [],
    "h4": [],
    "h5": [],
    "h6": [],
    "head": [],
    "html": [],
    "img": ["src"],
    "li": [],
    "meta": ["content", "name"],
    "p": [],
    "title": [],
    "ul": [],
}
WHITELIST_URL = []

SKIP_HTML_FILES = '["index.html"]'

HEROKU_APP_NAME = "sfdoc.example.com"
