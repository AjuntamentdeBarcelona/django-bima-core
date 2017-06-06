# -*- encoding utf-8 -*-
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.utils.timezone import now
from flickrapi import FlickrAPI
from urllib.request import urlopen
import json
import logging
import re
import uuid

from .models import Photo, PhotoExif
from .utils import latitude_decimal_degree, longitude_decimal_degree


logger = logging.getLogger(__name__)


class Flickr(object):
    """
    Business object to import photos from the external Flickr API service.
    It allows to store in S3 the image content file and all information associated to it, including exif metadata.
    To run this importer you need to instance the class providing the right credentials and the format you expected
    response (json by default). The, call to 'get_photo' and 'create_photo' with the previous call response as
    the parameter of it.

    Egg.
        flk = Flickr('key', 'password')
        photo = flk.get_photo('external_id')
        flk.create_photo(User, Album, photo, author, photo_copyright)
    """

    def __init__(self, api_key, secret, response_format='json', store_token=False):
        self.flickr_api_client = FlickrAPI(api_key=api_key, secret=secret, format=response_format,
                                           store_token=store_token)

    def get_photo(self, pk, safe=True):
        return self._get_photo_info(pk, safe=safe)

    def create_photo(self, user, album, photo, author, photo_copyright, language=None, safe=True):
        """
        Create an instance of Photo from an existing user, album and validated flickr photo information.
        If 'safe' is specified as True it will raise an exception,
        otherwise it catches the errors and handles the errors.

        The photo is created with information like name, description, available exif and tags with LANGUAGE_CODE as
        default language of each one.

        :param user:
        :param album:
        :param photo:
        :param author:
        :param photo_copyright:
        :param language:
        :param safe:
        :return:
        """
        pk = photo.get('id')

        # get binary data of image
        image, original_photo = None, self.get_original_photo(pk, safe=safe)
        if original_photo and 'source' in original_photo:
            image = ContentFile(urlopen(original_photo['source']).read(), name=self._get_file_name(photo))

        # get meta info
        photo_tags = self._get_photo_tags(photo)
        photo_exif = self._get_photo_exif(photo, **original_photo)
        photo_location = self._get_photo_location(photo)

        # create photo and nested related models
        exif, created = PhotoExif.objects.update_or_create(photo__flickr_id=pk, defaults=photo_exif)
        defaults = {
            'image': image, 'album': album, 'owner': user, 'exif': exif, 'title': self._get_title(photo),
            'status': Photo.PRIVATE, 'flickr_username': self._get_username(photo),
            'description': self._get_title(photo),
            'author': author, 'copyright': photo_copyright,
            'categorize_date': now().date()
        }
        defaults.update(**photo_exif)
        defaults.update(**photo_location)
        photo, created = Photo.objects.update_or_create(flickr_id=pk, defaults=defaults)
        photo.set_metadata(only_readable=False)

        # add keywords for the photo
        if photo and created:
            for tag in photo_tags:
                photo.keywords.add(tag, language=language or settings.LANGUAGE_CODE)

        return photo

    def get_original_photo(self, pk, safe=True):
        """
        Passed a photo pk gets the largest available image data
        :param pk:
        :return:
        """
        raw_json_response = self.flickr_api_client.photos.getSizes(photo_id=pk)
        response = json.loads(raw_json_response.decode('utf-8'))
        if 'stat' in response and response.get('stat') == 'ok':
            # Get biggest photo, the photos are ordered from smallest to largest
            try:
                return response['sizes']['size'][-1]
            except KeyError:
                logger.debug('There is no photo size available for "{}" identifier'.format(pk))
        if safe:
            raise ObjectDoesNotExist(response.get('message'))
        return None

    # ################
    # Internal methods
    # ################

    def _get_photo_info(self, pk, safe=True):
        """
        Returns information from photograph
        :param pk:
        :return:
        """
        raw_json_response = self.flickr_api_client.photos.getInfo(photo_id=pk)
        response = json.loads(raw_json_response.decode('utf-8'))
        if 'stat' in response and response.get('stat') == 'ok':
            try:
                return response['photo']
            except KeyError:
                logger.debug('Does not match any photo with "{}" identifier'.format(pk))
        if safe:
            raise ObjectDoesNotExist(response.get('message'))
        return None

    def _get_photo_exif(self, photo, **kwargs):
        """
        Returns specific exif data for specific photograph
        :param photo:
        :return:
        """
        raw_json_response = self.flickr_api_client.photos.getExif(photo_id=photo.get('id'))
        response = json.loads(raw_json_response.decode('utf-8'))
        photo_exif = {}
        if 'stat' in response and response.get('stat') == 'ok':
            exif = response['photo'].get('exif', [])
            try:
                height = int(kwargs.get('height', 0) or self._get_raw_content(exif, 'XResolution', 0))
                width = int(kwargs.get('width', 0) or self._get_raw_content(exif, 'YResolution', 0))
            except ValueError:
                # Get from flickr api a invalid value which cause an error to parse int.
                # In that cases, size is initialized to 0 by default.
                height = width = 0
            photo_exif = {
                'width': width, 'height': height,
                'exif_date': self._get_exif_date(exif),
                'camera_model': self._get_raw_content(exif, 'Model', ''),
                'longitude': photo.get('location', {}).get('longitude', 0),
                'latitude': photo.get('location', {}).get('latitude', 0),
                'orientation': 1 if height > width else 5,
            }

        # get gps information if there is in the exif data dict
        gps = response['photo'].get('gps', [])
        if gps:
            photo_exif.update({
                'longitude': self._get_longitude_value(gps),
                'latitude': self._get_latitude_value(gps),
                'altitude': self._get_altitude_value(gps)
            })

        return photo_exif

    def _get_photo_location(self, photo):
        """
        Returns location data from photo
        :param photo:
        :return:
        """
        return {
            'province': self._get_content(photo.get('location', {}), 'region', ''),
            'municipality': self._get_content(photo.get('location', {}), 'locality', ''),
            'district': self._get_content(photo.get('location', {}), 'county', ''),
            'neighborhood': self._get_content(photo.get('location', {}), 'neighbourhood', ''),
        }

    def _get_title(self, photo):
        return self._get_content(photo, 'title', uuid.uuid4().hex)

    def _get_username(self, photo):
        return photo['owner']['path_alias'] or photo['owner']['nsid']

    def _get_file_name(self, photo):
        return "{}.{}".format(slugify(self._get_title(photo)), photo.get('originalformat', 'jpg'))

    def _get_content(self, data, key, default=None):
        return data.get(key, {}).get('_content', default)

    def _get_raw_content(self, data, key, default=None):
        """
        Returns the value of the passed key form list of dictionaries.
        :param data_list:
        :param key:
        :return:
        """
        try:
            value = next((item["raw"]["_content"] for item in data if item['tag'] == key), default)
        except Exception:
            return default
        return value

    def _get_date_value(self, data, key):
        raw_date = self._get_raw_content(data, key)
        if raw_date:
            try:
                return datetime.strptime(raw_date, '%Y:%m:%d %H:%M:%S')
            except ValueError:
                logger.error('Flickr date in invalid format', exc_ifo=True)
        return None

    def _get_exif_date(self, data):
        exif_date = self._get_date_value(data, 'DateTimeOriginal')
        return exif_date or now()

    def _get_pixel_value(self, data, key):
        values = self._get_raw_content(data, key, 0)
        return latitude_decimal_degree(*re.findall(r'\d*\.\d+|\d+', values))

    def _get_latitude_value(self, data):
        # parse value: "3 deg 8' 48.93\"
        values = self._get_raw_content(data, 'GPSLatitude', '')
        return latitude_decimal_degree(*re.findall(r'\d*\.\d+|\d+', values))

    def _get_longitude_value(self, data):
        # parse value: "3 deg 8' 48.93\"
        values = self._get_raw_content(data, 'GPSLongitude', '')
        return longitude_decimal_degree(*re.findall(r'\d*\.\d+|\d+', values))

    def _get_altitude_value(self, data):
        # parse value: "5 m"
        values = self._get_raw_content(data, 'GPSAltitude', '')
        return longitude_decimal_degree(*re.findall(r'\d*\.\d+|\d+', values))

    def _get_photo_tags(self, photo):
        return [tag.get('raw') for tag in photo['tags'].get('tag', [])]
