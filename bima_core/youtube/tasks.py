# -*- coding: utf-8 -*-

import logging
import os
from tempfile import TemporaryDirectory

from django_rq import job
from bima_core.constants import RQ_UPLOAD_YOUTUBE_QUEUE
from bima_core.models import Photo

from . import api
from .models import YoutubeChannel


logger = logging.getLogger(__name__)


CHUNK_SIZE = 10 * 2 ** 20  # 10 MB


@job(RQ_UPLOAD_YOUTUBE_QUEUE)
def upload_video_youtube(youtube_channel_pk, photo_pk):
    """
    Upload a models.Photo to Youtube if it's a video and it's not already uploaded.
    """
    try:
        channel = YoutubeChannel.objects.get(pk=youtube_channel_pk)
    except Exception:
        logger.exception('Youtube channel does not exist.')
        return

    try:
        photo = Photo.objects.get(pk=photo_pk)
    except Exception:
        logger.exception('Photo does not exist.')
        return

    if not photo.is_video:
        logger.error('Photo is not a video', extra={'photo_pk': photo_pk})
        return

    try:
        with TemporaryDirectory() as dirname:
            logger.debug('Workdir: {}'.format(dirname))
            video_path = os.path.join(dirname, os.path.basename(photo.image.name))
            with open(video_path, 'wb') as video_file:
                for chunk in photo.image.chunks(CHUNK_SIZE):
                    video_file.write(chunk)
            response = api.upload_video(channel, video_path, photo.title, photo.description)
            logger.debug(response)
            photo.youtube_code = response['id']
            photo.save()
        logger.info('Video uploaded.')
    except Exception:
        logger.exception('Error uploading video')
