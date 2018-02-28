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

sfdoc uses environment variables for configuration, whether the site is run locally or on a server. As a Django app sfdoc supports the standard [Django settings](https://docs.djangoproject.com/en/1.11/topics/settings/). Additionally, the following variables are required:

* ARTICLE_AUTHOR
  * Name attribute of meta tag to use as author info (easyDITA user ID) - e.g. "article-author"
* ARTICLE_AUTHOR_OVERRIDE
  * Name attribute of meta tag to use as author info override (Salesforce Community user ID) - e.g. "article-author-override"
* ARTICLE_BODY_CLASS
  * Class attribute of div tag used to identify the article body - e.g. "article-body"
* AWS_ACCESS_KEY_ID
  * Amazon Web Services access key ID
* AWS_SECRET_ACCESS_KEY
  * Amazon Web Services secret access key
* AWS_STORAGE_BUCKET_NAME
  * Name of the storage bucket on AWS (used for article image hosting)
* DATABASE_URL
  * The URL of the Postgres database
* EASYDITA_INSTANCE_URL
  * The URL of your easyDITA instance - e.g. "https://example.easydita.com"
* EASYDITA_PASSWORD
  * easyDITA user password (needed for API access)
* EASYDITA_USERNAME
  * easyDITA user name (needed for API access)
* HTML_WHITELIST
  * JSON object whose keys are the whitelisted HTML tags, and the associated values are the whitelisted attributes for that tag - e.g. `{"div": ["class", "id"]}`
* S3_IMAGES_DRAFT_DIR
  * Name to use for the S3 directory where draft images are located - e.g. "draft"
* SALESFORCE_API_VERSION
  * Salesforce API version - e.g. "41.0"
* SALESFORCE_ARTICLE_AUTHOR_FIELD
  * Salesforce article field for the easyDITA author ID - e.g. "ArticleAuthor__c"
* SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD
  * Salesforce article field for the Salesforce Community user ID - e.g. "ArticleAuthorOverride__c"
* SALESFORCE_ARTICLE_BODY_FIELD
  * Salesforce article field for the article body - e.g. "ArticleBody__c"
* SALESFORCE_ARTICLE_TYPE
  * Salesforce  - e.g. "Info__kav"
* SALESFORCE_CLIENT_ID
  * Salesforce connected app Client ID
* SALESFORCE_JWT_PRIVATE_KEY
  * Salesforce connected app JWT private key
* SALESFORCE_SANDBOX
  * Is the connected Salesforce org a sandbox? True/False
* SALESFORCE_USERNAME
  * Salesforce org username for API access
* SKIP_FILES
  * JSON list of HTML filenames to skip when processing (wildcards supported) - e.g. `["index.html", "*-ignore.html"]`
* URL_WHITELIST
  * JSON list of URLs that may be linked to from articles (wildcards supported) - e.g. `["*.salesforce.com/*", "*.salesforce.org/nonprofit"]`

## Administration

Users must have staff permissions to view the publish app.
