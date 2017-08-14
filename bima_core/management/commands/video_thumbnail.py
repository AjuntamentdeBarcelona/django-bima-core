# encoding: utf-8

import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Temp command to generate a representative video thumbnail. Don't use me!"

    def add_arguments(self, parser):
        parser.add_argument('video', help="Video path")

    def handle(self, *args, **options):
        command = [
            'ffmpeg',
            '-i',
            options['video'],
            '-vf',
            'thumbnail=100',
            '-frames:v',
            '1',
            '-hide_banner',
            '-y',
            'thumb.jpg',
        ]

        try:
            proc = subprocess.run(command,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  universal_newlines=True)
        except FileNotFoundError:
            self.stdout.write('ffmpeg binary is not in your PATH, thumbnail not generated.')
            return

        if proc.returncode != 0:
            self.stderr.write(proc.stdout)
            return

        self.stdout.write('Thumbnail generated.')
