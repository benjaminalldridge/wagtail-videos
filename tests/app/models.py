from django.db import models
from django.core.validators import RegexValidator
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from wagtailvideos.blocks import VideoChooserBlock
from wagtailvideos.edit_handlers import VideoChooserPanel
from wagtailvideos.models import (
    AbstractTrackListing, AbstractVideo, AbstractVideoTrack,
    AbstractVideoTranscode)
from tests.app.widgets import PageBackgroundColourWidget


class CustomVideoModel(AbstractVideo):
    attribution = models.TextField(blank=True)

    admin_form_fields = (
        "title",
        "attribution",
        "file",
        "collection",
        "thumbnail",
        "tags",
    )


class CustomVideoTranscode(AbstractVideoTranscode):
    video = models.ForeignKey(
        CustomVideoModel, related_name="transcodes", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("video", "media_format")


class CustomTrackListing(AbstractTrackListing):
    video = models.OneToOneField(
        CustomVideoModel, related_name="track_listing", on_delete=models.CASCADE
    )


class CustomVideoTrack(AbstractVideoTrack):
    listing = ParentalKey(
        CustomTrackListing, related_name="tracks", on_delete=models.CASCADE
    )


class TestPage(Page):
    """Example page model showing both direct and StreamField video choices."""
    video_field = models.ForeignKey(
        CustomVideoModel,
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    video_streamfield = StreamField(
        [("video", VideoChooserBlock())], blank=True, use_json_field=True
    )

    # A page owns its applied background value. Video palettes remain derived
    # metadata, so changing a video later does not silently restyle a page.
    page_background_colour = models.CharField(
        blank=True,
        max_length=7,
        validators=[
            RegexValidator(
                r"^#[0-9a-fA-F]{6}$",
                message="Use a six-digit hexadecimal colour, for example #abc123.",
            )
        ],
    )

    content_panels = Page.content_panels + [
        VideoChooserPanel("video_field"),
        FieldPanel("video_streamfield"),
        FieldPanel("page_background_colour", widget=PageBackgroundColourWidget),
    ]
