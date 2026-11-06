"""Bounded local readability check for a DBS certificate attachment."""
import base64,subprocess,tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageOps
try:
    from .profile_document_quality import readable_text_for_review
except ImportError:
    from profile_document_quality import readable_text_for_review

def read_certificate(encoded):
    if not isinstance(encoded,str) or len(encoded)>14_000_000:raise ValueError('Choose a PDF under 10 MB or a JPEG/PNG under 6 MB.')
    header,body=encoded.split(',',1)
    if header not in ('data:application/pdf;base64','data:image/jpeg;base64','data:image/png;base64'):raise ValueError('Choose a PDF, JPEG or PNG certificate.')
    content=base64.b64decode(body,validate=True)
    if header=='data:application/pdf;base64':
        if not content.startswith(b'%PDF-') or len(content)>10_000_000:raise ValueError('Choose a valid PDF under 10 MB.')
        with tempfile.TemporaryDirectory(prefix='portal-dbs-') as temp:
            p=Path(temp);(p/'certificate.pdf').write_bytes(content)
            subprocess.run(['pdftoppm','-f','1','-l','1','-scale-to','2400','-png',str(p/'certificate.pdf'),str(p/'page')],check=True,capture_output=True,timeout=40)
            pages=list(p.glob('page-*.png'))
            if not pages:raise ValueError('The certificate has no readable page.')
            with Image.open(pages[0]) as image:readable_text_for_review(image)
        return content,'pdf'
    if len(content)>6_000_000:raise ValueError('Choose a photo under 6 MB.')
    with Image.open(BytesIO(content)) as image:
        if image.width*image.height>40_000_000:raise ValueError('This photo is too large.')
        image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((3200,3200));readable_text_for_review(image)
        out=BytesIO();image.save(out,'JPEG',quality=94)
    return out.getvalue(),'jpg'
