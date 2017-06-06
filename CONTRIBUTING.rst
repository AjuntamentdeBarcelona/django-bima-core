============
Contributing
============

You are welcome to contribute to the development of django-tables2 in various ways:

* Discover and report bugs. Make sure to include a minimal example to show your problem.
* Propose features, add tests or fix bugs by opening a Pull Request.
* Fix documenation or translations.

When contributing code or making bug fixes, we appreciate to have unit tests to verify the expected
behaviour.

Running the tests
=================

To run the tests you need to install requirements_test.txt with pip ::

    pip install -r requirements_test.txt

Then you can run the test suite by typing ``tox``. It will take care of installing the correct
dependencies. During development, you might not want to wait for the tests to run in all
environments. In that case, use the ``-e`` argument to specify an environment: ``tox -e py35-1.10``
to run the tests in Python 3.5 with Django 1.10, or ``PYTHONPATH=. py.test`` to run the tests
against your current environment (which is even quicker).


Source code style
=================

This project has a test that runs ``flake8``, if some file doesn't follow ``falke8`` rules in
``tox.ini`` the test will fail. Also, try follow the rules defined in ``.editorconfig`` file.


Migrations
==========

To generate migrations run ::

    $ django-admin makemigrations --settings=tests_project.project.settings

I18n
====

You can generate locale files with the following commands: ::

    $ cd bima_core
    $ django-admin makemessages
    $ django-admin compilemessages
