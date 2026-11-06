"""Save a private headshot against the authenticated associate only."""
import base64
import binascii
from io import BytesIO
import frappe
from PIL import Image, ImageOps, UnidentifiedImageError


def clean_photo(encoded):
    if not isinstance(encoded, str) or len(encoded) > 8_000_000:
        raise ValueError('Use a photo smaller than 6 MB.')
    header, separator, data = encoded.partition(',')
    if not separator or header not in {'data:image/jpeg;base64', 'data:image/png;base64'}:
        raise ValueError('Use a JPEG or PNG photo.')
    try:
        raw = base64.b64decode(data, validate=True)
        with Image.open(BytesIO(raw)) as image:
            if image.width * image.height > 16_000_000 or min(image.size) < 240:
                raise ValueError('Use a clear headshot at least 240 pixels wide and high.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1200, 1600))
            output = BytesIO()
            image.save(output, format='JPEG', quality=90)  # Discard EXIF/location metadata.
            return output.getvalue()
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('This photo could not be read. Please take it again.') from exc


@frappe.whitelist(methods=['POST'])
def save_profile_photo(image_base64):
    from onemotion.api.profile_onboarding import _associate, _state
    from frappe.utils.file_manager import save_file
    doc = _associate()
    try:
        content = clean_photo(image_base64)
    except ValueError as exc:
        frappe.throw(str(exc), frappe.ValidationError)
    photo = save_file('profile-headshot.jpg', content, 'Associate', doc.name,
                      is_private=1, df='id_photo')
    # The authenticated endpoint owns this field; ordinary profile edits cannot set URLs.
    frappe.db.set_value('Associate', doc.name, 'id_photo', photo.file_url)
    doc.reload()
    return _state(doc)
