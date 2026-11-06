import base64, importlib.util, sys, types, unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]/'backend'
sys.path.insert(0,str(ROOT))
import profile_document_ocr, profile_policy, profile_names, profile_document_quality, profile_document_reader
class CaptureValidationTests(unittest.TestCase):
    def setUp(self):
        frappe=types.ModuleType('frappe')
        frappe.whitelist=lambda **kw: lambda function:function
        def fail(message,*args): raise ValueError(message)
        frappe.throw=fail
        self.modules=patch.dict(sys.modules,{'frappe':frappe,'onemotion':types.ModuleType('onemotion'),'onemotion.api':types.ModuleType('onemotion.api'),'onemotion.api.profile_document_ocr':profile_document_ocr,'onemotion.api.profile_policy':profile_policy,'onemotion.api.profile_names':profile_names,'onemotion.api.profile_document_quality':profile_document_quality,'onemotion.api.profile_document_reader':profile_document_reader})
        self.modules.start();self.addCleanup(self.modules.stop)
    def load(self,name):
        spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    def test_dbs_site_marker(self):
        module=self.load('profile_dbs')
        self.assertFalse(module.needs_dbs('London AMZL-123'))
        self.assertFalse(module.needs_dbs('amzl-456'))
        self.assertTrue(module.needs_dbs('OTHER-123'))
        self.assertTrue(module.needs_dbs(''))
    def test_both_licence_photos_required(self):
        module=self.load('profile_documents')
        doc={'tab_dl_photocard_front':'/private/front.jpg'}
        with self.assertRaises(ValueError):module.enforce_document_locks(doc,{'dl_number':'new'})
        doc['tab_dl_photocard_rear']='/private/back.jpg'
        module.enforce_document_locks(doc,{'dl_number':'new'})
    def test_passport_upload_and_read_required_for_personal_fields(self):
        module=self.load('profile_documents')
        doc={'passp_file':'/private/passport.jpg'}
        with self.assertRaises(ValueError):module.enforce_document_locks(doc,{'passport_number':'123456789'})
        doc['portal_passport_scanned']=1
        module.enforce_document_locks(doc,{'passport_number':'123456789'})
    def test_photo_decoder_rejects_non_images_and_tiny_images(self):
        module=self.load('profile_photo')
        for value in ['https://another-person/photo.jpg','data:image/jpeg;base64,bm90LWFuLWltYWdl']:
            with self.assertRaises(ValueError): module.clean_photo(value)
        source=BytesIO();Image.new('RGB',(20,20)).save(source,'PNG')
        with self.assertRaises(ValueError):module.clean_photo('data:image/png;base64,'+base64.b64encode(source.getvalue()).decode())
    def test_photo_reencoded_without_metadata(self):
        module=self.load('profile_photo');source=BytesIO();image=Image.new('RGB',(300,400),'white')
        exif=image.getexif();exif[270]='Private test metadata';image.save(source,'JPEG',exif=exif)
        result=module.clean_photo('data:image/jpeg;base64,'+base64.b64encode(source.getvalue()).decode())
        with Image.open(BytesIO(result)) as clean:
            self.assertEqual(clean.size,(300,400));self.assertFalse(clean.getexif())

    def test_address_locked_until_evidence_uploaded(self):
        module=self.load('profile_documents')
        with self.assertRaises(ValueError): module.enforce_document_locks({}, {'city':'London'})
        module.enforce_document_locks({'proof_of_address_doc':'/private/evidence.jpg'}, {'city':'London'})

    def test_clear_passport_manual_review_unlocks_details(self):
        module=self.load('profile_documents')
        doc={'passp_file':'/private/passport.jpg','portal_passport_manual_review':1}
        self.assertTrue(module.document_state(doc)['passport_ready'])
        module.enforce_document_locks(doc,{'passport_number':'123456789'})
