from datetime import datetime
from datetime import timedelta
from http import HTTPStatus

from django.conf import settings
import jwt
import requests


def get_access_token(connected_app):
    """Use JWT to get OAuth access token."""
    payload = {
        'iss': settings.SALESFORCE_CLIENT_ID,
        'sub': settings.SALESFORCE_USERNAME,
        'aud': settings.SALESFORCE_AUTH_SITE,
        'exp': datetime.utcnow() + timedelta(minutes=1),
    }
    encoded_jwt = jwt.encode(
        payload,
        settings.SALESFORCE_CLIENT_SECRET,
        algorithm='RS256',
    )
    url = settings.SALESFORCE_AUTH_SITE + '/services/oauth2/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    params = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': encoded_jwt,
    }
    response = requests.post(
        url,
        data=encoded_jwt,
        headers=headers,
        params=params,
    )
    if response.status_code >= HTTPStatus.BAD_REQUEST:
        raise Exception('Status {}: {}'.format(
            response.status_code,
            response.content,
        ))
    return response.body['access_token']


def get_salesforce_api():
    """Get an instance of the Salesforce REST API."""
    return Salesforce(
        instance=settings.SALESFORCE_INSTANCE,
        session_id=get_access_token(),
    )
