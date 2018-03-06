# sfdoc

sfdoc is a Django web app that securely integrates easyDITA with Salesforce to enable automated publishing for documentation writers.

## Salesforce

Articles are uploaded as drafts, then published when the bundle changes are approved in sfdoc. If bundles changes are rejected, no action is taken in the Salesforce org (drafts remain). Articles are created and drafts updated as needed. sfdoc treats article URL names as unique IDs for the articles, so if an article changes its URL name it will be seen as a new article. Articles that have been deleted in easyDITA will be archived in the Salesforce org.

### Connected app

You will need to create a connected app in the Salesforce org to use for API access. Follow these steps to create the connected app in your Salesforce org:

1. [Create a Private Key and Self-Signed Digital Certificate](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm)
2. [Create a Connected App](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm)

Use the client ID and private key when setting up the environment variables.

### Org setup

Several custom fields need to be created on the Knowledge article object. See the `env` section of this project's [app.json](app.json) for details.

Make sure that Knowledge is enabled in the org and that the API user is marked as a Knowledge user.

## easyDITA

sfdoc assumes that easyDITA has been configured to use their Notify Pull Publishing feature, where the webhook has been configured to be sent to your sfdoc instance at `/publish/webhook/`. Publish from the top-level DITA map to ensure that related changes are propagated through the system.

The easyDITA bundle referenced by the webhook must contain HTML files which are create with the DITA Open Toolkit in easyDITA. There are some assumptions about the file naming and contents:

* HTML files must have certain tags and attributes - see [html.py](sfdoc/publish/html.py) for details
* Image filenames must be unique
* Article URL names must be unique

## Amazon Web Services S3

S3 is used to host the images for both draft and production stages.

Production images are stored in a flat structure at the root of the bucket. Draft images are stored in a flat structure inside a folder at the root of the bucket (folder name is set as environment variable). Storing the items in a flat structure ensures clear and conside image URLs, but the tradeoff is that all image filenames must be unique, so that images aren't overwritten.

sfdoc uploads linked images to the draft directory, then once the bundle changes are approved they are copied to the production directory (bucket root) and deleted from the draft directory.

## Environment variables

sfdoc uses environment variables for configuration, whether the site is run locally or on a server. As a Django app sfdoc supports the standard [Django settings](https://docs.djangoproject.com/en/1.11/topics/settings/).

Further required environment variables are listed in the `env` section of this project's [app.json](app.json) file.

## Run the app locally

Local interactions with any Django app are done using the manage.py file.

### Prerequisites

On Mac OS, `brew` can install both of these.

* [Postgres](https://www.postgresql.org/) must be installed and running, with a database created for the app
* [Redis](https://redis.io/) must be installed and running

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

## Deploy to Heroku

Use this button to deploy your own instance of sfdoc to Heroku.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Administration

Users must have staff permissions to view the publish app.
