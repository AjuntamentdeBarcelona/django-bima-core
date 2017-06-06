# -*- coding: utf-8 -*-
from django.contrib.auth.backends import ModelBackend
from django_auth_ldap.backend import LDAPBackend as _LDAPBackend
from ..constants import READER_GROUP_NAME

from models import Group


class LDAPBackend(_LDAPBackend):
    """
    The main backend class. Although it actually delegates most of its work to
    django-auth-ldap implementation.
    """

    @property
    def default_group(self):
        return Group.objects.get(name=READER_GROUP_NAME)

    @staticmethod
    def staff_authentication(username, password, **kwargs):
        user = ModelBackend().authenticate(username, password, **kwargs)
        if user and (user.is_staff or user.is_superuser):
            return user

    def user_exists(self, username):
        model = self.get_user_model()
        username_field = getattr(model, 'USERNAME_FIELD', 'username')
        return model.objects.filter(**{username_field + '__iexact': username, 'is_active': True}).exists()

    def authenticate(self, username, password, **kwargs):
        """
        Authenticate against the LDAP backend

        :param username:
        :param password:
        :param kwargs:
        :return:
        """
        # authenticate with superuser or staff permissions
        staff = self.staff_authentication(username, password, **kwargs)
        if staff is not None:
            return staff

        # if is not superuser or staff is needed authenticate through LDAP
        user = super().authenticate(username, password, **kwargs)
        if user and self.default_group not in user.groups.all():
            user.groups.add(self.default_group)
        return user

    def has_perm(self, user, perm, obj=None):
        # check perms with django auth backend
        return False

    def has_module_perms(self, user, app_label):
        # check perms with django auth backend
        return False

    def get_all_permissions(self, user, obj=None):
        # check perms with django auth backend
        return ()

    def get_group_permissions(self, user, obj=None):
        # check perms with django auth backend
        return ()
