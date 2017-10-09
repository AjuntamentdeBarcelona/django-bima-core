# -*- coding: utf-8 -*-

import logging
import os
import tempfile

from apiclient.discovery import build
from constance import config
import httplib2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser


logger = logging.getLogger(__name__)


# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Message to display if the CLIENT_SECRETS_FILE is missing.
MISSING_CLIENT_SECRETS_MESSAGE = "WARNING: Please configure OAuth 2.0"


def _get_client_secret():
    """
    Creates a temp file with the client_secret.json content from django-constance
    and returns its path.
    """
    path = None
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as client_secret:
        client_secret.write(config.GOOGLE_CLIENT_SECRET)
        path = client_secret.name
    logger.debug('client secret path: {}'.format(path))
    return path


def _get_token():
    """
    Creates a temp file with the oauth2.json token content from django-constance
    and returns its path.
    """
    path = None
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as token:
        if config.GOOGLE_OAUTH2_TOKEN:
            token.write(config.GOOGLE_OAUTH2_TOKEN)
        path = token.name
    logger.debug('oauth2 token path: {}'.format(path))
    return path


def _set_token(path):
    """
    Writes oauth2.json content in django-constance.
    """
    with open(path) as token:
        config.GOOGLE_OAUTH2_TOKEN = token.read()
    logger.debug('oauth2 token saved in django-constance')


def get_authenticated_service(args=None):
    """
    Authorize the request and store authorization credentials.

    In the first authorization it will print a Google auth URL in the terminal
    to do the authorization manually.

    In order to be 12 factors friendly, client_secret.json and oauth2.json
    files are read from and written to django-constance.

    https://12factor.net
    https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
    """
    client_secret_path = _get_client_secret()
    flow = flow_from_clientsecrets(client_secret_path,
                                   scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)
    flow.params['access_type'] = 'offline'  # auto refresh token
    flow.params['include_granted_scopes'] = 'true'

    token_path = _get_token()
    storage = Storage(token_path)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        if args is None:
            # Force to print Google auth URL in the terminal.
            args = argparser.parse_args(args=['--noauth_local_webserver'])
        credentials = run_flow(flow, storage, args)
        _set_token(token_path)

    os.remove(client_secret_path)
    os.remove(token_path)

    return build(API_SERVICE_NAME, API_VERSION, http=credentials.authorize(httplib2.Http()))


def list_channels(username):
    service = get_authenticated_service()
    response = service.channels().list(part='snippet,contentDetails,statistics',
                                       forUsername=username).execute()
    return response['items']
