# -*- coding: utf-8 -*-

import logging
import tempfile

from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..permissions import ReadPermissionMixin


logger = logging.getLogger(__name__)


class YoutubeAccount(ReadPermissionMixin, models.Model):
    username = models.CharField(_('Username'), max_length=100, unique=True, help_text=_(
        'Example: user@company.com'))
    client_secret = models.TextField(_('Client secret'), help_text=_(
        'Content of client_secret.json for this Youtube account.'))

    class Meta:
        verbose_name = _('Youtube account')
        ordering = ('username', )

    def __str__(self):
        return self.username

    def client_secret_to_file(self):
        """
        Writes the client_secret in a temp file and returns its path.

        The caller is responsible for deleting the file.
        """
        path = None
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(self.client_secret)
            path = f.name
        logger.debug('client secret path: {}'.format(path))
        return path


class YoutubeChannel(ReadPermissionMixin, models.Model):
    name = models.CharField(_('Name'), max_length=100, help_text=_('Informative name for users.'))
    channel_id = models.CharField(_('Channel id'), max_length=100, unique=True, help_text=_(
        'Example: UCT0ndP9FPOea9dgPkqB74Pw'))
    account = models.ForeignKey(YoutubeAccount, verbose_name=_('Youtube account'))
    token = models.TextField(_('Token'), blank=True, help_text=_(
        "Autorefresh JSON token from Google OAuth2, don't edit manually."))

    class Meta:
        verbose_name = _('Youtube channel')
        ordering = ('name', )

    def __str__(self):
        return self.name

    def token_to_file(self):
        """
        Writes the token in a temp file an returns its path.

        The caller is responsible for deleting the file.
        """
        path = None
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            if self.token:
                f.write(self.token)
            path = f.name
        logger.debug('oauth2 token path: {}'.format(path))
        return path

    def save_token_from_file(self, file_path):
        """
        Saves the content of file_path into self.token.
        """
        with open(file_path) as f:
            self.token = f.read()
        self.save()

    def client_secret_to_file(self):
        """
        Writes the accounts client_secret in a temp file and returns its path.

        The caller is responsible for deleting the file.
        """
        return self.account.client_secret_to_file()
