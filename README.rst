wagtailvideos
=============

Based on wagtailimages. The aim was to have feature parity with images
but for html5 videos. Includes the ability to transcode videos to a
html5 compliant codec using ffmpeg and also the ability to add and manage VTT text
tracks for subtitles/captions.

Requirements
------------

-  Wagtail >= 6.3 and Django >= 4.2 (for older Wagtail versions see the tags)
-  Pillow >= 9.1.0 (installed automatically, for thumbnail and palette processing)
-  `ffmpeg <https://ffmpeg.org/>`__ (optional, for transcoding and generated thumbnails)

Installing
----------

Install using pypi

.. code:: bash

    pip install wagtailvideos

Add `wagtailvideos` to your installed apps.

.. code:: python

    INSTALLED_APPS = [
        'wagtailvideos',
    ]

Using
-----

On a page model:
~~~~~~~~~~~~~~~~

Implement as a ``ForeignKey`` relation, same as wagtailimages.

.. code:: python

    from django.db import models

    from wagtail.admin.edit_handlers import FieldPanel
    from wagtail.core.fields import RichTextField
    from wagtail.core.models import Page

    from wagtailvideos.edit_handlers import VideoChooserPanel


    class HomePage(Page):
        body = RichtextField()
        header_video = models.ForeignKey('wagtailvideos.Video',
                                         related_name='+',
                                         null=True,
                                         on_delete=models.SET_NULL)

        content_panels = Page.content_panels + [
            FieldPanel('body'),
            VideoChooserPanel('header_video'),
        ]

In a Streamfield:
~~~~~~~~~~~~~~~~~

A VideoChooserBlock is included

.. code:: python

  from wagtail.admin.edit_handlers import StreamFieldPanel
  from wagtail.core.fields import StreamField
  from wagtail.core.models import Page

  from wagtailvideos.blocks import VideoChooserBlock


  class ContentPage(Page):
    body = StreamField([
        ('video', VideoChooserBlock()),
    ])

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

In template:
~~~~~~~~~~~~

The video template tag takes one required postitional argument, a video
field. All extra attributes are added to the surrounding ``<video>``
tag. The original video and all extra transcodes are added as
``<source>`` tags.

.. code:: django

    {% load wagtailvideos_tags %}
    {% video self.header_video autoplay controls width=256 %}

Jinja2 extensions are also included.

Dominant colours:
~~~~~~~~~~~~~~~~~

Each video stores a three-colour palette in its non-editable ``dominant_colours``
field. The extractor reads the video's thumbnail, rather than decoding the video
file. It quantizes that image, discards values with relative luma below 30% or
above 95%, and persists the three most prevalent remaining colours together with
their analogous, complement, and triad values.

The upload lifecycle extracts a palette whenever it receives a new thumbnail. A
configured transcoding backend normally creates that thumbnail as part of video
metadata generation. When no backend is installed, add a thumbnail manually to
make a palette available. A missing or unsuitable thumbnail leaves the video
usable but does not create a palette.

Editors can rerun extraction from the video edit page with ``Extract colours``.
The stored values are included in the video chooser data so custom admin widgets
can expose them as colour choices. The package does not impose page or block
styling; projects decide how a selected value is stored and rendered.

How to transcode using ffmpeg:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the video collection manager from the left hand menu. In the video
editing section you can see the available transcodes and a form that can
be used to create new transcodes. It is assumed that your compiled
version of ffmpeg has the matching codec libraries required for the
transcode.


Disable transcode:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transcode can be disabled using the ``WAGTAIL_VIDEOS_DISABLE_TRANSCODE`` setting.

.. code:: django

    # settings.py
    WAGTAIL_VIDEOS_DISABLE_TRANSCODE = True

Modify maximum file size:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Maximum file size that can be uploaded is defaulted to 1GB. This can be overriden using the
``WAGTAILVIDEOS_MAX_UPLOAD_SIZE`` setting

.. code:: django

    # settings.py
    WAGTAILVIDEOS_MAX_UPLOAD_SIZE = 1024*1024*1024

Chunked uploads (optional):
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Chunked uploads are disabled by default. If enabled, uploads are split into
multiple requests and reassembled server-side. This is useful when running
behind proxies/CDNs that enforce per-request body limits (for example,
Cloudflare free plan limits).

Set ``WAGTAILVIDEOS_UPLOAD_CHUNK_SIZE`` (in bytes) to enable chunking for the
multiple-upload admin screen.

.. code:: django

    # settings.py
    # 95MB chunks to stay below 100MB per-request limits
    WAGTAILVIDEOS_UPLOAD_CHUNK_SIZE = 95 * 1024 * 1024

Modify Thumbnail extension:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The automatically generated Thumbnail extension can be modified  using the ``WAGTAIL_VIDEOS_THUMBNAIL_EXTENSION`` setting. Default value is jpg

.. code:: django

    # settings.py
    WAGTAIL_VIDEOS_THUMBNAIL_EXTENSION = 'webp'

Custom Video models:
~~~~~~~~~~~~~~~~~~~~

Same as Wagtail Images, a custom model can be used to replace the built in Video model using the
``WAGTAILVIDEOS_VIDEO_MODEL`` setting.

``dominant_colours`` is inherited from ``AbstractVideo`` and must not be added to
``admin_form_fields`` because it is derived metadata. After adding the field to an
existing custom video model by upgrading, generate and apply the migration for
the project application.

.. code:: bash

    python manage.py makemigrations videos
    python manage.py migrate

.. code:: django

    # settings.py
    WAGTAILVIDEOS_VIDEO_MODEL = 'videos.AttributedVideo'

    # app.videos.models
    from django.db import models
    from modelcluster.fields import ParentalKey
    from wagtailvideos.models import AbstractVideo, AbstractVideoTranscode

    class AttributedVideo(AbstractVideo):
        attribution = models.TextField()

        admin_form_fields = (
            'title',
            'attribution',
            'file',
            'collection',
            'thumbnail',
            'tags',
        )

    class CustomTranscode(AbstractVideoTranscode):
        video = models.ForeignKey(AttributedVideo, related_name='transcodes', on_delete=models.CASCADE)

        class Meta:
            unique_together = (
                ('video', 'media_format')
            )

    class CustomTrackListing(AbstractTrackListing):
        video = models.OneToOneField(AttributedVideo, related_name='track_listing', on_delete=models.CASCADE)

    class CustomVideoTrack(AbstractVideoTrack):
        listing = ParentalKey(CustomTrackListing, related_name='tracks', on_delete=models.CASCADE)





Future features
---------------

-  Some docs
-  Richtext embed
-  Transcoding via external service rather than ffmpeg
