"""Wagtail chooser widgets and their serialised dominant-colour state."""

import json

from django import forms
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.staticfiles import versioned_static
from wagtail.admin.widgets import BaseChooser, BaseChooserAdapter

try:
    from wagtail.admin.telepath import register
except ImportError:
    from wagtail.telepath import register

from wagtailvideos import get_video_model


def get_chooser_colour_data(video):
    """Return the compact palette shape consumed by chooser JavaScript.

    The model stores harmonies beside each source colour. The client renders
    rows, so this function transposes that storage shape into one list per row.
    """
    colours = list(video.dominant_colours or [])[:3]

    return {
        "sampled": colours,
        "harmonies": {
            "analogous": [colour["harmonies"]["analogous"] for colour in colours],
            "complement": [colour["harmonies"]["complement"] for colour in colours],
            "triad": [colour["harmonies"]["triad"] for colour in colours],
        },
    }

class AdminVideoChooser(BaseChooser):
    """A video chooser that carries preview and persisted palette data."""

    choose_one_text = _('Choose a video')
    template_name = "wagtailvideos/widgets/video_chooser.html"
    chooser_modal_url_name = "wagtailvideos_chooser:choose"
    icon = "media"
    classname = "image-chooser"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = get_video_model()

    def get_value_data_from_instance(self, instance):
        """Add video-specific preview and palette values to chooser state."""
        data = super().get_value_data_from_instance(instance)
        data["preview"] = {
            "url": instance.thumbnail.url if instance.thumbnail else "",
            "width": 165,
            "height": 165,
        }
        data["dominant_colours"] = get_chooser_colour_data(instance)
        data["extract_colours_url"] = reverse(
            "wagtailvideos:extract_dominant_colours_response",
            args=(instance.pk,),
        )
        return data

    def get_context(self, name, value_data, attrs):
        """Provide empty palette rows when the chooser has no selected video."""
        context = super().get_context(name, value_data, attrs)
        context["preview"] = value_data.get("preview", {})
        context["dominant_colours"] = value_data.get(
            "dominant_colours",
            {
                "sampled": [],
                "harmonies": {
                    "analogous": [],
                    "complement": [],
                    "triad": [],
                },
            },
        )
        context["extract_colours_url"] = value_data.get("extract_colours_url", "")
        return context

    def render_js_init(self, id_, name, value_data):
        """Construct the video-specific chooser subclass for legacy widgets."""
        return "new VideoChooser({0});".format(json.dumps(id_))

    @property
    def media(self):
        """Load the image chooser base class before the video extension."""
        return forms.Media(
            js=[
                versioned_static("wagtailimages/js/image-chooser-modal.js"),
                versioned_static("wagtailimages/js/image-chooser.js"),
                versioned_static("wagtailvideos/js/video-chooser.js"),
            ]
        )

class VideoChooserAdapter(BaseChooserAdapter):
    """Register the video chooser for Wagtail's Telepath StreamField runtime."""

    js_constructor = "wagtailvideos.widgets.VideoChooser"

    @cached_property
    def media(self):
        """Load the Telepath base adapter before its video subclass."""
        return forms.Media(
            js=[
                versioned_static("wagtailimages/js/image-chooser-telepath.js"),
                versioned_static("wagtailvideos/js/video-chooser-telepath.js"),
            ]
        )

register(VideoChooserAdapter(), AdminVideoChooser)
