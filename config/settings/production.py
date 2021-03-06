"""
Production Configurations

- Use Amazon's S3 for storing static files and uploaded media
- Use mailgun to send emails
- Use Redis for cache

"""

import logging

from boto.s3.connection import OrdinaryCallingFormat

from .base import *  # noqa

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Raises ImproperlyConfigured exception if DJANGO_SECRET_KEY not in os.environ
SECRET_KEY = env("DJANGO_SECRET_KEY")


# This ensures that Django will be able to detect a secure connection
# properly on Heroku.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Use Whitenoise to serve static files
# See: https://whitenoise.readthedocs.io/
WHITENOISE_MIDDLEWARE = ["whitenoise.middleware.WhiteNoiseMiddleware"]
MIDDLEWARE = WHITENOISE_MIDDLEWARE + MIDDLEWARE
DEFENDER_MIDDLEWARE = ["defender.middleware.FailedLoginMiddleware"]
MIDDLEWARE = MIDDLEWARE + DEFENDER_MIDDLEWARE


# SECURITY CONFIGURATION
# ------------------------------------------------------------------------------
# See https://docs.djangoproject.com/en/dev/ref/middleware/#module-django.middleware.security
# and https://docs.djangoproject.com/en/dev/howto/deployment/checklist/#run-manage-py-check-deploy

# set this to 60 seconds and then to 518400 when you can prove it works
SECURE_HSTS_SECONDS = 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# SITE CONFIGURATION
# ------------------------------------------------------------------------------
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["https://github.com/SalesforceFoundation/sfdoc"]
)
# END SITE CONFIGURATION

INSTALLED_APPS += ["gunicorn"]
INSTALLED_APPS += ["defender"]


# Static Assets
# ------------------------
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See:
# https://docs.djangoproject.com/en/dev/ref/templates/api/#django.template.loaders.cached.Loader
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------

# Use the Heroku-style specification
# Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
DATABASES["default"] = env.db("DATABASE_URL")

# CACHING
# ------------------------------------------------------------------------------

REDIS_LOCATION = "{0}/{1}".format(env("REDIS_URL", default="redis://127.0.0.1:6379"), 0)
# Heroku URL does not pass the DB number, so we parse it in
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_LOCATION,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # mimics memcache behavior.
            # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
        },
    }
}


# Custom Admin URL, use {% url 'admin:index' %}
ADMIN_URL = env("DJANGO_ADMIN_URL")

# django-defender configuration
DEFENDER_REDIS_NAME = "default"

# Make it easy to differentiate between local, staging and prod versions
ENV_COLOR = env("ENV_COLOR", default=" #1798c1")
ENV_NAME = env("ENV_NAME", default="")

# AWS
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = env("AWS_S3_BUCKET")

# Salesforce
SALESFORCE_CLIENT_ID = env("SALESFORCE_CLIENT_ID")
SALESFORCE_JWT_PRIVATE_KEY = process_key(env("SALESFORCE_JWT_PRIVATE_KEY"))
SALESFORCE_SANDBOX = env.bool("SALESFORCE_SANDBOX")
SALESFORCE_USERNAME = env("SALESFORCE_USERNAME")

# whitelists
WHITELIST_HTML = env.json("WHITELIST_HTML")
WHITELIST_URL = env.json("WHITELIST_URL")

SKIP_HTML_FILES = env.json("SKIP_HTML_FILES")

# easyDITA
EASYDITA_INSTANCE_URL = env("EASYDITA_INSTANCE_URL")
EASYDITA_USERNAME = env("EASYDITA_USERNAME")
EASYDITA_PASSWORD = env("EASYDITA_PASSWORD")