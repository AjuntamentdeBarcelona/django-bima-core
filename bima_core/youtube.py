# -*- coding: utf-8 -*-

"""
Youtube sandbox to play with its API.
"""

from apiclient.discovery import build
import httplib2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "./client_secret.json"

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the auth token returned by Google.
TOKEN_FILE = "./dam-oauth2.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is missing.
MISSING_CLIENT_SECRETS_MESSAGE = "WARNING: Please configure OAuth 2.0"


def get_authenticated_service(args=None):
    """
    Authorize the request and store authorization credentials.

    https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
    """
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                                   scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)
    flow.params['access_type'] = 'offline'
    flow.params['include_granted_scopes'] = True

    storage = Storage(TOKEN_FILE)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(API_SERVICE_NAME, API_VERSION, http=credentials.authorize(httplib2.Http()))


def list_channels(username):
    service = get_authenticated_service()
    response = service.channels().list(part='snippet,contentDetails,statistics',
                                       forUsername=username).execute()
    try:
        item = response['items'][0]
        print('This channel\'s ID is {}. Its title is {}, and it has {} views.'.format(
            item['id'],
            item['snippet']['title'],
            item['statistics']['viewCount'],
        ))
    except IndexError:
        print('No channels for user {}. Response:'.format(username))
        print(response)


if __name__ == '__main__':
    list_channels('')
