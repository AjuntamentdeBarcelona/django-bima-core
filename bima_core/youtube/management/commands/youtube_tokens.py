# encoding: utf-8

from django.core.management.base import BaseCommand

from ... import api
from ... import models


class Command(BaseCommand):
    help = "Setup Youtube tokens for all channels that doesn't have one."

    def handle(self, *args, **options):
        channels = models.YoutubeChannel.objects.all()
        for channel in channels:
            api.get_authenticated_service(channel)
