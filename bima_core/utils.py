# -*- coding: utf-8 -*-
import re
from LatLon23 import Latitude, Longitude
from dateutil import parser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, QueryDict
from exifread import Ratio
import os
import six
import unicodedata

from .constants import ADMIN_GROUP_NAME


def idpath(fs, root, id, extension=''):
    """
    Build path to upload files in S3
    """
    if root and not root.endswith(os.path.sep):
        root += os.path.sep

    paths = fs.shard(id)

    if extension and not extension.startswith(os.path.extsep):
        extension = os.path.extsep + extension

    return os.path.join(root, *paths) + extension


def get_filename(path):
    return os.path.basename(path)


def is_iterable(obj):
    return isinstance(obj, (list, tuple, set))


def build_absolute_uri(domain, path, args=None, query=None, request=None):
    """
    Return an absolute url from domain, path and extra params
    :param domain:
    :param path:
    :param args: params of the request path (optional)
    :param query: query params in request (optional)
    :param request: to check absolute uri (optional)
    :return:
    """
    # build extra args of path
    if args and is_iterable(args):
        args = "/{}/".format("/".join(args))

    # build url with extra args and check with requests if exists
    location = "{}/{}".format(domain.strip('/'), (path or '').strip('/'))
    location = "{}/{}/".format(location.strip('/'), (args or '').strip('/'))
    if request is not None and isinstance(request, HttpRequest):
        location = request.build_absolute_uri(location=location)

    # build query params
    if query and isinstance(query, dict):
        try:
            querydict = QueryDict('', mutable=True)
            querydict.update(query)
            query = "?{}".format(querydict.urlencode())
        except (ValueError, KeyError):
            query = ""
    location = "{}{}".format(location, query or '')
    return location


def parse_ratio(ratio):
    """
    Get ratio float
    """
    if isinstance(ratio, Ratio):
        try:
            return float(ratio.num) / float(ratio.den)
        except ZeroDivisionError:
            return 0.0
    return ratio


def parse_ratios(ratios):
    """
    Parse a Ratio item or a list of them
    """
    if not is_iterable(ratios):
        return parse_ratio(ratios)

    iterable_ratios = []
    for ratio in ratios:
        iterable_ratios.append(parse_ratio(ratio))
    return iterable_ratios


def latitude_decimal_degree(degree=0, minute=0, seconds=0):
    """
    Convert latitude coordinates in DMS to decimal degree
    Return None if has error.
    """
    if degree == minute == seconds == 0:
        return 0

    try:
        return Latitude(*parse_ratio([degree, minute, seconds])).decimal_degree
    except TypeError:
        return 0


def longitude_decimal_degree(degree=0, minute=0, seconds=0):
    """
    Convert longitude coordinates in DMS to decimal degree
    Return None if has error.
    """
    if degree == minute == seconds == 0:
        return 0

    try:
        return Longitude(*parse_ratio([degree, minute, seconds])).decimal_degree
    except TypeError:
        return 0


def get_exif_info(exif, key, single=True, default=None):
    """
    Get and parse values from EXIF python dict.
    Return a single and primary value (string, float) or a list of values
    if it is specified.
    """
    try:
        exif_item = exif.get(key, None)
        values = exif_item.values if exif_item else None

        if isinstance(values, six.string_types):
            return values

        if is_iterable(values):
            values = values[0] if single else values
        else:
            values = values if single else [values, ]
        return parse_ratios(values) or default
    except Exception:
        return default


def get_exif_datetime(exif, key):
    """
    Get and parse datetime from EXIF python dict or return None if has some error.
    """
    try:
        value = get_exif_info(exif, key)
        # reformat wrong format date with regular expression
        if value and re.match(r'(\d+(:)*){3}\s(\d+:*){3}', value):
            value = value.replace(':', '-', 2)
        return parser.parse(value)
    except (ValueError, OverflowError, AttributeError, TypeError):
        return None


def get_exif_longitude(exif, key):
    """
    Get and parse longitude from EXIF python dict or return None if has some error.
    """
    return longitude_decimal_degree(*get_exif_info(exif, key, False))


def get_exif_latitude(exif, key):
    """
    Get and parse latitude from EXIF python dict or return None if has some error.
    """
    return latitude_decimal_degree(*get_exif_info(exif, key, False))


def get_exif_altitude(exif, key):
    """
    Get and parse altitude from EXIF python dict or return 0 as a default value
    """
    return get_exif_info(exif, key, default=0)


def belongs_to_some_group(user, groups):
    """
    Check if the user belongs to some group.
    :param user:
    :param groups:
    :return:
    """
    if not (user and isinstance(user, get_user_model()) and groups and is_iterable(groups)):
        return False
    return user.groups.filter(name__in=groups).exists()


def belongs_to_group(user, group):
    """
    Check if the user belongs to the group.
    :param user: user
    :param group: group name
    :return: boolean
    """
    if not group:
        return False
    return belongs_to_some_group(user, [group, ])


def belongs_to_admin_group(user):
    """
    Check if the user belongs to the admin group.
    :param user: user
    :return: boolean
    """
    return belongs_to_group(user, ADMIN_GROUP_NAME)


def belongs_to_system(user):
    """
    Check id the user belongs to the system users
    :param user: user
    :return: boolean
    """
    return isinstance(user, get_user_model()) and not isinstance(user, AnonymousUser)


def is_staff_or_superuser(user):
    """
    Check if user is staff or superuser
    :param user:
    :return:
    """
    return user.is_staff or user.is_superuser


def normalize_text(text, form='NFKD'):
    """
    Return utf-8 unicode string after normalize text in NFKD (Compatibility Decomposition, followed by Canonical
    Composition) by default
    :param text:
    :param form: normalization form. Accepts NFD, NFC, NFKD, NFKC
    :return: string
    """

    return unicodedata.normalize(form, str(text or '')).encode('ascii', 'ignore').decode('utf-8')


# Decorator to analyze performance

def timer_performance(function):
    """
    Decorator to measure elapse time of function which decorate
    """
    def _wrapped_function(*args, **kwargs):
        import time
        start = time.time()
        response = function(*args, **kwargs)
        print("***[{}]: Elapsed {}s".format(function.__name__, time.time() - start))
        return response
    return _wrapped_function
