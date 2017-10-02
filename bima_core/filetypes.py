# -*- coding: utf-8 -*-

import os
from urllib.parse import urlparse
from enum import Enum, unique


# from bima-back
IMAGE_EXTENSIONS = ('.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.psd')


# from https://support.google.com/youtube/troubleshooter/2888402?hl=en
VIDEO_EXTENSIONS = ('.mov', '.mpeg4', '.mp4', '.avi', '.wmv', '.mpegps', '.flv', '.3gpp', '.webm')


# from https://help.soundcloud.com/hc/en-us/articles/115003452847-Uploading-requirements
AUDIO_EXTENSIONS = ('.aiff', '.wav', '.flac', '.alac', '.ogg', '.mp2', '.mp3', '.aac', '.amr', '.wma')


@unique
class FileType(Enum):
    unknown = 0
    photo = 1
    video = 2
    audio = 3

    @classmethod
    def get_url_file_type(cls, url):
        path = urlparse(url).path
        return cls.get_path_file_type(path)

    @classmethod
    def get_path_file_type(cls, path):
        extension = os.path.splitext(path)[1].lower()
        if extension in IMAGE_EXTENSIONS:
            return cls.photo
        if extension in VIDEO_EXTENSIONS:
            return cls.video
        if extension in AUDIO_EXTENSIONS:
            return cls.audio
        return cls.unknown
