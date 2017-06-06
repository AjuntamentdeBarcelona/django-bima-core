# -*- coding: utf-8 -*-

from django_auth_ldap import config
from functools import partial
from kaio import Options
import ldap

opts = Options()
get = partial(opts.get, section='Ldap')


class LDAPMixin(object):

    @property
    def AUTH_LDAP_SERVER_URI(self):
        return get('AUTH_LDAP_SERVER_URI', '')

    @property
    def AUTH_LDAP_ADMIN_DN(self):
        return get('AUTH_LDAP_ADMIN_DN', '')

    @property
    def AUTH_LDAP_ADMIN_PASSWORD(self):
        return get('AUTH_LDAP_ADMIN_PASSWORD', '')

    @property
    def AUTH_LDAP_BIND_DN(self):
        return get('AUTH_LDAP_BIND_DN', '')

    @property
    def AUTH_LDAP_BIND_PASSWORD(self):
        return get('AUTH_LDAP_BIND_PASSWORD', '')

    @property
    def AUTH_LDAP_REQUIRE_GROUP(self):
        return get('AUTH_LDAP_REQUIRE_GROUP', None)

    @property
    def AUTH_LDAP_USER_SEARCH(self):
        auth_ldap_user_search_dn = get('AUTH_LDAP_USER_SEARCH_DN', '')
        return config.LDAPSearch(auth_ldap_user_search_dn, ldap.SCOPE_SUBTREE, "(uid=%(user)s)")

    @property
    def AUTH_LDAP_GROUP_SEARCH(self):
        auth_ldap_group_search_dn = get('AUTH_LDAP_GROUP_SEARCH_DN', '')
        return config.LDAPSearch(auth_ldap_group_search_dn, ldap.SCOPE_SUBTREE, "(objectClass=posixGroup)")

    @property
    def AUTH_LDAP_GROUP_TYPE(self):
        try:
            auth_ldap_group_type = getattr(config, get('AUTH_LDAP_GROUP_TYPE', ''))
        except AttributeError:
            return None
        return auth_ldap_group_type()

    @property
    def AUTH_LDAP_USER_ATTR_MAP(self):
        mapping = {
            "first_name": get('AUTH_LDAP_USER_FIRST_NAME_MAP', 'givenName'),
            "last_name": get('AUTH_LDAP_USER_LAST_NAME_MAP', 'sn'),
            "email": get('AUTH_LDAP_USER_EMAIL_MAP', 'mail'),
        }
        mapping.update(self.AUTH_LDAP_USER_EXTRA_ATTR_MAP)
        return mapping

    @property
    def AUTH_LDAP_USER_EXTRA_ATTR_MAP(self):
        return {
            "username": get('AUTH_LDAP_USER_USERNAME_MAP', 'uid'),
        }
