# -*- coding: utf-8 -*-
from rest_framework.routers import SimpleRouter, Route, DynamicRoute


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
            detail=False,
            initkwargs={'suffix': 'Create'}
        ),
        # Dynamically generated list routes.
        DynamicRoute(
            url=r'^{prefix}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            detail=False,
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
            detail=False,
            initkwargs={'suffix': 'Create'}
        ),
        # Dynamically generated list routes.
        DynamicRoute(
            url=r'^{prefix}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            detail=False,
            initkwargs={}
        ),
        # Delete route
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={'delete': 'destroy'},
            name='{basename}-unlink',
            detail=False,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes.
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{methodname}{trailing_slash}$',
            name='{basename}-{methodnamehyphen}',
            detail=False,
            initkwargs={}
        ),
    ]
