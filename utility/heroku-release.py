import os

if os.environ.get(HEROKU_APP_NAME, "").startswith("sfdoc-review-apps-"):
    os.system("pip install --upgrade -r test/requirements.txt")
    os.system("pytest")

# Todo:

# check for HEROKU_APP_NAME . startswith(sfdoc-review-apps-)
# then run `pip install --upgrade test/requirements.txt`
# then run pytest with all of the environment variables
