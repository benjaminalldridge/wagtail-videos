"""Admin widgets owned by the example Wagtail site.

The dominant-colour package exposes palette values for a chosen video. This
widget owns the separate page-level choice that an editor saves and renders.
"""

from django import forms


class PageBackgroundColourWidget(forms.TextInput):
    """Render the saved page colour input with selectable video palette values."""

    template_name = "app/widgets/page_background_colour.html"

    class Media:
        css = {"all": ["wagtailvideos/css/page-background-colour.css"]}
        js = ["wagtailvideos/js/page-background-colour.js"]
