import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

class ContactMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe=types.ModuleType('frappe');frappe.whitelist=lambda **kw:lambda fn:fn
        utils=types.ModuleType('frappe.utils');utils.now_datetime=lambda:None
        with patch.dict(sys.modules,{'frappe':frappe,'frappe.utils':utils}):
            spec=importlib.util.spec_from_file_location('contact_start',Path(__file__).resolve().parents[1]/'backend/profile_contact_start.py')
            cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)

    def test_new_contact_creates_no_implicit_match(self):
        self.assertIsNone(self.module.decide_match([],[]))
    def test_same_person_multiple_cda_rows(self):
        self.assertEqual(self.module.decide_match(['A','A'],['A','A']),'A')
    def test_email_match_can_add_unused_phone(self):
        self.assertEqual(self.module.decide_match(['A'],[]),'A')
    def test_phone_only_cannot_claim_account(self):
        with self.assertRaises(ValueError):self.module.decide_match([],['A'])
    def test_conflicting_people_never_merge(self):
        with self.assertRaises(ValueError):self.module.decide_match(['A'],['B'])
    def test_duplicate_emails_or_phones_stop(self):
        for emails,phones in [(['A','B'],[]),(['A'],['A','B'])]:
            with self.assertRaises(ValueError):self.module.decide_match(emails,phones)
    def test_existing_link_never_reassigned(self):
        with self.assertRaises(ValueError):self.module.decide_match(['B'],[],'A')
    def test_link_retries_use_same_record(self):
        self.assertEqual(self.module.decide_match(['A'],['A'],'A'),'A')
    def test_historical_and_emergency_email_cannot_claim_account(self):
        class Doc(dict):pass
        for row in [dict(cda_email='a@example.com',cda_type='Emergency',cda_verified='2026-01-01'),dict(cda_email='a@example.com',cda_type='Personal',audit_status='Old',cda_verified='2026-01-01'),dict(cda_email='a@example.com',cda_type='Personal')]:
            self.assertFalse(self.module.trusted_email_owner(Doc(contact_details_archive=[row]),'a@example.com'))
    def test_verified_personal_email_can_match(self):
        self.assertTrue(self.module.trusted_email_owner(dict(contact_details_archive=[dict(cda_email='a@example.com',cda_type='Personal',cda_verified='2026-01-01')]),'a@example.com'))

if __name__=='__main__':unittest.main()
