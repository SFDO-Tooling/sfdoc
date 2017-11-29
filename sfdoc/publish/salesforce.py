from calendar import timegm
from datetime import datetime

from django.conf import settings
import json
import jwt
import requests
from simple_salesforce import Salesforce


def get_salesforce_api():
    """Get an instance of the Salesforce REST API."""
    payload = {
        'alg': 'RS256',
        'iss': settings.SALESFORCE_CLIENT_ID,
        'sub': settings.SALESFORCE_USERNAME,
        'aud': settings.SALESFORCE_AUTH_SITE,
        'exp': timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(
        payload,
        settings.SALESFORCE_JWT_PRIVATE_KEY,
        algorithm='RS256',
    )
    url = settings.SALESFORCE_AUTH_SITE + '/services/oauth2/token'
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': encoded_jwt,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    response_data = json.loads(response.text)
    return Salesforce(
        instance_url=response_data['instance_url'],
        session_id=response_data['access_token'],
    )
