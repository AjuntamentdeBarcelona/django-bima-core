# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from bima_core.constants import DEFAULT_GROUPS

from ...models import Group


class Command(BaseCommand):
    help = "Create defaults groups for users"
    model = Group

    def handle(self, *args, **options):
        self.stdout.write('Creating groups...')
        for group in DEFAULT_GROUPS:
            self.model.objects.update_or_create(name=group)
        self.stdout.write(self.style.SUCCESS('Groups have been successfully created'))
