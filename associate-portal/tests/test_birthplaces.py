import sys,unittest,json,types,importlib.util
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'backend';sys.path.insert(0,str(ROOT))
import profile_birthplaces as places
class BirthplaceTests(unittest.TestCase):
 def test_filter_rejects_foreign_places_and_businesses_and_deduplicates(self):
  def feature(name,country='GB',kind='town',region='England'):
   return {'properties':dict(name=name,countrycode=country,osm_key='place',osm_value=kind,state=region,osm_id=1,osm_type='N')}
  features=[feature('Example'),feature('Example'),feature('Wrong country','US'),feature('Shop',kind='shop'),feature('Little village',kind='village')]
  response=types.SimpleNamespace(read=lambda n:json.dumps({'features':features}).encode())
  mock=unittest.mock.MagicMock();mock.__enter__.return_value=response
  with patch.object(places,'urlopen',return_value=mock):r=places.search_places('United Kingdom','Ex')
  self.assertEqual([p['name'] for p in r['places']],['Example','Little village'])
 def test_unicode_place_names_and_number_only_rejection(self):
  for name in ['Cluj-Napoca','Iași','6th of October','St. John’s']:self.assertTrue(places.valid_place_name(name))
  for name in ['12345','<script>','A','A\nB']:self.assertFalse(places.valid_place_name(name))
 def test_country_mapping_and_short_query(self):
  self.assertEqual(places.country_code('Romania'),'RO');self.assertEqual(places.country_code('United Kingdom'),'GB')
  self.assertEqual(places.search_places('United Kingdom','x')['places'],[])
 def module(self,cache):
  frappe=types.ModuleType('frappe');frappe.whitelist=lambda **kw:lambda fn:fn
  frappe.session=types.SimpleNamespace(user='tester');frappe.cache=lambda:types.SimpleNamespace(get_value=lambda key:cache.get(key))
  def fail(message):raise ValueError(message)
  frappe.throw=fail
  with patch.dict(sys.modules,{'frappe':frappe,'onemotion.api.profile_birthplaces':places}):
   spec=importlib.util.spec_from_file_location('birthplace_api',ROOT/'profile_birthplace_api.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module
 def test_selection_country_binding_and_manual_review(self):
  class Doc(dict):
   def set(self,k,v):self[k]=v
  api=self.module({'portal-birthplace:tester:known':dict(name='Example',country='United Kingdom',reference='osm:N:1')})
  doc=Doc(birth_country='United Kingdom');data=dict(birth_city='Example',portal_birthplace_token='known')
  api.apply_birthplace(doc,data);self.assertEqual(doc['portal_birthplace_status'],'Matched')
  with self.assertRaises(ValueError):api.apply_birthplace(doc,dict(birth_country='Romania',birth_city='Example',portal_birthplace_token='known'))
  api.apply_birthplace(doc,dict(birth_city='Old Village',portal_birthplace_manual=1))
  self.assertEqual(doc['portal_birthplace_status'],'Review');self.assertEqual(doc['portal_birthplace_manual'],1)
  incoming=dict(birth_country='Romania');api.apply_birthplace(doc,incoming)
  self.assertEqual(incoming['birth_city'],'');self.assertEqual(doc['portal_birthplace_status'],'')
