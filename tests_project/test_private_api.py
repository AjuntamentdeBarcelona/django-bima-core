# -*- encoding: utf-8 -*-
import json
from unittest import mock

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
import pytest

from .conftest import CHUNK_SIZE, encode_multipart_data, update_multipart_headers, update_chunk_range_headers, \
    checksum_file


class TestMixin(object):

    @staticmethod
    def validate_status_response(response, status):
        return response.status_code == status

    @staticmethod
    def validate_elements_response(response, number_elements=1):
        rest_framework_settings = getattr(settings, 'REST_FRAMEWORK', {})
        if not rest_framework_settings.get('PAGE_SIZE', None):
            return number_elements == len(response.data)
        return number_elements == response.data.get('count')


@pytest.mark.django_db
@pytest.mark.integration_test
class TestUserApi(TestMixin):

    def test_who_am_i(self, client, reader_headers):
        """
        Get the profile user of the request (who is who has requested the info)
        """
        response = client.get(reverse('whoami'), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_create_user(self, client, admin_headers, user):
        """
        Admin user can create new users
        """
        response = client.post(reverse('user-list'), data=user, **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_list_user(self, client, admin_headers):
        """
        Only admin can show users
        """
        response = client.get(reverse('user-list'), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_user(self, client, admin_headers, user_instance):
        """
        Only admin can retrieve user profile
        """
        response = client.get(reverse('user-detail', args=[user_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_delete_user(self, client, admin_headers, user_instance):
        """
        Only admin can delete users
        """
        response = client.delete(reverse('user-detail', args=[user_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_create_user(self, client, reader_headers, user):
        """
        Try to create user with reader permission (only admin can do it).
        """
        response = client.post(reverse('user-list'), data=user, **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_list_user(self, client, reader_headers, user):
        """
        Try to list user with reader permission (only admin can do it).
        """
        response = client.post(reverse('user-list'), data=user, **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_detail_user(self, client, reader_headers, user_instance):
        """
        Try to retrieve user with reader permission (only admin can do it).
        """
        response = client.post(reverse('user-detail', args=[user_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_delete_user(self, client, reader_headers, user_instance):
        """
        Try to delete user with reader permission (only admin can do it).
        """
        response = client.delete(reverse('user-detail', args=[user_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 403)


@pytest.mark.django_db
@pytest.mark.integration_test
class TestAlbumApi(TestMixin):

    def test_create_album(self, client, admin_headers, album):
        """
        Admin user can create new albums
        """
        response = client.post(reverse('album-list'), data=album, **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_list_album(self, client, admin_headers):
        """
        Admin user can list albums
        """
        response = client.get(reverse('album-list'), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_list_album_as_editor(self, client, editor_headers):
        """
        Editor user can list his own albums
        """
        response = client.get(reverse('album-list'), **editor_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_album(self, client, admin_headers, album_instance):
        """
        Admin user can get an album detail
        """
        response = client.get(reverse('album-detail', args=[album_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_album_as_reader(self, client, reader_headers, album_instance):
        """
        Reader user can get an album detail which is a membership
        """
        response = client.get(reverse('album-detail', args=[album_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_delete_album(self, client, admin_headers, album_instance):
        """
        Admin user can delete albums
        """
        response = client.delete(reverse('album-detail', args=[album_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_create_album(self, client, reader_headers, album):
        """
        Try to create albums with reader permission (only admin can do it).
        """
        response = client.post(reverse('album-list'), data=album, **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_list_album(self, client, random_reader_headers):
        """
        Try to list albums with reader user who is not a membership of it (only admin can do it).
        """
        response = client.get(reverse('album-list'), **random_reader_headers)
        assert self.validate_status_response(response, 200)

    def test_no_permitted_detail_album(self, client, random_reader_headers, album_instance):
        """
        Try to get an album detail with reader user who is not a membership of it (only admin can do it).
        """
        response = client.get(reverse('album-detail', args=[album_instance.id]), **random_reader_headers)
        assert self.validate_status_response(response, 403)


@pytest.mark.django_db
@pytest.mark.integration_test
class TestPhotoApi(TestMixin):

    def test_create_photo(self, client, admin_headers, photo):
        """
        The user trying to create upload a photo into the album is admin, so he can do this.
        """
        with mock.patch('bima_core.tasks.up_image_to_s3.delay', return_value=None):
            response = client.post(reverse('photo-list'), data=photo, **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_create_extended_photo(self, client, admin_headers, extended_photo):
        """
        The user trying to create upload a photo into the album is admin, so he can do this.
        """
        with mock.patch('bima_core.tasks.up_image_to_s3.delay', return_value=None):
            response = client.post(reverse('photo-list'), data=json.dumps(extended_photo),
                                   content_type='application/json', **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_create_photo_as_photograph(self, client, photographer_headers, photo_of_photographer):
        """
        The user is trying to create a photo into the album as a photographer
        """
        with mock.patch('bima_core.tasks.up_image_to_s3.delay', return_value=None):
            response = client.post(reverse('photo-list'), data=photo_of_photographer, **photographer_headers)
        assert self.validate_status_response(response, 201)

    def test_update_photo(self, client, admin_headers, photo_instance, photo):
        """
        Is not necessary mock 'up_image_to_s3' task because the image is already in filesystem so update call
        will not queue task.
        """
        response = client.patch(reverse('photo-detail', args=[photo_instance.id]), data=photo,
                                content_type='application/x-www-form-urlencoded', **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_update_photo_as_photograph(self, client, photographer_headers, photo_instance_of_photographer,
                                        photo_of_photographer):
        """
        This test has the same behaviour of 'up_image_to_s3' than 'test_update_photo'.
        """
        response = client.patch(reverse('photo-detail', args=[photo_instance_of_photographer.id]),
                                data=photo_of_photographer, content_type='application/x-www-form-urlencoded',
                                **photographer_headers)
        assert self.validate_status_response(response, 200)

    def test_list_public_photos(self, client, reader_headers, public_photo_set):
        """
        List public photos and check number of elements
        """
        response = client.get(reverse('photo-list'), **reader_headers)
        assert self.validate_status_response(response, 200)
        assert self.validate_elements_response(response, len(public_photo_set))

    def test_list_private_photos(self, client, photographer_headers, photo_instance_of_photographer, private_photo_set):
        """
        List private photos and check number of elements
        """
        response = client.get(reverse('photo-list'), **photographer_headers)
        assert self.validate_status_response(response, 200)
        assert self.validate_elements_response(response, 1)

    def test_detail_public_photo(self, client, reader_headers, public_photo_instance):
        """
        Get detail of a public photo
        """
        response = client.get(reverse('photo-detail', args=[public_photo_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_public_extended_photo(self, client, reader_headers, public_extended_photo_instance):
        """
        Get detail of a photo that has more information
        """
        response = client.get(reverse('photo-detail', args=[public_extended_photo_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_private_photos(self, client, reader_headers, photo_instance_of_reader, private_photo_set):
        """
        Get detail of a private photo
        """
        response = client.get(reverse('photo-detail', args=[photo_instance_of_reader.id]), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_publish_photo(self, client, editor_headers, photo_instance_of_editor, publish_status):
        """
        Change photo status to public
        """
        response = client.patch(reverse('photo-detail', args=[photo_instance_of_editor.id]),
                                data={'status': publish_status}, content_type='application/x-www-form-urlencoded',
                                **editor_headers)
        assert self.validate_status_response(response, 200)

    def test_unpublish_photo(self, client, editor_headers, photo_instance_of_editor, private_status):
        """
        Change photo status to private
        """
        response = client.patch(reverse('photo-detail', args=[photo_instance_of_editor.id]),
                                data={'status': private_status}, content_type='application/x-www-form-urlencoded',
                                **editor_headers)
        assert self.validate_status_response(response, 200)

    def test_delete_photo(self, client, admin_headers, photo_instance):
        """
        Delete a photo as an admin
        """
        response = client.delete(reverse('photo-detail', args=[photo_instance.id, ]), **admin_headers)
        assert self.validate_status_response(response, 204)

    def test_delete_photo_as_editor(self, client, editor_headers, photo_instance_of_editor):
        """
        Delete photo as an editor
        """
        response = client.delete(reverse('photo-detail', args=[photo_instance_of_editor.id]), **editor_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_create_photo(self, client, editor_headers, photo):
        """
        Try to create photo as an editor with no permissions
        """
        response = client.post(reverse('photo-list'), data=photo, **editor_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_create_photo_as_reader(self, client, reader_headers, photo):
        """
        Try to create a photo as a reader with no permissions
        """
        response = client.post(reverse('photo-list'), data=photo, **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_update_photo(self, client, editor_headers, photo_instance, photo):
        """
        Try to update a photo as an editor with no permissions
        """
        response = client.patch(reverse('photo-detail', args=[photo_instance.id]), data=photo,
                                content_type='application/x-www-form-urlencoded', **editor_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_list_private_photos(self, client, photographer_headers, private_photo_set):
        """
        Try to get the list of private photos as a photographer with no permissions
        """
        response = client.get(reverse('photo-list'), **photographer_headers)
        assert self.validate_status_response(response, 200)
        assert self.validate_elements_response(response, 0)

    def test_no_permitted_detail_private_photos(self, client, photographer_headers, photo_instance_of_reader):
        """
        Try to get the details of private photos as a photographer with no permissions
        """
        response = client.get(reverse('photo-detail', args=[photo_instance_of_reader.id]), **photographer_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_delete_photo(self, client, editor_headers, photo_instance):
        """
        Try to delete a photo as an editor with no permissions
        """
        response = client.delete(reverse('photo-detail', args=[photo_instance.id, ]), **editor_headers)
        assert self.validate_status_response(response, 403)


@pytest.mark.django_db
@pytest.mark.integration_test
class TestGalleryApi(TestMixin):

    def test_create_gallery(self, client, admin_headers, gallery):
        """
        Admin user can create new gallery
        """
        response = client.post(reverse('gallery-list'), data=gallery, **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_update_gallery(self, client, admin_headers, gallery_instance, gallery):
        """
        Admin user can update galleries
        """
        response = client.patch(reverse('gallery-detail', args=[gallery_instance.id]), data=gallery,
                                content_type='application/x-www-form-urlencoded', **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_list_galleries(self, client, reader_headers):
        """
        Reader user list galleries (anyone can do it).
        """
        response = client.get(reverse('gallery-list'), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_galleries(self, client, reader_headers, gallery_instance):
        """
        Reader user can get gallery detail (anyone can do it).
        """
        response = client.get(reverse('gallery-detail', args=[gallery_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_delete_gallery(self, client, admin_headers, gallery_instance):
        """
        Admin user can delete galleries
        """
        response = client.delete(reverse('gallery-detail', args=[gallery_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_create_gallery(self, client, photographer_headers, gallery):
        """
        Try to create gallery with photographer permission (only admin can do it).
        """
        response = client.post(reverse('gallery-list'), data=gallery, **photographer_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_update_gallery(self, client, reader_headers, gallery_instance, gallery):
        """
        Try to create albums with reader permission (only admin can do it).
        """
        response = client.patch(reverse('gallery-detail', args=[gallery_instance.id]), data=gallery,
                                content_type='application/x-www-form-urlencoded', **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_delete_gallery(self, client, reader_headers, gallery_instance):
        """
        Try to delete album with reader permission (only admin can do it).
        """
        response = client.delete(reverse('gallery-detail', args=[gallery_instance.id]), **reader_headers)
        assert self.validate_status_response(response, 403)

    # Link & unlink photos to galleries

    def test_link_photos_to_gallery(self, client, editor_headers, gallery_instance, photo_instance):
        """
        Admin user can create new gallery
        """
        data = {'gallery': gallery_instance.id, 'photo': photo_instance.id}
        response = client.post(reverse('gallery-link'), data=data, **editor_headers)
        assert self.validate_status_response(response, 201)

    def test_unlink_photos_to_gallery(self, client, editor_headers, link_instance):
        """
        Admin user can create new gallery
        """
        response = client.delete(reverse('gallery-unlink', args=[link_instance.id]), **editor_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_link_photos_to_gallery(self, client, random_editor_headers, gallery_instance, photo_instance):
        """
        Admin user can create new gallery
        """
        data = {'gallery': gallery_instance.id, 'photo': photo_instance.id}
        response = client.post(reverse('gallery-link'), data=data, **random_editor_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_unlink_photos_to_gallery(self, client, random_editor_headers, link_instance):
        """
        Admin user can create new gallery
        """
        response = client.delete(reverse('gallery-unlink', args=[link_instance.id]), **random_editor_headers)
        assert self.validate_status_response(response, 403)


@pytest.mark.django_db
@pytest.mark.integration_test
class TestTaxonomyApi(TestMixin):

    def test_create_taxonomy(self, client, admin_headers, taxonomy):
        """
        Admin user can create new taxonomy
        """
        response = client.post(reverse('damtaxonomy-list'), data=taxonomy, **admin_headers)
        assert self.validate_status_response(response, 201)

    def test_update_taxonomy(self, client, admin_headers, taxonomy_instance, taxonomy):
        """
        Admin user can update taxonomies
        """
        response = client.patch(reverse('damtaxonomy-detail', args=[taxonomy_instance.id]), data=taxonomy,
                                content_type='application/x-www-form-urlencoded', **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_list_taxonomy(self, client, admin_headers):
        """
        List taxonomies as an admin
        """
        response = client.get(reverse('damtaxonomy-list'), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_list_taxonomy_as_reader(self, client, reader_headers):
        """
        List taxonomies as a reader
        """
        response = client.get(reverse('damtaxonomy-list'), **reader_headers)
        assert self.validate_status_response(response, 200)

    def test_detail_taxonomy(self, client, admin_headers, taxonomy_instance):
        """
        See taxonomies detail as an admin
        """
        response = client.get(reverse('damtaxonomy-detail', args=[taxonomy_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 200)

    def test_delete_taxonomy(self, client, admin_headers, taxonomy_instance):
        """
        Delete taxonomies as an admin
        """
        response = client.delete(reverse('damtaxonomy-detail', args=[taxonomy_instance.id]), **admin_headers)
        assert self.validate_status_response(response, 204)

    def test_no_permitted_create_taxonomy(self, client, reader_headers, taxonomy):
        """
        Try to create a taxonomy as a reader with no permissions
        """
        response = client.post(reverse('damtaxonomy-list'), data=taxonomy, **reader_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_update_taxonomy(self, client, editor_headers, taxonomy_instance, taxonomy):
        """
        Try to update a taxonomy as an editor with no permissions
        """
        response = client.patch(reverse('damtaxonomy-detail', args=[taxonomy_instance.id]), data=taxonomy,
                                content_type='application/x-www-form-urlencoded', **editor_headers)
        assert self.validate_status_response(response, 403)

    def test_no_permitted_delete_taxonomies(self, client, editor_headers, taxonomy_instance):
        """
        Anyone can delete taxonomies, non only admin
        """
        response = client.delete(reverse('damtaxonomy-detail', args=[taxonomy_instance.id]), **editor_headers)
        assert self.validate_status_response(response, 403)


@pytest.mark.django_db
@pytest.mark.integration_test
class TestUploadChunkedApi(TestMixin):

    def test_upload_photo(self, client, admin_headers, image_file):
        # To use with requests
        # files = {"file": (image_file.name, next(image_file.chunks(CHUNK_SIZE)))}
        # requests.put(reverse('photo-upload'), data={'filename': image_file.name}, files=files)

        # initialize data
        headers = update_multipart_headers(admin_headers)
        data = {'filename': image_file.name}
        offset, url = 0, reverse('photo-upload')

        # successive requests to upload chunks file
        for chunk_file in image_file.chunks(CHUNK_SIZE):
            headers = update_chunk_range_headers(headers, offset, chunk_file, image_file)
            data.update({'file': ContentFile(chunk_file, name=image_file.name)})
            response = client.put(url, data=encode_multipart_data(data), **headers)

            assert response.status_code == 200
            assert 'id' in response.data and 'offset' in response.data
            offset = response.data.get('offset')
            url = response.data.get('url')

        # close transaction upload chunk
        response = client.post(url, data={'md5': checksum_file(image_file)}, **headers)

        assert response.status_code == 200
        assert response.data.get('status', 1) == 2
