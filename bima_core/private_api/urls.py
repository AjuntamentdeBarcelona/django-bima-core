# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import path, re_path
from rest_framework.routers import SimpleRouter
from bima_core.constants import UUID_REGEX
from .routers import CreateDeleteRouter
from .views import ObtainAuthToken, GroupViewSet, UserViewSet, AlbumViewSet, PhotoViewSet, WhoAmI, \
    TaxonomyViewSet, GalleryViewSet, LinkerPhotoViewSet, LoggerViewSet, ImportPhotoFlickr, TaxonomyListViewSet, \
    UploadChunkedPhoto, LoggerListView, CopyrightViewSet, AuthorViewSet, RestrictionViewSet, PhotoSearchView, \
    KeywordViewSet, NameViewSet, UpdatePhoto, PhotoTypeViewSet, TaxonomyLevelViewSet, YoutubeChannelList, \
    YoutubeUpload, VimeoAccountList, VimeoUpload, GalleryListViewSet, AlbumListViewSet, SwaggerPrivateSchemaView

urlpatterns = [
    path('docs/', SwaggerPrivateSchemaView.as_view()),

    # Auth endpoint
    path('api-token-auth/', ObtainAuthToken.as_view()),

    # User endpoint
    path('whoami/', WhoAmI.as_view(), name='whoami'),

    # Photos endpoints
    path('photos/upload/', UploadChunkedPhoto.as_view(), name='photo-upload'),
    re_path(r'photos/upload/(?P<pk>{})/chunk/$'.format(UUID_REGEX), UploadChunkedPhoto.as_view(),
            name='photo-upload-chunk'),
    re_path(r'photos/import/(?P<flickr>[\w\d]+)/album/<int:pk>/(?P<author>[\w\d]+)/(?P<copyright>[\w\d]+)/',
            ImportPhotoFlickr.as_view(), name='photo-import'),
    path('photos/<int:pk>/addition/', UpdatePhoto.as_view(), name='photo-update-addition'),

    path('photos/<int:pk>/youtube/', YoutubeChannelList.as_view(), name='photo-youtube-channels'),
    re_path(r'photos/<int:pk>/youtube/(?P<channel_pk>[\d]+)/$', YoutubeUpload.as_view(), name='photo-youtube-upload'),

    path('photos/<int:pk>/vimeo/', VimeoAccountList.as_view(), name='photo-vimeo-accounts'),
    re_path(r'photos/<int:pk>/vimeo/(?P<account_pk>[\d]+)/$', VimeoUpload.as_view(), name='photo-vimeo-upload'),

    # Categories and galleries flat endpoints
    path('categories/flat/', TaxonomyListViewSet.as_view(), name='category-list'),
    path('galleries/flat/', GalleryListViewSet.as_view(), name='gallery-list'),
    path('albums/flat/', AlbumListViewSet.as_view(), name='album-list'),

    # Loggers endpoints
    path('exports/logger/', LoggerListView.as_view(), name='export-logger'),

    # Semantic photo search
    path('search/', PhotoSearchView.as_view(), name='search'),

]

simple_router = SimpleRouter()

# CRUD views set
simple_router.register('groups', GroupViewSet)
simple_router.register('users', UserViewSet)
simple_router.register('albums', AlbumViewSet)
simple_router.register('photos', PhotoViewSet)
simple_router.register('categories', TaxonomyViewSet)
simple_router.register('categories-level', TaxonomyLevelViewSet, 'damtaxonomylevel')
simple_router.register('galleries', GalleryViewSet)

# Create & List view set
simple_router.register('logger', LoggerViewSet)

# Readonly views set
simple_router.register('names', NameViewSet)
simple_router.register('keywords', KeywordViewSet)
simple_router.register('copyrights', CopyrightViewSet)
simple_router.register('restrictions', RestrictionViewSet)
simple_router.register('authors', AuthorViewSet)
if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
    simple_router.register('types', PhotoTypeViewSet)

# Create & delete view set
create_delete_router = CreateDeleteRouter()
create_delete_router.register('link', LinkerPhotoViewSet, basename='gallery')

urlpatterns += simple_router.urls
urlpatterns += create_delete_router.urls
