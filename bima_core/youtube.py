# -*- coding: utf-8 -*-

import logging
import os
import random
import tempfile
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from constance import config
import httplib
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

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (IOError, httplib2.HttpLib2Error, httplib.NotConnected,
                        httplib.IncompleteRead, httplib.ImproperConnectionState,
                        httplib.CannotSendRequest, httplib.CannotSendHeader,
                        httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


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


# TODO: WIP: upload videos to Youtube.
# Based on https://developers.google.com/youtube/v3/docs/videos/insert.

def upload_video(photo):
    """
    Upload the models.Photo video instance as private video if it's not already uploaded.
    """
    if photo.youtube_code:
        logger.warning('Video already in Youtube', extra={
            'photo': photo,
            'youtube_code': photo.youtube_code
        })
        return

    if not photo.is_video:
        logger.warning('Photo is not a video', extra={'photo': photo})
        return

    service = get_authenticated_service()
    try:
        _initialize_upload(
            service=service,
            body={
                'snippet': {
                    'title': photo.title,
                    'description': photo.description,
                    'tags': photo.keywords,
                    # 'category': photo.categories[0],  # TODO: Category or Youtube channel?
                },
                'status': {
                    'provacyStatus': 'private',
                },
            },
            file_path=photo.image.url,  # TODO: Download the file to a local temp dir
        )
    except HttpError as e:
        logger.exception("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


def _initialize_upload(service, body, file_path):
    """
    Call the API's videos.insert method to create and upload the video.
    """
    insert_request = service.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )
    _resumable_upload(insert_request)


def _resumable_upload(insert_request):
    """
    This method implements an exponential backoff strategy to resume a failed upload.
    """
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logger.debug("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    logger.debug("Video id '%s' was successfully uploaded." % response['id'])
                else:
                    logger.error("The upload failed with an unexpected response: %s" % response)
                    return
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            logger.debug(error)
            retry += 1
            if retry > MAX_RETRIES:
                logger.error("No longer attempting to retry.")
                return

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logger.debug("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
