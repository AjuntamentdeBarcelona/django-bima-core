# -*- coding: utf-8 -*-
from collections import OrderedDict
from constance import config
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class NumberPagination(PageNumberPagination):

    def get_page_size(self, request):
        page_size = super().get_page_size(request)
        if config.PAGE_SIZE:
            return config.PAGE_SIZE
        return page_size

    def get_next_link(self):
        if not self.page.has_next():
            return None
        return self.page.next_page_number()

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        return self.page.previous_page_number()

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('per_page', self.page.paginator.per_page),
            ('results', data)
        ]))


class LargeNumberPagination(NumberPagination):

    def get_page_size(self, request):
        page_size = super().get_page_size(request)
        if config.LARGE_PAGE_SIZE:
            return config.LARGE_PAGE_SIZE
        return page_size


class TaxonomyNumberPagination(NumberPagination):

    def get_page_size(self, request):
        return 4
