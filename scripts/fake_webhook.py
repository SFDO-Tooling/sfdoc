import sys
import requests
from pprint import pprint


def jsonify(output_UUID, resource_UUID):
    return {
        "event_id": "dita-ot-publish-complete",
        "event_data": {
            "publish-result": "success",
            "output-uuid": output_UUID,
            "description": "HTML",
            "processor": "superfaker",
            "date-time": "2019-05-30T00:51:58.996Z",
        },
        "resource_id": resource_UUID,
    }


url = "https://sfdoc-staging.sfdc.sh/publish/webhook/"
output_UUID = "726c4040-a68c-11e9-b28c-42010af00002"
resource_UUID = "7b62ee90-2886-11e8-8740-42010af00002"
result = requests.post(url, json=jsonify(output_UUID, resource_UUID))

pprint(result)
