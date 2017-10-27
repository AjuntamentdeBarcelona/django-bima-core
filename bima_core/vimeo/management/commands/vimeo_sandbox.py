# encoding: utf-8

from django.core.management.base import BaseCommand
import vimeo


ACCESS_TOKEN = 'change-me'  # scopes: public private create upload


class Command(BaseCommand):
    help = "Temporal command to play with vimeo API."

    def handle(self, *args, **options):
        v = vimeo.VimeoClient(token=ACCESS_TOKEN)

        about_me = v.get('/me')
        assert about_me.status_code == 200
        self.stdout.write('About me: {}'.format(about_me.text))

        video_uri = v.upload('/Users/dsastre/Movies/social.mp4')
        video = v.patch(video_uri, data={'name': 'Social', 'description': 'Video for social networks.'})
        assert video.status_code == 200
        self.stdout.write('Video URI: {}'.format(video_uri))
