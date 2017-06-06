# -*- coding: utf-8 -*-
from rest_framework.routers import SimpleRouter, Route, DynamicListRoute, DynamicDetailRoute


class CreateRouter(SimpleRouter):
    """
    A router for create APIs
    """
    routes = [
        # Create route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={'post': 'create'},
            name='{basename}-create',
            initkwargs={'suffix': 'Create'}
        ),
        # Dynamically generated list routes.
        DynamicListRoute(
            url=r'^{prefix}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
    ]


class CreateDeleteRouter(SimpleRouter):
    """
    A router for create / delete APIs
    """
    routes = [
        # Create route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={'post': 'create'},
            name='{basename}-link',
            initkwargs={'suffix': 'Create'}
        ),
        # Dynamically generated list routes.
        DynamicListRoute(
            url=r'^{prefix}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
        # Delete route
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={'delete': 'destroy'},
            name='{basename}-unlink',
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes.
        DynamicDetailRoute(
            url=r'^{prefix}/{lookup}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
    ]
