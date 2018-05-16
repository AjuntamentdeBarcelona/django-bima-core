import os
import shutil

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Empty chunked upload directory to free space"

    def handle(self, *args, **options):
        chunks_path = settings.DRF_CHUNKED_UPLOAD_PATH.split(os.sep)[0]
        dir_path = os.path.join(settings.MEDIA_ROOT, chunks_path)
        self.empty_dir(dir_path)

    def empty_dir(self, dir_path):
        for the_file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, the_file)

            if os.path.isfile(file_path):
                os.unlink(file_path)
                self.stdout.write('Deleted file "{}".'.format(file_path))

            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                self.stdout.write('Deleted folder "{}".'.format(file_path))
