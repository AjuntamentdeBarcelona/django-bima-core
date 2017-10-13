# encoding: utf-8

from django.core.management.base import BaseCommand

from ... import tasks


class Command(BaseCommand):
    help = "Temp command to try things..."

    def handle(self, *args, **options):
        tasks.upload_video_youtube.delay(youtube_channel_pk=2, photo_pk=136)
