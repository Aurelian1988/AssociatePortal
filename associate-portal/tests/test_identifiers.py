import importlib.util, sys, types, unittest
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]/'backend'
class IdentifierTests(unittest.TestCase):
    def setUp(self):
        self.frappe=types.ModuleType('frappe');self.frappe.db=Mock()
        import profile_policy
        modules={'frappe':self.frappe,'onemotion':types.ModuleType('onemotion'),'onemotion.api':types.ModuleType('onemotion.api'),'onemotion.api.profile_policy':profile_policy}
        self.patch=patch.dict(sys.modules,modules);self.patch.start();self.addCleanup(self.patch.stop)
        spec=importlib.util.spec_from_file_location('identifier_test_module',ROOT/'profile_identifiers.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
    def test_normalisation_duplicate_and_self_exclusion(self):
        self.frappe.db.sql.return_value=[('other',)]
        errors=self.module.identifier_errors({'nino_number':'qq 12 34 56 a','utr_number':'12345 67890','vat_number':'gb 123 4567 89'},'self')
        self.assertEqual(set(errors),{'nino_number','utr_number','vat_number'})
        params=[call.args[1] for call in self.frappe.db.sql.call_args_list]
        self.assertEqual(params,[('QQ123456A','self'),('1234567890','self'),('GB123456789','self')])
        for message in errors.values(): self.assertNotIn('other',message.replace('another',''))
    def test_empty_optional_fields_do_not_query_or_conflict(self):
        self.assertEqual(self.module.identifier_errors({'nino_number':' ','utr_number':'','vat_number':None}),{})
        self.frappe.db.sql.assert_not_called()
    def test_bad_formats_rejected_before_database(self):
        errors=self.module.identifier_errors({'nino_number':'123','utr_number':'12345678901','vat_number':'123456789'})
        self.assertEqual(len(errors),3);self.frappe.db.sql.assert_not_called()
