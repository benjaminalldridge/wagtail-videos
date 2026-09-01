"""Extract and persist a thumbnail-derived palette for a video.

Each sampled colour has one source-aligned record for each harmony. The video
admin template and chooser both render one three-tile row per harmony.
"""

import colorsys
from PIL import Image, UnidentifiedImageError

# Palette policy: return three swatches after excluding unusable dark and light values.
DEFAULT_COUNT = 3
CANDIDATE_COUNT = 24
MIN_USABLE_LUMA = 0.30
MAX_USABLE_LUMA = 0.95


# Conventional HSV hue rotations, aligned with source swatch index 0, 1, and 2.
# The RGB luma coefficients below are Rec. 709 / WCAG relative-luminance values:
# https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
HARMONY_ROTATIONS = {
    "analogous": (-30, 0, 30),
    "complement": (180, 180, 180),
    "triad": (0, 120, 240),
}

def extract(video, count=DEFAULT_COUNT):
    """Extract and return palette records from this video's thumbnail."""
    if not video.thumbnail:
        raise RuntimeError("This video has no thumbnail to sample.")

    return extract_from_file(video.thumbnail, count=count)

def prepare_image(image, sample_size=160):
    """Flatten one thumbnail into a small RGB image for quantization."""
    image = image.convert("RGB")
    image.thumbnail((sample_size, sample_size))
    return image

def _rgb_to_hex(rgb):
    """Translate RGB values into the equivalent hex (#aabbcc) format."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def _rgb_to_hsv(rgb):
    """Convert standard RGB to its HSV representation."""
    red, green, blue = (channel / 255 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    return {
        "h": int(round(hue * 360)) % 360,
        "s": int(round(saturation * 100)),
        "v": int(round(value * 100)),
    }

def _rgb_to_luma(rgb):
    """Return Rec. 709 luma, using RGB channels normalised to the 0..1 range."""
    red, green, blue = (channel / 255 for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue

def _has_usable_luma(rgb):
    """Validate the luma against our upper and lower bounds."""
    luma = _rgb_to_luma(rgb)
    return MIN_USABLE_LUMA <= luma <= MAX_USABLE_LUMA

def _rotate_hue(rgb, degrees):
    """Rotate input HSV Hue a given angle while preserving Saturation and Value."""
    red, green, blue = (channel / 255 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    hue_rotation = degrees / 360
    hue = (hue + hue_rotation) % 1 # standard modulo for this type of calculation
    rotated = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(int(round(channel * 255)) for channel in rotated)

def _add_harmonies(colours):
    """Attach one matching harmony record to each sampled colour.

    ``colours[0]`` receives the first angle in every harmony tuple, and so on.
    This matches the three columns rendered by the admin template.
    """

    for index, colour in enumerate(colours):
        rgb = tuple(colour["rgb"])
        colour["harmonies"] = {}

        for name, rotations in HARMONY_ROTATIONS.items():
            rotation = rotations[index]
            colour["harmonies"][name] = _format_colour(
                _rotate_hue(rgb, rotation)
            )

    return colours


def _format_colour(rgb, percentage=None):
    """Build the stable JSON shape shared by admin, chooser, and StreamField."""
    hex_value = _rgb_to_hex(rgb)
    hsv = _rgb_to_hsv(rgb)

    colour = {
        "hex": hex_value,
        "rgb": list(rgb),
        "hsv": hsv,
        "display": {
            "hex": hex_value,
            "rgb": "RGB({0}, {1}, {2})".format(*rgb),
            "hsv": "HSV({h}, {s}, {v})".format(**hsv),
        },
    }

    if percentage is not None:
        colour["percentage"] = round(percentage, 4)

    return colour


def _get_candidates(image, count):
    """Return luma-valid quantized RGB candidates ordered by pixel count."""
    quantized = image.quantize(colors=max(CANDIDATE_COUNT, count * 8))
    palette = quantized.getpalette()
    colour_counts = quantized.getcolors()

    candidates = []
    for pixel_count, palette_index in colour_counts:
        offset = palette_index * 3
        rgb = tuple(palette[offset : offset + 3])

        if _has_usable_luma(rgb):
            candidates.append({
                "rgb": rgb,
                "pixel_count": pixel_count,
            })

    return sorted(
        candidates,
        key=lambda candidate: candidate["pixel_count"],
        reverse=True,
    )

def extract_from_file(image_file, count=DEFAULT_COUNT):
    """Open a Django storage file and extract its palette."""
    image_file.open("rb")
    try:
        with Image.open(image_file) as image:
            return extract_from_image(image, count=count)
    except (OSError, UnidentifiedImageError) as error:
        raise RuntimeError("The video thumbnail could not be read.") from error
    finally:
        image_file.close()

def extract_from_image(image, count=DEFAULT_COUNT):
    """Extract palette records from one Pillow image."""
    image = prepare_image(image)
    candidates = _get_candidates(image, count=count)

    if len(candidates) < count:
        raise RuntimeError("The thumbnail does not contain enough usable colours.")

    total = sum(candidate["pixel_count"] for candidate in candidates)
    colours = [
        _format_colour(
            candidate["rgb"],
            percentage=(candidate["pixel_count"] / total) * 100,
        )
        for candidate in candidates[:count]
    ]

    return _add_harmonies(colours)
