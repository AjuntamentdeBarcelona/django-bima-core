# -*- coding: utf-8 -*-
from django.contrib.auth.models import UserManager as _UserManager
from django.contrib.contenttypes.models import ContentType
from django.db import models, router, transaction
from django.db.models import signals
from django.utils.timezone import now
from taggit.managers import _TaggableManager
from taggit.utils import require_instance_manager

from .constants import COMPLETED_UPLOAD


class ActiveManagerMixin(object):
    """
    Base manager to provide an 'active' query filter
    """

    def active(self):
        """
        Only active instances
        """
        return self.filter(is_active=True)

    def inactive(self):
        """
        Only inactive instances
        """
        return self.filter(is_active=False)

    def soft_delete(self):
        """
        Soft delete all elements of queryset. (mark as inactive and deactivation date).
        """
        # update active status of each photo
        self.update(is_active=False, deleted_at=now())


class ActiveManager(ActiveManagerMixin, models.QuerySet):
    """
    Manager to filter active instances
    """


class UserManager(ActiveManagerMixin, _UserManager):
    """
    Manager to filter active instances
    """

    def get_queryset(self):
        return ActiveManager(self.model)


class TaxonomyManager(models.Manager):
    """
    A manager that adds an "active()" method for all parent taxonomies
    """

    def active(self, *args, **kwargs):
        """
        Only parent categories that are active
        """
        return self.filter(active=True, parent__isnull=True, *args, **kwargs)


class PhotoChunkedManager(models.Manager):
    """
    A manager that adds a "completed()" method for all chunk files
    """

    def completed(self):
        """
        Only completely uploaded photos
        """
        return self.filter(status=getattr(self.model, 'COMPLETE', COMPLETED_UPLOAD))


class KeywordManager(_TaggableManager):

    def _get_tagged_keywords(self, **kwargs):
        content_type = ContentType.objects.get_for_model(self.model)
        return self.through.objects.filter(content_type=content_type, object_id=self.instance.id, **kwargs)

    def _lookup_kwargs(self, language=None):
        kwargs = self.through.lookup_kwargs(self.instance)
        if language:
            kwargs.update({'language': language})
        return kwargs

    def get_queryset(self, extra_filters=None):
        kwargs = extra_filters if extra_filters else {}
        return self._get_tagged_keywords(**kwargs)

    @require_instance_manager
    def add(self, *tags, language=None, cleanup=False):
        """
        This method has been overwritten to pass an extra argument to '_lookup_kwargs' when is just to create
        related instance
        :param tags: list of string tags
        :param language: code of language
        """
        db = router.db_for_write(self.through, instance=self.instance)

        tag_objs = self._to_tag_model_instances(tags)
        new_ids = set(t.pk for t in tag_objs)

        tags = self.through._default_manager.using(db)
        if cleanup:
            tags.filter(**self._lookup_kwargs(language)).delete()
        new_ids = new_ids - set(tags.filter(**self._lookup_kwargs()).values_list('tag_id', flat=True))

        signals.m2m_changed.send(
            sender=self.through, action="pre_add",
            instance=self.instance, reverse=False,
            model=self.through.tag_model(), pk_set=new_ids, using=db,
        )

        for tag in tag_objs:
            self.through._default_manager.using(db).get_or_create(
                tag=tag, **self._lookup_kwargs(language))

        signals.m2m_changed.send(
            sender=self.through, action="post_add",
            instance=self.instance, reverse=False,
            model=self.through.tag_model(), pk_set=new_ids, using=db,
        )


class AlbumManager(ActiveManager):
    """
    Manager to get active albums.
    """

    @transaction.atomic()
    def soft_delete(self):
        """
        Soft delete all elements of queryset. (mark as inactive).
        """
        # update active status of each photo and mark as private
        super().soft_delete()
        # soft delete related photos from albums
        self.model.photos_album.field.model.objects.filter(album__in=self).soft_delete()


class PhotoManager(ActiveManager):
    """
    Manager to get active galleries
    """

    @transaction.atomic()
    def soft_delete(self):
        """
        Soft delete all elements of queryset. (mark as inactive).
        """
        # update active status of each photo and mark as private
        super().soft_delete()
        self.update(status=self.model.PRIVATE)
        # delete photo-gallery relation (GalleryMembership)
        self.model.photo_galleries.field.model.objects.filter(photo__in=self).delete()
