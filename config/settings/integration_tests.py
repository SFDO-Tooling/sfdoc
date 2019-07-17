"""
Integration test

- Okay to clear database (should run as test_XXXX anyhow)
- Okay to delete all articles from Salesforce instance
- Namespace objects in S3
- Use authentication info from the .env
"""

from .base import *  # noqa
from .utils import process_key

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

# Mail settings
# ------------------------------------------------------------------------------

EMAIL_xRT = 1025

EMAIL_HOST = "localhost"
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)


# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# django-debug-toolbar
# ------------------------------------------------------------------------------
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INSTALLED_APPS += ["debug_toolbar"]

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

# article related
ARTICLE_AUTHOR = env("ARTICLE_AUTHOR", default="ArticleOwner")
ARTICLE_AUTHOR_OVERRIDE = env(
    "ARTICLE_AUTHOR_OVERRIDE", default="ArticleContributorOverride"
)
ARTICLE_BODY_CLASS = env("ARTICLE_BODY_CLASS", default="sfdo-kb__body")

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY", default="RPr%].dHP4VLcU}SW(5o4;cH(]4i7?noV.q5*.%16!@#TYO/ku"
)

# AWS
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = env("AWS_S3_BUCKET")

# Salesforce
SALESFORCE_CLIENT_ID = env("SALESFORCE_CLIENT_ID")
SALESFORCE_JWT_PRIVATE_KEY = process_key(env("SALESFORCE_JWT_PRIVATE_KEY"))
SALESFORCE_SANDBOX = env.bool("SALESFORCE_SANDBOX")
SALESFORCE_USERNAME = env("SALESFORCE_USERNAME")
SALESFORCE_ARTICLE_AUTHOR_FIELD = env("SALESFORCE_ARTICLE_AUTHOR_FIELD")
SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD = env(
    "SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD"
)
SALESFORCE_ARTICLE_TYPE = env("SALESFORCE_ARTICLE_TYPE")
SALESFORCE_ARTICLE_BODY_FIELD = env("SALESFORCE_ARTICLE_BODY_FIELD")
SALESFORCE_ARTICLE_URL_PATH_PREFIX = env(
    "SALESFORCE_ARTICLE_URL_PATH_PREFIX", default="/articles/Resource/"
)
SALESFORCE_ARTICLE_TEXT_INDEX_FIELD = env(
    "SALESFORCE_ARTICLE_TEXT_INDEX_FIELD", default=False
)
SALESFORCE_ARTICLE_LINK_LIMIT = env("SALESFORCE_ARTICLE_LINK_LIMIT", default=100)
SALESFORCE_API_VERSION = env("SALESFORCE_API_VERSION")
SALESFORCE_COMMUNITY = env("SALESFORCE_COMMUNITY")

# whitelists
WHITELIST_HTML = env.json("WHITELIST_HTML")
WHITELIST_URL = env.json("WHITELIST_URL")

SKIP_HTML_FILES = env.json("SKIP_HTML_FILES")

# easyDITA
EASYDITA_INSTANCE_URL = env("EASYDITA_INSTANCE_URL")
EASYDITA_USERNAME = env("EASYDITA_USERNAME")
EASYDITA_PASSWORD = env("EASYDITA_PASSWORD")

HEROKU_APP_NAME = "localhost:8000"

RUN_INTEGRATION_TESTS = env("RUN_INTEGRATION_TESTS", default=True)

# Make it easy to differentiate between local, staging and prod versions
ENV_COLOR = env("ENV_COLOR", default=" #1798c1")
ENV_NAME = env("ENV_NAME", default="")
