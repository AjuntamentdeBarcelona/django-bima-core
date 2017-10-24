# -*- coding: utf-8 -*-

import logging
import os
import random
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
import http.client
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
RETRIABLE_EXCEPTIONS = (IOError, httplib2.HttpLib2Error, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Size in bytes of chunks to upload to Youtube.
CHUNK_SIZE = 100 * 2 ** 20  # 100 MB


def get_authenticated_service(youtube_channel):
    """
    Authorize the request and store authorization credentials.

    In the first authorization it will print a Google auth URL in the terminal
    to do the authorization manually.

    In order to be 12 factors friendly, client_secret.json and oauth2.json
    files are read from and written to django-constance.

    https://12factor.net
    https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
    """
    client_secret_path = youtube_channel.client_secret_to_file()
    flow = flow_from_clientsecrets(client_secret_path,
                                   scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)
    flow.params['access_type'] = 'offline'  # auto refresh token
    flow.params['include_granted_scopes'] = 'true'

    token_path = youtube_channel.token_to_file()
    storage = Storage(token_path)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        print('Please, choose channel "{} ({})" from account "{}".'.format(
            youtube_channel.name, youtube_channel.channel_id, youtube_channel.account.username))
        # Force to print Google auth URL in the terminal.
        args = argparser.parse_args(args=['--noauth_local_webserver'])
        credentials = run_flow(flow, storage, args)
        youtube_channel.save_token_from_file(token_path)

    os.remove(client_secret_path)
    logger.info('File {} deleted.'.format(client_secret_path))

    os.remove(token_path)
    logger.info('File {} deleted.'.format(token_path))

    return build(API_SERVICE_NAME, API_VERSION, http=credentials.authorize(httplib2.Http()))


def upload_video(youtube_channel, file_path, title, description='', tags=None, privacy='private'):
    """
    Upload video file to Youtube with auto resume.

    Based on https://developers.google.com/youtube/v3/docs/videos/insert.
    """
    service = get_authenticated_service(youtube_channel)
    try:
        return _initialize_upload(
            service=service,
            body={
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                },
                'status': {
                    'privacyStatus': privacy,
                },
            },
            file_path=file_path
        )
    except HttpError as e:
        logger.exception("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
        raise


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
        media_body=MediaFileUpload(file_path, chunksize=CHUNK_SIZE, resumable=True)
    )
    return _resumable_upload(insert_request)


def _resumable_upload(insert_request):
    """
    This method implements an exponential backoff strategy to resume a failed upload.

    TODO: Better error handling.
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
    return response
