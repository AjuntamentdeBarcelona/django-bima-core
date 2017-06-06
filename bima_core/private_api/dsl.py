import re

from django.conf import settings

from bima_core.translation import TranslationMixin
from bima_core.models import Photo


class DSL(TranslationMixin):
    """
    DSL Definition. Simple definition of language (pattern) to process a string and generate an specific response.
    The pattern matches two kind of expressions:
        - keyword:"text with spaces"
        - "text with spaces"
    where double quotes are redundant if the text has no blank spaces.
    The response has been designed to build an easy query filter, so both methods: 'get_values'
    and 'get_categorized_values' return the required data to filter.

    ex:
        title:"Golden Gate Bridge" "San Francisco" author:Unknown album:SF "golden gate bridge"

        The search is:
            title (ca) is : Golden Gate Bridge
            OR
            title (es) is : Golden Gate Bridge
            OR
            title (en) is : Golden Gate Bridge
            OR
            any field is : San Francisco
            OR
            author is : Unknown
            OR
            album is : SF
            OR
            any field is: golden gate bridge
    """

    def __init__(self, text_input):
        self.text_input = text_input
        self.pattern = self.build_pattern()
        self.mapping = self.get_mapping_model_keywords()
        self.validate()

    def get_values(self):
        """
        Get a list text for auto-filter by single text
        :return: list of string
        """
        values = []

        # process value through pattern (domain specific language)
        for match in re.finditer(self.pattern, self.text_input):
            if match.group('keyword') is None and match.group('block_keyword') is None:
                text = match.group('block_text') or match.group('text')
                values.append(text)

        return values

    def get_categorized_values(self):
        """
        Get a dict with all filter params specified by model fields
        :return: dict
        """
        # initialize variables
        categorized_values = {}

        # process value through pattern (domain specific language)
        for match in re.finditer(self.pattern, self.text_input):
            keyword = match.group('block_keyword') or match.group('keyword')
            text = match.group('block_text') or match.group('text')

            # skip if not exists keyword
            if not keyword:
                continue

            lookup_keys = []
            # if the keyword is not included in the mapping,
            # we add it to the lookup_keys directly
            if keyword not in self.mapping:
                lookup_keys.append(keyword)

            for key in self.mapping.get(keyword, []):
                key = keyword if not key else key
                lookup_keys.append(key)

            for key in lookup_keys:
                categorized_values.update({"{}".format(key): text})

        return categorized_values

    def get_categorized_translatable_values(self):
        """
        Get a dict with all filter params specified by model translatable fields
        :return: dict
        """
        # initialize variables
        categorized_values = {}

        # process translatable fields
        translatable_fields = self.get_base_translation_field_name()
        for key, value in self.get_categorized_values().items():
            # update categorized values with translatable fields
            if key in translatable_fields:
                for code, name in settings.LANGUAGES:
                    categorized_values["{}_{}".format(key, code)] = value
        return categorized_values

    # internal methods

    @staticmethod
    def build_pattern():
        """
        This regular expression matches for any string (with special characters) which is between double quotes and
        has or not marked for an accurate search.
        The other case to match is when the word is not between quotes, then matches while not found a white space.
        :return:
        """
        regex = r"((?P<block_keyword>\w+):)?\"(?P<block_text>.+?)\"" \
                r"|" \
                r"((?P<keyword>\w+):)?(?P<text>\S+)"

        return re.compile(regex)

    def validate(self):
        """
        Validate inherited class definition.
        Raise an error if not pass validation
        """
        if not self.Meta.model:
            raise NotImplementedError("Define a model model")
        if not self.pattern:
            raise Exception("Invalid pattern")

    def get_mapping_model_keywords(self):
        """
        Try to get class mapping definition with '_mapping' attribute name or generate a field map for each
        related model field.
        :return: dictionary with default models fields as key and an array with mapped key for each key
        """
        if getattr(self, '_mapping', None):
            return self._mapping
        mapping = {}
        # iterate only hover related model fields
        for name, field in self.get_all_related_fields().items():
            # generate map field key with 'title' attribute field name as default. ej: album__title
            field_name_mapping = self.extended_field_name_mapping(field)
            if field_name_mapping:
                mapping[name] = field_name_mapping
        return mapping

    def get_all_related_fields(self):
        """
        Get all related fields like a dictionary.
        :return: dictionary with name of field as key and field as value
        """
        return {field.name: field for field in self.Meta.model._meta.fields if field.related_model is not None}

    @staticmethod
    def extended_field_name_mapping(field, by='title'):
        """
        Expand related field name with 'title' attribute field (as default)
        :return: list of expansion attributes
        """
        if by in [f.name for f in field.related_model._meta.fields]:
            return ['{}__{}'.format(field.name, by), ]
        return []


class PhotoDSL(DSL):
    """
    DSL to search photos
    """

    _mapping = {
        'title': ['title', 'normalized_title', ],
        'description': ['description', 'normalized_description', ],
        'album': ['album__title', 'album__description', ],
        'author': ['author__first_name', 'author__last_name', ],
        'copyright': ['copyright__title', ],
        'restriction': ['external_usage_restriction__title', 'internal_usage_restriction__title', ]
    }

    class Meta:
        model = Photo
