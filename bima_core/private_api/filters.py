# -*- encoding: utf-8 -*-
import django_filters
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django_filters import rest_framework as filters
from django_filters.filterset import remote_queryset
from haystack.query import SearchQuerySet

from bima_core.constants import HAYSTACK_DEFAULT_OPERATORS
from bima_core.filetypes import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, FILE_EXTENSIONS
from bima_core.models import Photo, Album, DAMTaxonomy, Gallery, Group, AccessLog, Copyright, UsageRight, \
    PhotoAuthor, TaggedKeyword, TaggedName, PhotoType

from .dsl import PhotoDSL
from .fields import MultipleNumberFilter, MultipleNumberAndUnassignedFilter


class FilterMixin(object):
    """
    Mixin to override default lookup for text fields and set id as a default filter field
    """

    filter_overrides = {
        models.CharField: {
            'filter_class': django_filters.CharFilter,
            'extra': lambda f: {'lookup_expr': 'icontains'},
        },
        models.TextField: {
            'filter_class': django_filters.CharFilter,
            'extra': lambda f: {'lookup_expr': 'icontains'},
        },
        models.ManyToManyField: {
            'filter_class': django_filters.ModelMultipleChoiceFilter,
            'extra': lambda f: {'lookup_expr': 'in', 'queryset': remote_queryset(f)},
        },
    }

    def __init__(self, *args, **kwargs):
        self.base_filters['id'] = MultipleNumberFilter(field_name='id')
        super().__init__(*args, **kwargs)


class FullNameFilterMixin(object):
    """
    Mixin to define common user feature like get their full name
    """

    def filter_full_name(self, queryset, field_name, value):
        if value:
            return queryset.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value))
        return queryset


# Model filters

class GroupFilter(FilterMixin, filters.FilterSet):

    class Meta:
        model = Group
        fields = ('name', )


class UserFilter(FilterMixin, FullNameFilterMixin, filters.FilterSet):
    full_name = filters.CharFilter(method='filter_full_name')
    is_active = filters.CharFilter(method='filter_is_active')

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'full_name', 'email', 'groups', 'is_active', )

    def filter_is_active(self, queryset, field_name, value):
        if value in (True, 'True', 'true', '1'):
            _value = True
        elif value in (False, 'False', 'false', '0'):
            _value = False
        else:
            return queryset
        return queryset.filter(is_active=_value)


class AlbumFilter(FilterMixin, filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Album
        fields = ('title', 'description', 'slug', 'owners', )


class PhotoFilter(FilterMixin, filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    gallery = MultipleNumberAndUnassignedFilter(field_name='photo_galleries__gallery')
    keywords_tags = filters.CharFilter(method='keywords_filter')
    album = MultipleNumberFilter()
    categories = MultipleNumberAndUnassignedFilter()
    s3_path = filters.CharFilter(method='s3_path_filter')
    file_type = filters.Filter(method='filter_file_type')
    original_file_name = filters.CharFilter(method='filter_original_file_name')
    if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
        photo_type = MultipleNumberAndUnassignedFilter()

    class Meta:
        model = Photo
        fields = ('status', 'title', 'description', 'owner', 'album', 'gallery', 'keywords_tags', 'categories',
                  'original_file_name', 'youtube_code', 'vimeo_code', 's3_path', 'file_type', )
        if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
            fields += ('photo_type', )

    def s3_path_filter(self, queryset, field_name, value):
        return queryset.filter(image__icontains=value)

    def filter_file_type(self, queryset, field_name, value):
        file_types = self.form.data.getlist('file_type')
        file_extensions = []
        q = Q()
        if 'image' in file_types:
            file_extensions = file_extensions + list(IMAGE_EXTENSIONS)
            file_extensions.remove('.eps')
        if 'vector' in file_types:
            file_extensions = file_extensions + ['.eps']
        if 'video' in file_types:
            file_extensions = file_extensions + list(VIDEO_EXTENSIONS)
        if 'audio' in file_types:
            file_extensions = file_extensions + list(AUDIO_EXTENSIONS)
        if 'file' in file_types:
            file_extensions = file_extensions + list(FILE_EXTENSIONS)
        for file_extension in file_extensions:
            q = q | Q(original_file_name__endswith=file_extension)
        return queryset.filter(q)

    def keywords_filter(self, queryset, name, value):
        list = value.split(',')
        q = Q()
        for list_value in list:
            if list_value:
                q = q | Q(keywords__name__iexact=list_value.strip())
        return queryset.filter(q).distinct()

    def filter_original_file_name(self, queryset, name, value):
        return queryset.filter(original_file_name__icontains=value)

class TaxonomyFilter(FilterMixin, django_filters.FilterSet):
    name = filters.CharFilter(method='filter_name')
    exclude_slug = filters.CharFilter(field_name='slug', lookup_expr='exact', exclude=True)
    root = filters.BooleanFilter(field_name='parent', lookup_expr='isnull')

    class Meta:
        model = DAMTaxonomy
        fields = ('parent', 'name', 'slug', 'exclude_slug', 'root')

    def filter_name(self, queryset, name, value):
        return queryset.filter(name__icontains=value)

class GalleryFilter(FilterMixin, filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Gallery
        fields = ('title', 'slug', 'owners', 'status', )



class AccessLogFilter(FilterMixin, filters.FilterSet):
    added_from = filters.DateTimeFilter(field_name='added_at', lookup_expr='gt')
    added_to = filters.DateTimeFilter(field_name='added_at', lookup_expr='lt')

    class Meta:
        model = AccessLog
        fields = ('action', 'added_from', 'added_to', 'user', )


class CopyrightFilter(FilterMixin, filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Copyright
        fields = ('slug', 'name', )


class UsageRightFilter(FilterMixin, filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = UsageRight
        fields = ('slug', 'title', )


class PhotoAuthorFilter(FilterMixin, FullNameFilterMixin, filters.FilterSet):
    full_name = filters.CharFilter(method='filter_full_name')

    class Meta:
        model = PhotoAuthor
        fields = ('first_name', 'last_name', 'full_name', )


class TagFilter(FilterMixin, django_filters.FilterSet):
    tag = django_filters.CharFilter(lookup_expr='icontains')

    @property
    def qs(self):
        self._qs = super().qs.distinct('tag_id')
        return self._qs


class NameFilter(TagFilter):

    class Meta:
        model = TaggedName
        fields = ('tag', )


class KeywordFilter(TagFilter):

    class Meta:
        model = TaggedKeyword
        fields = ('language', 'tag', )


class PhotoTypeFilter(FilterMixin, filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = PhotoType
        fields = ('name',)


# Special search filter


class PhotoSearchFilter(filters.FilterSet):
    q = filters.CharFilter(method='filter_q')
    file_type = filters.Filter(method='filter_file_type')

    class Meta:
        model = Photo
        fields = ('q', 'file_type', )

    def filter_queryset(self, queryset):
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.

        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
            # assert isinstance(queryset, models.QuerySet), \
            #     "Expected '%s.%s' to return a QuerySet, but got a %s instead." \
            #     % (type(self).__name__, name, type(queryset).__name__)
        return queryset

    def filter_q(self, queryset, field_name, value):
        """
        If not has value to filter return queryset.
        Filter values using haystack: firstly will prepare query filter with 'AND' operator for all fields
        to search (including multi-language fields) and then do the same operation with 'OR' operator.
        """
        if not value:
            return queryset

        dsl = PhotoDSL(value)
        return self._filter_q(dsl, Q.AND) | self._filter_q(dsl, Q.OR)

    def _filter_q(self, dsl, operator):
        """
        Apply operator filter for each filter argument whether categorized or not.
        If operator is not valid, return empty query result.
        :param dsl: definition of photo search language
        :param operator: Operator to join queries
        :return: query
        """
        search = SearchQuerySet().models(*[self.Meta.model, ])

        if operator not in HAYSTACK_DEFAULT_OPERATORS:
            return search.none()

        # filter for not categorize values
        for value in dsl.get_values():
            search = self._get_operation_filter(search, operator)(content=value)

        # filter for categorized translatable values always with operator OR
        for categorized_translatable_value in dsl.get_categorized_translatable_values().items():
            search = self._get_operation_filter(search, Q.OR)(categorized_translatable_value)

        # filter for categorized not translatable values
        for categorized_value in dsl.get_categorized_values().items():
            search = self._get_operation_filter(search, operator)(categorized_value)

        # return only active photos
        search = self._get_operation_filter(search, Q.AND)(('is_active', 'True'))

        return search

    @staticmethod
    def _get_operation_filter(search, operator=Q.OR):
        """
        Get filter operation on SearchQuerySet with defined operator
        """
        return getattr(search, "filter_{}".format(operator.lower()))

    def filter_file_type(self, queryset, field_name, value):
        if not value:
            return queryset
        file_types = value.split(', ')
        file_extensions = []
        q = Q()

        search = SearchQuerySet(query=queryset.query).models(*[self.Meta.model, ])

        if 'image' in file_types:
            file_extensions = file_extensions + list(IMAGE_EXTENSIONS)
            file_extensions.remove('.eps')
        if 'vector' in file_types:
            file_extensions = file_extensions + ['.eps']
        if 'video' in file_types:
            file_extensions = file_extensions + list(VIDEO_EXTENSIONS)
        if 'audio' in file_types:
            file_extensions = file_extensions + list(AUDIO_EXTENSIONS)
        if 'file' in file_types:
            file_extensions = file_extensions + list(FILE_EXTENSIONS)

        first = True
        for file_extension in file_extensions:
            if first:
                q = Q(original_file_name__endswith=str(file_extension))
                first = False
            q |= Q(original_file_name__endswith=str(file_extension))

        search = search.filter_and(q)

        return search
