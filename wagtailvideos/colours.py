"""Use various well-known translations to get the dominant colours in an input video.

The sampled colours are persisted to storage in their various (pre-calculated) values 
rather than running the calculation on-demand repeatedly.
"""

import colorsys
from PIL import Image, UnidentifiedImageError

# Define the boundaries for our calculations, ensure we don't undersample or sample junk
DEFAULT_COUNT = 3 # Number of swatches to return
CANDIDATE_COUNT = 24 # Number of candidates to quantize against, oversample for safety
MIN_USABLE_LUMA = 0.30 # Limit minimum luma so darks don't pollute results
MAX_USABLE_LUMA = 0.95 # Limit max luma so whites don't pullute


# Conventional harmony relationships, producing a three-swatch row of results each
HARMONY_ROTATIONS = {
    "analogous": (-30, 0, 30), # Analogous is hue +/- 30 degrees
    "complement": (180, 180, 180), # Complementart is hue + 180 degrees
    "triad": (0, 120, 240), # Triad is hue + 0/120/240 degrees
}

# Do the actual processing, takes in a video object and a count of swatches to return
def extract(video, count=DEFAULT_COUNT):
    """Extract and return palette records from this video's thumbnail."""
    if not video.thumbnail:
        raise RuntimeError("This video has no thumbnail to sample.")

    return extract_from_file(video.thumbnail, count=count)

def prepare_image(image, sample_size=160):
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
    """Use RGB->Rec.709 luma conversion as it makes the most sense for video."""
    red, green, blue = (channel / 255 for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue

def _has_usable_luma(rgb):
    """Validate the luma against our upper and lower bounds."""
    luma = _rgb_to_luma(rgb)
    return MIN_USABLE_LUMA <= luma(rgb) <= MAX_USABLE_LUMA

def _rotate_hue(rgb, degrees):
    """Rotate input HSV Hue a given angle while preserving Saturation and Value."""
    red, green, blue = (channel / 255 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    hue_rotation = degrees / 360
    hue = (hue + hue_rotation) % 1 # standard modulo for this type of calculation
    rotated = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(int(round(channel * 255)) for channel in rotated)


def _format_colour(rgb, percentage=None):
    """Build the stable JSON shape shared by admin, chooser, and StreamField."""
    colour = {
        "hex": _rgb_to_hex(rgb),
        "rgb": list(rgb),
        "hsv": _rgb_to_hsv(rgb),
        "display": {
            "hex": _rgb_to_hex(rgb),
            "rgb": "RGB {0}, {1}, {2}".format(*rgb),
            "hsv": "HSV {h}deg, {s}%, {v}%".format(**_rgb_to_hsv(rgb)),
        },
    }

    # Calculate the colour harmonies ahead of time
    colour["harmonies"] = {
        name: [
            _rgb_to_hex(_rotate_hue(rgb, degrees))
            for degrees in rotations
        ]
        for name, rotations in HARMONY_ROTATIONS.items()
    }

    if percentage is not None:
        colour["percentage"] = round(percentage, 4)
    return colour


def _get_candidates(image, count):
    """Get a quantized list of candidate swatches to work with"""
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

def _load_rgb_image(image, sample_size):
    """Resize a Pillow image for palette extraction."""
    image.thumbnail((sample_size, sample_size))

    # Use copy here to ensure the handle is not dropped
    return image.convert("RGB").copy()

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
    return [
        _format_colour(
            candidate["rgb"],
            percentage=(candidate["pixel_count"] / total) * 100,
        )
        for candidate in candidates[:count]
    ]