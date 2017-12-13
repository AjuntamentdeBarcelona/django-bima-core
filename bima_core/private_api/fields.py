# -*- coding: utf-8 -*-
from django import forms
from django.apps import apps
from dry_rest_permissions.generics import DRYPermissionsField
from rest_framework import fields
import django_filters


# Base Fields and widgets


class MultipleNumberInput(forms.NumberInput):

    def value_from_datadict(self, data, files, name):
        if data and hasattr(data, 'getlist'):
            return data.getlist(name, [])
        return []


class MultipleNumberField(forms.IntegerField):
    widget = MultipleNumberInput

    def to_python(self, value):
        return [super(MultipleNumberField, self).to_python(v) for v in value]


# Rest serializers


class UserPermissionsField(fields.CharField):
    """
    The user permission is a field used to service all global permissions (read, write) over each
    application model. By default the user has not request.
    """
    default_actions = ('write', 'read', )

    def __init__(self, app_label, **kwargs):
        """
        Gets all models for the application specified as parameter. If the application does not exist, not return
        any permission.
        """
        try:
            self.models = apps.get_app_config(app_label).models
        except LookupError:
            self.models = {}
        super().__init__(read_only=True, **kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        """
        Representation all model permissions as a python dictionary.
        """
        permissions = dict.fromkeys(self.models.keys())
        for model_name, model in self.models.items():
            for action in self.default_actions:
                global_method_name = "has_{action}_permission".format(action=action)
                if not permissions[model_name]:
                    permissions[model_name] = {}
                permissions[model_name][action] = False
                if hasattr(model, global_method_name) and 'request' in self.context:
                    permissions[model_name][action] = getattr(model, global_method_name)(self.context['request'])
        return permissions


class PermissionField(DRYPermissionsField):
    """
    It is an overwritten DRYPermissionField class to permit serialize object permission.
    It solves a bug if an specific action method does not exit.
    """

    def to_internal_value(self, data):
        pass

    def to_representation(self, value):
        """
        Overwritten to avoid the error when try to discover the object permission and model class is not defined
        """
        results = {}
        for action, method_names in self.action_method_map.items():
            results[action] = False
            if not self.object_only and method_names.get('global', None) is not None:
                if hasattr(self.parent.Meta.model, method_names['global']):
                    results[action] = getattr(self.parent.Meta.model, method_names['global'])(self.context['request'])
            if not self.global_only and method_names.get('object', None) is not None:
                if hasattr(value, method_names['object']):
                    results[action] = getattr(value, method_names['object'])(self.context['request'])
        return results


# Django Filter


class MultipleNumberFilter(django_filters.Filter):
    """
    Field to permit 'in' lookup expression.
    """
    field_class = MultipleNumberField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, lookup_expr='in', **kwargs)


class MultipleNumberAndUnassignedFilter(MultipleNumberFilter):
    """
    Field to permit 'in' or 'or' lookup expressions.
    """
    unassigned_value = -1

    def filter(self, qs, value):
        if self.unassigned_value not in value:
            return super().filter(qs, value)
        qs_null = self.get_method(qs)(**{'%s__%s' % (self.name, 'isnull'): True})
        value.remove(self.unassigned_value)
        if value:
            qs_filter = super().filter(qs, value)
            return qs_filter | qs_null
        return qs_null
