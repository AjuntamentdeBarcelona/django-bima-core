# -*- coding: utf-8 -*-

# Constance config
DEFAULT_CONSTANCE = {
    # thumbor params
    'IMAGE_LARGE_WITH': (1024, 'Default with (in pixels) of large image.'),
    'IMAGE_LARGE_HEIGHT': (768, 'Default height (in pixels) of large image.'),
    'IMAGE_MEDIUM_WITH': (800, 'Default with (in pixels) of medium image.'),
    'IMAGE_MEDIUM_HEIGHT': (480, 'Default height (in pixels) of medium image.'),
    'IMAGE_SMALL_WITH': (480, 'Default with (in pixels) of small image.'),
    'IMAGE_SMALL_HEIGHT': (320, 'Default height (in pixels) of small image.'),
    'THUMBNAIL_WITH': (320, 'Default with (in pixels) of thumbnails.'),
    'THUMBNAIL_HEIGHT': (240, 'Default height (in pixels) of thumbnails.'),
    'THUMBNAIL_FILL_COLOUR': ('#EDEDED', 'Hexadecimal representation of color to fill thumbnails'),

    # pagination and mailing params
    'BIMA_CORE_NAME': ('Digital Assets Management', 'Name of bima coreapplication'),
    'BIMA_CORE_SITE_URL': ('http://localhost:8001', 'Endpoint of bima core'),
    'BIMA_CORE_RESET_PASSWORD_PATH': ('/reset-password/', 'Endpoint of bima core to change password'),
    'BIMA_CORE_CHANGE_PASSWORD_PATH': ('/change-password/', 'Endpoint of bima core to change password'),
    'PAGE_SIZE': (20, 'Number of items of any list. If you clean it, it will be 20 by default.'),
    'LARGE_PAGE_SIZE': (1000, 'Number of items for large custom lists. Used to export logs, for example'),

    'FLICKR_PHOTO_URL': ('https://www.flickr.com/photos/', 'Flickr photos endpoint.'),
}

ADMIN_GROUP_NAME = 'admin'
EDITOR_GROUP_NAME = 'editor'
READER_GROUP_NAME = 'reader'
PHOTOGRAPHER_GROUP_NAME = 'photographer'
DEFAULT_GROUPS = (ADMIN_GROUP_NAME, EDITOR_GROUP_NAME, READER_GROUP_NAME, PHOTOGRAPHER_GROUP_NAME, )

RQ_UPLOAD_QUEUE = 'upload'
RQ_HAYSTACK_PHOTO_INDEX_QUEUE = 'haystack-photo-index'
RQ_UPLOAD_YOUTUBE_QUEUE = 'youtube'

COMPLETED_UPLOAD = 2
CHAR_REGEX = r'[\w\d]'
UUID_REGEX = r'{char}{{8}}-{char}{{4}}-{char}{{4}}-{char}{{4}}-{char}{{12}}'.format(**{'char': CHAR_REGEX})

HAYSTACK_DEFAULT_OPERATORS = ('AND', 'OR', )
