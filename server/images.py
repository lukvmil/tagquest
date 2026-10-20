from io import BytesIO

from PIL import Image, ImageOps


MAX_IMAGE_DIM = 1600
IMAGE_QUALITY = 80


class InvalidImage(Exception):
    pass


def process_image(data: bytes) -> bytes:
    """Re-encodes an upload as a downscaled WebP. Metadata (EXIF, GPS) isn't carried over."""
    try:
        with Image.open(BytesIO(data)) as img:
            # phones store rotation in EXIF, so apply it before EXIF is dropped
            img = ImageOps.exif_transpose(img)
            img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))

            out = BytesIO()
            img.save(out, "WEBP", quality=IMAGE_QUALITY)
            return out.getvalue()
    except (OSError, Image.DecompressionBombError) as e:
        raise InvalidImage() from e
