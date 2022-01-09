"""
Integration test

- Okay to clear database (should run as test_XXXX anyhow)
- Okay to delete all articles from Salesforce instance
- Namespace objects in S3
- Use authentication info from the .env
"""

from .base import *  # noqa

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

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------


# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY", default="RPr%].dHP4VLcU}SW(5o4;cH(]4i7?noV.q5*.%16!@#TYO/ku"
)

RUN_INTEGRATION_TESTS = env("RUN_INTEGRATION_TESTS", default=True)

# AWS
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = env("AWS_S3_BUCKET")

AWS_S3_DRAFT_IMG_DIR = env("AWS_S3_DRAFT_IMG_DIR", default='testimages/draft/')
AWS_S3_PUBLIC_IMG_DIR = env("AWS_S3_PUBLIC_IMG_DIR", default='testimages/public/')

# Salesforce
SALESFORCE_CLIENT_ID = env("SALESFORCE_CLIENT_ID")
SALESFORCE_JWT_PRIVATE_KEY = process_key(env("SALESFORCE_JWT_PRIVATE_KEY"))
SALESFORCE_SANDBOX = env.bool("SALESFORCE_SANDBOX")
SALESFORCE_USERNAME = env("SALESFORCE_USERNAME")
SALESFORCE_ARTICLE_LINK_LIMIT = 100


# django-rq
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")
REDIS_URL += "/1"
RQ_QUEUES = {"default": {"URL": REDIS_URL, "AUTOCOMMIT": False}}

# Make it easy to differentiate between local, staging and prod versions
ENV_COLOR = env("ENV_COLOR", default=" #1798c1")
ENV_NAME = env("ENV_NAME", default="")

# whitelists
WHITELIST_HTML = env.json("WHITELIST_HTML")
WHITELIST_URL = env.json("WHITELIST_URL")

SKIP_HTML_FILES = env.json("SKIP_HTML_FILES")

# easyDITA
EASYDITA_INSTANCE_URL = env("EASYDITA_INSTANCE_URL")
# One of our test cases changed in EasyDITA and needs to be fixed back.
EASYDITA_USERNAME = "mock" # env("EASYDITA_USERNAME")
EASYDITA_PASSWORD = env("EASYDITA_PASSWORD")