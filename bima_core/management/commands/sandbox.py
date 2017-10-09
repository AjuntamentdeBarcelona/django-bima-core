# encoding: utf-8

from django.core.management.base import BaseCommand

from ...tasks import print_youtube_channels


class Command(BaseCommand):
    help = "Temp command to try things..."

    def handle(self, *args, **options):
        print_youtube_channels.delay('dsastre')
