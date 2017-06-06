# -*- encoding: utf-8 -*-
from django.core.management import BaseCommand

import pytest


@pytest.mark.integration_test
@pytest.mark.django_db
def test_system_check():
    """
    Performs the Django system check.
    """
    base_command = BaseCommand()
    system_check_errors = base_command.check()
    assert not system_check_errors
