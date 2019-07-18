import sys
import requests
from pprint import pprint
sys.path.append(".")
from sfdoc.publish.tests import fake_easydita

url = "http://localhost:8000/publish/webhook/"

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


def call(json):
    result = requests.post(url, json=json)
    print(url, str(result))



# Bundle A
call(fake_easydita.fake_webhook_body_doc_A)

# Bundle B
call(fake_easydita.fake_webhook_body_doc_B)

# Bundle A
call(fake_easydita.fake_webhook_body_doc_A_V2)

# Bundle B
call(fake_easydita.fake_webhook_body_doc_b_V3)

# Bundle A
call(fake_easydita.fake_webhook_body_doc_A_V4)

# Bundle B
call(fake_easydita.fake_webhook_body_doc_B)
