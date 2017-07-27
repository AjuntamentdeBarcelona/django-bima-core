# -*- coding: utf-8 -*-
from categories.models import CategoryBase
from constance import config
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext as _i
from django.contrib.auth.models import AbstractUser, Group as _Group
from django_thumbor import generate_url
from drf_chunked_upload.models import ChunkedUpload
from exifread import process_file
from geoposition.fields import GeopositionField
from hashfs import HashFS
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, Tag
from .fields import LanguageField
from .managers import TaxonomyManager, PhotoChunkedManager, KeywordManager, AlbumManager, PhotoManager, UserManager
from .permissions import UserPermissionMixin, AlbumPermissionMixin, PhotoPermissionMixin, \
    GalleryPermissionMixin, GalleryMembershipPermissionMixin, TaxonomyPermissionMixin, AccessLogPermissionMixin, \
    GroupPermissionMixin, PhotoChunkPermissionMixin, RightPermissionMixin, ReadPermissionMixin
from .utils import idpath, get_exif_info, get_exif_datetime, get_exif_longitude, get_exif_latitude, \
    get_exif_altitude, build_absolute_uri
import logging
import os
import six

logger = logging.getLogger(__name__)


#
# Abstract models
#

class SoftDeleteModelMixin(object):
    """
    Mixin to soft delete model instance
    """

    def soft_delete(self, field='is_active', commit=True):
        """
        Mark active model instance as not active and commit the change as default.
        """
        setattr(self, field, False)
        setattr(self, 'deleted_at', now())
        # commit changes
        if commit:
            self.save()

    def delete(self, using=None, keep_parents=False, force=False):
        """
        Overwritten method to soft delete model instance as default. If 'force' is checked will delete it from db.
        """
        if not force:
            self.soft_delete()
            return 1, {self._meta.label: 1}
        return super().delete(using, keep_parents)


class AbstractTimestampModel(models.Model):
    """
    Abstract class to extract common timestamp fields
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creation date'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Modification date'))

    class Meta:
        ordering = ('-modified_at', 'created_at', )
        abstract = True


class AbstractSlugModel(AbstractTimestampModel):
    """
    Abstract class to use to complete other with slug field.
    """
    _populate_slug_from = 'pk'
    _populate_blank_slug = False

    # TODO: make unique after migrate required all data
    # slug = models.SlugField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.slug

    def get_populate_slug_from(self):
        return self._populate_slug_from

    def save(self, *args, **kwargs):
        if self._populate_blank_slug or not self.slug:
            population_slug = getattr(self, self.get_populate_slug_from())
            if hasattr(population_slug, '__call__'):
                population_slug = population_slug()
            self.slug = slugify(population_slug)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('-modified_at', 'created_at', 'slug', )
        abstract = True


class AbstractTitleSlugModel(AbstractSlugModel):
    """
    Abstract class to use to complete other with common fields like slug (unique value to identify each item) and a
    title to describe it.
    """
    _populate_slug_from = 'title'
    title = models.CharField(max_length=128, verbose_name=_('Title'))

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-modified_at', 'created_at', 'slug', )
        abstract = True


#
# Back-office models
#


class Group(GroupPermissionMixin, _Group):
    """
    Proxy model to django auth group model to define extra properties and set
    access permission
    """

    class Meta:
        proxy = True


class User(UserPermissionMixin, SoftDeleteModelMixin, AbstractUser):
    """
    Overridden django auth user model to custom delete method as soft-deleted method
    and custom ordering queryset
    """

    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Delete date'))

    objects = UserManager()

    class Meta:
        ordering = ('is_active', 'username', 'date_joined', )


class TaggedKeyword(GenericTaggedItemBase, ReadPermissionMixin):
    """
    Relationship between tags or photo keywords with a language.
    Tag is a case sensitive free text entry entity, so it is possible there is a tag named 'mytag' and another one
    named 'MyTag' for the same language.
    """

    language = LanguageField(default=settings.LANGUAGE_CODE)
    tag = models.ForeignKey(Tag, related_name="%(app_label)s_%(class)s_tags")

    class Meta:
        unique_together = ('object_id', 'tag', 'language', )


class TaggedName(GenericTaggedItemBase, ReadPermissionMixin):
    """
    Tags to represent people names.
    This class has been created to allow define restrictions on it. If had not been needed an only read view set
    through the model this would not overwritten it.
    """

    tag = models.ForeignKey(Tag, related_name="%(app_label)s_%(class)s_tags")


class PhotoType(ReadPermissionMixin, models.Model):
    """
    Model to represent different types of photos, like brands.
    """
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Photo Type')
        verbose_name_plural = _('Photo Types')
        ordering = ('name', )


class Album(AlbumPermissionMixin, SoftDeleteModelMixin, models.Model):
    """
    Model to represent a physical grouping of photos. Each photo belongs to an album and only to one.
    """

    title = models.CharField(max_length=128, verbose_name=_('Title'))
    description = models.TextField(verbose_name=_('Description'))
    slug = models.SlugField(unique=True)
    cover = models.ForeignKey('Photo', blank=True, null=True, verbose_name=_('Cover'), related_name='covers_album')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creation date'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Modification date'))
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Delete date'))
    owners = models.ManyToManyField(User, related_name='albums')

    objects = AlbumManager.as_manager()

    def __str__(self):
        return self.title

    @property
    def photo(self):
        """
        :return: Album cover or the first photo instance of the album or None
        """
        return self.cover or self.photos_album.first()

    def is_membership(self, user):
        return user in self.owners.all()

    def soft_delete(self, field='is_active', commit=True):
        """
        Overwrite method to soft delete all related photos
        """
        response = super().soft_delete(field, commit)
        self.photos_album.soft_delete()
        return response

    class Meta:
        verbose_name = _('Album')
        verbose_name_plural = _('Albums')
        ordering = ('-modified_at', )


class Copyright(RightPermissionMixin, AbstractSlugModel):
    """
    Model to define copyrights.
    """

    _populate_slug_from = 'name'
    name = models.CharField(max_length=128, verbose_name=_('Name'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Copyright')
        verbose_name_plural = _('Copyrights')
        ordering = ('-modified_at', 'created_at', 'slug', )


class UsageRight(RightPermissionMixin, AbstractTitleSlugModel):
    """
    Class to model the usage restrictions.
    """

    description = models.TextField(blank=True, default='', verbose_name=_('Description'))

    def get_populate_slug_from(self):
        return "title_{}".format(settings.LANGUAGE_CODE)

    class Meta:
        verbose_name = _('Usage right')
        verbose_name_plural = _('Usage rights')


class PhotoAuthor(RightPermissionMixin, AbstractSlugModel):
    """
    This model registers the author of a concrete photo. To do this, it is only needed to store
    his name (first name and surname).
    """

    _populate_slug_from = 'get_full_name'
    first_name = models.CharField(max_length=50, verbose_name=_('First name'))
    last_name = models.CharField(max_length=50, verbose_name=_('last name'), blank=True, default='')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        return '{} {}'.format(self.first_name, self.last_name).strip()

    class Meta:
        verbose_name = _('Author')
        verbose_name_plural = _('Authors')


class PhotoExif(models.Model):
    """
    Class to model meta information associated to a photo.
    This information could be self provided by photo meta data or loaded from flickr API.
    """

    width = models.IntegerField(default=0, verbose_name=_('Width'))
    height = models.IntegerField(default=0, verbose_name=_('Height'))
    exif_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Original date'))
    camera_model = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Camera model'))
    orientation = models.IntegerField(blank=True, null=True, verbose_name=_('Orientation'))
    longitude = models.FloatField(default=0, verbose_name=_('Exif longitude'))
    latitude = models.FloatField(default=0, verbose_name=_('Exif latitude'))
    altitude = models.FloatField(default=0, verbose_name=_('Exif altitude'))
    size = models.IntegerField(default=0, verbose_name=_('Exif size (bytes)'))

    def __str__(self):
        label = ''
        if hasattr(self, 'photo'):
            label = self.photo and self.photo.title
        label = label or self.pk
        return _i("{} exif".format(label))


class Photo(PhotoPermissionMixin, SoftDeleteModelMixin, models.Model):
    """
    This model registers the content image file uploaded previously chunk by chunk and more over saves meta information
    about the photo like title, description, geo-information, copyrights and exif information.
    There is a related model to save auto-calculated exif information or, if photo importation is specified as
    flickr, this information is initialized by provided information.
    """

    PRIVATE = 0
    PUBLISHED = 1
    STATUS_CHOICES = [
        (PRIVATE, _('Private')),
        (PUBLISHED, _('Published')),
    ]

    UPLOAD_ERROR = 0
    UPLOADING = 1
    UPLOADED = 2
    UPLOAD_CHOICES = (
        (UPLOAD_ERROR, _('Upload error')),
        (UPLOADING, _('Uploading')),
        (UPLOADED, _('Uploaded')),
    )

    def image_path(instance, filename):
        basename, ext = os.path.splitext(filename)
        fs = HashFS('photos', depth=4, width=2, algorithm='sha256')
        stream = getattr(instance, 'image').chunks()
        id = fs.computehash(stream)
        return idpath(fs, id, extension=ext)

    # new fields
    identifier = models.CharField(max_length=50, verbose_name=_('Identifier'), blank=True, default='')
    image = models.ImageField(upload_to=image_path, max_length=200, blank=True, null=True, verbose_name=_('Image'))
    title = models.CharField(max_length=128, verbose_name=_('Title'))
    status = models.IntegerField(choices=STATUS_CHOICES, default=PRIVATE, verbose_name=_('Status'))
    upload_status = models.IntegerField(_('Upload status'), choices=UPLOAD_CHOICES, default=UPLOADING)
    description = models.TextField(blank=True, default='', verbose_name=_('Description'))
    original_file_name = models.CharField(max_length=200, verbose_name=_('Original file name'))
    internal_comment = models.TextField(blank=True, default='', verbose_name=_('Internal comment'))
    original_platform = models.CharField(max_length=200, default='', blank=True)
    categorize_date = models.DateField(verbose_name=_('Categorize date'), null=True, blank=True)

    # Location
    position = GeopositionField(null=True, blank=True)
    province = models.CharField(max_length=100, verbose_name=_('Province'), blank=True, default='')
    municipality = models.CharField(max_length=100, verbose_name=_('Municipality'), blank=True, default='')
    district = models.CharField(max_length=200, blank=True, default='', verbose_name=_('District'))
    neighborhood = models.CharField(max_length=200, blank=True, default='', verbose_name=_('Neighborhood'))
    address = models.CharField(max_length=200, blank=True, default='', verbose_name=_('Address'))
    postcode = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Postcode'))

    # Editable photo exif
    width = models.IntegerField(default=0, verbose_name=_('Width'))
    height = models.IntegerField(default=0, verbose_name=_('Height'))
    size = models.IntegerField(default=0, verbose_name=_('Size (bytes)'))
    exif_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Exif date'))
    camera_model = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Camera model'))
    orientation = models.IntegerField(blank=True, null=True, verbose_name=_('Orientation'))
    longitude = models.FloatField(default=0, verbose_name=_('Exif longitude'))
    latitude = models.FloatField(default=0, verbose_name=_('Exif latitude'))
    altitude = models.FloatField(default=0, verbose_name=_('Exif altitude'))

    # Readable auto-loaded photo exif
    exif = models.OneToOneField(PhotoExif, blank=True, null=True, verbose_name=_('EXIF'))

    # copyrights
    author = models.ForeignKey(PhotoAuthor, blank=True, null=True, verbose_name=_('Author'),
                               related_name='author_photos')
    copyright = models.ForeignKey(Copyright, blank=True, null=True, verbose_name=_('Copyright'),
                                  related_name='copyright_photos')
    internal_usage_restriction = models.ForeignKey(UsageRight, blank=True, null=True,
                                                   verbose_name=_('Internal usage restriction'),
                                                   related_name='internal_usage_restriction_photos')
    external_usage_restriction = models.ForeignKey(UsageRight, blank=True, null=True,
                                                   verbose_name=_('External usage restriction'),
                                                   related_name='external_usage_restriction_photos')

    # extra info
    flickr_id = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Flickr id'))
    flickr_username = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Flickr username'))
    owner = models.ForeignKey(User, verbose_name=_('Owner'), related_name='photos')
    photo_type = models.ForeignKey(PhotoType, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name=_('Type'), related_name='photos_type')
    categories = models.ManyToManyField('DAMTaxonomy', blank=True, related_name='taxonomy_photos')
    keywords = TaggableManager(blank=True, through=TaggedKeyword, manager=KeywordManager, verbose_name=_('Keywords'),
                               related_name='keyword_photos')
    names = TaggableManager(blank=True, through=TaggedName, verbose_name=_('Names'), related_name='name_photos')
    album = models.ForeignKey(Album, verbose_name=_('Album'), related_name='photos_album')

    # Timestamp meta information
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creation date'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Modification date'))
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Delete date'))

    objects = PhotoManager.as_manager()

    def __str__(self):
        return self.title

    @property
    def is_horizontal(self):
        """
        Orientation values of exif:
            1: 'Horizontal (normal)',
            2: 'Mirrored horizontal',
            3: 'Rotated 180',
            4: 'Mirrored vertical',
            5: 'Mirrored horizontal then rotated 90 CCW',
            6: 'Rotated 90 CW',
            7: 'Mirrored horizontal then rotated 90 CW',
            8: 'Rotated 90 CCW'
        """
        return self.orientation in [1, 2, 5, 7]

    @property
    def image_thumbnail(self):
        return self._generate_url(config.THUMBNAIL_WITH, config.THUMBNAIL_HEIGHT, smart=False, fit_in=True)

    @property
    def image_small_fit(self):
        return self._generate_url(config.IMAGE_SMALL_WITH, config.IMAGE_SMALL_HEIGHT, smart=False, fit_in=True)

    @property
    def image_small(self):
        return self._generate_url(config.IMAGE_SMALL_WITH, config.IMAGE_SMALL_HEIGHT, auto_resize=True)

    @property
    def image_medium(self):
        return self._generate_url(config.IMAGE_MEDIUM_WITH, config.IMAGE_MEDIUM_HEIGHT, auto_resize=True)

    @property
    def image_large(self):
        return self._generate_url(config.IMAGE_LARGE_WITH, config.IMAGE_LARGE_HEIGHT, auto_resize=True)

    @property
    def image_original(self):
        return self._generate_url()

    @property
    def image_file(self):
        return getattr(self.image, 'url', '')

    @property
    def image_flickr(self):
        if self.flickr_id and self.flickr_username:
            return build_absolute_uri(config.FLICKR_PHOTO_URL, '', args=[self.flickr_username, self.flickr_id, ])

    def _generate_url(self, width=None, height=None, smart=False, fit_in=False, fill_colour=None, auto_resize=False):
        image_url = "{}/{}".format(getattr(settings, 'AWS_LOCATION', ''), self.image.name).strip('/')

        # set the correct orientation if force not to be auto-cropped
        size = [width, height]
        if not(self.is_horizontal or fit_in):
            size.reverse()
        thumbor_params = {key: value for key, value in zip(['width', 'height', ], size) if value}

        # set default filter to always generate a jpeg image format
        thumbor_params['filters'] = ['format(jpeg)', ]

        # delete height or width param according photo orientation to auto resize it
        if auto_resize:
            thumbor_params.pop('height' if self.is_horizontal else 'width', None)

        # set auto-fill filter and default colour
        if fit_in:
            fill_colour = (fill_colour or config.THUMBNAIL_FILL_COLOUR).strip('#')
            filters = thumbor_params.get('filters', [])
            filters.append('fill({})'.format(fill_colour))
            thumbor_params.update({'filters': filters})

        url = generate_url(image_url, smart=smart, fit_in=fit_in, **thumbor_params)

        # remove unsave string from thumbor url
        if getattr(settings, 'THUMBOR_URL_REMOVE_UNSAFE', False):
            url = url.replace('/unsafe/', '/')

        # add prefix to media url
        prefix = getattr(settings, 'THUMBOR_MEDIA_URL_PREFIX', '')
        if prefix:
            media_url = getattr(settings, 'THUMBOR_MEDIA_URL', '')
            url = url.replace("/{}/".format(media_url), "/{}/{}/".format(prefix, media_url))

        return url

    def is_owner(self, user):
        return user == self.owner

    def is_membership(self, user):
        return self.is_owner(user) or user in self.album.owners.all()

    def get_image_metadata(self, with_exif=True):
        """
        Method to extract metadata from existing image.
        Continue if saving image content although get some error extracting it
        """
        # do not extracting metadata while does not image exists
        if not self.image:
            return
        # get image metadata
        metadata = {
            'width': self.image.width or 0,
            'height': self.image.height or 0,
            'size': self.image.size,
        }
        # get exif of image file
        if with_exif:
            try:
                exif_info = process_file(self.image.file, details=False)
                if exif_info:
                    metadata.update({
                        'exif_date': get_exif_datetime(exif_info, 'EXIF DateTimeOriginal'),
                        'camera_model': get_exif_info(exif_info, 'Image Model', default=''),
                        'orientation': get_exif_info(exif_info, 'Image Orientation'),
                        'longitude': get_exif_longitude(exif_info, 'GPS GPSLongitude'),
                        'latitude': get_exif_latitude(exif_info, 'GPS GPSLatitude'),
                        'altitude': get_exif_altitude(exif_info, 'GPS GPSAltitude'),
                    })
            except Exception as exc:
                logger.error("Error processing exif from {} photo\n\n{}".format(self.title, exc), exc_info=True)
        return metadata

    def set_metadata(self, only_readable=True, with_exif=True, commit=True):
        """
        Assign all only readable metadata to respective fields PhotoExif model.
        The operation of the assignment is that, the values of metadata that come from the API and do not evaluate to
        False prevail over those calculated from the content of the image.
        """
        # do not updating metadata while does not image exists
        if not self.image:
            return

        # create photo exif if not exist
        if not self.exif:
            self.exif = PhotoExif.objects.create()

        # set values into exif instance
        for k, v in six.iteritems(self.get_image_metadata(with_exif)):
            # This condition allows assign value to metadata fields without being overwritten by those in the image
            if not only_readable and (not getattr(self, k, None) and v):
                setattr(self, k, v)
            setattr(self.exif, k, v)
        self.exif.save()

        # commit changes
        if commit:
            self.save()

    class Meta:
        verbose_name = _('Photo')
        verbose_name_plural = _('Photos')
        ordering = ('-modified_at', 'owner', )


class PhotoChunked(PhotoChunkPermissionMixin, ChunkedUpload):
    """
    Model to upload chunk files.
    This model permits to upload big images in parts.
    """

    objects = PhotoChunkedManager()

    class Meta:
        verbose_name = _('Photo chunk')
        verbose_name_plural = _('Photo chunks')
        ordering = ('-completed_at', '-status', '-created_at', )


class Gallery(GalleryPermissionMixin, AbstractTimestampModel):
    """
    Model for galleries, which represents a logical set of photos.
    By default, each gallery is private and has not an image cover.
    The attribute 'owners' represents all users who can access to it (according to their privileges).
    """

    PRIVATE = 0
    PUBLISHED = 1

    STATUS_CHOICES = [
        (PRIVATE, _('Private')),
        (PUBLISHED, _('Published')),
    ]

    title = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    description = models.TextField(verbose_name=_('Description'), blank=True, default='')
    status = models.IntegerField(choices=STATUS_CHOICES, default=PRIVATE, verbose_name=_('Status'))
    photos = models.ManyToManyField(User, related_name='galleries', through='GalleryMembership')
    cover = models.ForeignKey(Photo, blank=True, null=True, verbose_name=_('Cover'), related_name='covers_gallery')

    owners = models.ManyToManyField(User, related_name='user_galleries')

    def __str__(self):
        return self.title

    @property
    def photo(self):
        """
        :return: Gallery cover or the first photo instance of the gallery or None
        """
        return self.cover or getattr(self.galleries_membership.first(), 'photo', None)

    def is_membership(self, user):
        return user in self.owners.all()

    class Meta:
        verbose_name = _('Gallery')
        verbose_name_plural = _('Galleries')
        ordering = ('-modified_at', )


class GalleryMembership(GalleryMembershipPermissionMixin, models.Model):
    """
    Modeling of a 3-band relationship between users, photos and galleries.
    """

    photo = models.ForeignKey(Photo, related_name='photo_galleries', on_delete=models.CASCADE)
    gallery = models.ForeignKey(Gallery, related_name='galleries_membership', on_delete=models.CASCADE)

    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Addition date'))
    added_by = models.ForeignKey(User, related_name='user_albums')


class DAMTaxonomy(TaxonomyPermissionMixin, CategoryBase):
    """
    Model to categorize photos.
    It is a hierarchical structure with unique slug and optional code.
    """
    code = models.CharField(_('code'), max_length=50, blank=True)
    slug = models.SlugField(verbose_name=_('slug'), max_length=200)
    parents = TaxonomyManager()

    @property
    def ancestors(self):
        return self.get_ancestors(ascending=True, include_self=False)

    @property
    def title_for_admin(self):
        active = _('active') if self.active else _('inactive')
        return '{} ({})'.format(self.name, active)

    class Meta:
        verbose_name = _('Taxonomy')
        verbose_name_plural = _('Taxonomies')
        ordering = ('slug', )


class AccessLog(AccessLogPermissionMixin, models.Model):
    """
    Modeling user actions through photos.
    The available actions are: 'view' and 'download'
    """

    VIEWED = 0
    DOWNLOADED = 1

    ACTION_CHOICES = [
        (VIEWED, _('Viewed')),
        (DOWNLOADED, _('Downloaded')),
    ]

    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, verbose_name=_('Photo'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    action = models.IntegerField(choices=ACTION_CHOICES, verbose_name=_('Action'))

    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Addition date'))

    class Meta:
        verbose_name = _('Access log')
        verbose_name_plural = _('Access logs')
        ordering = ('-added_at', )
