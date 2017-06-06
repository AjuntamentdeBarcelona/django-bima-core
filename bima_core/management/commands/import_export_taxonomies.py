import csv
import inspect
import os
import tablib

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from ...resouces import TaxonomyResource


class Command(BaseCommand):
    help = "Action to import / export all taxonomies to translate 'name' field in all available languages"
    resource = None

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', action='store', dest='file', default=None,
                            help="File to upload and import data.")
        parser.add_argument('-a', '--action', action='store', dest='action', default=None,
                            help="Action to do. If you want to do an import is required specify a file",
                            choices=['import', 'export'])
        parser.add_argument('-o', '--output', action='store', dest='output', default='taxonomies_export.csv',
                            help="The name of output file.")

    def handle(self, *args, **options):
        # set object attribute all declared options
        for field in ('action', 'file', 'output'):
            setattr(self, field, options[field])
        self.is_valid()
        # define resource for import & export
        self.resource = self.get_resource()
        # execute action (import / export)
        getattr(self, '{}_data'.format(self.action))()
        self.stdout.write(self.style.SUCCESS("{} has finished successfully".format(self.action.capitalize())))

    def is_valid(self):
        """
        Validate command options.
        """
        if not self.action:
            raise ValidationError("Is required define action: 'import' and 'export'.")

        if self.action == 'import' and not self.file:
            raise ValidationError("Is required specify file for 'import' action.")

        if self.file and not (os.path.exists(self.file) and os.path.isfile(self.file)):
            raise ValidationError("The file '{}' does not exist.".format(self.file))

    def get_resource(self):
        if not self.resource:
            self.resource = TaxonomyResource
        if inspect.isclass(self.resource):
            self.resource = self.resource()
        return self.resource

    def import_data(self):
        """
        Import taxonomies: Create or update taxonomies from file.
        The procedure is: read the content from file, instance dataset & import dataset (excluding headers)
        """
        with open(self.file, 'r', encoding='utf-8') as f:
            content_read = csv.reader(f)
            headers = next(content_read)
            dataset = tablib.Dataset(*content_read, headers=headers)
        self.resource.import_data(dataset)
        self.stdout.write("Importing data from '{}' file...".format(self.output))

    def export_data(self):
        """
        Export taxonomies: Generate an output file with the content of declared fields in resource.
        """
        self.stdout.write("Writing file '{}'...".format(self.output))
        with open(self.output, 'w', encoding='utf-8') as f:
            f.write(self.resource.export().csv)
