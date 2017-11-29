from calendar import timegm
from datetime import datetime

from django.conf import settings
import json
import jwt
import requests
from simple_salesforce import Salesforce


def get_salesforce_api():
    """Get an instance of the Salesforce REST API."""
    url = settings.SALESFORCE_LOGIN_URL
    if settings.SALESFORCE_SANDBOX:
        url = url.replace('login', 'test')
    payload = {
        'alg': 'RS256',
        'iss': settings.SALESFORCE_CLIENT_ID,
        'sub': settings.SALESFORCE_USERNAME,
        'aud': url,
        'exp': timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(
        payload,
        settings.SALESFORCE_JWT_PRIVATE_KEY,
        algorithm='RS256',
    )
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': encoded_jwt,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    auth_url = url + '/services/oauth2/token'
    response = requests.post(url=auth_url, data=data, headers=headers)
    response.raise_for_status()
    response_data = json.loads(response.text)
    return Salesforce(
        instance_url=response_data['instance_url'],
        session_id=response_data['access_token'],
        sandbox=settings.SALESFORCE_SANDBOX,
        client_id='sfdoc',
    )
