"""
Package to encapsulate all features to authenticate with LDAP protocol.
This package contains:

1:. A Mixin to include in your setting Base configuration class.

    Egg: settings.py
        class Base(LDAPMixin, Configuration):
            ...

2:. An authentication backend which extends of 'django_auth_ldap.backend.LDAPBackend' and try to validate user in the
external system and in the current system at the same time. So, to validate user is required the user exists in the
current system.

    Egg: settings.py
        AUTHENTICATION_BACKENDS = [
            'ldap.backend.LDAPBackend',
            'django.contrib.auth.backends.ModelBackend'
        ]
"""
