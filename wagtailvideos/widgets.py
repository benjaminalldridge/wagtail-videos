"""Wagtail chooser widgets and their serialised dominant-colour state."""

import json

from django import forms
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
    """Return the correct swatch palette shape consumed by the JS side.

    The model encodes harmonies beside each source colour, then the client renders
    those rows, so this function transposes that storage shape into one list per row.
    """
    # Limit old or manually edited JSON to the three positions the UI supports.
    # We ignore invalid entries so a partial/historic value can't break editing
    colours = [
        colour
        for colour in (video.dominant_colours or [])[:3]
        if isinstance(colour, dict)
    ]
    harmonies = {name: [] for name in ("analogous", "complement", "triad")}

    for colour in colours:
        # Old palette payloads may predate harmony support or be manually edited
        colour_harmonies = colour.get("harmonies", {})
        if not isinstance(colour_harmonies, dict):
            continue

        for name in harmonies:
            harmony = colour_harmonies.get(name)
            if isinstance(harmony, dict):
                harmonies[name].append(harmony)

    # Transpose per-source harmonies into the row-oriented shape used by widgets
    return {
        "sampled": colours,
        "harmonies": harmonies,
    }


class AdminVideoChooser(BaseChooser):
    """A video chooser that carries preview as well as persisted palette data."""

    choose_one_text = _('Choose a video')
    template_name = "wagtailvideos/widgets/video_chooser.html"
    chooser_modal_url_name = "wagtailvideos_chooser:choose"
    icon = "media"
    classname = "image-chooser"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = get_video_model()

    def get_value_data_from_instance(self, instance):
        """Add video-specific preview and swatch palette values to the chooser state."""
        data = super().get_value_data_from_instance(instance)
        # We need to use generated thumbnail because it is the logical extraction source
        data["preview"] = {
            "url": instance.thumbnail.url if instance.thumbnail else "",
            "width": 165,
            "height": 165,
        }
        # Carry persisted colour values through both ordinary fields and StreamField state
        data["dominant_colours"] = get_chooser_colour_data(instance)
        return data

    def get_context(self, name, value_data, attrs):
        """Return empty swatch palette rows when the chooser has no selected video."""
        context = super().get_context(name, value_data, attrs)
        # Preserve the base chooser's context while adding video-specific state onto it
        context["preview"] = value_data.get("preview", {})
        # If we haven't run an extraction, the context must remain safe
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
        return context

    def render_js_init(self, id_, name, value_data):
        """Build out the video-specific chooser subclass for legacy widgets."""
        # Wagtail expects a JavaScript source here, not a callable Python object
        return "new VideoChooser({0});".format(json.dumps(id_))

    @property
    def media(self):
        """Load the image chooser base class before the video extension."""
        # `VideoChooser` subclasses Wagtail's image chooser in the browser
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
