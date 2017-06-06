from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from ..utils import normalize_text as _normalize_text


register = template.Library()


@register.simple_tag()
def translatable(instance, field_name, normalize=False):
    """
    Allow render all translated values of field name.
    ex:
        {% translatable object, 'foo' %}

        It will render: "foo value code lang es.\nfoo value code lang en.\nfoo value code lang ca."
    :return: string
    """
    value_text = ""
    for code, name in settings.LANGUAGES:
        value = getattr(instance, '{}_{}'.format(field_name, code), '')
        if normalize:
            value = _normalize_text(value)
        value_text = "{}{}\n".format(value_text, value)
    return mark_safe(value_text)


@register.filter(name='normalize')
def normalize_text(text):
    return _normalize_text(text)


@register.filter(name='compose_normalization')
def compose_normalization_text(text):
    return "{}\n{}".format(text, _normalize_text(text))
