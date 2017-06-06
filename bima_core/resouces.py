# -*- coding: utf-8 -*-
from import_export import resources

from .models import DAMTaxonomy
from .translation import TranslationMixin


class TaxonomyResource(TranslationMixin, resources.ModelResource):
    """
    Resource to import / export taxonomies.
    This class extends to 'TranslationMixin' to allow to get translatable fields.
    """

    def get_export_order(self):
        return self._get_field_names()

    def _get_field_names(self):
        """
        Define the fields which are needed for import/export.
        Translatable fields are included in the list to return.
        """
        return ['id', ] + self.get_translation_fields('name')

    class Meta:
        model = DAMTaxonomy
