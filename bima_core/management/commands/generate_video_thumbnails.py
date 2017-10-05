# encoding: utf-8

import logging
import os
from tempfile import TemporaryDirectory

from django.core.management.base import BaseCommand
from django.db.models import Q

from ...models import Photo


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate thumbnails for video Photo models that doesn't have one."

    def handle(self, *args, **options):
        try:
            with TemporaryDirectory() as dirname:
                logger.debug('Workdir: {}'.format(dirname))
                for photo in Photo.objects.filter(Q(video_thumbnail__isnull=True) |
                                                  Q(video_thumbnail='')):
                    if photo.is_video:
                        self.generate_thumbnail(photo, dirname)
            self.stdout.write('Thumbnails generated.')
        except Exception:
            logger.exception('Error generating video thumbnails')

    @staticmethod
    def generate_thumbnail(photo, workdir):
        generated = False
        video_path = os.path.join(workdir, os.path.basename(photo.image.name))
        try:
            with open(video_path, 'wb') as video_file:
                video_file.write(photo.image.read())
            generated = photo.generate_video_thumbnail(video_path)
            if generated:
                logger.debug('Thumbnail {} generated'.format(photo.video_thumbnail.name))
            os.remove(video_path)
        except Exception:
            logger.exception('Error generating thumbnail', extra={'video': video_path})
        return generated
