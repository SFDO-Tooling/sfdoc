# Guide to Heretto (EasyDita) Webhooks

## Step 1: Heroku calls Sfdoc via HTTP Post

Heretto (EasyDita) calls this tiny webhook with a POST:

```
@require_POST
def webhook(request):
    """Receive webhook from easyDITA."""
    webhook = Webhook.objects.create(body=request.body.decode('utf-8'))
    process_webhook.delay(webhook.pk)
    return HttpResponse('OK')
```

https://github.com/SFDO-Tooling/sfdoc/blob/8ea7fd252a489b35820073abc36dce3d4f3573f7/sfdoc/publish/views.py#L208

Which just stores the data in a database for processing in an async queue. (Heroku cannot deal with web requests that take longer than 30 second to process, but background jobs can be long-running)

An example of the JSON stored in this database table:

```
{
  "event_id": "dita-ot-publish-complete",
  "event_data": {
    "output-uuid": "a5757040-a3e8-11ec-b267-024282b79599",
    "publish-result": "success",
    "final_user": "sknox@salesforce.com",
    "branch": "master",
    "workflow": "quick-review"
  },
  "resource_id": "4487f3a0-51bd-11e9-903f-42010af00002"
}
```

The table is indexed here:

https://sfdoc.herokuapp.com/admin-c35ot12TpZCX5Hcn/publish/webhook/

## Step 2: Sfdoc parses the JSON

The async job parses some JSON:

https://github.com/SFDO-Tooling/sfdoc/blob/8ea7fd252a489b35820073abc36dce3d4f3573f7/sfdoc/publish/tasks.py#L313

It's looking for webhook messages with `event_id = dita-ot-publish-complete` like the above.

Further examples:

https://github.com/SFDO-Tooling/sfdoc/blob/8ea7fd252a489b35820073abc36dce3d4f3573f7/sfdoc/publish/tests/fake_easydita.py#L4

## Step 3: Download Zipfile

Based on the JSON, it knows what zipfile to download. The resource_id is persistent and represents the ditamap, I think. output-uuid represents a single zipfile.

The URL is based on the Output-UUID:

https://github.com/SFDO-Tooling/sfdoc/blob/8ea7fd252a489b35820073abc36dce3d4f3573f7/sfdoc/publish/models.py#L121

Like this:

```
`url = f"https://salesforce.easydita.com/rest/all-files/{UUID}/bundle"`
```

https://github.com/SFDO-Tooling/sfdoc/blob/8ea7fd252a489b35820073abc36dce3d4f3573f7/sfdoc/publish/tasks.py#L23

```
def _download_and_unpack_easydita_bundle(bundle, path):
    logger = get_logger(bundle)

    logger.info('Downloading easyDITA bundle from %s', bundle.url)
    assert bundle.url.startswith("https://")
    auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
    response = requests.get(bundle.url, auth=auth)
    zip_file = BytesIO(response.content)
    utils.unzip(zip_file, path, recursive=True, ignore_patterns=["*/assets/*"])
```

Seems to use just HTTP auth.

You can get one of these zipfiles from a command line (or browser?) like this:

`curl -o filename -u [mrbelvedere@salesforce.org](mailto:mrbelvedere@salesforce.org):$password https://salesforce.easydita.com/rest/all-files/9e1e2bc0-8276-11e9-b28c-42010af00002/bundle`

Fill in the real password...

## Step 4: Download the zipfile

The zipfile has the HTML data in it in a bit of a weird format.

For one thing, it’s a Zipfile with a Zipfile inside of it.

```
 4799689  Defl:N  4161751  13% 03-16-2022 18:23 242efa26  BundleA_2019-05-30T01-02Z.zip
     400  Defl:N      213  47% 03-16-2022 18:23 bc70c14e  __manifest__.xml
```

Here’s an example:

[easydita.zip](https://quip.com/2/blob/IfPAAAgay5m/onqZgKUaFofOoR_LBMPwmQ?name=easydita.zip&user_id=ZUeAEAsx8E9&user_id=ZUeAEAsx8E9)


