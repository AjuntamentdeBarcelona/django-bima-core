# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.files.storage import FileSystemStorage as _FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.core.files.storage import get_storage_class


def file_system_storage():
    return get_storage_class('bima_core.storage.FileSystemStorage')


@deconstructible
class FileSystemStorage(_FileSystemStorage):

    def __init__(self, *args, **kwargs):
        super().__init__(base_url=settings.FILE_SYSTEM_MEDIA_URL, *args, **kwargs)
