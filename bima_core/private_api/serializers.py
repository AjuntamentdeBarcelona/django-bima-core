# -*- coding: utf-8 -*-

from itertools import groupby
from operator import itemgetter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from drf_chunked_upload.serializers import ChunkedUploadSerializer
from drf_haystack.serializers import HaystackSerializerMixin
from rest_auth.serializers import PasswordResetSerializer as _PasswordResetSerializer
from rest_framework import serializers
from rest_framework.authtoken import serializers as auth_serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.reverse import reverse
from rest_framework_recursive.fields import RecursiveField
from taggit_serializer.serializers import TagListSerializerField

from bima_core.importers import Flickr
from bima_core.models import AccessLog, Album, DAMTaxonomy, Gallery, GalleryMembership, Group, \
    Photo, PhotoChunked, Copyright, UsageRight, PhotoAuthor, TaggedKeyword, TaggedName, PhotoType
from bima_core.tasks import up_image_to_s3
from bima_core.translation import TranslationMixin
from bima_core.utils import belongs_to_admin_group, is_iterable, is_staff_or_superuser

from .fields import UserPermissionsField, PermissionField
from .forms import PasswordResetForm


# Mixin Serializers


class ThumborSerializerMixin(object):
    """
    Mixin to auto-generate thumborized image from source image fields of the instance objects.
    You can custom how many fields, their name and properties using 'thumbor_fieldset'.
      egg:
      (
        ('image_field_1', ('original', 'large', 'medium', 'small', 'thumbnails'),
        ('image_field_2', ('thumbnails', ),
      )
    """

    use_filed_as_prefix = True
    thumbor_fieldsets = ()

    def get_thumbor_fieldsets(self):
        """`
        Get thumbor fieldsets defined
        """
        if self.thumbor_fieldsets is None or not is_iterable(self.thumbor_fieldsets):
            raise ValueError("To thumborize image fields is required specify a lit of image fields")
        return self.thumbor_fieldsets

    def get_thumbor_fields(self):
        """
        Return the dict of field names -> thumbor field instances that should be
        used for `self.fields` when instantiating the serializer.
        """
        thumborized_fields, thumbor_fieldsets = {}, self.get_thumbor_fieldsets()
        for attrs, fields in thumbor_fieldsets:
            for field_name in fields:
                # build field name of serializer
                if self.use_filed_as_prefix and is_iterable(attrs) and len(attrs) > 1:
                    field_name = "{}_{}".format(attrs[1], field_name)
                # build params for serializer field
                params = {'read_only': True}
                if attrs[0] is not None:
                    params.update({'source': '{}.{}'.format(attrs[0], field_name)})
                # update fields with each defined field of fieldset
                thumborized_fields[field_name] = serializers.CharField(**params)
        return thumborized_fields

    def get_fields(self):
        """
        Override serializer method to update dict of fields and clean S3 url images
        """
        fields = super().get_fields()
        # clean all declared image fields
        for base_field_name, field in self.thumbor_fieldsets:
            fields.pop(base_field_name, None)
        # update with new thumborized image fields
        fields.update(**self.get_thumbor_fields())
        return fields


class TranslationSerializerMixin(TranslationMixin):
    """
    Mixin to auto-generate multi-language fields from translatable model fields.
    This fields should be of modeltranslation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_read_only_fields()

    def update_read_only_fields(self):
        """
        Update 'read_only_fields' with translation field name if base field is defined as read only.
        """
        read_only_fields = list(getattr(self.Meta, 'read_only_fields', []))
        for base_field_name in self.get_base_translation_field_name():
            if base_field_name in read_only_fields:
                read_only_fields.extend(self.get_translation_fields(base_field_name))
        self.Meta.read_only_fields = tuple(set(read_only_fields))

    def get_field_names(self, declared_fields, info):
        """
        Get fields names from serializer with all additional translatable fields declared in 'model-translation'
        registered module.
        :return: list of name fields
        """
        # update fields with translatable fields
        field_names = super().get_field_names(declared_fields, info)
        field_names = list(field_names) + self.get_all_translation_fields()
        return field_names

    def get_fields(self):
        """
        Get all fields, included translation fields. For each translatable sets the value of 'required' attribute of
        base field and exclude it (base field) from fields.
        :return: list of fields
        """
        fields = super().get_fields()
        # set default language field required if base field is required and set base field not required and read_only
        for field_name in self.get_base_translation_field_name():
            field = fields[field_name]
            fields['{}_{}'.format(field_name, settings.LANGUAGE_CODE)].required = field.required
            field.required = False
            fields.read_only = True
        return fields


class ReadOnlyFieldMixin(object):
    """
    Mixin class to force declared and meta fields as read only. Very useful when you extend classes
    with declared fields (no read only) and you want them to be read only in the extended class.
    """

    def get_fields(self):
        fields = super().get_fields()
        for name, field in fields.items():
            if name in getattr(self.Meta, 'read_only_fields', tuple()):
                field.read_only = True
                field.required = False
        return fields


class ValidatePermissionSerializer(object):
    """
    Grouping of simple features to validate user permissions in serializers.
    """

    @property
    def user(self):
        return self.context['request'].user

    @property
    def action(self):
        return getattr(self.context['view'], 'action', None)

    @property
    def is_update_action(self):
        return self.action in ['update', 'partial_update', ]

    @property
    def is_create_action(self):
        return self.action == 'create'

    @property
    def view_kwargs(self):
        return self.context['view'].kwargs

    @property
    def view_lookup_field(self):
        return self.context['view'].lookup_field


class ReadPermissionSerializerMixin(object):
    """
    Base right serializer
    """

    class Meta:
        fields = ('id', 'slug', 'title', )
        read_only_fields = fields

    def get_fields(self):
        fields = super().get_fields()
        fields['permissions'] = PermissionField(actions=('read', ), read_only=True)
        return fields


class UserSerializerMixin(object):
    """
    base user serializer
    """

    class Meta:
        fields = ('id', 'first_name', 'last_name', 'is_superuser', )

    def get_fields(self):
        fields = super().get_fields()
        fields['full_name'] = serializers.CharField(source='get_full_name', read_only=True)
        return fields


# Base model serializers


class AuthTokenSerializer(auth_serializers.AuthTokenSerializer):

    def validate(self, attrs):
        """
        DAM users must belog to a group.
        """
        attrs = super().validate(attrs)
        user = attrs['user']
        if not user.groups.exists():
            msg = _('User must belong to a group.')
            raise serializers.ValidationError(msg, code='authorization')
        return attrs


class GroupSerializer(serializers.ModelSerializer):
    """
    Group serializer.
    """

    permissions = PermissionField(actions=('read', ))

    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions', )
        read_only_fields = ('name', )


class CopyrightSerializer(serializers.ModelSerializer):
    """
    Copyright serializer
    """

    class Meta:
        model = Copyright
        fields = ('id', 'slug', 'name', )
        read_only_fields = fields

    def get_fields(self):
        fields = super().get_fields()
        fields['permissions'] = PermissionField(actions=('read', ), read_only=True)
        return fields


class UsageRightSerializer(serializers.ModelSerializer):
    """
    Copyright serializer
    """

    class Meta:
        model = UsageRight
        fields = ('id', 'slug', 'title', )
        read_only_fields = fields

    def get_fields(self):
        fields = super().get_fields()
        fields['permissions'] = PermissionField(actions=('read', ), read_only=True)
        return fields


class BaseAlbumSerializer(serializers.ModelSerializer):
    """
    Album serializer.
    Short album serializer, useful to extend serializer with readonly album information.
    """

    class Meta:
        model = Album
        fields = ('id', 'title', )


class BaseTaxonomySerializer(serializers.ModelSerializer):
    """
    Taxonomy serializer.
    Short taxonomy serializer, useful to extend serializer with readonly taxonomy information.
    """

    title = serializers.CharField(read_only=True, source='name')

    class Meta:
        model = DAMTaxonomy
        fields = ('id', 'title', )


class TagSerializer(serializers.ModelSerializer):
    """
    Keyword model serializer.
    """

    id = serializers.IntegerField(read_only=True, source='tag.id')
    tag = serializers.CharField(read_only=True, source="tag.name")

    class Meta:
        model = NotImplementedError
        fields = ('id', 'tag', )


class KeywordTagSerializer(TagSerializer):
    """
    Taggedkeyword serializer
    """

    class Meta(TagSerializer.Meta):
        model = TaggedKeyword


class NameTagSerializer(TagSerializer):
    """
    Taggedname serializer
    """

    class Meta(TagSerializer.Meta):
        model = TaggedName


class PhotoTypeSerializer(serializers.ModelSerializer):
    """
    Photo type model serializer
    """

    class Meta:
        model = PhotoType
        fields = ('id', 'name', )


class KeywordSerializer(serializers.Serializer):
    """
    Keyword serializer to create, update or render Tag items.
    """

    language = serializers.ChoiceField(choices=settings.LANGUAGES, required=True)
    tag = serializers.CharField(max_length=100, required=True)

    default_error_messages = {
        'invalid': _("Not permitted create 'keyword' instances")
    }

    @staticmethod
    def update_or_create(photo, keywords, cleanup=True):
        """
        This method use the manager to create new tags with the required languages.
        If there is not keywords represents the user want to clean all existent tags.
        """
        # clear current keywords
        if cleanup or not keywords:
            photo.keywords.clear()
        # create new language tagged keywords cleaning all current tags for the same language
        for language, tags in groupby(keywords, key=itemgetter('language')):
            photo.keywords.add(*[t.get('tag') for t in tags], language=language, cleanup=cleanup)

    def create(self, validated_data):
        raise ValidationError(self.default_error_messages)

    def update(self, instance, validated_data):
        raise ValidationError(self.default_error_messages)


class NameSerializer(TagListSerializerField):
    """
    Name serializer to create, update or render Tagged names of photos.
    """

    default_error_messages = {
        'invalid': _("Not permitted create 'name' instances")
    }

    @staticmethod
    def update_or_create(photo, names, cleanup=True):
        """
        This method uses the manager to create new tags with the required languages.
        If there are no keywords, it means that the user wants to clean all existent tags.
        """
        # clear current names
        if cleanup:
            photo.names.clear()
        # create new tagged names
        if is_iterable(names) and len(names) > 0:
            photo.names.add(*names)

    def create(self, validated_data):
        raise ValidationError(self.default_error_messages)

    def update(self, instance, validated_data):
        raise ValidationError(self.default_error_messages)


class BasePhotoSerializer(ValidatePermissionSerializer, ThumborSerializerMixin, TranslationSerializerMixin,
                          serializers.ModelSerializer):
    permissions = PermissionField()
    thumbor_fieldsets = (
        ((None, 'image'), ('thumbnail', )),
    )

    class Meta:
        model = Photo
        fields = ('id', 'title', 'description', 'permissions')


# Extra info serializers


class OwnerSerializer(UserSerializerMixin, serializers.ModelSerializer):
    """
    Short user serializer.
    Used in all serializer which instance has an owner related field.
    """

    roles = serializers.ListField(child=serializers.CharField(), source='groups.all', read_only=True)

    class Meta(UserSerializerMixin.Meta):
        model = get_user_model()
        fields = UserSerializerMixin.Meta.fields + ('email', 'roles', )


class PhotoAuthorSerializer(UserSerializerMixin, serializers.ModelSerializer):
    """
    Author serializer.
    Used basically to read/list photo authors.
    """

    class Meta(UserSerializerMixin.Meta):
        model = PhotoAuthor
        fields = ('id', 'first_name', 'last_name', )


class PhotoGalleryMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer to show readable information of gallery membership.
    Used in PhotoSerializer to show the relation about users, galleries and photos.
    """

    title = serializers.CharField(source='gallery.title')
    owners = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.active(), many=True,
                                                source='gallery.owners')

    class Meta:
        model = GalleryMembership
        fields = ('id', 'gallery', 'title', 'owners', )
        read_only_fields = fields

    def get_fields(self):
        """
        Add translatable field 'title'. Is not used TranslationSerializerMixin because this is a special case
        where field has source attribute pointing to nested model.
        """
        fields = super().get_fields()
        for code, name in settings.LANGUAGES:
            fields['title_{}'.format(code)] = serializers.CharField(source='gallery.title_{}'.format(code))
        return fields


class PhotoExtraInfoSerializer(serializers.ModelSerializer):
    """
    Serializer used to show readable information of photos.
    Used in PhotoSerializer to only show related information of photos.
    """

    status_display = serializers.CharField(read_only=True, source='get_status_display')
    photo_galleries = PhotoGalleryMembershipSerializer(read_only=True, many=True)
    categories = BaseTaxonomySerializer(read_only=True, many=True)
    album = BaseAlbumSerializer(read_only=True)
    owner = OwnerSerializer(read_only=True)
    author_display = serializers.CharField(read_only=True, source='author.get_full_name')
    copyright_display = serializers.CharField(read_only=True, source='copyright.name')
    internal_restriction_display = serializers.CharField(read_only=True, source='internal_usage_restriction.title')
    external_restriction_display = serializers.CharField(read_only=True, source='external_usage_restriction.title')
    is_horizontal = serializers.BooleanField(read_only=True)

    class Meta:
        model = Photo
        fields = ('status_display', 'photo_galleries', 'categories', 'album', 'owner', 'author_display',
                  'copyright_display', 'internal_restriction_display', 'external_restriction_display',
                  'is_horizontal', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.PHOTO_TYPES_ENABLED:
            self.fields['photo_type'] = PhotoTypeSerializer(read_only=True)
            self.Meta.fields += ('photo_type',)


class AlbumExtraInfoSerializer(serializers.ModelSerializer):
    """
    Serializer used to show readable information of albums.
    Used in AlbumSerializer to only show related information of albums.
    """

    owners = OwnerSerializer(read_only=True, many=True)

    class Meta:
        model = Album
        fields = ('owners', )


class GalleryExtraInfoSerializer(serializers.ModelSerializer):
    """
    Serializer used to show readable information of albums.
    Used in AlbumSerializer to only show related information of albums.
    """

    owners = OwnerSerializer(read_only=True, many=True)
    status_display = serializers.CharField(read_only=True, source='get_status_display')

    class Meta:
        model = Gallery
        fields = ('owners', 'status_display', )


class TaxonomyExtraInfoSerializer(serializers.ModelSerializer):
    """
    Serializer used to show readable information of albums.
    Used in AlbumSerializer to only show related information of albums.
    """

    parent = BaseTaxonomySerializer(read_only=True)
    children = serializers.IntegerField(source='get_descendant_count')

    class Meta:
        model = DAMTaxonomy
        fields = ('parent', 'children', )


class UserExtraInfoSerializer(serializers.ModelSerializer):
    """
    Serializer used to show readable information of albums.
    Used in AlbumSerializer to only show related information of albums.
    """

    groups = GroupSerializer(read_only=True, many=True)

    class Meta:
        model = get_user_model()
        fields = ('groups', )


# Objects serializers


class PasswordResetSerializer(_PasswordResetSerializer):
    """
    Override password reset serializer from 'django-rest-auth' package to customize the form which send the email.
    """

    password_reset_form_class = PasswordResetForm


class UserSerializer(OwnerSerializer):
    """
    User serializer.
    Permit assign groups when create or update instance in the same request.
    """

    email = serializers.EmailField(required=True)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True)
    extra_info = serializers.SerializerMethodField(read_only=True)
    permissions = PermissionField()

    class Meta(OwnerSerializer.Meta):
        fields = OwnerSerializer.Meta.fields + ('username', 'is_active', 'groups', 'extra_info', 'permissions', )

    def _update_or_create(self, validated_data, instance=None):
        set_groups, groups = False, []
        if 'groups' in validated_data:
            set_groups = True
            groups = validated_data.pop('groups', [])
        user, _ = self.Meta.model.objects.update_or_create(pk=getattr(instance, 'id', None), defaults=validated_data)
        if set_groups:
            user.groups.clear()
            user.groups.add(*groups)
        return user

    @transaction.atomic()
    def create(self, validated_data):
        """
        Creates an user instance and sets his permission groups. Also sends a notification to him to confirm the signup
        and requests he sets his password, because a random password has been set
        """
        validated_data['password'] = make_password(None)
        user = self._update_or_create(validated_data)
        # send signup confirmation email with link to set password
        form = PasswordResetForm(data={'email': user.email})
        if form.is_valid():
            form.save(welcome=True)
        return user

    @transaction.atomic()
    def update(self, instance, validated_data):
        """
        Update an existing user instance and sets his new
        """
        return self._update_or_create(validated_data, instance)

    def get_extra_info(self, obj):
        """
        Method to serialize extra information from self instance.
        """
        return UserExtraInfoSerializer(obj, read_only=True, context=self.context).data


class WhoAmISerializer(UserSerializer):
    """
    User serializer.
    Serializer all required user information. More over all global permissions over each specified application model
    """

    permissions = UserPermissionsField(app_label='bima_core')


class AlbumSerializer(ThumborSerializerMixin, TranslationSerializerMixin, BaseAlbumSerializer):
    """
    Album serializer.
    Is permitted to set many owners of each in the same request.
    """

    owners = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.active(), many=True)
    photos = serializers.PrimaryKeyRelatedField(read_only=True, source='photos_album', many=True)
    cover = serializers.PrimaryKeyRelatedField(queryset=Photo.objects.active(), required=False)
    extra_info = serializers.SerializerMethodField(read_only=True)
    permissions = PermissionField()

    class Meta(BaseAlbumSerializer.Meta):
        fields = ('id', 'title', 'description', 'slug', 'created_at', 'modified_at', 'owners', 'photos', 'extra_info',
                  'cover', 'permissions', )

    def get_thumbor_fieldsets(self):
        """
        Permit return thumborized image fields.
        """
        return (('photo', 'image'), ('thumbnail', )),

    def get_extra_info(self, obj):
        """
        Method to serialize extra information from self instance.
        """
        return AlbumExtraInfoSerializer(obj, read_only=True, context=self.context).data

    def validate_cover(self, value):
        if not self.instance.photos_album.filter(id=value.id).exists():
            raise ValidationError(
                _('Invalid pk "{pk}" - photo does not exist into current album.'.format(pk=value.id)), code='cover'
            )
        return value


class GallerySerializer(ThumborSerializerMixin, TranslationSerializerMixin, serializers.ModelSerializer):
    """
    Gallery serializer.
    Is permitted set many owners of each in the same request.
    """

    owners = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.active(), many=True)
    cover = serializers.PrimaryKeyRelatedField(queryset=Photo.objects.active(), required=False)
    extra_info = serializers.SerializerMethodField(read_only=True)
    permissions = PermissionField()

    class Meta:
        model = Gallery
        fields = ('id', 'title', 'description', 'slug', 'photos', 'status', 'created_at', 'modified_at', 'owners',
                  'extra_info', 'cover', 'permissions', )

    def get_thumbor_fieldsets(self):
        """
        Permit return thumborized image fields.
        """
        return (('photo', 'image'), ('thumbnail', )),

    def get_extra_info(self, obj):
        """
        Method to serialize extra information from self instance.
        """
        return GalleryExtraInfoSerializer(obj, read_only=True, context=self.context).data

    def validate_cover(self, value):
        if not self.instance.galleries_membership.filter(photo_id=value.id).exists():
            raise ValidationError(
                _('Invalid pk "{pk}" - photo does not exist into current gallery.'.format(pk=value.id)), code='cover'
            )
        return value


class GalleryMembershipSerializer(ValidatePermissionSerializer, serializers.ModelSerializer):
    """
    Serializer for links between photos and galleries.
    Allows a photo to belong to a gallery.
    """

    permissions = PermissionField()

    class Meta:
        model = GalleryMembership
        fields = ('id', 'photo', 'gallery', 'added_at', 'permissions', )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # validated for admins
        if belongs_to_admin_group(self.user):
            return attrs
        # owners and membership validation
        if self.is_create_action and not attrs['gallery'].is_membership(self.user):
            raise PermissionDenied
        return attrs

    def create(self, validated_data):
        """
        Auto assign user to the membership link with authenticated user information.
        To permit request of new
        """
        validated_data['added_by'] = self.context['request'].user
        try:
            return self.Meta.model.objects.get(photo=validated_data['photo'], gallery=validated_data['gallery'])
        except self.Meta.model.DoesNotExist:
            return super().create(validated_data)


class TaxonomyListSerializer(TranslationSerializerMixin, BaseTaxonomySerializer):
    """
    BaseTaxonomySerializer with Translation Mixin.
    Is not necessary to serialize the permission node because only admins can write and everybody can read it.
    """

    class Meta(BaseTaxonomySerializer.Meta):
        fields = ('id', 'name', )


class TaxonomySerializer(TranslationSerializerMixin, BaseTaxonomySerializer):
    """
    Taxonomy serializer extended from BaseTaxonomySerializer.
    It defines a read only field to list tree children.
    """
    ancestors = TaxonomyListSerializer(read_only=True, many=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=DAMTaxonomy.objects.all(), required=False, allow_null=True)
    children = serializers.ListSerializer(child=RecursiveField(), read_only=True)
    extra_info = serializers.SerializerMethodField(read_only=True)
    permissions = PermissionField()

    class Meta(BaseTaxonomySerializer.Meta):
        fields = ('id', 'name', 'slug', 'parent', 'ancestors', 'children', 'extra_info', 'permissions', )

    def get_extra_info(self, obj):
        """
        Method to serialize extra information from self instance.
        """
        return TaxonomyExtraInfoSerializer(obj, read_only=True, context=self.context).data

    def validate_parent(self, value):
        if self.instance and value and self.instance.pk == value.pk:
            raise ValidationError(_("A Category can not be its own parent."))
        return value


class AccessLogSerializer(serializers.ModelSerializer):
    """
    AccessLog serializer.
    Register authenticated user's actions.
    Actions allowed:
        - models.AccessLog.ACTION_CHOICES: (<viewed>: 0, <download>: 1)
    """

    user = OwnerSerializer(read_only=True)
    title = serializers.CharField(source='photo.title', read_only=True)
    permissions = PermissionField()

    class Meta:
        model = AccessLog
        fields = ('photo', 'action', 'added_at', 'user', 'title', 'get_action_display', 'permissions', )

    def create(self, validated_data):
        """
        Auto assign user to logger access with authenticated user information.
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PhotoSerializer(BasePhotoSerializer):
    """
    Photo serializer.
    It is permitted to set many categories and keywords of each in the same request.
    It is defined all metadata as read only filed because it is auto-generated from image content, so it is not
    necessary to specify it on the create/update request.
    """

    image = serializers.PrimaryKeyRelatedField(queryset=PhotoChunked.objects.completed(), write_only=True)
    author = serializers.PrimaryKeyRelatedField(queryset=PhotoAuthor.objects.all(), required=False, allow_null=True)
    copyright = serializers.PrimaryKeyRelatedField(queryset=Copyright.objects.all(), required=False, allow_null=True)
    internal_usage_restriction = serializers.PrimaryKeyRelatedField(
        queryset=UsageRight.objects.all(), required=False, allow_null=True)
    external_usage_restriction = serializers.PrimaryKeyRelatedField(
        queryset=UsageRight.objects.all(), required=False, allow_null=True)
    categories = serializers.PrimaryKeyRelatedField(queryset=DAMTaxonomy.objects.active(), required=False, many=True)
    keywords = KeywordSerializer(required=False, many=True)
    names = NameSerializer(required=False)
    extra_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Photo
        fields = ('id', 'image', 'title', 'status', 'description', 'address', 'district', 'neighborhood', 'postcode',
                  'position', 'width', 'height', 'exif_date', 'camera_model', 'orientation', 'longitude', 'latitude',
                  'altitude', 'owner', 'categories', 'keywords', 'created_at', 'modified_at', 'album', 'extra_info',
                  'permissions', 'image_flickr', 'names', 'copyright', 'author', 'internal_usage_restriction',
                  'external_usage_restriction', 'identifier', 'original_file_name', 'categorize_date', 'size')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.PHOTO_TYPES_ENABLED:
            self.fields['photo_type'] = serializers.PrimaryKeyRelatedField(
                queryset=PhotoType.objects.all(), required=False, allow_null=True)
            self.Meta.fields += ('photo_type',)

    def get_thumbor_fieldsets(self):
        """
        Permit return thumborized image fields.
        This method validates permission of each request user to permit download (view) thumbor image urls
        When user creates the photo instance only serializes the thumbnail.
        """
        thumbor_fields = {'thumbnail', 'small_fit'}
        # if user who request has download permission will receive all photo sizes
        if self._has_download_permission():
            thumbor_fields |= {'small', 'medium', 'original', 'large', }
        return ((None, 'image'), thumbor_fields),

    def get_field_names(self, declared_fields, info):
        """
        Append field names with 'image_file' the original file uploaded to default backend if user who request photo
        has download permission
        """
        field_names = super().get_field_names(declared_fields, info)
        if self._has_download_permission():
            field_names.append('image_file')
        return field_names

    def validate(self, attrs):
        """
        Validate that the user who requests it, is superuser or a member of the photo or the album.
        """
        attrs = super().validate(attrs)
        # validated for admins
        if belongs_to_admin_group(self.user):
            return attrs
        # owners and membership validation
        if self.is_create_action and not attrs['album'].is_membership(self.user):
            raise PermissionDenied
        if self.is_update_action and not self.instance.is_membership(self.user):
                raise PermissionDenied
        return attrs

    def update_or_create(self, validated_data, instance=None, cleanup=True):
        """
        It creates or updates photo instances and sets them into queue to upload image in background
        """
        # get related data to set
        image = validated_data.pop('image', None)
        keywords = validated_data.pop('keywords', None)
        names = validated_data.pop('names', None)
        # create or update photo instance
        photo = super().update(instance, validated_data) if instance else super().create(validated_data)

        # will update image content, language tagged keywords and tagged names if has valid data
        if image is not None:
            up_image_to_s3.delay(photo.id, image.id)
        if keywords is not None:
            self.fields['keywords'].child.update_or_create(photo, keywords, cleanup)
        if names is not None:
            self.fields['names'].update_or_create(photo, names, cleanup)

        return photo

    def create(self, validated_data):
        return self.update_or_create(validated_data)

    def update(self, instance, validated_data):
        return self.update_or_create(validated_data, instance)

    def get_extra_info(self, obj):
        """
        Method to serialize extra information from self instance.
        """
        return PhotoExtraInfoSerializer(obj, read_only=True, context=self.context).data

    def _has_download_permission(self):
        """
        Validate if the user who requests the photo has permission to download it
        """
        return hasattr(self.instance, 'has_download_permission') and self.instance.has_download_permission(self.user)


class PhotoUpdateSerializer(PhotoSerializer):
    """
    Photo serializer.
    This serializer extends from 'PhotoSerializer' to overwrite 'update_or_create' method because it is in charge of
    create/update instance and overall add nested instances for each m2m field.
    This serializer skip cleanup m2m relations, so always adds items to each.
    """

    def update_or_create(self, validated_data, instance=None, cleanup=False):
        """
        The m2m affected fields are: categories, keywords and names, but the last two are manipulated in the super.
        The most important change is the 'cleanup' attribute value, now False by default.
        """
        categories = validated_data.pop('categories', None)
        photo = super().update_or_create(validated_data, instance, cleanup)
        if categories is not None:
            photo.categories.add(*categories)
        return photo


class PhotoSearchSerializer(HaystackSerializerMixin, PhotoSerializer):
    """
    Photo serializer for searches
    """


class PhotoChunkedSerializer(ChunkedUploadSerializer):
    """
    Photo chunk serializer to upload big photos in parts.
    """
    file = serializers.FileField()
    permissions = PermissionField()
    md5 = serializers.CharField(max_length=32, required=False)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    def get_url(self, obj):
        return reverse('photo-upload-chunk', kwargs={'pk': obj.id}, request=self.context['request'])

    class Meta(ChunkedUploadSerializer.Meta):
        model = PhotoChunked
        exclude = ()


# Flickr serializer


class PhotoFlickrSerializer(ReadOnlyFieldMixin, PhotoSerializer):
    """
    Photo flickr serializer.
    Is defined a set of methods to validate photo imports from flickr into an album.
    It requires a valid photo identifier <<flickr>> and an existent album <<pk>> that the user who request the
    importation can write into.
    Now it also required an <<author>> and <<copyright>>
    """

    class Meta(PhotoSerializer.Meta):
        read_only_fields = tuple(PhotoSerializer.Meta.fields)

    def __init__(self, *args, **kwargs):
        """
        Initialization service client to connect with flickr's api
        """
        super().__init__(*args, **kwargs)
        self.flickr = Flickr(settings.FLICKR_API_KEY, settings.FLICKR_SECRET_KEY)
        self.kwargs = getattr(self.context.get('view', None), 'kwargs', {})
        self.request = self.context['request']

    def validate(self, attrs):
        return attrs

    def validate_kwargs(self, raise_exception=False):
        """
        Uri params Validation.
        Is required an existent album with the user requester is an owner of it. Also it validate flickr returns
        information about the photo identifier.
        """
        pk, flickr = self.kwargs['pk'], self.kwargs['flickr']
        author_id, copyright_id = self.kwargs['author'], self.kwargs['copyright']
        errors = {}

        if not hasattr(self, '_validated_data'):
            self._validated_data = {}

        # try to get the requested user's album if not belongs to admin group
        albums = Album.objects.active()
        if not (belongs_to_admin_group(self.user) or is_staff_or_superuser(self.user)):
            albums.filter(owners=self.request.user)
        album = albums.filter(pk=pk).first()

        if not album:
            errors.update({'pk': _("Album '{}' does not exist".format(pk))})
        self._validated_data['album'] = album

        # api flickr request to try to get the requested photo id
        photo = self.flickr.get_photo(flickr, safe=raise_exception)
        if not photo:
            errors.update({'flickr': _("Photo '{}' does not exist".format(flickr))})
        self._validated_data['photo'] = photo

        # confirm the author exists
        author = PhotoAuthor.objects.filter(id=author_id).first()
        if not author:
            errors.update({'author': _("Author '{}' does not exist".format(author_id))})
        self._validated_data['author'] = author

        # confirm the copyright exists
        photo_copyright = Copyright.objects.filter(id=copyright_id).first()
        if not photo_copyright:
            errors.update({'copyright': _("Copyright '{}' does not exist".format(photo_copyright))})
        self._validated_data['copyright'] = photo_copyright

        # raise the first error message
        if errors and raise_exception:
            raise ValidationError(errors)

        return errors

    def is_valid(self, raise_exception=False):
        """
        Global Validation: uri params and data validation.
        """
        is_valid = super().is_valid(raise_exception)
        errors = self.validate_kwargs(raise_exception)
        return is_valid and not bool(errors)

    @transaction.atomic()
    def create(self, validated_data):
        """
        Create a photo with flickr information
        """
        return self.flickr.create_photo(
            self.request.user, validated_data['album'], validated_data['photo'],
            validated_data['author'], validated_data['copyright']
        )
