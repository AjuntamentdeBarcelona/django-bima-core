# -*- coding: utf-8 -*-
from constance import config
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm as _PasswordResetForm

from bima_core.utils import build_absolute_uri


class PasswordResetForm(_PasswordResetForm):
    """
    Override form to custom users who can request change password, email templates and overall
    context data to build a body of the mail
    """
    subject_template_name = 'emails/singup/signup_reset_password_subject.html'
    body_template_name = 'emails/singup/signup_reset_password_body.txt'
    html_body_template_name = 'emails/singup/signup_reset_password_body.html'

    def get_users(self, email):
        """
        Return active users for an specific email
        """
        return get_user_model()._default_manager.filter(
            email__iexact=email, is_active=True)

    def save(self, welcome=False, *args, **kwargs):
        """
        Send the reset password email.
        If is specified as 'welcome' email, it will send a cordial welcome message
        """
        subject_template_name = self.subject_template_name
        email_template_name = self.body_template_name
        html_email_template_name = self.html_body_template_name
        extra_email_context = {
            'welcome': welcome,
            'site_name': config.BIMA_CORE_NAME,
            'bima_core_change_password_site': build_absolute_uri(config.BIMA_CORE_SITE_URL,
                                                                 config.BIMA_CORE_CHANGE_PASSWORD_PATH)
        }
        super().save(subject_template_name=subject_template_name, email_template_name=email_template_name,
                     extra_email_context=extra_email_context, html_email_template_name=html_email_template_name,
                     *args, **kwargs)
