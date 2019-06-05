# SFDoc's Architecture and Data Flow

## Architecture

Raw documents are authored in EasyDITA. They are processed
there and then sent to SFDoc as HTML with images.

SFDoc copies and validates the data before sending images to 
S3 and HTML to Salesforce Org. (SFDO calls their Org "WLMA")

SFDoc itself has two main components: a series of RQ tasks that
process the data and move it from place to place and a 
Django Web UI that allows reviewing data before publishing it.

## High Level Flow

SFDoc connects EasyDITA to the WLMA Salesforce Org and stores images on S3.

The process has five main phases:

 1. Callback: Receiving notice from EasyDITA of a document being published. 
    This creates a Webhook object which is processed by a queue worker.
 
 2. Processing: The queue worker calls back into EasyDITA to get the Zipped bundle and
    publish it. The zipfile contains HTML and images.

 3. Uploading: Individual articles and images are uploaded to WLMA and S3.

 4. Review: Later, a documenation administrator can review changes in draft form
    on WLMA.

 5. Publishing: When the administrator is happy, they can publish these articles so 
    that the articles become visible on WLMA.

### 1. Callback

After a user publishes in EasyDITA, EasyDITA calls SFDoc with a JSON Callback
including the UUID of the Ditamap that was published. 

The callback queues up an sfdoc.publish.process_webhook job to run later.

### 2. Processing

The process_webhook job is responsible for downloading and processing the
bundle. 

First it creates a "bundle" object which represents the bundle of files that
was downloaded. See sfdoc.publish.models for more info on the Bundle objects.

This bundle is put into an approval queue.

Then a job is queued (there's a job queue, separate from the approval queue)
to actually download and process the bundle so that it will be ready for approval or 
rejection.

When the bundle's processing job gets to the front of the job queue,
processing happens. This consists of:

 * downloading the bundle as a zipfile
 * unzipping it to a temporary directory
 * processing the HTML to validate URLs and tags
 * collect references to images
 * check for articles destined to have URLs that are identical 
 * check for images with the same name
 * look for images to delete because they aren't used anymore
 * look for articles to archive because they aren't used anymore

Notes about the images and articles to delete/update are stored in the
Article and Image models in the postgres database. These can be used to
show a reviewer what will change if the bundle is pushed to production.

### 3. Uploading

Images are uploaded to S3 and WLMA. There is a "draft" prefix (folder) on 
S3 for images that are not public yet. Draft images use the draft feature of
Salesforce Knowledge.

### 4. Review

There ia a Django UI that the end-user can use to review draft bundles on 
WLMA/S3.

### 5. Publishing

Publishing consists of moving the S3 files and changing the publish status
in WLMA.
