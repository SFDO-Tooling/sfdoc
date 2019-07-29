import sys
import requests
sys.path.append(".")

# This little script helps you to test SFDoc by uploading
# json. You can customize the script however it makes sense
# for what you are trying to test. You can either pull in real
# JSON and use the "call" function or you can synthesize JSON
# using two UUIDs from EasyDITA by calling 

url = "http://localhost:8000/publish/webhook/"

def json_from_UUIDs(output_UUID, resource_UUID):
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


def json_from_UUIDs(json):
    result = requests.post(url, json=json)
    print(url, str(result))

# Example 1: Call from UUIDs:
#
# call(jsonify("5216ef10-ae67-11e9-b28c-42010af00002", "7b62ee90-2886-11e8-8740-42010af00002"))

# Example 2: Call several from JSON
#
# from sfdoc.publish.tests import fake_easydita
# call(fake_easydita.fake_webhook_body_doc_A)
# call(fake_easydita.fake_webhook_body_doc_B)
# call(fake_easydita.fake_webhook_body_doc_A_V2)
# call(fake_easydita.fake_webhook_body_doc_b_V3)
# call(fake_easydita.fake_webhook_body_doc_A_V4)

# call(fake_easydita.fake_webhook_body_doc_B)
