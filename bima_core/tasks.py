# -*- coding: utf-8 -*-
import logging
import time

from django.apps import apps
from django.core.files.base import File, ContentFile
from django.db.models.utils import make_model_tuple
from django_rq import job
from haystack.exceptions import NotHandled

from . import youtube
from .constants import RQ_UPLOAD_QUEUE, RQ_HAYSTACK_PHOTO_INDEX_QUEUE, RQ_UPLOAD_YOUTUBE_QUEUE
from .models import Photo, PhotoChunked
from .utils import get_filename
from .filetypes import FileType


logger = logging.getLogger(__name__)


@job(RQ_UPLOAD_QUEUE)
def up_image_to_s3(photo_id, image_id):
    """
    Upload the file to S3. If it's a video, generate its thumbnail and upload it to S3.
    """
    try:
        photo = Photo.objects.get(id=photo_id)
        image = PhotoChunked.objects.get(id=image_id)

        filetype = FileType.get_path_file_type(image.filename)

        if filetype == FileType.photo:
            photo.image = ContentFile(image.file.read(), name=image.filename)
            photo.set_metadata(only_readable=False, commit=False)
        else:
            photo.image = File(image.file, name=image.filename)
            photo.size = photo.image.size

        if not photo.original_file_name:
            photo.original_file_name = get_filename(image.file.name)

        # upload new image
        photo.save()

        # update upload status after upload has been really done
        photo.upload_status = Photo.UPLOADED
        photo.save()

        if filetype == FileType.video:
            photo.generate_video_thumbnail(image.file.path)

        return photo
    except Photo.DoesNotExist:
        logger.error("Photo {} does not exits. Image will not be saved.".format(photo_id), exc_info=True)
    except PhotoChunked.DoesNotExist:
        logger.error("Photo chunk {} does not exits. Image will not be saved.".format(image_id), exc_info=True)
        photo.upload_status = Photo.UPLOADED if photo.image else Photo.UPLOAD_ERROR
        photo.save()
    except Exception:
        logger.error("An error occurred updating photo {} with image chunk {}".format(photo_id, image_id),
                     exc_info=True, extra={'photo_id': photo_id, 'image_id': image_id})
        photo = Photo.objects.get(id=photo_id)
        photo.upload_status = Photo.UPLOADED if photo.image else Photo.UPLOAD_ERROR
        photo.save()


@job(RQ_HAYSTACK_PHOTO_INDEX_QUEUE)
def rebuild_photo_index(sender_class, instance_id, action_name):
    """
    Given an individual model instance, determine which backends the
    update/update should be sent to & update the object on those backends.
    """
    if action_name not in ('update_object', 'remove_object', ):
        logger.error("Action '{}' is not valid operation for haystack index.".format(action_name), exc_info=True)
        return

    try:
        haystack_signal_processor = apps.get_app_config('haystack').signal_processor
        model = apps.get_model(*make_model_tuple(sender_class))
        instance = _get_instance(model, instance_id)
    except Exception:
        logger.error("An error occurred updating photo index id '{}' with the current haystack application "
                     "configuration".format(instance_id), extra={'sender': sender_class, 'instance': instance_id},
                     exc_info=True)
        return

    using_backends = haystack_signal_processor.connection_router.for_write(instance=instance)
    for using in using_backends:
        try:
            index = haystack_signal_processor.connections[using].get_unified_index().get_index(sender_class)
            getattr(index, action_name)(instance, using=using)
        except NotHandled:
            logger.info("There is not index defined for the sender '{}' class".format(sender_class._meta.label))


def _get_instance(model, instance_id):
    """
    Post save signals are fired after the INSERT SQL have been done but the transaction may not
    have been commited yet. In that case, the instance is not in the database and we have to do a
    busy wait.
    """
    max_attempts = 3
    wait_between_attempts = 0.5  # in seconds

    for attempt in range(max_attempts):
        try:
            return model.objects.get(id=instance_id)
        except model.DoesNotExist:
            logger.debug('Waitting for transaction...')
            time.sleep(wait_between_attempts)

    raise model.DoesNotExist('{} with id {} does not exist'.format(model.__name__, instance_id))


@job(RQ_UPLOAD_YOUTUBE_QUEUE)
def print_youtube_channels(username):
    """
    Quick example of Youtube task.
    """
    channels = youtube.list_channels(username)

    if not channels:
        print('No channels for user {}.'.format(username))
        return

    for channel in channels:
        print('This channel\'s ID is {}. Its title is {}, and it has {} views.'.format(
            channel['id'],
            channel['snippet']['title'],
            channel['statistics']['viewCount'],
        ))
