# encoding: utf-8

from pprint import pprint
from django.core.management.base import BaseCommand

from ... import tasks, youtube


class Command(BaseCommand):
    help = "Temp command to try things..."

    def handle(self, *args, **options):
        channels = youtube.list_channels()
        for channel in channels:
            pprint(channel)

        tasks.upload_video_youtube.delay(photo_pk=136)
