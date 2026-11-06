import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from profile_names import normalise_name,valid_name,contact_name
from profile_address_evidence import extract_address_evidence,evidence_status,six_months_before
from profile_policy import schema,completion,SECTIONS,birth_certificate_route
class NamesAndAddressTests(unittest.TestCase):
    def test_name_normalisation_and_contact(self):
        self.assertEqual(normalise_name('  ANNE--MARIE   SMITH  '),'Anne Marie Smith')
        self.assertEqual(contact_name({'first_name':'  JOHN ','middle_name':' ','last_name':'DOE'}),'John Doe')
        self.assertTrue(valid_name(normalise_name('JOSÉ')))
        self.assertFalse(valid_name("O'Connor"));self.assertFalse(valid_name('Name2'))
    def test_address_acceptance_boundary_and_exact_name(self):
        today=date(2026,11,4)
        self.assertEqual(evidence_status('SMITH','Smith','2026-05-04',today),'Accepted')
        for value in ['2026-05-03','2026-11-05',None,'bad']:
            self.assertEqual(evidence_status('Smith','Smith',value,today),'Review')
        self.assertEqual(evidence_status('Smithson','Smith','2026-10-01',today),'Review')
        self.assertEqual(six_months_before(date(2026,8,31)),date(2026,2,28))
    def test_address_recipient_not_supplier_and_ambiguous_date(self):
        text='Supplier\n4 Other Road\nLondon\nSW1A 1AA\nALEX SMITH\n10 HIGH STREET\nLONDON\nSW1A 2AA\nStatement date: 01 Oct 2026'
        result=extract_address_evidence(text,'Smith',date(2026,11,4))
        self.assertEqual(result['status'],'Accepted')
        self.assertEqual(result['suggestions']['postal_code'],'SW1A 2AA')
        self.assertEqual(result['suggestions']['street_address'],'10 High Street')
        self.assertEqual(extract_address_evidence(text+'\nInvoice date: 02 Oct 2026','Smith',date(2026,11,4))['status'],'Review')
    def test_isolated_recipient_with_town_county_and_sender_beside_it(self):
        page='ALEX SMITH Supplier Limited\nDate of issue: 28/05/2026'
        recipient='Mr Alex Smith\nMeadow House\nGreen Lane\nOXFORD Oxfordshire\nOX1 1AA'
        result=extract_address_evidence(page,'Smith',date(2026,11,4),recipient_texts=[recipient])
        self.assertEqual(result['suggestions'],dict(street_address='Meadow House, Green Lane',city='Oxford',state_region='Oxfordshire',postal_code='OX1 1AA',country='United Kingdom'))
        self.assertEqual(result['document_date'],'2026-05-28')
        self.assertEqual(result['status'],'Accepted')
    def test_ambiguous_recipient_addresses_require_review(self):
        blocks=['Alex Smith\n10 High Street\nLondon\nSW1A 2AA','Alex Smith\n20 High Street\nLondon\nSW1A 1AA']
        result=extract_address_evidence('Date: 01/10/2026','Smith',date(2026,11,4),recipient_texts=blocks)
        self.assertEqual(result['suggestions'],{})
        self.assertEqual(result['status'],'Review')
    def test_no_sender_fallback_when_recipient_crop_is_unreadable(self):
        result=extract_address_evidence('Smith Trading\n10 Other Street\nLondon\nSW1A 2AA','Smith',recipient_texts=['Unclear'])
        self.assertEqual(result['suggestions'],{})
    def test_birth_certificate_route_replaces_passport_and_share_codes(self):
        values={'birth_country':'United Kingdom','birth_nationality':'British','portal_no_passport':1,'passport_issuing_country':'Ireland'}
        available={f[0] for _,fs in SECTIONS for f in fs}
        groups=schema(values,available)
        keys={f['key'] for g in groups for f in g['fields']}
        self.assertTrue(birth_certificate_route(values));self.assertIn('bc_file',keys)
        self.assertNotIn('passport_number',keys);self.assertNotIn('portal_rtw_share_code',keys)
        self.assertNotIn('portal_immigration_share_code',keys)
        values['birth_country']='Ireland'
        self.assertFalse(birth_certificate_route(values))
        self.assertIn('portal_no_passport',completion(values,schema(values,available))['errors'])
