"""
Local settings

- Run in Debug mode

- Use console backend for emails

- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .base import *  # noqa

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY", default="RPr%].dHP4VLcU}SW(5o4;cH(]4i7?noV.q5*.%16!@#TYO/ku"
)

# Mail settings
# ------------------------------------------------------------------------------

EMAIL_PORT = 1025

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

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

# AWS
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = env("AWS_S3_BUCKET")

# Salesforce
SALESFORCE_CLIENT_ID = env("SALESFORCE_CLIENT_ID")
SALESFORCE_JWT_PRIVATE_KEY = process_key(env("SALESFORCE_JWT_PRIVATE_KEY"))
SALESFORCE_SANDBOX = env.bool("SALESFORCE_SANDBOX")
SALESFORCE_USERNAME = env("SALESFORCE_USERNAME")

# Make it easy to differentiate between local, staging and prod versions
ENV_COLOR = env("ENV_COLOR", default="green")
ENV_NAME = env("ENV_NAME", default="Local")

# whitelists
WHITELIST_HTML = env.json("WHITELIST_HTML")
WHITELIST_URL = env.json("WHITELIST_URL")

SKIP_HTML_FILES = env.json("SKIP_HTML_FILES")

# easyDITA
EASYDITA_INSTANCE_URL = env("EASYDITA_INSTANCE_URL")
EASYDITA_USERNAME = env("EASYDITA_USERNAME")
EASYDITA_PASSWORD = env("EASYDITA_PASSWORD")