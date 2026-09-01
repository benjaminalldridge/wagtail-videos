from django.test import TestCase

from tests.utils import create_test_video_file
from wagtailvideos.widgets import AdminVideoChooser, get_chooser_colour_data


class VideoChooserWidgetTests(TestCase):
    """Protect the chooser markup consumed by page-level colour controls."""

    def test_renders_persisted_palette_values_as_hidden_source_data(self):
        """A chooser renders sampled and harmonic values without recomputation."""
        video = AdminVideoChooser().model.objects.create(
            title="Palette video",
            file=create_test_video_file(),
        )
        video.dominant_colours = [
            {
                "hex": "#336699",
                "display": {"hex": "#336699"},
                "harmonies": {
                    "analogous": {"display": {"hex": "#339966"}},
                    "complement": {"display": {"hex": "#996633"}},
                    "triad": {"display": {"hex": "#663399"}},
                },
            }
        ]
        video.save(update_fields=["dominant_colours"])

        html = AdminVideoChooser().render("video", video, attrs={"id": "id_video"})

        self.assertIn('data-video-palette-source', html)
        self.assertIn('data-video-palette-title="Palette video"', html)
        self.assertIn('data-palette-group="Sampled"', html)
        self.assertIn('data-colour="#336699"', html)
        self.assertIn('data-palette-group="Complement"', html)
        self.assertIn('data-colour="#996633"', html)

    def test_ignores_incomplete_persisted_palette_records(self):
        """Historic JSON without harmonies must not prevent a chooser rendering."""
        video = AdminVideoChooser().model.objects.create(
            title="Legacy palette video",
            file=create_test_video_file(),
        )
        video.dominant_colours = [
            {"hex": "#336699"},
            "not a colour record",
        ]

        palette = get_chooser_colour_data(video)

        self.assertEqual(palette["sampled"], [{"hex": "#336699"}])
        self.assertEqual(
            palette["harmonies"],
            {"analogous": [], "complement": [], "triad": []},
        )
