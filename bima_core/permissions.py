# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.cache import cache
from dry_rest_permissions.generics import allow_staff_or_superuser

from .constants import ADMIN_GROUP_NAME, EDITOR_GROUP_NAME, PHOTOGRAPHER_GROUP_NAME, \
    CACHE_PERMISSIONS_OWNER_ALBUM_PREFIX_KEY, CACHE_PERMISSIONS_TIMEOUT

from .utils import belongs_to_admin_group, belongs_to_some_group, belongs_to_group, belongs_to_system, \
    is_staff_or_superuser


class AdminPermissionMixin(object):
    """
    Mixin to allow all users
    """
    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return belongs_to_admin_group(request.user)

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return belongs_to_admin_group(request.user)

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return belongs_to_admin_group(request.user)

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return belongs_to_admin_group(request.user)


class ReadPermissionMixin(AdminPermissionMixin):
    """
    Mixin to allow all users read, but write is only for admins
    """
    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return belongs_to_system(request.user)

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return belongs_to_system(request.user)


class GroupPermissionMixin(AdminPermissionMixin):
    """
    Permission mixin for group model access.
    Only administrators can list, retrieve, create and update it.
    """


class UserPermissionMixin(AdminPermissionMixin):
    """
    Permission mixin for user model access.
    Only administrators can list, retrieve, create and update it.
    Note that list of users which any user can show will be filtered in filter backend view.
    """

    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return belongs_to_system(request.user)

    @allow_staff_or_superuser
    def has_object_list_permission(self, request):
        return belongs_to_admin_group(request.user)

    @allow_staff_or_superuser
    def has_object_retrieve_permission(self, request):
        return belongs_to_admin_group(request.user) or self == request.user


class AlbumPermissionMixin(ReadPermissionMixin):
    """
    Permission mixin for album model access.
    Only can access to read albums those users who are assigned as owners.
    Note that list of albums which any user can show will be filtered in filter backend view.
    """

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return belongs_to_admin_group(request.user) or request.user in self.owners.all()


class PhotoPermissionMixin(object):
    """
    Permission mixin for photo model access
    """

    def _get_owners_ids(self, has_cache=True):
        """
        Get album owners ids
        :param has_cache:
        :return:
        """
        # if cache enabled, get cache
        try:
            if has_cache:
                cache_key = "{}_{}".format(CACHE_PERMISSIONS_OWNER_ALBUM_PREFIX_KEY, self.album.id)
                cache_value = cache.get(cache_key)
                if cache_value:
                    return cache_value
        except Exception:
            # if exception occurred, disable cache
            has_cache = False

        # get value
        owners = list(self.album.owners.values_list('id', flat=True))

        # if cache enabled, set cache
        if has_cache:
            cache.set(cache_key, owners, getattr(settings, 'CACHE_PERMISSIONS_TIMEOUT', CACHE_PERMISSIONS_TIMEOUT))

        return owners

    def _read_or_create_permission(self, user):
        owners = [self.owner.id, ] + self._get_owners_ids()
        return belongs_to_admin_group(user) or getattr(user, 'id', -1) in owners

    def _editor_and_album_owner_permission(self, user):
        owners = [self.owner.id, ] + self._get_owners_ids()
        return belongs_to_group(user, EDITOR_GROUP_NAME) and getattr(user, 'id', -1) in owners

    def _photographer_and_owner(self, user):
        return belongs_to_group(user, PHOTOGRAPHER_GROUP_NAME) and user == self.owner

    def _write_permission(self, user):
        return (
            belongs_to_admin_group(user) or self._editor_and_album_owner_permission(user) or
            self._photographer_and_owner(user)
        )

    def has_download_permission(self, user):
        # allow staff or superusers
        if is_staff_or_superuser(user):
            return True
        return (self.status == self.PUBLISHED or self._editor_and_album_owner_permission(user) or
                self._photographer_and_owner(user))

    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return belongs_to_system(request.user)

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return belongs_to_some_group(request.user, [ADMIN_GROUP_NAME, EDITOR_GROUP_NAME, PHOTOGRAPHER_GROUP_NAME, ])

    @allow_staff_or_superuser
    def has_object_retrieve_permission(self, request):
        return self.status == self.PUBLISHED or (
            self._read_or_create_permission(request.user) and self.status == self.PRIVATE
        )

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return self._write_permission(request.user)

    @allow_staff_or_superuser
    def has_object_update_permission(self, request):
        return self._write_permission(request.user)

    @allow_staff_or_superuser
    def has_object_destroy_permission(self, request):
        return belongs_to_admin_group(request.user) or self._editor_and_album_owner_permission(request.user)


class PhotoChunkPermissionMixin(PhotoPermissionMixin):
    """
    Photo chunk overridden permission methods
    """

    @allow_staff_or_superuser
    def has_object_retrieve_permission(self, request):
        return belongs_to_system(request.user)

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return self.has_write_permission(request)

    @allow_staff_or_superuser
    def has_object_update_permission(self, request):
        return self.has_write_permission(request)

    @allow_staff_or_superuser
    def has_object_destroy_permission(self, request):
        return False


class GalleryPermissionMixin(ReadPermissionMixin):
    """
    Permission mixin for gallery model access.
    Anyone can list and retrieve galleries. They are public, but only admins can create them.
    """


class GalleryMembershipPermissionMixin(AdminPermissionMixin):
    """
    Permission mixin for gallery links model access.
    Only admins and editors can assign photos to galleries, but editors only can do this if they are owners
    of the gallery.
    """

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return belongs_to_some_group(request.user, [ADMIN_GROUP_NAME, EDITOR_GROUP_NAME, ])

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return belongs_to_admin_group(request.user) or request.user in self.gallery.owners.all()


class TaxonomyPermissionMixin(ReadPermissionMixin):
    """
    Permission mixin for taxonomy model access.
    All system users can list and retrieve, but only admin can write taxonomy instances.
    """


class AccessLogPermissionMixin(object):
    """
    Permission mixin for log view and download images.
    """
    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return belongs_to_admin_group(request.user)

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return belongs_to_system(request.user)

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return belongs_to_system(request.user)


class RightPermissionMixin(ReadPermissionMixin):
    """
    Permission mixin for copyright model access.
    All system users can list and retrieve, but only admin can write copyright instances.
    """
