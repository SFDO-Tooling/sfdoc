import os
import pytest
import environ
from django.conf import settings

if os.environ.get("HEROKU_APP_NAME", "").startswith("sfdoc-review-apps-"):
    env = environ.Env()
    @pytest.fixture(scope='session')
    def django_db_setup():
        settings.DATABASES['default'] = env.db("DATABASE_URL")
