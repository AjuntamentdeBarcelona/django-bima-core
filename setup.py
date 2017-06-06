# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    'LatLon23>=1,<2',
    'Pillow>=3.4.2,<3.5',
    'django-auth-ldap>=1.2.8,<2',
    'django-constance[database]>=1.3,<2',
    'django-filter<1',
    'django-geoposition>=0.3',
    'django-haystack>=2.5.1,<2.7',
    'django-import-export>=0.5.1,<1',
    'django-modeltranslation>=0.12,<0.13',
    'django-rest-auth>=0.8.1,<1',
    'django-rest-swagger>=2.1.0,<2.2',
    'django-rq>=0.9.4,<1',
    'django-taggit-serializer>=0.1.5,<0.2',
    'django-taggit>=0.21.3,<0.23',
    'django-thumbor>=0.5.6,<0.6',
    'django-yubin>=0.3.1,<1',
    'django_categories>=1.4.3,<1.5',
    'djangorestframework-recursive>=0.1.1,<0.2',
    'djangorestframework>=3.5.2,<3.7',
    'drf-chunked-upload==0.2.2',
    'drf-haystack>=1.6.0,<1.7',
    'dry-rest-permissions>=0.1.8,<0.2',
    'exifread>=2.1.2,<3',
    'flickrapi>=2.1.2,<3',
    'hashfs>=0.7.0,<0.8',
    'python-dateutil>=2.5.3,<3',
    'rest-framework-generic-relations>=1.1.0,<1.2',
]


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='django-bima-core',
    version='0.8.0',
    packages=find_packages(exclude=['tests_project.*', 'tests_project']),
    include_package_data=True,
    license='GPLv3',
    description='Django app to manage digital assets via REST API and Django admin.',
    long_description=README,
    install_requires=INSTALL_REQUIRES,
    author='Advanced Programming Solutions SL (APSL)',
    author_email='info@apsl.net',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
