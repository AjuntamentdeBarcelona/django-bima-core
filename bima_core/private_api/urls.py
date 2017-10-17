# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url
from rest_framework.routers import SimpleRouter
from bima_core.constants import UUID_REGEX
from .routers import CreateDeleteRouter
from .views import schema_view, ObtainAuthToken, GroupViewSet, UserViewSet, AlbumViewSet, PhotoViewSet, WhoAmI, \
    TaxonomyViewSet, GalleryViewSet, LinkerPhotoViewSet, LoggerViewSet, ImportPhotoFlickr, TaxonomyListViewSet, \
    UploadChunkedPhoto, LoggerListView, CopyrightViewSet, AuthorViewSet, RestrictionViewSet, PhotoSearchView, \
    KeywordViewSet, NameViewSet, UpdatePhoto, PhotoTypeViewSet, TaxonomyLevelViewSet, YoutubeChannelList, YoutubeUpload

urlpatterns = [
    url(r'^docs/$', schema_view),

    # Auth endpoint
    url(r'^api-token-auth/', ObtainAuthToken.as_view()),

    # User endpoint
    url(r'^whoami/$', WhoAmI.as_view(), name='whoami'),

    # Photos endpoints
    url(r'^photos/upload/$', UploadChunkedPhoto.as_view(), name='photo-upload'),
    url(r'^photos/upload/(?P<pk>{})/chunk/$'.format(UUID_REGEX), UploadChunkedPhoto.as_view(),
        name='photo-upload-chunk'),
    url(r'^photos/import/(?P<flickr>[\w\d]+)/album/(?P<pk>[\w\d]+)/(?P<author>[\w\d]+)/(?P<copyright>[\w\d]+)/$',
        ImportPhotoFlickr.as_view(), name='photo-import'),
    url(r'^photos/(?P<pk>[\d]+)/addition/$', UpdatePhoto.as_view(), name='photo-update-addition'),
    url(r'^photos/(?P<pk>[\d]+)/youtube/$', YoutubeChannelList.as_view(), name='photo-youtube-channels'),
    url(r'^photos/(?P<pk>[\d]+)/youtube/(?P<channel_pk>[\d]+)/$', YoutubeUpload.as_view(), name='photo-youtube-upload'),

    # Categories endpoints
    url(r'^categories/flat/$', TaxonomyListViewSet.as_view(), name='category-list'),

    # Loggers endpoints
    url(r'^exports/logger/$', LoggerListView.as_view(), name='export-logger'),

    # Semantic photo search
    url(r'^search/$', PhotoSearchView.as_view(), name='search'),
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
create_delete_router.register('link', LinkerPhotoViewSet, base_name='gallery')

urlpatterns += simple_router.urls
urlpatterns += create_delete_router.urls
