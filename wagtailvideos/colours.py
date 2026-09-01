"""Extract and persist a colour swatch palette for a given video.

Use known colour science conversions to translate a source video's thumbnail into a 
usable set of RGB values, translations into other colour models (eg. HSV), and a list 
of hue harmonies based on different visual models (eg. Analogous or Complementary).
"""

import colorsys
from PIL import Image, UnidentifiedImageError

# Provide 3 return swatches after excluding unusable dark and light values
DEFAULT_COUNT = 3
CANDIDATE_COUNT = 24 # Ensure enough swatches for quantization
MIN_USABLE_LUMA = 0.30 # Ensure the swatch is not too dark
MAX_USABLE_LUMA = 0.95 # Ensure the watch is not too light


# Conventional HSV hue rotations, aligned with source swatch index 0, 1, and 2. 
# The coefficients used are standard Rec.709 relative-luminance values: 
# https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
HARMONY_ROTATIONS = {
    "analogous": (-30, 0, 30),
    "complement": (180, 180, 180),
    "triad": (0, 120, 240),
}

def extract(video, count=DEFAULT_COUNT):
    """Extract and return palette records from this video's thumbnail."""
    # Thumbnail extraction is the logical place for this until extended to support ffmpeg
    if not video.thumbnail:
        raise RuntimeError("The input video has no thumbnail available to sample.")

    return extract_from_file(video.thumbnail, count=count)

def prepare_image(image, sample_size=160):
    """Flatten a thumbnail into a small RGB image for quantization so we can work efficiently."""
    # Remove alpha and palette modes to ensure we have RGB values available
    image = image.convert("RGB")
    # Process as a subsampled bitmap to keep extraction working predictably on large input sizes
    image.thumbnail((sample_size, sample_size))
    return image

def _rgb_to_hex(rgb):
    """Translate RGB values into the equivalent hex (#aabbcc) format."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def _rgb_to_hsv(rgb):
    """Convert standard RGB to its HSV representation."""
    # `colorsys` demands values in 0..1 format rather than 0..255
    red, green, blue = (channel / 255 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    return {
        "h": int(round(hue * 360)) % 360, # degrees hue
        "s": int(round(saturation * 100)), # percentage saturation
        "v": int(round(value * 100)), # percentage value
    }

def _rgb_to_luma(rgb):
    """Return normalised RGB values (0..1) using Rec.709 conversion factors."""
    red, green, blue = (channel / 255 for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue

def _has_usable_luma(rgb):
    """Validate the luma against our upper and lower bounds."""
    luma = _rgb_to_luma(rgb)
    # Very dark and very light values are not useful for our purposes
    return MIN_USABLE_LUMA <= luma <= MAX_USABLE_LUMA

def _rotate_hue(rgb, degrees):
    """Rotate an input HSV Hue a given angle while preserving Saturation and Value."""
    red, green, blue = (channel / 255 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    hue_rotation = degrees / 360
    # Modulo wraps rotations crossing the red boundary back into the valid hue range
    hue = (hue + hue_rotation) % 1
    rotated = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(int(round(channel * 255)) for channel in rotated)

def _add_harmonies(colours):
    """Attach one matching harmony record to each sampled colour.

    `colours[0]` receives the first angle in every harmony tuple, etc.
    The output format matches the three columns expected by the admin template.
    """
    for index, colour in enumerate(colours):
        # Preserve our sampled RGB value so that harmony does not mutate it
        rgb = tuple(colour["rgb"])
        # Each record owns its aligned harmony values in JSON
        colour["harmonies"] = {}

        for name, rotations in HARMONY_ROTATIONS.items():
            # This indexed angle keeps every row aligned to its source tile
            rotation = rotations[index]
            colour["harmonies"][name] = _format_colour(
                _rotate_hue(rgb, rotation)
            )

    return colours


def _format_colour(rgb, percentage=None):
    """Build the known JSON shape shared by admin, chooser, and StreamField."""
    hex_value = _rgb_to_hex(rgb)
    hsv = _rgb_to_hsv(rgb)

    colour = {
        # The actual payload shape expected by the frontend
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
        # Provide a prevalence for source colours; skip derived harmonies
        colour["percentage"] = round(percentage, 4)

    return colour


def _get_candidates(image, count):
    """Return quantized RGB candidates ordered by pixel count based on luma thresholds."""
    # Quantization reduces a thumbnail to a bounded candidate set of swatches before filtering
    quantized = image.quantize(colors=max(CANDIDATE_COUNT, count * 8))
    palette = quantized.getpalette()
    colour_counts = quantized.getcolors()

    candidates = [] # The candidates are offered to the application, then validated
    for pixel_count, palette_index in colour_counts:
        # Pillow stores RGB swatch palette entries consecutively, using three values per colour
        offset = palette_index * 3
        rgb = tuple(palette[offset : offset + 3])

        # Have we got enough luma for the provided swatch? If so, persist it
        if _has_usable_luma(rgb):
            # Keep both colour and count so output can report source prevalence later
            candidates.append({
                "rgb": rgb,
                "pixel_count": pixel_count,
            })

    # Return the most represented usable values first so we can select a sane palette
    return sorted(
        candidates,
        key=lambda candidate: candidate["pixel_count"],
        reverse=True,
    )

def extract_from_file(image_file, count=DEFAULT_COUNT):
    """Open a Django storage file and extract its palette."""
    # We may require an explicit open before we can read
    image_file.open("rb")
    try:
        with Image.open(image_file) as image:
            return extract_from_image(image, count=count)
    except (OSError, UnidentifiedImageError) as error:
        # Storage and image errors need to be surfaced into the public extraction contract
        raise RuntimeError("The video thumbnail could not be read.") from error
    finally:
        # Close the file handle after we are done
        image_file.close()

def extract_from_image(image, count=DEFAULT_COUNT):
    """Extract palette records from exactly one image."""
    image = prepare_image(image)

    # Get a list of candidate swatch palettes we can operate on
    candidates = _get_candidates(image, count=count)

    if len(candidates) < count:
        # We must return no fewer than the requested number of candidates from the process
        raise RuntimeError("The thumbnail does not contain enough usable colours.")

    # Percentages use every usable candidate instead of simply capping at the requested count
    total = sum(candidate["pixel_count"] for candidate in candidates)
    colours = [
        _format_colour(
            candidate["rgb"],
            percentage=(candidate["pixel_count"] / total) * 100,
        )
        for candidate in candidates[:count]
    ]

    # Add the our harmony data in after the fact because this is dependent on the rest succeeding
    return _add_harmonies(colours)
