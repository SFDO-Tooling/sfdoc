from calendar import timegm
from datetime import datetime

from django.conf import settings
import jwt
import requests
from simple_salesforce import Salesforce


def get_salesforce_api(review=False):
    """Get an instance of the Salesforce REST API."""
    if review:
        client_id = settings.SALESFORCE_CLIENT_ID_REVIEW
        key = settings.SALESFORCE_JWT_PRIVATE_KEY_REVIEW
        sandbox = settings.SALESFORCE_SANDBOX_REVIEW
        username = settings.SALESFORCE_USERNAME_REVIEW
    else:
        client_id = settings.SALESFORCE_CLIENT_ID
        key = settings.SALESFORCE_JWT_PRIVATE_KEY
        sandbox = settings.SALESFORCE_SANDBOX
        username = settings.SALESFORCE_USERNAME
    url = 'https://login.salesforce.com'
    if sandbox:
        url = url.replace('login', 'test')
    payload = {
        'alg': 'RS256',
        'iss': client_id,
        'sub': username,
        'aud': url,
        'exp': timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(payload, key, algorithm='RS256')
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': encoded_jwt,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    auth_url = url + '/services/oauth2/token'
    response = requests.post(url=auth_url, data=data, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return Salesforce(
        instance_url=response_data['instance_url'],
        session_id=response_data['access_token'],
        sandbox=sandbox,
        version=settings.SALESFORCE_API_VERSION,
        client_id='sfdoc',
    )
