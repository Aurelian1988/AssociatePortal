import copy,sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from profile_document_approval import record_capture,note_edits,decide,evaluate,invalidate_changed,REQUIRED,draft_values
TODAY=date(2026,11,4)
PROFILE=dict(first_name='Alex',last_name='Smith',dob='1987-08-15')

def fixture(group):
    values=dict(PROFILE)
    if group=='address':
        values.update(street_address='10 High Street',city='London',postal_code='SW1A 2AA',country='United Kingdom')
        parts=['proof_of_address']
    elif group=='passport':
        values.update(passport_number='123456789',passport_issuing_country='United Kingdom',passport_issue_date='2020-01-01',passport_expiry_date='2030-01-01',birth_nationality='British',birth_country='United Kingdom',birthpassport_gender='Male')
        parts=['passport']
    else:
        values.update(dl_number='SMITH123456AB9CD',dl_issuing_country='United Kingdom',dl_issue_date='2020-01-01',dl_photocard_expiry='2030-01-01',dl_expiry_date='2053-12-27')
        parts=['licence_front','licence_back']
    records={}
    for part in parts:
        raw={k:values[k] for k in REQUIRED[group]}
        evidence=dict(image_readable=True,confidence_floor=90,validated_fields=list(raw),ocr_version='test',mrz_valid=True,printed_consistent=True,recipient_last_name='Smith',document_date_confident=True,one_recipient_address=True)
        reading=dict(suggestions=raw,approval_evidence=evidence,address_evidence={'document_date':'2026-05-28'})
        records=record_capture(records,part,reading,PROFILE,part,'test-digest-'+part)
    return records,values

class ApprovalTests(unittest.TestCase):
    def test_all_three_positive_paths(self):
        for group in REQUIRED:
            records,values=fixture(group)
            decision=evaluate(group,records[group],values,TODAY,True)
            self.assertEqual(decision['status'],'Approved',decision['reasons'])
    def test_corrections_remain_review_even_when_reverted(self):
        records,values=fixture('passport')
        records=note_edits(records,{'passport_number':'987654321'})
        records=note_edits(records,{'passport_number':values['passport_number']})
        self.assertEqual(evaluate('passport',records['passport'],values,TODAY,True)['status'],'Review')
        records,values=fixture('passport')
        records=note_edits(records,{},['passport_number'])
        self.assertEqual(evaluate('passport',records['passport'],values,TODAY,True)['status'],'Review')
    def test_formatting_alone_is_not_a_correction(self):
        records,values=fixture('address')
        records=note_edits(records,dict(street_address='  10 HIGH STREET  ',postal_code='sw1a2aa'))
        self.assertFalse(records['address']['manual_fields'])
        self.assertEqual(evaluate('address',records['address'],values,TODAY)['status'],'Approved')
    def test_missing_fields_confidence_and_identity_fail_closed(self):
        for mutation in ['field','confidence','profile','image','surname','date_of_birth']:
            records,values=fixture('passport');entry=records['passport'];source=entry['sources']['passport']
            if mutation=='field':source['raw_values'].pop('passport_issue_date')
            if mutation=='confidence':source['evidence']['validated_fields']=[]
            if mutation=='profile':entry['profile_before']={}
            if mutation=='image':source['content_hash']=''
            if mutation=='surname':entry['profile_before']['last_name']='Smithson'
            if mutation=='date_of_birth':entry['profile_before']['dob']='1988-08-15'
            self.assertEqual(evaluate('passport',entry,values,TODAY,True)['status'],'Review',mutation)
    def test_expiry_exception_and_issue_rules(self):
        records,values=fixture('passport');source=records['passport']['sources']['passport']
        for country,expected in [('United Kingdom','Approved'),('Luxembourg','Review')]:
            values.update(passport_expiry_date='2025-01-01',passport_issuing_country=country);source['raw_values'].update(values)
            self.assertEqual(evaluate('passport',records['passport'],values,TODAY,True)['status'],expected)
        values.update(passport_expiry_date='2030-01-01',passport_issuing_country='United Kingdom',passport_issue_date=TODAY.isoformat());source['raw_values'].update(values)
        self.assertEqual(evaluate('passport',records['passport'],values,TODAY,True)['status'],'Review')
    def test_uniqueness_and_mrz_checks_mandatory(self):
        records,values=fixture('passport')
        for uniqueness in [None,False]:self.assertEqual(evaluate('passport',records['passport'],values,TODAY,uniqueness)['status'],'Review')
        records['passport']['sources']['passport']['evidence']['mrz_valid']=False
        self.assertEqual(evaluate('passport',records['passport'],values,TODAY,True)['status'],'Review')
    def test_both_licence_dates_and_front_back_binding(self):
        for field in ['dl_photocard_expiry','dl_expiry_date','dl_number']:
            records,values=fixture('driving_licence')
            if field=='dl_number':records['driving_licence']['sources']['licence_back']['raw_values'][field]='OTHER'
            else:
                values[field]='2025-01-01'
                for source in records['driving_licence']['sources'].values():source['raw_values'][field]=values[field]
            self.assertEqual(evaluate('driving_licence',records['driving_licence'],values,TODAY)['status'],'Review')
    def test_address_date_boundaries_and_ambiguity(self):
        records,values=fixture('address');source=records['address']['sources']['proof_of_address']
        for day,expected in [('2026-05-04','Approved'),('2026-05-03','Review'),('2026-11-05','Review')]:
            source['document_date']=day
            self.assertEqual(evaluate('address',records['address'],values,TODAY)['status'],expected)
        source['document_date']='2026-05-28';source['evidence']['one_recipient_address']=False
        self.assertEqual(evaluate('address',records['address'],values,TODAY)['status'],'Review')
    def test_approval_invalidated_and_history_retained(self):
        records,values=fixture('passport');records=decide(records,'passport',values,TODAY,True)
        values['last_name']='Jones';records=invalidate_changed(records,values)
        self.assertEqual(records['passport']['status'],'Review')
        self.assertEqual(records['passport']['history'][-1]['status'],'Approved')
    def test_replacement_does_not_inherit_approval(self):
        records,values=fixture('passport');records=decide(records,'passport',values,TODAY,True)
        records=record_capture(records,'passport',{'suggestions':{}},values,'new-file','new-digest')
        self.assertEqual(records['passport']['status'],'Review');self.assertNotIn('decision',records['passport'])
        self.assertEqual(records['passport']['history'][-1]['status'],'Approved')
    def test_existing_scans_have_no_assumed_approval(self):
        self.assertEqual(evaluate('address',{},PROFILE,TODAY)['status'],'Review')

    def test_unsaved_scan_values_survive_reload_without_overwriting_saved_corrections(self):
        records,values=fixture('address')
        self.assertEqual(draft_values(records,'address')['city'],'London')
        records=note_edits(records,{'city':'Oxford','street_address':''},['city','street_address'])
        self.assertNotIn('city',draft_values(records,'address'))
        self.assertNotIn('street_address',draft_values(records,'address'))
        self.assertEqual(draft_values(records,'address')['postal_code'],'SW1A 2AA')
