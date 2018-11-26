# -*- coding: utf-8 -*-
from haystack import indexes

from .models import Photo
from .translation import TranslationMixin
from .utils import normalize_text


class PhotoIndex(TranslationMixin, indexes.ModelSearchIndex, indexes.Indexable):
    """
    Class to determine what data should be placed in search index.
    """
    normalized_title = indexes.CharField(model_attr='title')
    normalized_description = indexes.CharField(model_attr='description')

    categories = indexes.CharField()
    keywords = indexes.CharField()
    names = indexes.CharField()

    class Meta:
        model = Photo

    def get_updated_field(self):
        return "modified_at"

    def prepare_categories(self, obj):
        """
        Prepare multi-valued field with all category names
        :param obj: photo instance
        :return: list
        """
        return "\n".join(obj.categories.values_list('name', flat=True))

    def prepare_keywords(self, obj):
        """
        Prepare multi-valued field with all keywords names
        :param obj: photo instance
        :return: list
        """
        return "\n".join(obj.keywords.values_list('tag__name', flat=True))

    def prepare_names(self, obj):
        """
        Prepare multi-valued field with all names
        :param obj: photo instance
        :return: list
        """
        return "\n".join(obj.names.values_list('name', flat=True))

    def prepare_normalized_title(self, obj):
        """
        Prepare multi-language field to normalize its content
        :param obj: photo instance
        :return: normalized string
        """
        return self._normalize_multilang_field(obj, self.normalized_title.model_attr)

    def prepare_normalized_description(self, obj):
        """
        Prepare multi-language field to normalize its content
        :param obj: photo instance
        :return: normalized string
        """
        return self._normalize_multilang_field(obj, self.normalized_description.model_attr)

    def _normalize_multilang_field(self, obj, field_name):
        """
        Gets all multi-language fields by specified field name, compose text and return its normalization.
        :param obj: photo instance
        :param field_name: field name
        :return: normalized string
        """
        text = ""
        for field in self.get_translation_fields(field_name):
            text = "{}\n{}".format(text, getattr(obj, field, ''))
        return normalize_text(text)
