from django_filters.rest_framework import DjangoFilterBackend


class HaystackDjangoFilterBackend(DjangoFilterBackend):

    def get_filter_class(self, view, queryset=None):
        return getattr(view, 'filter_class', None)
