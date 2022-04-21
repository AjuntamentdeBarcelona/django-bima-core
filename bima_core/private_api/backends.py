from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

class HaystackDjangoFilterBackend(DjangoFilterBackend):

    def get_filter_class(self, view, queryset=None):
        return getattr(view, 'filter_class', None)
