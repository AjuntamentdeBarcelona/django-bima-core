# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    'LatLon23>=1,<2',
    'Pillow==8.0.1',
    'django-auth-ldap==2.3.0',
    'django-constance[database]==2.6.0',
    'django-filter==2.4.0',
    'django-geoposition-2@git+https://git@github.com/pramon-apsl/django-geoposition.git',
    'django-haystack==3.0',
    'django-import-export==2.4.0',
    'django-modeltranslation==0.16.2',
    'django-mptt==0.11.0',
    'django-mptt-admin==2.0.3',
    'django-rest-auth==0.9.5',
    'django-rest-swagger==2.2.0',
    'django-rq==2.4.0',
    'django-taggit-serializer==0.1.7',
    'django-taggit==1.2.0',
    'django-thumbor>=0.5.6,<0.6',
    'django-yubin>=1.6.0,<2',
    'django_categories==1.8',
    'djangorestframework-recursive==0.1.2',
    'djangorestframework==3.12.2',
    'drf-chunked-upload==0.4.2',
    'drf-haystack==1.8.10',
    'dry-rest-permissions>=0.1.8,<0.2',
    'exifread==2.1.2',
    'flickrapi>=2.1.2,<3',
    'google-api-python-client>=1.6.4,<1.7',
    'hashfs>=0.7.0,<0.8',
    'python-dateutil>=2.5.3,<3',
    'rest-framework-generic-relations==2.1.0',
    'drf-yasg==1.20.0',
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
