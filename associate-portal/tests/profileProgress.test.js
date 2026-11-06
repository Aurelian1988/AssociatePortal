import { test } from 'node:test'
import assert from 'node:assert/strict'
import { profileProgress, applicableSections, licenceType } from '../src/utils/profileProgress.js'
const sections = [{title:'Personal Details',fields:[{key:'first_name',required:true},{key:'dob',required:true}]},{title:'National Insurance',fields:[{key:'nino_number',required:false},{key:'utr_number',required:false}]},{title:'VAT Details',fields:[{key:'vat_registered',required:false},{key:'vat_number',required:false}]},{title:'Work Details',fields:[{key:'site',required:false}]}]
test('work details hidden until explicitly submitted, not at 100%',()=>{
 const profile={submitted:false,sections}
 assert.equal(applicableSections(profile,{vat_registered:0}).length,1)
 assert.equal(applicableSections({...profile,submitted:true},{vat_registered:0}).length,4)
})
test('VAT does not affect onboarding completion',()=>{
 const values={first_name:'Example',dob:'2000-01-01',vat_registered:0}
 assert.equal(profileProgress(values,applicableSections({sections},values)).percentage,100)
})
test('missing and whitespace values cannot reach 100%',()=>{
 const values={first_name:' ',dob:'2000-01-01',vat_registered:1,vat_number:''}
 const result=profileProgress(values,applicableSections({sections},values))
 assert.equal(result.complete,false);assert.equal(result.percentage,50)
})
test('invalid dates, future births and reversed dates fail',()=>{
 const s=[{fields:[{key:'dob',required:true},{key:'dl_issue_date',required:true},{key:'dl_expiry_date',required:true}]}]
 assert.equal(profileProgress({dob:'2020-02-31'},s).errors.dob,'Enter a valid date')
 assert.equal(profileProgress({dob:'2999-01-01'},s).errors.dob,'Cannot be in the future')
 assert.equal(profileProgress({dob:'2000-01-01',dl_issue_date:'2020-01-01',dl_expiry_date:'2019-01-01'},s).complete,false)
})
test('identity cards cannot replace passports',()=>{
 const profile={sections:[{title:'Identity',fields:[{key:'passport_number',required:true},{key:'idc_number',required:true}]}]}
 const values={portal_identity_type:'Identity card',idc_number:'example'}
 assert.equal(profileProgress(values,applicableSections(profile,values)).percentage,0)
})
test('profile picture is required and increases completion only once saved',()=>{
 const fields=[{fields:[{key:'first_name',required:true},{key:'id_photo',required:true}]}]
 assert.equal(profileProgress({first_name:'Example'},fields).percentage,50)
 assert.equal(profileProgress({first_name:'Example'},fields).complete,false)
 assert.equal(profileProgress({first_name:'Example',id_photo:'/private/files/headshot.jpg'},fields).percentage,100)
})
test('address since rejects today and future, accepts yesterday',()=>{
 const fields=[{fields:[{key:'address_since',required:true}]}]
 for(const value of ['2026-11-04','2026-11-05']) assert.equal(profileProgress({address_since:value},fields,'2026-11-04').complete,false)
 assert.equal(profileProgress({address_since:'2026-11-03'},fields,'2026-11-04').complete,true)
})
test('either non-UK passport or non-British birth nationality shows both code sections',()=>{
 const profile={sections:[{title:'Right to Work',fields:[{key:'portal_rtw_share_code',required:true}]},{title:'Immigration',fields:[{key:'portal_immigration_share_code',required:true}]}]}
 assert.equal(applicableSections(profile,{passport_issuing_country:'United Kingdom',birth_nationality:'British'}).length,0)
 assert.equal(applicableSections(profile,{passport_issuing_country:'Ireland',birth_nationality:'British'}).length,2)
 assert.equal(applicableSections(profile,{passport_issuing_country:'United Kingdom',birth_nationality:'Irish'}).length,2)
})
test('DBS question remains available for all sites; site controls follow-up guidance',()=>{
 const profile={dbs_required:true,sections:[{title:'DBS Check',fields:[{key:'portal_has_recent_dbs',required:true}]}]}
 const values={active_site:'AMZL-fake',_portal_dbs_required:false}
 assert.equal(applicableSections(profile,values).length,1)
 assert.equal(profileProgress(values,applicableSections(profile,values)).complete,false)
 assert.equal(applicableSections({...profile,dbs_required:false},{}).length,1)
})
test('UK-born British no-passport route requires birth certificate and hides share codes',()=>{
 const profile={sections:[{title:'Identity',fields:[{key:'passport_number',required:true}]},{title:'Birth Certificate',fields:[{key:'bc_file',required:true}]},{title:'Right to Work',fields:[{key:'portal_rtw_share_code',required:true}]},{title:'Immigration',fields:[{key:'portal_immigration_share_code',required:true}]}]}
 const values={birth_nationality:'British',birth_country:'United Kingdom',portal_no_passport:1,passport_issuing_country:'Ireland'}
 const fields=applicableSections(profile,values)
 assert.equal(fields.flatMap(s=>s.fields).length,1)
 assert.equal(profileProgress(values,fields).complete,false)
 values.bc_file='/private/files/birth-certificate.jpg'
 assert.equal(profileProgress(values,fields).complete,true)
})

test('no licence excludes fields, errors and completion requirements; reopening restores them',()=>{
 const sections=[{title:'Driving Licence',fields:[{key:'portal_no_driving_licence',required:false},{key:'dl_number',required:true},{key:'dl_expiry_date',required:true}]}]
 const values={role:'DA',portal_no_driving_licence:1,dl_expiry_date:'bad'}
 assert.deepEqual(profileProgress(values,sections).errors,{})
 assert.equal(profileProgress(values,sections).total,0)
 values.portal_no_driving_licence=0
 assert.equal(profileProgress(values,sections).errors.dl_number,'Required')
 assert.equal(profileProgress(values,sections).total,2)
})
test('licence classification follows ERP country rule including non EU European countries',()=>{
 for(const country of ['United Kingdom','Northern Ireland'])assert.equal(licenceType(country),'Full UK')
 for(const country of ['Ireland','Luxembourg','Romania'])assert.equal(licenceType(country),'EU')
 for(const country of ['Norway','Switzerland','United States'])assert.equal(licenceType(country),'International')
 assert.equal(licenceType(''),'')
})

test('either licence expiry blocks submission, today is valid and opt-out removes the block',()=>{
 const fields=[{key:'dl_expiry_date',required:true},{key:'dl_photocard_expiry',required:true}]
 for(const key of fields.map(f=>f.key)){
  const values={dl_expiry_date:'2035-01-01',dl_photocard_expiry:'2035-01-01',[key]:'2026-11-03'}
  const sections=[{title:'Driving Licence',fields}]
  assert.match(profileProgress(values,sections,'2026-11-04').errors[key],/expired/)
  values[key]='2026-11-04';assert.equal(profileProgress(values,sections,'2026-11-04').complete,true)
  values[key]='2026-11-03';values.portal_no_driving_licence=1
  assert.deepEqual(profileProgress(values,sections,'2026-11-04').errors,{})
 }
})

test('expired passport rule follows issuing country rather than nationality',()=>{
 const sections=[{title:'Identity',fields:[{key:'passport_expiry_date',required:true}]}]
 const values={passport_expiry_date:'2020-01-01',passport_issuing_country:'United Kingdom',birth_nationality:'French'}
 assert.equal(profileProgress(values,sections,'2026-11-04').complete,true)
 values.passport_issuing_country='Luxembourg';values.birth_nationality='British'
 assert.match(profileProgress(values,sections,'2026-11-04').errors.passport_expiry_date,/expired/)
})

test('passport and driving licence issue dates must precede today',()=>{
 for(const key of ['passport_issue_date','dl_issue_date']){
  const sections=[{fields:[{key,required:true}]}]
  for(const date of ['2026-11-04','2026-11-05'])assert.equal(profileProgress({[key]:date},sections,'2026-11-04').errors[key],'Issue date must be before today')
  assert.equal(profileProgress({[key]:'2026-11-03'},sections,'2026-11-04').complete,true)
 }
})

test('onboarding hides former mother-name and National Insurance panels',()=>{
 const profile={sections:[{title:'DBS',fields:[{key:'mothers_first_name',required:true}]},{title:'National Insurance',fields:[{key:'nino_number'}]},{title:'DBS Check',fields:[{key:'portal_has_recent_dbs',required:true},{key:'portal_has_dbs_share_code',required:true},{key:'portal_dbs_share_code',required:true},{key:'portal_dbs_reference',required:true}]}],dbs_required:true}
 for(const values of [{portal_has_recent_dbs:'No'},{portal_has_recent_dbs:'Yes',portal_has_dbs_share_code:'No'},{portal_has_recent_dbs:'Yes',portal_has_dbs_share_code:'Yes',portal_dbs_share_code:'TEST',portal_dbs_reference:'REF'}]){
  const sections=applicableSections(profile,values)
  assert.deepEqual(sections.map(s=>s.title),['DBS Check'])
  assert.equal(profileProgress(values,sections).complete,true)
 }
})
