import importlib.util,json,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'backend'
sys.path.insert(0,str(ROOT))
import profile_policy
class StageTests(unittest.TestCase):
    def setUp(self):
        frappe=types.ModuleType('frappe');frappe.whitelist=lambda **kw:lambda fn:fn
        with patch.dict(sys.modules,{'frappe':frappe,'onemotion':types.ModuleType('onemotion'),'onemotion.api':types.ModuleType('onemotion.api'),'onemotion.api.profile_policy':profile_policy}):
            spec=importlib.util.spec_from_file_location('stages',ROOT/'profile_stages.py');self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.values={'email':'person@example.com','mobile':'+447700900123','birth_nationality':'British','birth_country':'United Kingdom','passport_issuing_country':'United Kingdom','mothers_first_name':'Jane','mothers_maiden_name':'Smith','_portal_dbs_required':True}
        self.available={f[0] for _,fs in profile_policy.SECTIONS for f in fs}
    def state(self,doc):return self.module.stage_state(doc,self.values,profile_policy.schema(self.values,self.available))
    def test_contact_first_and_not_in_personal(self):
        stages=self.state({})['stages']
        self.assertEqual([s['id'] for s in stages],['contact','driving_licence','passport','personal','address','national_insurance'])
        self.assertEqual([f['key'] for f in stages[0]['fields']],['email','mobile'])
        self.assertNotIn('mobile',[f['key'] for s in stages if s['id']=='personal' for f in s['fields']])
    def test_optional_stages(self):
        self.values.update(portal_no_passport=1,_portal_dbs_required=False)
        ids=[s['id'] for s in self.state({})['stages']]
        self.assertEqual(ids[:4],['contact','driving_licence','passport','birth_certificate'])
        self.assertNotIn('background_screening',ids);self.assertEqual(ids[0],'contact')
    def test_resume_saved_stage_and_invalidate_changed_route(self):
        self.values.update(portal_no_passport=1,portal_no_driving_licence=1)
        stages=self.state({})['stages']
        doc={'portal_onboarding_progress':json.dumps({s['id']:self.module.signature(s,self.values) for s in stages if s['id'] in {'contact','passport','driving_licence'}})}
        self.assertEqual(self.state(doc)['current_stage'],'birth_certificate')
        self.values['portal_no_passport']=0
        self.assertEqual(self.state(doc)['current_stage'],'passport')
    def test_data_alone_does_not_count_as_submitted(self):
        self.values.update(portal_no_passport=1,portal_no_driving_licence=1)
        result=self.state({})
        self.assertTrue(result['stages'][0]['complete'])
        self.assertFalse(result['stages'][0]['submitted'])
        self.assertFalse(result['all_stages_submitted'])

    def test_no_licence_stage_can_submit_without_files_and_invalidates_on_reopen(self):
        self.values.update(role='',portal_no_driving_licence=1)
        stage=next(s for s in self.state({})['stages'] if s['id']=='driving_licence')
        self.assertTrue(stage['complete'])
        saved={'portal_onboarding_progress':json.dumps({'driving_licence':self.module.signature(stage,self.values)})}
        self.assertTrue(next(s for s in self.state(saved)['stages'] if s['id']=='driving_licence')['submitted'])
        self.values['portal_no_driving_licence']=0
        self.assertFalse(next(s for s in self.state(saved)['stages'] if s['id']=='driving_licence')['submitted'])

    def test_personal_requires_saved_profile_photo(self):
        self.values.update(first_name='Example',last_name='Person',dob='1990-01-01',birthpassport_gender='Male',birth_country='United Kingdom',birth_city='Example Town',preferred_language='English',portal_birthplace_status='Matched',portal_birthplace_country='United Kingdom',id_photo='')
        stage=next(s for s in self.state({})['stages'] if s['id']=='personal')
        self.assertEqual(stage['errors'],{'id_photo':'Required'})
        self.assertFalse(stage['complete'])
        self.values['id_photo']='/private/files/test-headshot.jpg'
        stage=next(s for s in self.state({})['stages'] if s['id']=='personal')
        self.assertTrue(stage['complete'])


    def test_background_screening_replaces_old_fields(self):
        for required in (True,False):
            self.values['_portal_dbs_required']=required
            stage=next(x for x in self.state({})['stages'] if x['id']=='national_insurance')
            self.assertEqual(stage['title'],'Background Screening')
            self.assertEqual([f['key'] for f in stage['fields']],['portal_has_recent_dbs'])
            self.assertFalse(stage['complete'])
            self.assertEqual(self.state({})['stages'][0]['id'],'contact')

    def test_dbs_branches(self):
        for recent,code,reference,complete in [('No','','',True),('Yes','','',False),('Yes','No','',True),('Yes','Yes','',False),('Yes','Yes','REF',True)]:
            self.values.update(portal_has_dbs_certificate='No',portal_has_recent_dbs=recent,portal_has_dbs_share_code=code,portal_dbs_share_code='TEST',portal_dbs_reference=reference)
            stage=next(x for x in self.state({})['stages'] if x['id']=='national_insurance')
            self.assertEqual(stage['complete'],complete)

    def test_certificate_question_only_after_no_share_code(self):
        self.values.update(portal_has_recent_dbs='Yes',portal_has_dbs_share_code='No')
        stage=lambda:next(x for x in self.state({})['stages'] if x['id']=='national_insurance')
        self.assertIn('portal_has_dbs_certificate',[f['key'] for f in stage()['fields']])
        self.assertFalse(stage()['complete'])
        for answer in ('Yes','No'):
            self.values['portal_has_dbs_certificate']=answer
            self.assertEqual(stage()['complete'],answer=='No')
        self.values['portal_has_dbs_certificate']='Yes'
        self.values['portal_dbs_certificate_file']='/private/files/test-certificate.pdf'
        self.assertTrue(stage()['complete'])
        self.values['portal_has_dbs_share_code']='Yes'
        self.assertNotIn('portal_has_dbs_certificate',[f['key'] for f in stage()['fields']])

    def test_amazon_route_only_requires_mothers_names(self):
        self.values.update(_portal_dbs_amazon_site=True,portal_has_recent_dbs='Yes',portal_has_dbs_share_code='Yes',portal_has_dbs_certificate='Yes')
        stage=lambda:next(x for x in self.state({})['stages'] if x['id']=='national_insurance')
        self.assertEqual([f['key'] for f in stage()['fields']],['mothers_first_name','mothers_maiden_name'])
        self.assertTrue(stage()['complete'])
        self.values['mothers_first_name']=''
        self.assertFalse(stage()['complete'])
