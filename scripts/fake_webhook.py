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

# Bundle A
output_UUID = "726c4040-a68c-11e9-b28c-42010af00002"
resource_UUID = "77b09a40-819a-11e9-b28c-42010af00002"

# Bundle B
output_UUID = "211d8cc0-8275-11e9-b28c-42010af00002"
resource_UUID = "bf0080a0-8270-11e9-b28c-42010af00002"

# Bundle B V3
output_UUID = "de6045b0-8b95-11e9-b28c-42010af00002"
resource_UUID = "bf0080a0-8270-11e9-b28c-42010af00002"

result = requests.post(url, json=jsonify(output_UUID, resource_UUID))

pprint(result)
