# encoding: utf-8

from django.core.management.base import BaseCommand

from ... import youtube


class Command(BaseCommand):
    help = "Authenticate against Google OAuth2 servers."

    def handle(self, *args, **options):
        youtube.get_authenticated_service()
