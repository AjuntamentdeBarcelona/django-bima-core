# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _


class VimeoAccount(models.Model):
    name = models.CharField(_('Name'), max_length=100)
    username = models.CharField(_('Username'), max_length=100, blank=True, help_text=_(
        'Example: userZZZ'))
    client_id = models.CharField(_('Client ID'), max_length=100, unique=True)
    client_secrets = models.CharField(_('Client secrets'), max_length=200, unique=True)
    access_token = models.CharField(_('Access token'), max_length=100, unique=True, help_text=_(
        'Token must have at least scopes "public private create upload".'))

    class Meta:
        verbose_name = _('Vimeo account')
        ordering = ('name', )

    def __str__(self):
        return self.name
