# -*- coding: utf-8 -*-

from django.conf.urls import include, url


urlpatterns = [
    url(r'^private_api/', include('bima_core.private_api.urls')),
]
