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
    # An optional backend can leave a video without a generated thumbnail.
    if not video.thumbnail:
        return

    try:
        # Persist the fixed three-tile palette used by every current admin surface.
        video.extract_dominant_colours(count=3)
    except RuntimeError as error:
        # Extraction is enrichment, so keep the uploaded video available on failure.
        logger.warning(
            "Could not extract dominant colours for video %s: %s",
            video.pk,
            error,
        )


def _source_file_changed(video, created):
    """Return whether this save introduces a video source needing new metadata."""
    if created:
        # New model rows have no previous source from which metadata could be reused
        return True

    # Names remain stable across Django's FieldFile wrappers during form saves
    return video._initial_file_name != video.file.name


def _thumbnail_changed(video, created):
    """Return whether this save introduces a thumbnail needing a new palette."""
    if created:
        # A supplied thumbnail on a new record is the first usable palette source
        return bool(video.thumbnail)

    # A manual thumbnail assignment must refresh palette data even when the video
    # source itself has not changed
    return video._initial_thumbnail_name != video.thumbnail.name


def video_post_save(instance, created, **kwargs):
    """Complete metadata and palette generation after a video file is saved.

    All Wagtail upload surfaces save the video model, so this receiver provides
    one lifecycle hook for ordinary, chooser, and multiple uploads. A replaced
    source file invalidates all derived values, while ordinary later saves leave
    an editor's deliberately refreshed palette untouched.
    """
    # The guarded save below emits ``post_save`` again; never restart this work.
    if hasattr(instance, "_from_signal"):
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "file" not in update_fields:
        # JSON palette saves and other narrow updates do not require metadata work.
        return

    if not instance.file:
        # A partially constructed custom video model has nothing to inspect.
        return

    backend = get_transcoder_backend()
    source_changed = _source_file_changed(instance, created)
    thumbnail_changed = _thumbnail_changed(instance, created)

    # The transcoder creates the default thumbnail. A manually supplied
    # thumbnail still works when the optional backend is not installed.
    # Mark internal saves so Django's receiver does not recurse indefinitely.
    instance._from_signal = True
    try:
        if backend.installed():
            # Generate the default thumbnail before sampling colours from it.
            backend.update_video_metadata(instance)
        elif source_changed and not thumbnail_changed:
            # An old generated thumbnail describes the replaced source, not this one
            # Clear it so neither the admin preview nor palette can use stale metadata
            instance.thumbnail = None

        # A palette from the previous source must never remain selectable
        palette_source_changed = thumbnail_changed or (
            source_changed and backend.installed()
        )
        if source_changed or palette_source_changed:
            instance.dominant_colours = []

        # The source file size is independent of optional transcoder availability.
        instance.file_size = instance.file.size
        if palette_source_changed and instance.thumbnail:
            # Sample only a thumbnail generated for the new source or deliberately
            # supplied by an editor; an unavailable thumbnail leaves the palette empty
            _extract_dominant_colours(instance)

        # Mark derived state handled before the guarded save and the edit view's
        # historical second save run the receiver again
        instance._initial_file = instance.file
        instance._initial_thumbnail = instance.thumbnail
        instance._initial_file_name = instance.file.name
        instance._initial_thumbnail_name = instance.thumbnail.name
        # Persist thumbnail metadata, source size, and any successful palette together.
        instance.save()
    finally:
        # Always clear the recursion marker, including after a backend exception.
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
