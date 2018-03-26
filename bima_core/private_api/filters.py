# -*- encoding: utf-8 -*-
import django_filters
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django_filters import CharFilter
from django_filters.compat import remote_queryset
from haystack.query import SearchQuerySet

from bima_core.constants import HAYSTACK_DEFAULT_OPERATORS
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
            'extra': lambda f: {'lookup_type': 'icontains'},
        },
        models.TextField: {
            'filter_class': django_filters.CharFilter,
            'extra': lambda f: {'lookup_type': 'icontains'},
        },
        models.ManyToManyField: {
            'filter_class': django_filters.ModelMultipleChoiceFilter,
            'extra': lambda f: {'lookup_type': 'in', 'queryset': remote_queryset(f)},
        },
    }

    def __init__(self, *args, **kwargs):
        self.base_filters['id'] = MultipleNumberFilter(name='id')
        super().__init__(*args, **kwargs)


class FullNameFilterMixin(object):
    """
    Mixin to define common user feature like get their full name
    """

    def filter_full_name(self, queryset, value):
        if value:
            return queryset.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value))
        return queryset


# Model filters

class GroupFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = Group
        fields = ('name', )


class UserFilter(FilterMixin, FullNameFilterMixin, django_filters.FilterSet):
    full_name = django_filters.MethodFilter()

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'full_name', 'email', 'groups', )


class AlbumFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = Album
        fields = ('title', 'description', 'slug', 'owners', )


class PhotoFilter(FilterMixin, django_filters.FilterSet):
    gallery = MultipleNumberAndUnassignedFilter(name='photo_galleries__gallery')
    album = MultipleNumberFilter()
    categories = MultipleNumberAndUnassignedFilter()
    s3_path = CharFilter(method='s3_path_filter')
    if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
        photo_type = MultipleNumberAndUnassignedFilter()

    class Meta:
        model = Photo
        fields = ('status', 'title', 'description', 'owner', 'album', 'gallery', 'categories',
                  'original_file_name', 'youtube_code', 'vimeo_code', 's3_path', )
        if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
            fields += ('photo_type', )

    def s3_path_filter(self, queryset, name, value):
        return queryset.filter(image__icontains=value)


class TaxonomyFilter(FilterMixin, django_filters.FilterSet):
    exclude_slug = django_filters.CharFilter(name='slug', lookup_type='exact', exclude=True)
    root = django_filters.BooleanFilter(name='parent', lookup_type='isnull')

    class Meta:
        model = DAMTaxonomy
        fields = ('parent', 'name', 'slug', 'exclude_slug', 'root')


class GalleryFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = Gallery
        fields = ('title', 'slug', 'owners', )


class AccessLogFilter(FilterMixin, django_filters.FilterSet):
    added_from = django_filters.DateTimeFilter(name='added_at', lookup_type='gt')
    added_to = django_filters.DateTimeFilter(name='added_at', lookup_type='lt')

    class Meta:
        model = AccessLog
        fields = ('action', 'added_from', 'added_to', 'user', )


class CopyrightFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = Copyright
        fields = ('slug', 'name', )


class UsageRightFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = UsageRight
        fields = ('slug', 'title', )


class PhotoAuthorFilter(FilterMixin, FullNameFilterMixin, django_filters.FilterSet):
    full_name = django_filters.MethodFilter()

    class Meta:
        model = PhotoAuthor
        fields = ('first_name', 'last_name', 'full_name', )


class TagFilter(FilterMixin, django_filters.FilterSet):
    tag = django_filters.CharFilter(name='tag__name', lookup_expr='icontains')

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


class PhotoTypeFilter(FilterMixin, django_filters.FilterSet):

    class Meta:
        model = PhotoType
        fields = ('name',)


# Special search filter


class PhotoSearchFilter(django_filters.FilterSet):
    q = django_filters.MethodFilter()

    class Meta:
        model = Photo
        fields = ('q', )

    def filter_q(self, queryset, value):
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
