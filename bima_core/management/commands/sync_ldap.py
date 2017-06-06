from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import ldap

from ...constants import READER_GROUP_NAME
from ...ldapi.mixins import LDAPMixin
from ...models import Group


class Command(LDAPMixin, BaseCommand):
    help = "Sync ldap user accounts."

    @property
    def default_group(self):
        return Group.objects.get(name=READER_GROUP_NAME)

    def get_ldap_user(self, con, user):
        return self.AUTH_LDAP_USER_SEARCH.execute(con, {'user': user})

    def handle(self, *args, **options):
        con = ldap.initialize(self.AUTH_LDAP_SERVER_URI, bytes_mode=False)
        con.simple_bind_s(self.AUTH_LDAP_BIND_DN, self.AUTH_LDAP_BIND_PASSWORD)
        ldap_result = con.search_s(self.AUTH_LDAP_REQUIRE_GROUP, ldap.SCOPE_SUBTREE)

        user_model = get_user_model()

        for account_login in ldap_result[0][1]['memberUid']:
            username = account_login.decode('utf-8')
            user, created = user_model.objects.get_or_create(username=username)
            ldap_user = self.get_ldap_user(con, username)
            if ldap_user:
                user.first_name = ldap_user[0][1]['givenName'][0].strip()
                user.last_name = ldap_user[0][1]['sn'][0].strip()
                user.email = ldap_user[0][1]['mail'][0]
            self.stdout.write(user.first_name, user.last_name, user.email)
            user.set_unusable_password()
            user.save()

            if user and self.default_group not in user.groups.all():
                user.groups.add(self.default_group)
