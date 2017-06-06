# -*- coding: utf-8 -*-
from categories.base import CategoryBaseAdmin, CategoryBaseAdminForm
from categories.settings import JAVASCRIPT_URL
from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected
from django.contrib.admin.utils import model_ngettext, NestedObjects
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as _GroupAdmin, UserAdmin as _UserAdmin
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db import router
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin

from .constants import DEFAULT_GROUPS
from .models import Album, Photo, Gallery, GalleryMembership, DAMTaxonomy, AccessLog, Group, PhotoExif, PhotoChunked, \
    TaggedKeyword, Copyright, UsageRight, PhotoAuthor, TaggedName, PhotoType


def soft_delete_selected(modeladmin, request, queryset):
    """
    In charge of deactivating instances instead of deleting them
    """
    opts = modeladmin.model._meta
    using = router.db_for_write(modeladmin.model)
    count = queryset.count()

    if not count:
        return None

    # soft delete selected items
    if hasattr(queryset, 'soft_delete'):
        queryset.soft_delete()
    else:
        for obj in queryset:
            soft_delete_item = getattr(obj, 'soft_delete', None)
            if not soft_delete_item:
                modeladmin.message_user(request, _("{verbose_name_plural} has not soft delete available.".format({
                    "verbose_name_plural": opts.verbose_name_plural})), messages.SUCCESS)
                return None
            soft_delete_item()

    # soft delete nested items
    collector = NestedObjects(using=using)
    collector.collect(queryset)
    for model_base, nested_objects_collected in collector.data.items():
        if model_base == modeladmin.model or not hasattr(model_base, 'soft_delete'):
            continue

        for nested_object in nested_objects_collected:
            nested_object.soft_delete()

    # response success message
    modeladmin.message_user(request, _("Successfully soft deleted {count} {items}.".format(
        count=count, items=model_ngettext(modeladmin.opts, count))), messages.SUCCESS)
    return None


# if you want to disable 'delete_selected' for all classes, uncomment next line
# admin.site.disable_action('delete_selected')
delete_selected.short_description = _("Permanently delete selected %(verbose_name_plural)s")
soft_delete_selected.short_description = _("Soft delete selected %(verbose_name_plural)s")

# unregister groups model
admin.site.unregister(AuthGroup)


@admin.register(get_user_model())
class UserAdmin(_UserAdmin):
    """
    Overwritten user admin
    """
    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
        'date_joined',
        'is_active',
        'is_staff',
    )
    list_filter = ('is_active', 'is_staff', )
    search_fields = ('username', 'first_name', 'last_name', 'email', )
    date_hierarchy = 'date_joined'
    actions = (soft_delete_selected, )


@admin.register(Group)
class GroupAdmin(_GroupAdmin):
    """
    Overwritten group admin
    """
    actions = None

    def _has_group_permissions(self, obj):
        return getattr(obj, 'name', None) not in DEFAULT_GROUPS

    def has_delete_permission(self, request, obj=None):
        return self._has_group_permissions(obj)

    def get_readonly_fields(self, request, obj=None):
        if self._has_group_permissions(obj):
            return ()
        return 'id', 'name', 'permissions',


@admin.register(Album)
class AlbumAdmin(TabbedTranslationAdmin):
    list_display = (
        'id',
        'title',
        'slug',
        'created_at',
        'modified_at',
        'is_active',
    )
    list_filter = ('created_at', 'modified_at', 'is_active', )
    raw_id_fields = ('owners', 'cover', )
    search_fields = ('slug',)
    date_hierarchy = 'created_at'
    actions = (soft_delete_selected, )


@admin.register(PhotoExif)
class PhotoExifAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'photo',
        'width',
        'height',
        'exif_date',
        'camera_model',
        'orientation',
        'longitude',
        'latitude',
        'altitude',
    )
    readonly_fields = list_display


@admin.register(Copyright)
class CopyrightAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    list_filter = (
        'created_at',
        'modified_at',
    )
    readonly_fields = ('slug', )
    date_hierarchy = 'created_at'


@admin.register(UsageRight)
class UsageRightAdmin(TabbedTranslationAdmin):
    list_display = (
        'title',
        'slug',
    )
    list_filter = (
        'created_at',
        'modified_at',
    )
    readonly_fields = ('slug', )
    date_hierarchy = 'created_at'


@admin.register(PhotoAuthor)
class PhotoAuthorAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'slug',
    )
    readonly_fields = ('slug', )
    date_hierarchy = 'created_at'


@admin.register(PhotoType)
class PhotoTypeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
    )


class KeywordInlineAdmin(GenericTabularInline):
    model = TaggedKeyword
    raw_id_fields = ('tag', )
    extra = 1


class NameInlineAdmin(GenericTabularInline):
    model = TaggedName
    raw_id_fields = ('tag', )
    extra = 1


@admin.register(Photo)
class PhotoAdmin(TabbedTranslationAdmin):
    list_display = (
        'id',
        'title',
        'status',
        'width',
        'height',
        'size',
        'owner',
        'album',
        'created_at',
        'modified_at',
        'is_active',
    )
    list_filter = (
        'exif_date',
        'owner',
        'created_at',
        'modified_at',
        'album',
        'copyright',
        'is_active',
    )
    search_fields = ('title', 'identifier', 'original_file_name', )
    exclude = ('keywords', 'names', )
    raw_id_fields = ('album', 'owner', 'categories', 'exif', 'copyright', )
    date_hierarchy = 'created_at'
    inlines = (KeywordInlineAdmin, NameInlineAdmin, )
    actions = (soft_delete_selected, )


class GalleryMembershipInlineAdmin(admin.TabularInline):
    model = GalleryMembership
    raw_id_fields = ('photo', 'added_by')
    extra = 1


@admin.register(Gallery)
class GalleryAdmin(TabbedTranslationAdmin):
    list_display = (
        'id',
        'title',
        'slug',
        'status',
        'created_at',
        'modified_at'
    )
    list_filter = ('created_at', 'modified_at')
    raw_id_fields = ('photos', 'owners')
    search_fields = ('slug',)
    date_hierarchy = 'created_at'
    prepopulated_fields = {'slug': ('title', )}
    inlines = (GalleryMembershipInlineAdmin, )


@admin.register(DAMTaxonomy)
class DAMTaxonomyAdmin(TabbedTranslationAdmin, CategoryBaseAdmin):
    form = CategoryBaseAdminForm
    list_display = ('slug', 'name', 'active')

    class Media:
        js = (JAVASCRIPT_URL + 'genericcollections.js',)


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'photo', 'user', 'action', 'added_at')
    list_filter = ('photo', 'user', 'added_at', )


@admin.register(PhotoChunked)
class PhotoChunkedAdmin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'user', 'status', 'created_at', 'completed_at', )
    list_filter = ('created_at', 'completed_at', )
    actions = ()

    def has_add_permission(self, request):
        return False
