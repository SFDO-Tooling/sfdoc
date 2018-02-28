# sfdoc

sfdoc is a Django web app that securely integrates easyDITA with Salesforce to enable automated publishing for documentation writers.

## Running the app locally

Local interactions with any Django app are done using the manage.py file.

### Prerequisites

* [Postgres](https://www.postgresql.org/) must be installed and running, with a database created for the app

### Setup

1. Clone the repository
2. [Create a virtual environment with Python 3](https://docs.python.org/3/library/venv.html#creating-virtual-environments)
3. Activate the virtual environment and install the requirements: `$ pip install -r requirements/local.txt`
4. Create a `.env` file with the necessary environment variables and use it every time you run manage.py by setting the environment variable `DJANGO_READ_DOT_ENV_FILE=True`.

### Django commands

```bash
$ python manage.py test             # run tests
$ python manage.py createsuperuser  # create a superuser
$ python manage.py runserver        # run the app locally
```

## Environment variables

sfdoc uses environment variables for configuration, whether the site is run locally or on a server. As a Django app sfdoc supports the standard [Django settings](https://docs.djangoproject.com/en/1.11/topics/settings/).

Further required environment variables are listed in the `env` section of this project's [app.json](app.json) file.

## Administration

Users must have staff permissions to view the publish app.
