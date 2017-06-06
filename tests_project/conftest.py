# -*- encoding: utf-8 -*-
from uuid import UUID
from django.conf import settings
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.forms import model_to_dict
from django.test.client import MULTIPART_CONTENT, BOUNDARY, encode_multipart
from faker import Factory
from hashlib import md5
from model_mommy import mommy
from os.path import abspath, join, dirname
from rest_framework.authtoken.models import Token
import pytest
import random

from bima_core.constants import ADMIN_GROUP_NAME, EDITOR_GROUP_NAME, READER_GROUP_NAME, PHOTOGRAPHER_GROUP_NAME
from bima_core.models import Album, Photo, DAMTaxonomy, Gallery, GalleryMembership, PhotoChunked


CHUNK_SIZE = 1000
IMAGES_BASE_DIR = 'images'
faker = Factory.create()


def _clean_data(data, safe_mode=True):
    cleaned_data = {}
    for key, value in data.items():
        if value is None or value == '' and safe_mode:
            continue
        # force to a serializable json type
        if isinstance(value, QuerySet):
            value = list(value)
        elif isinstance(value, UUID):
            value = str(value)
        cleaned_data[key] = value
    return cleaned_data


def _get_content_file(file_name):
    file_path = abspath(join(dirname(__file__), IMAGES_BASE_DIR, file_name))
    with open(file_path, 'rb') as f:
        return ContentFile(f.read(), name=file_name)


def _new_keyword(quantity=1):
    return [{'language': random.choice(settings.LANGUAGES)[0], 'tag': faker.word()} for _ in range(quantity)]


def _new_name(quantity=1):
    return [faker.name() for _ in range(quantity)]


def _new_user(username=None, sufix='', group=None):
    username = "{}{}".format(username, '_' + sufix)
    new_user = mommy.make(get_user_model(), username=username)
    new_user.groups.add(group)
    return new_user


def _new_photo(owners, image):
    """
    :param owners: Expected list or tuple of users
    :param image: Content file instance of image
    :return: Dictionary with data to create photo
    """
    # prepare data
    new_album = mommy.make(Album, owners=owners)
    owner = new_album.owners.first()
    image_chunk = mommy.make(PhotoChunked, file=image, user=owner, status=PhotoChunked.COMPLETE)
    # build photo data
    photo_data = model_to_dict(mommy.prepare(Photo))
    photo_data.update({'image': image_chunk.id, 'owner': owner.id, 'album': new_album.id})
    return _clean_data(photo_data)


def _extend_photo(photo_data):
    photo_data.update({"keywords": _new_keyword(quantity=3), "names": _new_name(quantity=3)})
    return photo_data


def _new_photo_instance(owners, image, status=Photo.PRIVATE, extended=None, quantity=1):
    """
    :param owners: Expected list or tuple of users
    :param image: Content file instance of image
    :return: Instance of photo
    """
    new_album = mommy.make(Album, owners=owners)
    kwargs = {'status': status, 'image': image, 'album': new_album, 'owner': new_album.owners.first()}
    if extended and isinstance(extended, dict):
        kwargs.update(extended)
    if quantity > 1:
        kwargs.update(_quantity=quantity)
    return mommy.make(Photo, **kwargs)


def _new_extended_photo_instance(owners, image, status=Photo.PRIVATE, quantity=1):
    extended_photo_data = _extend_photo({})
    return _new_photo_instance(owners, image, status, extended_photo_data, quantity)


def _build_headers(token):
    return {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}


def encode_multipart_data(data, content_type=MULTIPART_CONTENT):
    data = {} if data is None else data
    if content_type is MULTIPART_CONTENT:
        return encode_multipart(BOUNDARY, data)
    return data


def update_multipart_headers(headers):
    if isinstance(headers, dict):
        headers.update({'content_type': MULTIPART_CONTENT})
    return headers


def update_chunk_range_headers(headers, offset, chunk, file):
    if isinstance(headers, dict):
        headers.update({'HTTP_CONTENT_RANGE': 'bytes {}-{}/{}'.format(offset, offset + len(chunk), file.size)})
    return headers


def checksum_file(file):
    checksum = md5()
    for chunk in file.chunks(CHUNK_SIZE):
        checksum.update(chunk)
    return checksum.hexdigest()


@pytest.fixture()
def publish_status():
    yield Photo.PUBLISHED


@pytest.fixture()
def private_status():
    yield Photo.PRIVATE


@pytest.fixture()
def groups():
    group_list, group_names = [], [ADMIN_GROUP_NAME, READER_GROUP_NAME, EDITOR_GROUP_NAME, PHOTOGRAPHER_GROUP_NAME]
    for name in group_names:
        group_list.append(Group.objects.create(name=name))
    yield group_list


@pytest.fixture()
def admin_group(groups):
    yield groups[0].id


@pytest.fixture()
def editor_group(groups):
    yield groups[2].id


@pytest.fixture()
def reader_group(groups):
    yield groups[1].id


@pytest.fixture()
def photographer_group(groups):
    yield groups[-1].id


@pytest.fixture()
def random_group(groups):
    yield random.choice(groups).id


@pytest.fixture()
def admin_token(admin_group, suffix=''):
    admin_user = _new_user('admin_user', suffix, admin_group)
    return Token.objects.get_or_create(user=admin_user)[0]


@pytest.fixture()
def editor_token(editor_group, suffix=''):
    editor_user = _new_user('editor_user', suffix, editor_group)
    return Token.objects.get_or_create(user=editor_user)[0]


@pytest.fixture()
def reader_token(reader_group, suffix=''):
    reader_user = _new_user('reader_user', suffix, reader_group)
    return Token.objects.get_or_create(user=reader_user)[0]


@pytest.fixture()
def photographer_token(photographer_group, suffix=''):
    photographer_user = _new_user('photographer_user', suffix, photographer_group)
    return Token.objects.get_or_create(user=photographer_user)[0]


@pytest.fixture()
def random_reader_token(reader_group):
    yield reader_token(reader_group, 'random')


@pytest.fixture()
def random_editor_token(editor_group):
    yield editor_token(editor_group, 'random')


@pytest.fixture()
def admin_headers(admin_token):
    yield _build_headers(admin_token.key)


@pytest.fixture()
def editor_headers(editor_token):
    yield _build_headers(editor_token.key)


@pytest.fixture()
def reader_headers(reader_token):
    yield _build_headers(reader_token.key)


@pytest.fixture()
def photographer_headers(photographer_token):
    yield _build_headers(photographer_token.key)


@pytest.fixture()
def random_reader_headers(random_reader_token):
    yield _build_headers(random_reader_token.key)


@pytest.fixture()
def random_editor_headers(random_editor_token):
    yield _build_headers(random_editor_token.key)


@pytest.fixture()
def image_file():
    """
    Prepare the image content with a test file.
    This test file contains several exif fields (metadata).
    """
    return _get_content_file('logo_client_exifdata.jpg')


@pytest.fixture()
def user(random_group):
    """ Prepare data user instance. """
    user_data = model_to_dict(mommy.prepare(get_user_model(), email=faker.email(), username=faker.user_name()))
    user_data.update({'groups': [random_group, ]})
    yield _clean_data(user_data)


@pytest.fixture()
def user_instance():
    """ Create user instance. """
    yield mommy.make(get_user_model(), email=faker.email(), username=faker.user_name())


@pytest.fixture()
def user_set():
    """
    Create user instance set.
    Use iteration mode to avoid an integrity error to use the same username on each user.
    """
    yield [mommy.make(get_user_model(), email=faker.email(), username=faker.user_name()) for _ in range(3)]


@pytest.fixture()
def album():
    """ Prepare data album instance. """
    album_owner = mommy.make(get_user_model(), username='album_owner')
    album_data = model_to_dict(mommy.prepare(Album))
    album_data['owners'] = [album_owner.id, ]
    yield _clean_data(album_data)


@pytest.fixture()
def album_instance(editor_token, reader_token):
    """ Create album instance with editor and reader owners """
    album_for_editors = mommy.make(Album)
    album_for_editors.owners.add(editor_token.user)
    album_for_editors.owners.add(reader_token.user)
    yield album_for_editors


@pytest.fixture()
def taxonomy():
    """ Prepare data taxonomy instance. """
    yield _clean_data(model_to_dict(mommy.prepare(DAMTaxonomy)))


@pytest.fixture()
def taxonomy_instance():
    yield mommy.make(DAMTaxonomy)


@pytest.fixture()
def gallery():
    """ Prepare data gallery instance """
    yield _clean_data(model_to_dict(mommy.prepare(Gallery, slug='test', title='test'), exclude=('owners', 'photos', )))


@pytest.fixture()
def gallery_instance(editor_token, photographer_token):
    """
    Create gallery instance in database to permit its get/update/delete.
    A photographer user will set as a owner of this gallery.
    """
    owners = [Token.objects.get(key=editor_token).user, Token.objects.get(key=photographer_token).user, ]
    yield mommy.make(Gallery, owners=owners)


@pytest.fixture()
def link_instance(photo_instance, gallery_instance):
    yield mommy.make(GalleryMembership, photo=photo_instance, gallery=gallery_instance)


@pytest.fixture()
def photo(image_file):
    """ Prepare photo data to create instance via API. """
    owners = [mommy.make(get_user_model(), username='photo_owner'), ]
    yield _new_photo(owners, image_file)


@pytest.fixture()
def extended_photo(photo):
    """ Prepare extended photo data to create instance via API. """
    yield _extend_photo(photo)


@pytest.fixture()
def photo_of_photographer(photographer_token, image_file):
    owners = [photographer_token.user, ]
    yield _new_photo(owners, image_file)


@pytest.fixture()
def photo_instance(image_file):
    owners = [mommy.make(get_user_model(), username='private_photo_instance_owner'), ]
    yield _new_photo_instance(owners, image_file)


@pytest.fixture()
def public_photo_instance(publish_status, image_file):
    owners = [mommy.make(get_user_model(), username='public_photo_instance_owner'), ]
    yield _new_photo_instance(owners, image_file, status=publish_status)


@pytest.fixture()
def public_extended_photo_instance(publish_status, image_file):
    owners = [mommy.make(get_user_model(), username='public_extended_photo_instance_owner'), ]
    yield _new_extended_photo_instance(owners, image_file, status=publish_status)


@pytest.fixture()
def photo_instance_of_photographer(photographer_token, image_file):
    owners = [photographer_token.user, ]
    yield _new_photo_instance(owners, image_file)


@pytest.fixture()
def photo_instance_of_reader(reader_token, image_file):
    owners = [reader_token.user, ]
    yield _new_photo_instance(owners, image_file)


@pytest.fixture()
def photo_instance_of_editor(editor_token, image_file):
    owners = [editor_token.user, ]
    yield _new_photo_instance(owners, image_file)


@pytest.fixture()
def public_photo_set(publish_status, image_file):
    owners = [mommy.make(get_user_model(), username=faker.user_name()), ]
    yield _new_photo_instance(owners, image_file, status=publish_status, quantity=3)


@pytest.fixture()
def private_photo_set(image_file):
    owners = [mommy.make(get_user_model(), username=faker.user_name()), ]
    yield _new_photo_instance(owners, image_file, quantity=3)
