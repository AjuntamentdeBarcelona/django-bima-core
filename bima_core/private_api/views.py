# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _i
from drf_chunked_upload.views import ChunkedUploadView
from drf_haystack.generics import HaystackGenericAPIView
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import viewsets
from rest_framework.authtoken import views as auth_views
from rest_framework.filters import DjangoFilterBackend
from rest_framework.generics import ListAPIView as _ListAPIView, RetrieveAPIView as _RetrieveAPIView, \
    CreateAPIView as _CreateAPIView, UpdateAPIView as _UpdateAPIView
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.viewsets import GenericViewSet
from rest_framework_swagger.views import get_swagger_view

from bima_core.models import Album, DAMTaxonomy, Gallery, GalleryMembership, Group, Photo, PhotoChunked, AccessLog, \
    Copyright, UsageRight, PhotoAuthor, TaggedKeyword, TaggedName, PhotoType

from .backends import HaystackDjangoFilterBackend
from .filters import PhotoFilter, UserFilter, AlbumFilter, TaxonomyFilter, GalleryFilter, GroupFilter, \
    AccessLogFilter, CopyrightFilter, UsageRightFilter, PhotoAuthorFilter, PhotoSearchFilter, KeywordFilter, \
    NameFilter, PhotoTypeFilter
from .paginators import LargeNumberPagination, TaxonomyNumberPagination
from .permissions import FilterAlbumPermissionBackend, FilterPhotoPermissionBackend
from .serializers import GroupSerializer, UserSerializer, AlbumSerializer, PhotoSerializer, TaxonomySerializer, \
    TaxonomyListSerializer, GallerySerializer, GalleryMembershipSerializer, AccessLogSerializer, \
    PhotoFlickrSerializer, PhotoChunkedSerializer, WhoAmISerializer, CopyrightSerializer, UsageRightSerializer, \
    PhotoAuthorSerializer, PhotoSearchSerializer, KeywordTagSerializer, NameTagSerializer, PhotoUpdateSerializer, \
    BasePhotoSerializer, AuthTokenSerializer, PhotoTypeSerializer

schema_view = get_swagger_view(title=_i('BIMA Core: Private API'))


# Base views

class PermissionMixin(object):
    permission_classes = (DRYPermissions, )


class FilterMixin(object):
    filter_backends = (DjangoFilterBackend, )
    filter_class = NotImplementedError


class ViewSetSerializerMixin(object):
    def get_serializer_class(self):
        """ Return the class to use for serializer to the request method."""
        try:
            return self.action_serializer_class[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()


class FilterModelViewSet(PermissionMixin, FilterMixin, viewsets.ModelViewSet):
    """
    Base model view set class with default filter backend 'DjangoFilterBackend'
    """


class FilterReadOnlyModelViewSet(PermissionMixin, FilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    Base read only model view set class with default filter backend 'DjangoFilterBackend'
    """


class CreateViewSet(PermissionMixin, CreateModelMixin, GenericViewSet):
    """
    Base view set which permit only create instances
    """


class CreateListViewSet(PermissionMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    """
    Base view set which permit list and create instances
    """


class CreateDestroyViewSet(DestroyModelMixin, CreateViewSet):
    """
    Base view set which permit only create and destroy instances
    """


class CreateAPIView(PermissionMixin, _CreateAPIView):
    """
    Base view which permit only Create instances with permission restrictions
    """


class UpdateAPIView(PermissionMixin, _UpdateAPIView):
    """
    Base view which permit only Update instances with permission restrictions
    """


class RetrieveAPIView(PermissionMixin, _RetrieveAPIView):
    """
    Base view which permit only Retrieve instances with permission restrictions
    """


class ListAPIView(PermissionMixin, _ListAPIView):
    """
    Base view which permit only List instances with permission restrictions
    """


# Api views


class ObtainAuthToken(auth_views.ObtainAuthToken):
    """
    API to get token authentication.

    create:
    Return an authenticated token.
    """
    serializer_class = AuthTokenSerializer

    def get_serializer(self, *args, **kwargs):
        return super().serializer_class(data=self.request.data)


class WhoAmI(RetrieveAPIView):
    """
    API to get information about me.

    retrieve:
    Return a user instance.
    """
    serializer_class = WhoAmISerializer

    def get_object(self):
        return self.request.user


class ImportPhotoFlickr(CreateAPIView):
    """
    API view to import photos from flickr.
    It permit only crete new photo instances with the serializer fields, so the unique permitted action is 'post'.

    create:
    Create photo from flickr import.
    """
    serializer_class = PhotoFlickrSerializer
    queryset = Photo.objects.all()
    http_method_names = ('post', )


class UpdatePhoto(UpdateAPIView):
    """
    API view to update photos, used for massive photo updates.
    It permit only update photo instances and always add items for each m2m photo field.

    partial_update:
    Partial update photo instance with item addition in m2m relations.

    update:
    Complete update photo instance with item addition in m2m relations.
    """
    serializer_class = PhotoUpdateSerializer
    queryset = Photo.objects.all()
    http_method_names = ('patch', 'put', )


class UploadChunkedPhoto(PermissionMixin, ChunkedUploadView):
    """
    API to upload chunked file.

    create:
    End upload file with md5 checksum of file.

    update:
    Upload chunks file.
    """
    model = PhotoChunked
    serializer_class = PhotoChunkedSerializer
    http_method_names = ('post', 'put', 'get', )
    parser_classes = (MultiPartParser, )


class PhotoSearchView(PermissionMixin, FilterMixin, ListModelMixin, HaystackGenericAPIView):
    """
    API view to list filtered photos by custom search meta-language.

    list:
    List a search filter result of photos
    """
    index_models = (Photo, )
    serializer_class = PhotoSearchSerializer
    filter_class = PhotoSearchFilter
    filter_backends = (HaystackDjangoFilterBackend, )
    http_method_names = ('get', )

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


# Api view sets


class GroupViewSet(FilterReadOnlyModelViewSet):
    """
    API to list, retrieve groups

    list:
    List all group instances.

    retrieve:
    Return a group instance.
    """
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    filter_class = GroupFilter


class UserViewSet(FilterModelViewSet):
    """
    API to list, create, retrieve, update, delete users

    list:
    List all user instances.

    retrieve:
    Return an user instance.

    create:
    Create an user instance.

    update:
    Update an user instance.
    """
    serializer_class = UserSerializer
    queryset = get_user_model().objects.all()
    filter_class = UserFilter


class AlbumViewSet(FilterModelViewSet):
    """
    API to list, create, retrieve, update, delete albums

    list:
    List all album instances.

    retrieve:
    Return an album instance.

    create:
    Create an album instance.

    update:
    Update an album instance.
    """
    serializer_class = AlbumSerializer
    queryset = Album.objects.active()
    filter_class = AlbumFilter
    filter_backends = (FilterAlbumPermissionBackend, )


class PhotoViewSet(ViewSetSerializerMixin, FilterModelViewSet):
    """
    API to list, create, retrieve, update, delete photos

    list:
    List all photo instances.

    retrieve:
    Return a photo instance.

    create:
    Create a photo instance.

    partial_update:
    Partial update a photo instance.

    update:
    Complete update a photo instance.
    """
    serializer_class = PhotoSerializer
    queryset = Photo.objects.active()
    filter_class = PhotoFilter
    filter_backends = (FilterPhotoPermissionBackend, )
    action_serializer_class = {
        'list': BasePhotoSerializer
    }

    def get_queryset(self):
        """Optimize total number of queries and so reduce response time"""
        return super().get_queryset().select_related(
            'exif', 'author', 'copyright', 'internal_usage_restriction', 'external_usage_restriction', 'owner', 'album'
        ).prefetch_related(
            'categories', 'tagged_items', 'names', 'owner__groups'
        )


class TaxonomyViewSet(FilterModelViewSet):
    """
    API to list, create, retrieve, update, delete categories

    list:
    List all category instances.

    retrieve:
    Return a category instance.

    create:
    Create a category instance.

    update:
    Update a category instance.
    """
    serializer_class = TaxonomySerializer
    queryset = DAMTaxonomy.objects.active()
    filter_class = TaxonomyFilter
    pagination_class = TaxonomyNumberPagination


class TaxonomyListViewSet(FilterMixin, ListAPIView):
    """
    API to list taxonomies
    """
    serializer_class = TaxonomyListSerializer
    queryset = DAMTaxonomy.objects.active()
    filter_class = TaxonomyFilter


class GalleryViewSet(FilterModelViewSet):
    """
    API to list, create, retrieve, update, delete galleries

    list:
    List all gallery instances.

    retrieve:
    Return a gallery instance.

    create:
    Create a gallery instance.

    update:
    Update a gallery instance.
    """
    serializer_class = GallerySerializer
    queryset = Gallery.objects.all()
    filter_class = GalleryFilter


class LinkerPhotoViewSet(CreateDestroyViewSet):
    """
    API to create and delete photo links to galleries

    create:
    Create a photo link to a gallery.

    destroy:
    Delete a photo link to a gallery.
    """
    serializer_class = GalleryMembershipSerializer
    queryset = GalleryMembership.objects.all()


class LoggerBaseView(FilterMixin):
    """
    Base view for access logs
    """
    serializer_class = AccessLogSerializer
    queryset = AccessLog.objects.all()
    filter_class = AccessLogFilter


class LoggerViewSet(LoggerBaseView, CreateListViewSet):
    """
    API to logger actions to photos

    create:
    Create a an access log to a photo.
    """


class LoggerListView(LoggerBaseView, ListAPIView):
    """
    API call to get no paginated list of logger actions over photos.
    The limit is defined in the paginator

    list:
    Create a an access log to a photo.
    """
    pagination_class = LargeNumberPagination


class CopyrightViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve copyrights

    list:
    List all copyright instances.

    retrieve:
    Return a copyright instance.
    """
    serializer_class = CopyrightSerializer
    queryset = Copyright.objects.all()
    filter_class = CopyrightFilter


class RestrictionViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve usage rights

    list:
    List all usage right instances.

    retrieve:
    Return a usage right instance.
    """
    serializer_class = UsageRightSerializer
    queryset = UsageRight.objects.all()
    filter_class = UsageRightFilter


class AuthorViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve authors (to assign photos)

    list:
    List all author instances.

    retrieve:
    Return an author instance.
    """
    serializer_class = PhotoAuthorSerializer
    queryset = PhotoAuthor.objects.all()
    filter_class = PhotoAuthorFilter


class NameViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve tag names

    list:
    List all tagged names instances.

    retrieve:
    Return a tagged name instance.
    """
    serializer_class = NameTagSerializer
    queryset = TaggedName.objects.all()
    filter_class = NameFilter


class KeywordViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve tag keywords

    list:
    List all tagged keywords instances.

    retrieve:
    Return a tagged keyword instance.
    """
    serializer_class = KeywordTagSerializer
    queryset = TaggedKeyword.objects.all()
    filter_class = KeywordFilter


class PhotoTypeViewSet(FilterReadOnlyModelViewSet):
    """
    API to list and retrieve photo types

    list:
    List all photo types

    retrieve:
    Return a photo type instance

    """
    serializer_class = PhotoTypeSerializer
    queryset = PhotoType.objects.all()
    filter_class = PhotoTypeFilter
