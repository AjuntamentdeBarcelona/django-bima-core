# -*- coding: utf-8 -*-
from modeltranslation.translator import register, translator, TranslationOptions, NotRegistered
from modeltranslation.utils import get_translation_fields as _get_translation_fields
from .models import Album, Photo, DAMTaxonomy, Gallery, UsageRight


class TranslationMixin(object):
    """
    Mixin with usable methods for all class which require features related to model translation.
    To a correct usage of this mixin, is required a meta class with attribute model to access its fields.
    """

    def get_model(self):
        try:
            return self.Meta.model
        except AttributeError:
            raise NotImplementedError

    def get_base_translation_field_name(self):
        """
        Get field names defined as translatable on 'modeltranslation'
        :return: list of name fields
        """
        try:
            trans_options = translator.get_options_for_model(self.get_model())
            return trans_options.get_field_names()
        except NotRegistered:
            return []

    def get_all_translation_fields(self):
        """
        Get translatable fields from model translation.
        :return: list of name fields
        """
        translatable_fields = []
        for base_field_name in self.get_base_translation_field_name():
            translatable_fields.extend(self.get_translation_fields(base_field_name))
        return translatable_fields

    def get_translation_fields(self, field_names):
        return _get_translation_fields(field_names)


@register(Album)
class AlbumTranslationOptions(TranslationOptions):
    fields = ('title', 'description', )


@register(Photo)
class PhotoTranslationOptions(TranslationOptions):
    fields = ('title', 'description', )


@register(Gallery)
class GalleryTranslationOptions(TranslationOptions):
    fields = ('title', 'description', )


@register(DAMTaxonomy)
class DAMTaxonomyTranslationOptions(TranslationOptions):
    fields = ('name', )


@register(UsageRight)
class UsageRightTranslationOptions(TranslationOptions):
    fields = ('title', 'description', )
