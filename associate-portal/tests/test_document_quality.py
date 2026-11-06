import sys, types, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from profile_document_quality import check_sharpness, readable_text

class QualityTests(unittest.TestCase):
    def document(self):
        image=Image.new('RGB',(1000,1400),'white'); draw=ImageDraw.Draw(image)
        for y in range(150,1250,30): draw.text((170,y),'Document evidence surname address date 1234567890 '*3,fill='black')
        return image
    def test_sharp_text_accepted_blurred_blank_small_rejected(self):
        image=self.document();check_sharpness(image)
        for bad in [image.filter(ImageFilter.GaussianBlur(7)), Image.new('RGB',(1000,1400),'white'),image.resize((200,280))]:
            with self.assertRaises(ValueError):check_sharpness(bad)
    def test_ocr_confidence_required(self):
        words=['Document','surname','address','London','statement','November','2026']
        data={'text':words,'conf':['90']*7,**{k:[1]*7 for k in ('page_num','block_num','par_num','line_num')}}
        fake=types.SimpleNamespace(Output=types.SimpleNamespace(DICT='dict'),image_to_data=lambda *a,**kw:data)
        with patch.dict(sys.modules,{'pytesseract':fake}):
            self.assertIn('London',readable_text(self.document()))
            data['conf']=['15']*7
            with self.assertRaises(ValueError):readable_text(self.document())
    def test_ocr_failure_is_not_accepted(self):
        fake=types.SimpleNamespace(Output=types.SimpleNamespace(DICT='dict'),image_to_data=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('Unavailable')))
        with patch.dict(sys.modules,{'pytesseract':fake}):
            with self.assertRaises(RuntimeError):readable_text(self.document())

    def test_manual_fallback_requires_a_clear_photo(self):
        from profile_document_quality import readable_text_for_review,OCRConfidenceError
        with patch('profile_document_quality.readable_text',side_effect=OCRConfidenceError('Low confidence')):
            self.assertEqual(readable_text_for_review(self.document()),'')
            with self.assertRaises(ValueError):readable_text_for_review(Image.new('RGB',(1000,1400),'white'))
