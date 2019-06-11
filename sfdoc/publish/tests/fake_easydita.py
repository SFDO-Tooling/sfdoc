# output-uuid# https://salesforce.easydita.com/api/get/db/organizations/salesforce/published/77b09a40-819a-11e9-b28c-42010af00002/BundleA_2019-05-30T01-02Z.zip
fake_webhook_body_doc_A = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "9e1e2bc0-8276-11e9-b28c-42010af00002",
        "description": "HTML",
        "processor": "dita-open-toolkits/organization-dita-ot-2.2.5-custom.jcmconnect",
        "date-time": "2019-05-30T01:02:38.211Z",
    },
    "resource_id": "77b09a40-819a-11e9-b28c-42010af00002",
}

ditamap_A_titles = [
    "Article A3",
    "Article A2",
    "Article A1",
    "Article B1",
    "Test Documentation: Bundle A",
    "Article B2",
    "Article B3",
]

# https://salesforce.easydita.com/api/get/db/organizations/salesforce/published/77b09a40-819a-11e9-b28c-42010af00002/BundleA_2019-06-04T10-30Z.zip
fake_webhook_body_doc_A_V2 = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "d289e070-86b3-11e9-b28c-42010af00002",
        "description": "V2",
        "processor": "dita-open-toolkits/organization-dita-ot-2.2.5-custom.jcmconnect",
        "date-time": "2019-06-04T10:14:45.443Z",
    },
    "resource_id": "77b09a40-819a-11e9-b28c-42010af00002",
}

ditamap_A_V2_titles = [
    "Article A3! Updated",
    "Article A2",
    "Article A1",
    "Article B1",
    "Test Documentation: Bundle A",
    "Article B2",
]

ditamap_A_V5_titles = [
    "Article A3! Updated",
    "Article A1",
    "Test Documentation: Bundle A",
]

ditamap_B_titles = [
    "Article 1, Bundle B",
    "Article 3, Bundle B",
    "Article 2, Bundle B",
    "Test Documentation: Bundle B",
]

ditamap_B_V3_titles = [
    "Article 1, Bundle B",
    "Test Documentation: Bundle B",
]

# https://salesforce.easydita.com/api/get/db/organizations/salesforce/published/77b09a40-819a-11e9-b28c-42010af00002/BundleA_2019-06-04T16-31Z.zip
fake_webhook_body_doc_A_V3 = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "35fa58b0-86e6-11e9-b28c-42010af00002",
        "description": "V3 with image",
        "processor": "dita-open-toolkits/organization-dita-ot-2.2.5-custom.jcmconnect",
        "date-time": "2019-06-04T16:31:31.778Z",
    },
    "resource_id": "77b09a40-819a-11e9-b28c-42010af00002",
}

fake_webhook_body_doc_A_V4 = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "8a66e690-8725-11e9-b28c-42010af00002",
        "description": "V4 no image",
    },
    "resource_id": "77b09a40-819a-11e9-b28c-42010af00002",
}

fake_webhook_body_doc_A_V5 = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "3953bb10-8992-11e9-b28c-42010af00002",
        "description": "V5 no image",
    },
    "resource_id": "77b09a40-819a-11e9-b28c-42010af00002",
}

# https://salesforce.easydita.com/api/get/db/organizations/salesforce/published/bf0080a0-8270-11e9-b28c-42010af00002/BundleB_2019-05-30T00-51Z.zip
fake_webhook_body_doc_B = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "211d8cc0-8275-11e9-b28c-42010af00002",
        "description": "HTML",
        "processor": "dita-open-toolkits/organization-dita-ot-2.2.5-custom.jcmconnect",
        "date-time": "2019-05-30T00:51:58.996Z",
    },
    "resource_id": "bf0080a0-8270-11e9-b28c-42010af00002",
}

fake_webhook_body_doc_b_V3 = {
    "event_id": "dita-ot-publish-complete",
    "event_data": {
        "publish-result": "success",
        "output-uuid": "de6045b0-8b95-11e9-b28c-42010af00002",
        "description": "Version 3: Bundle B, Article 2 removed",
        "processor": "dita-open-toolkits/organization-dita-ot-2.2.5-custom.jcmconnect",
        "date-time": "2019-06-10T15:39:00.884Z",
    },
    "resource_id": "bf0080a0-8270-11e9-b28c-42010af00002",
}


preloaded_article_titles = [
    "foundationConnect Documentation",
    "foundationConnect FAQ",
    "foundationConnect Grantee Community Configuration Guide",
    "foundationConnect Overview",
    "foundationConnect Release Notes",
]
