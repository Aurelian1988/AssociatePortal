import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from profile_licence_expiry import rear_expiry
from profile_document_ocr import extract_fields
class LicenceExpiryTests(unittest.TestCase):
    def data(self,second='27.12.53'):
        words=[('9.',100,20),('10.',250,20),('12.',550,20),('22.04.02',250,70),('27.12.53',400,70),('22.04.02',250,110),(second,400,110)]
        return dict(text=[w[0] for w in words],left=[w[1]-10 for w in words],top=[w[2] for w in words],width=[20]*len(words),height=[20]*len(words),conf=[90]*len(words))
    def test_expiry_column_excludes_issue_dates(self):
        self.assertEqual(rear_expiry(self.data(),800,500,date(2026,11,4)),'2053-12-27')
    def test_different_categories_need_manual_review(self):
        self.assertIsNone(rear_expiry(self.data('27.12.30'),800,500,date(2026,11,4)))
    def test_missing_headers_do_not_guess(self):
        d=self.data();d['text'][1]='unknown'
        self.assertIsNone(rear_expiry(d,800,500))
    def test_front_and_rear_dates_never_cross_fields(self):
        text='4b. 20.03.2031\nEntitlement expiry: 27.12.2053'
        front=extract_fields(text,'licence_front');back=extract_fields(text,'licence_back')
        self.assertEqual(front['dl_photocard_expiry'],'2031-03-20')
        self.assertNotIn('dl_expiry_date',front)
        self.assertEqual(back['dl_expiry_date'],'2053-12-27')
        self.assertNotIn('dl_photocard_expiry',back)
