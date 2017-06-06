from django.core.management.base import BaseCommand

from ...models import Photo

DESTINATION_ALL = 'all'
DESTINATION_SIZE = 'size'
DESTINATION_OUTPUT = 'output'


class Command(BaseCommand):
    help = "Action to export thumborized images with in selected sizes"
    AVAILABLE_SIZES = ['thumbnail', 'small_fit', 'small', 'medium', 'large', 'original']

    def add_arguments(self, parser):
        parser.add_argument('-s', '--size', nargs='+', dest=DESTINATION_SIZE, default=['thumbnail', ],
                            choices=self.AVAILABLE_SIZES, help='Set of size you want exports. Default: thumbnail.')
        parser.add_argument('-a', '--all', action='store_true', dest=DESTINATION_ALL, default=False,
                            help='Export for all photos (activated or not). Default only activated photos.')
        parser.add_argument('-o', '--output', action='store', dest=DESTINATION_OUTPUT,
                            default=None, help="Full path name of the output file. Default 'stdout'")

    def handle(self, *args, **options):
        self.stdout.write("Starting to export with in sizes {}".format(', '.join(options[DESTINATION_SIZE])))
        # set object attribute all declared options
        for field in (DESTINATION_SIZE, DESTINATION_OUTPUT, DESTINATION_ALL):
            setattr(self, field, options[field])
        total = self.export_thumbor_urls()
        self.stdout.write(self.style.SUCCESS("Export has finished successfully (total: {})".format(total)))

    def export_thumbor_urls(self):
        """Export thumbor urls according the options"""
        queryset = Photo.objects.all() if getattr(self, DESTINATION_ALL) else Photo.objects.active()
        output = getattr(self, DESTINATION_OUTPUT)
        if output:
            output = open(output, 'w')
        for photo in queryset:
            for size in getattr(self, DESTINATION_SIZE):
                print(getattr(photo, 'image_{}'.format(size)), file=output)
        return queryset.count()
