import logging
import os
from contextlib import contextmanager

from django.core.files.temp import NamedTemporaryFile
from django.db import transaction
from django.db.models.signals import post_delete, post_save

from wagtailvideos import get_transcoder_backend, get_video_model


logger = logging.getLogger(__name__)


@contextmanager
def get_local_file(file):
    """
    Get a local version of the file, downloading it from the remote storage if
    required. The returned value should be used as a context manager to
    ensure any temporary files are cleaned up afterwards.
    """
    try:
        with open(file.path):
            yield file.path
    except NotImplementedError:
        _, ext = os.path.splitext(file.name)
        with NamedTemporaryFile(prefix='wagtailvideo-', suffix=ext) as tmp:
            try:
                file.open('rb')
                for chunk in file.chunks():
                    tmp.write(chunk)
            finally:
                file.close()
            tmp.flush()
            yield tmp.name


def post_delete_file_cleanup(instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    transaction.on_commit(lambda: instance.file.delete(False))
    if hasattr(instance, 'thumbnail'):
        # Delete the thumbnail for videos too
        transaction.on_commit(lambda: instance.thumbnail.delete(False))


def _extract_dominant_colours(video):
    """Populate a palette when the upload pipeline produced a usable thumbnail.

    Extraction is supplementary metadata. A thumbnail that cannot provide three
    luma-valid colours must leave the uploaded video usable, so failures are
    recorded for operators instead of being raised into the upload response.
    """
    if not video.thumbnail:
        return

    try:
        video.extract_dominant_colours(count=3)
    except RuntimeError as error:
        logger.warning(
            "Could not extract dominant colours for video %s: %s",
            video.pk,
            error,
        )


def video_post_save(instance, created, **kwargs):
    """Complete metadata and palette generation after a video file is saved.

    All Wagtail upload surfaces save the video model, so this receiver provides
    one lifecycle hook for ordinary, chooser, and multiple uploads. Palette
    extraction occurs only at creation; later model saves must not unexpectedly
    replace an editor's deliberately refreshed palette.
    """
    if hasattr(instance, "_from_signal"):
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "file" not in update_fields:
        return

    if not instance.file:
        return

    backend = get_transcoder_backend()

    # The transcoder creates the default thumbnail. A manually supplied
    # thumbnail still works when the optional backend is not installed.
    instance._from_signal = True
    try:
        if backend.installed():
            backend.update_video_metadata(instance)

        instance.file_size = instance.file.size
        if created:
            _extract_dominant_colours(instance)
        instance.save()
    finally:
        del instance._from_signal


def register_signal_handlers():
    Video = get_video_model()
    VideoTranscode = Video.get_transcode_model()
    TrackListing = Video.get_track_listing_model()
    VideoTrack = TrackListing.get_track_model()

    post_save.connect(video_post_save, sender=Video)
    post_delete.connect(post_delete_file_cleanup, sender=Video)
    post_delete.connect(post_delete_file_cleanup, sender=VideoTranscode)
    post_delete.connect(post_delete_file_cleanup, sender=VideoTrack)
