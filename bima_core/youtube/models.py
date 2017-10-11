# -*- coding: utf-8 -*-

import logging
# import tempfile

from django.db import models
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger(__name__)


class YoutubeAccount(models.Model):
    username = models.CharField(_('Username'), max_length=100, unique=True)
    client_secret = models.TextField(_('Client secret'), help_text=_(
        'Content of client_secret.json for this Youtube account.'))

    class Meta:
        verbose_name = _('Youtube account')
        ordering = ('username', )

    def __str__(self):
        return self.username

    def client_secret_to_file(self):
        """
        TODO: Writes the client_secret in a temp file an returns its path.
        """


class YoutubeChannel(models.Model):
    channel_id = models.CharField(_('Youtube channel id'), max_length=100, unique=True)
    name = models.CharField(_('Name'), max_length=100)
    account = models.ForeignKey(YoutubeAccount, verbose_name=_('Youtube account'))
    token = models.TextField(verbose_name=_('Autorefresh JSON token from Google OAuth2'), blank=True)

    class Meta:
        verbose_name = _('Youtube channel')
        ordering = ('name', )

    def __str__(self):
        return self.name

    def token_to_file(self):
        """
        TODO: Writes the token in a temp file an returns its path.
        """
