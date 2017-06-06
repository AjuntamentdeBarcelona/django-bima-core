# -*- encoding: utf-8 -*-
from django.contrib.auth import get_user_model
import pytest

from bima_core.models import Album, Photo


class TestMixin(object):

    @staticmethod
    def validate_inactive_instance(model, pks):
        """
        Checks if the list of pks correspond to inactive instances of the model
        """
        qs = model.objects.filter(pk__in=pks, is_active=False)
        return qs.count() == len(pks)

    @staticmethod
    def validate_inactive_nested_instance(model, pks, nested_field):
        qs = model.objects.filter(pk__in=pks, is_active=False)
        nested = getattr(model, nested_field).field.model.objects.filter(album__in=qs)
        return nested.count() == nested.filter(is_active=False).count()

    @staticmethod
    def validate_deleted_instance(model, pks):
        return not model.objects.filter(pk__in=pks).exists()

    @staticmethod
    def validate_deleted_nested_instance(model, pks, nested_field):
        qs = model.objects.filter(pk__in=pks, is_active=False)
        return not getattr(model, nested_field).field.model.objects.filter(album__in=qs).exists()


@pytest.mark.django_db
@pytest.mark.unit_test
class TestUser(TestMixin):

    def test_soft_delete_user(self, user_instance):
        """
        Soft delete user
        """
        pk = user_instance.id
        user_instance.delete()
        assert self.validate_inactive_instance(get_user_model(), [pk, ])

    def test_soft_delete_user_set(self, user_set):
        """
        Soft delete a set of users
        """
        pks = [user.id for user in user_set]
        get_user_model().objects.filter(pk__in=pks).soft_delete()
        assert self.validate_inactive_instance(get_user_model(), set(pks))

    def test_permanently_delete_user(self, user_instance):
        """
        Delete a user permanently
        """
        pk = user_instance.id
        user_instance.delete(force=True)
        assert self.validate_deleted_instance(get_user_model(), [pk, ])

    def test_permanently_delete_user_set(self, user_set):
        """
        Delete a set of users permanently
        """
        pks = [user.id for user in user_set]
        get_user_model().objects.filter(pk__in=pks).delete()
        assert self.validate_deleted_instance(get_user_model(), set(pks))


@pytest.mark.django_db
@pytest.mark.unit_test
class TestAlbum(TestMixin):

    def test_soft_delete_album(self, photo_instance):
        """
        Soft delete an album
        """
        album_instance = photo_instance.album
        pk = album_instance.id
        album_instance.delete()
        assert self.validate_inactive_instance(Album, [pk, ])
        assert self.validate_inactive_nested_instance(Album, [pk, ], 'photos_album')

    def test_soft_delete_album_set(self, public_photo_set, private_photo_set):
        """
        Soft delete a set of albums
        """
        pks = [photo.album_id for photo in public_photo_set]
        pks.extend([photo.album_id for photo in private_photo_set])
        Album.objects.filter(pk__in=pks).soft_delete()
        assert self.validate_inactive_instance(Album, set(pks))
        assert self.validate_inactive_nested_instance(Album, set(pks), 'photos_album')

    def test_permanently_delete_album(self, photo_instance):
        """
        Delete album permanently
        """
        album_instance = photo_instance.album
        pk = album_instance.id
        album_instance.delete(force=True)
        assert self.validate_deleted_instance(Album, [pk, ])

    def test_permanently_delete_album_set(self, public_photo_set, private_photo_set):
        """
        Delete a set of albums permanently
        """
        pks = [photo.album_id for photo in public_photo_set]
        pks.extend([photo.album_id for photo in private_photo_set])
        Album.objects.filter(pk__in=pks).delete()
        assert self.validate_deleted_instance(Album, set(pks))
        assert self.validate_inactive_nested_instance(Album, set(pks), 'photos_album')


@pytest.mark.django_db
@pytest.mark.unit_test
class TestPhoto(TestMixin):

    def test_soft_delete_photo(self, photo_instance):
        """
        Soft delete a photo
        """
        pk = photo_instance.id
        photo_instance.delete()
        assert self.validate_inactive_instance(Photo, [pk, ])

    def test_soft_delete_photo_set(self, public_photo_set):
        """
        Soft delete a photo set
        """
        pks = [photo.id for photo in public_photo_set]
        Photo.objects.filter(pk__in=pks).soft_delete()
        assert self.validate_inactive_instance(Photo, set(pks))

    def test_permanently_delete_photo(self, photo_instance):
        """
        Delete photo permanently
        """
        pk = photo_instance.id
        photo_instance.delete(force=True)
        assert self.validate_deleted_instance(Photo, [pk, ])

    def test_permanently_delete_photo_set(self, public_photo_set):
        """
        Delete a photo set permanently
        """
        pks = [photo.id for photo in public_photo_set]
        Photo.objects.filter(pk__in=pks).delete()
        assert self.validate_deleted_instance(Photo, set(pks))
