import os

if os.environ.get("HEROKU_APP_NAME", "").startswith("sfdoc-review-apps-"):
    assert not os.system("pip install --upgrade -r requirements/test.txt")
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.integration_tests"
    assert not os.system("pytest")
