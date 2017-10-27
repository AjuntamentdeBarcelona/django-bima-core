# -*- coding: utf-8 -*-

import vimeo


class VimeoAPIError(Exception):
    """Base exception for Vimeo API errors."""


def upload_video(vimeo_account, file_path, title, description='', tags=None):
    """
    Upload video file to Vimeo.
    """
    try:
        v = vimeo.VimeoClient(token=vimeo_account.ACCESS_TOKEN)
        video_uri = v.upload(file_path)
        video = v.patch(video_uri, data={
            'name': title,
            'description': description,
            'tags': tags or []  # TODO: tags format?
        })
    except Exception as e:
        raise VimeoAPIError('Error uploading video to Vimeo') from e

    if video.status_code != 200:
        raise VimeoAPIError('Vimeo error, status code: {}'.format(video.status_code))

    return {
        'uri': video_uri,
        'id': video_uri.split('/')[-1],
    }
