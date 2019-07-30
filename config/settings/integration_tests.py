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


# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY", default="RPr%].dHP4VLcU}SW(5o4;cH(]4i7?noV.q5*.%16!@#TYO/ku"
)

RUN_INTEGRATION_TESTS = env("RUN_INTEGRATION_TESTS", default=True)

AWS_S3_DRAFT_IMG_DIR = env("AWS_S3_DRAFT_IMG_DIR", default='testimages/draft/')
AWS_S3_PUBLIC_IMG_DIR = env("AWS_S3_PUBLIC_IMG_DIR", default='testimages/public/')

# django-rq
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")
REDIS_URL += "/1"
RQ_QUEUES = {"default": {"URL": REDIS_URL, "AUTOCOMMIT": False}}

# Make it easy to differentiate between local, staging and prod versions
ENV_COLOR = env("ENV_COLOR", default=" #1798c1")
ENV_NAME = env("ENV_NAME", default="")
