# -*- coding: utf-8 -*-

import logging
import os
from tempfile import TemporaryDirectory

from django_rq import job
from bima_core.constants import RQ_UPLOAD_YOUTUBE_QUEUE
from bima_core.models import Photo

from . import api


logger = logging.getLogger(__name__)


@job(RQ_UPLOAD_YOUTUBE_QUEUE)
def upload_video_youtube(photo_pk):
    """
    Upload a models.Photo to Youtube if it's a video and it's not already uploaded.
    """
    try:
        photo = Photo.objects.get(pk=photo_pk)
    except Exception:
        logger.exception('Photo does not exist.')
        return

    if photo.youtube_code:
        logger.error('Photo already in Youtube', extra={
            'photo_pk': photo_pk,
            'youtube_code': photo.youtube_code,
        })
        return

    if not photo.is_video:
        logger.error('Photo is not a video', extra={'photo_pk': photo_pk})
        return

    try:
        with TemporaryDirectory() as dirname:
            logger.debug('Workdir: {}'.format(dirname))
            video_path = os.path.join(dirname, os.path.basename(photo.image.name))
            with open(video_path, 'wb') as video_file:
                video_file.write(photo.image.read())  # TODO: read and write in chunks.
            response = api.upload_video(video_path, photo.title, photo.description)
            logger.debug(response)
            photo.youtube_code = response['id']
            photo.save()
        logger.info('Video uploaded.')
    except Exception:
        logger.exception('Error uploading video')
