from unittest import TestCase

from PIL import Image

from wagtailvideos.colours import extract_from_image


class DominantColourExtractionTests(TestCase):
    def test_harmonies_are_full_colour_records(self):
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
