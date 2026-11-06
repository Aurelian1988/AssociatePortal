import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'backend'))
from profile_policy import schema, completion, SECTIONS

class ProfilePolicyTests(unittest.TestCase):
    def setUp(self):
        self.available = {x[0] for _, fs in SECTIONS for x in fs} | {'site','contract_type','awr_status'}
        self.values = {k:'Example' for k in self.available}
        for key in self.values:
            if key in {'dob','address_since','dl_issue_date','dl_expiry_date','dl_photocard_expiry','passport_issue_date','passport_expiry_date','idc_issuedate','idc_expriydate'}: self.values[key]='2020-01-01'
        self.values.update(portal_has_recent_dbs='No',email='test@example.com',portal_birthplace_status='Matched',portal_birthplace_country='Example',role='DA', dl_expiry_date='2053-12-27', dl_photocard_expiry='2035-01-01', portal_identity_type='Passport', passport_issuing_country='United Kingdom', birth_nationality='British', portal_rtw_share_code='W12345678', portal_immigration_share_code='S12345678', vat_registered=0, vat_number='', nino_number='', utr_number='', contract_type='Self-employed')
    def result(self): return completion(self.values,schema(self.values,self.available))
    def test_blank_email_editable_existing_email_protected(self):
        from profile_policy import editable_field
        for value in (None,'','   '):
            self.values['email']=value
            field=next(f for g in schema(self.values,self.available) for f in g['fields'] if f['key']=='email')
            self.assertTrue(field['editable'])
            self.assertTrue(field['required'])
            self.assertEqual(field['type'],'email')
            self.assertFalse(self.result()['complete'])
        self.values['email']='person@example.com'
        self.assertFalse(editable_field('email',self.values))
        self.values['email']='invalid'
        self.assertIn('email',self.result()['errors'])

    def test_complete_has_100(self): self.assertEqual(self.result()['percentage'],100)
    def test_optional_and_staff_fields_excluded(self):
        for key in ['middle_name','mobile2','state_region','site','contract_type','awr_status']: self.values[key]=''
        self.assertTrue(self.result()['complete'])
    def test_missing_licence_blocks(self):
        self.values['dl_number']='  '
        self.assertFalse(self.result()['complete']); self.assertLess(self.result()['percentage'],100)
    def test_false_checkbox_is_complete(self): self.assertNotIn('vat_registered',self.result()['errors'])
    def test_vat_number_optional_even_if_registered(self):
        self.values['vat_registered']=1
        self.assertNotIn('vat_number',self.result()['errors'])
    def test_employed_excludes_utr(self):
        self.values.update(contract_type='PAYE',utr_number='')
        self.assertTrue(self.result()['complete'])
    def test_identity_card_does_not_replace_passport(self):
        self.values['portal_identity_type']='Identity card'
        for key in list(self.values):
            if key.startswith('passport_'): self.values[key]=''
        self.assertFalse(self.result()['complete'])
        self.values['idc_number']=''
        self.assertFalse(self.result()['complete'])
    def test_unused_identity_dates_not_validated(self):
        self.values['idc_issuedate']='2030-01-01'; self.values['idc_expriydate']='2020-01-01'
        self.assertTrue(self.result()['complete'])
    def test_invalid_date_blocks(self):
        self.values['dob']='2020-02-31'; self.assertFalse(self.result()['complete'])
    def test_future_birth_blocks(self):
        self.values['dob']='2999-01-01'; self.assertFalse(self.result()['complete'])
    def test_expiry_precedes_issue_blocks(self):
        self.values['dl_expiry_date']='2019-01-01'; self.assertFalse(self.result()['complete'])
    def test_conditional_share_codes(self):
        base = self.result()
        self.values.update(passport_issuing_country='Ireland', portal_rtw_share_code='', portal_immigration_share_code='')
        result = self.result()
        self.assertEqual(result['total'],base['total']+2)
        self.assertFalse(result['complete'])
        self.values.update(passport_issuing_country='United Kingdom', birth_nationality='Irish')
        self.assertFalse(self.result()['complete'])
        self.values.update(portal_rtw_share_code='W12 345 678', portal_immigration_share_code='S12 345 678', passport_expiry_date='2099-01-01')
        self.assertTrue(self.result()['complete'])
    def test_photo_required_and_counts(self):
        complete = self.result()
        self.values['id_photo'] = ''
        missing = self.result()
        self.assertFalse(missing['complete'])
        self.assertEqual(missing['completed'], complete['completed'] - 1)
        self.assertLess(missing['percentage'],100)
    def test_address_since_strictly_past(self):
        from datetime import date, timedelta
        for value in [date.today(), date.today()+timedelta(days=1)]:
            self.values['address_since']=value.isoformat()
            self.assertIn('address_since',self.result()['errors'])
        self.values['address_since']=(date.today()-timedelta(days=1)).isoformat()
        self.assertTrue(self.result()['complete'])
    def test_dbs_required_only_when_applicable(self):
        before=self.result()
        self.values.update(_portal_dbs_required=True,portal_dbs_share_code='',portal_has_recent_dbs='No')
        after=self.result()
        self.assertEqual(after['total'],before['total'])
        self.assertTrue(after['complete'])
        self.values['mothers_first_name']=''
        self.assertFalse(self.result()['complete'])
        self.values['mothers_first_name']='Jane'
        self.assertTrue(self.result()['complete'])
    def test_no_schema_fails_closed(self): self.assertFalse(completion({},[])['complete'])


    def test_no_licence_excludes_requirements_and_restores_on_reopen(self):
        self.values.update(dl_number='',dl_expiry_date='invalid',portal_no_driving_licence=1)
        self.assertTrue(self.result()['complete'])
        self.values['portal_no_driving_licence']=0
        self.assertIn('dl_number',self.result()['errors'])
    def test_licence_details_required_unless_explicitly_opted_out(self):
        self.values['role']='Office'
        self.values['portal_no_driving_licence']=1
        for key in list(self.values):
            if key.startswith('dl_') or key.startswith('tab_dl_'):self.values[key]=''
        self.assertTrue(self.result()['complete'])

    def test_either_licence_expiry_blocks_completion_unless_opted_out(self):
        for key in ('dl_expiry_date','dl_photocard_expiry'):
            old=self.values[key];self.values[key]='2020-01-01'
            self.assertIn('expired',self.result()['errors'][key])
            self.assertFalse(self.result()['complete'])
            self.values['portal_no_driving_licence']=1
            self.assertNotIn(key,self.result()['errors'])
            self.values['portal_no_driving_licence']=0;self.values[key]=old

    def test_expired_passport_uses_issuing_country_not_nationality(self):
        self.values.update(passport_expiry_date='2020-01-01',passport_issuing_country='United Kingdom',birth_nationality='French')
        self.assertNotIn('passport_expiry_date',self.result()['errors'])
        self.values.update(passport_issuing_country='Luxembourg',birth_nationality='British')
        self.assertIn('expired',self.result()['errors']['passport_expiry_date'])

    def test_issue_dates_must_be_strictly_in_past(self):
        from datetime import date,timedelta
        for key in ('dl_issue_date','passport_issue_date'):
            for offset in (0,1):
                self.values[key]=(date.today()+timedelta(days=offset)).isoformat()
                self.assertEqual(self.result()['errors'][key],'Issue date must be before today')
            self.values[key]=(date.today()-timedelta(days=1)).isoformat()
            self.assertNotIn(key,self.result()['errors'])
            self.values[key]='2020-01-01'


    def test_travel_document_keeps_capture_fields_and_requires_current_expiry(self):
        from profile_policy import identity_type
        self.values.update(portal_identity_type='Travel Document',passport_issuing_country='United Kingdom')
        self.assertEqual(identity_type(self.values,self.available),'Travel Document')
        keys={f['key'] for g in schema(self.values,self.available) for f in g['fields']}
        self.assertTrue({'passp_file','passport_number','passport_issue_date','passport_expiry_date'}<=keys)
        self.assertIn('passport_expiry_date',self.result()['errors'])

if __name__=='__main__': unittest.main()
