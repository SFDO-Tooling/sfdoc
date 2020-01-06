import os
import pytest
import environ
from django.conf import settings

# this recipe convinces pytest-sjango to use the pre-existing 
# database instead of creating a new one. Heroku apps seem
# to not have permissions to create databases on the fly.

# https://pytest-django.readthedocs.io/en/latest/database.html#using-an-existing-external-database-for-tests

if os.environ.get("HEROKU_APP_NAME", "").startswith("sfdoc-review-apps-"):
    env = environ.Env()
    @pytest.fixture(scope='session')
    def django_db_setup():
        settings.DATABASES['default'] = env.db("DATABASE_URL")
