# -*- coding: utf-8 -*-
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from dry_rest_permissions.generics import DRYPermissionFiltersBase
from rest_framework.exceptions import ValidationError

from bima_core.utils import belongs_to_admin_group, is_staff_or_superuser


class PermissionBackend(DRYPermissionFiltersBase):
    """
    This class overwrites DRYPermissionFilterBase to change 'filter_queryset' method to use it as a base
    permission filter.
    """
    def filter_queryset(self, request, queryset, view):
        raise ValidationError("Check the inheritance of your filter backend class.")

    def filter_permission_queryset(self, request, queryset, view):
        """
        Overwritten method to support both backends
        """
        return super().filter_queryset(request, queryset, view)


class PermissionFiltersBackend(DjangoFilterBackend, PermissionBackend):
    """
    This class combines two 'DjangoFilterBackend' and 'PermissionBackend'. The defined order is very important
    to preserve the correct execution of methods.

    DjangoFilterBackend is used to permit using filters with coreapi scheme.
    PermissionBackend is the backend which provides you the filter list method to control permissions.
    """

    def filter_queryset(self, request, queryset, view):
        queryset = self.filter_permission_queryset(request, queryset, view)
        return super().filter_queryset(request, queryset, view)


class FilterAlbumPermissionBackend(PermissionFiltersBackend):
    """
    Filter albums by owner users if the user who requests is not administrator.
    """

    def filter_list_queryset(self, request, queryset, view):
        # filter by owner
        if not (belongs_to_admin_group(request.user) or is_staff_or_superuser(request.user)):
            return queryset.filter(owners=request.user)
        # admin user
        return queryset


class FilterPhotoPermissionBackend(PermissionFiltersBackend):
    """
    Filter photos by album owners of it if the user who requests is not administrator.
    """

    def filter_list_queryset(self, request, queryset, view):
        """
        Filter photos by album or photo owner if not belongs to admin group. Also return all public photos.
        Otherwise gets all photos.
        """
        # filter by owner
        if not (belongs_to_admin_group(request.user) or is_staff_or_superuser(request.user)):
            return queryset.filter(
                Q(owner=request.user) | Q(album__owners=request.user) | Q(status=queryset.model.PUBLISHED)
            ).distinct()
        # admin user
        return queryset
