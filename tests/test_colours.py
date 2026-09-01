from unittest import TestCase

from PIL import Image

from wagtailvideos.colours import MAX_COUNT, extract_from_image


class DominantColourExtractionTests(TestCase):
    """Protect the JSON contract shared by admin, choosers, and page pickers."""

    def test_harmonies_are_full_colour_records(self):
        """Every stored harmony must support the same display formats as a source."""
        image = Image.new("RGB", (30, 10))
        pixels = image.load()
        source_colours = ((110, 129, 128), (160, 125, 105), (109, 146, 96))

        for x in range(image.width):
            for y in range(image.height):
                pixels[x, y] = source_colours[x // 10]

        colours = extract_from_image(image)

        self.assertEqual(len(colours), 3)
        for colour in colours:
            for harmony in ("analogous", "complement", "triad"):
                record = colour["harmonies"][harmony]
                self.assertIsInstance(record, dict)
                self.assertIn("hex", record)
                self.assertIn("display", record)

    def test_rejects_unsupported_colour_counts(self):
        """The public helper rejects invalid Pillow quantization sizes."""
        image = Image.new("RGB", (1, 1), (110, 129, 128))

        with self.assertRaisesRegex(ValueError, "must be between 1"):
            extract_from_image(image, count=0)

        with self.assertRaisesRegex(ValueError, "must be between 1"):
            extract_from_image(image, count=MAX_COUNT + 1)
