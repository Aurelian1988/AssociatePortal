import {nameFields,normaliseName,validName} from './profileNames.js'
const present = value => value !== null && value !== undefined && String(value).trim() !== ''
const yes = value => ['1','yes','true'].includes(String(value).trim().toLowerCase())
export const noDrivingLicence = values => yes(values.portal_no_driving_licence)
export const licenceRequired = values => !noDrivingLicence(values)
const dates = new Set(['dob','address_since','dl_issue_date','dl_expiry_date','dl_photocard_expiry','passport_issue_date','passport_expiry_date','idc_issuedate','idc_expriydate'])
const pastDates = new Set(['dob','address_since','dl_issue_date','passport_issue_date','idc_issuedate'])
export const isBritish = values => ['british','british citizen'].includes(String(values.birth_nationality || '').trim().toLowerCase())
export const birthCertificateRoute = values => isBritish(values) && ['united kingdom','uk','gb','gbr'].includes(String(values.birth_country || '').trim().toLowerCase()) && yes(values.portal_no_passport)
const travelExcluded=new Set('british|british citizen|english|scottish|welsh|northern irish|united kingdom|uk|gb|gbr|austrian|belgian|bulgarian|croatian|cypriot|czech|danish|estonian|finnish|french|german|greek|hungarian|irish|italian|latvian|lithuanian|luxembourger|luxembourgish|luxembourgian|maltese|dutch|polish|portuguese|romanian|slovak|slovakian|slovenian|spanish|swedish|austria|belgium|bulgaria|croatia|cyprus|czechia|czech republic|denmark|estonia|finland|france|germany|greece|hungary|ireland|italy|latvia|lithuania|luxembourg|malta|netherlands|poland|portugal|romania|slovakia|slovenia|spain|sweden'.split('|'))
export function travelDocumentAllowed(values){const n=String(values.birth_nationality||'').trim().toLowerCase();return !!n&&!travelExcluded.has(n)}
export function requiresImmigration(values) {
  if (birthCertificateRoute(values)) return false
  const passport = String(values.passport_issuing_country || '').trim().toLowerCase()
  const nationality = String(values.birth_nationality || '').trim().toLowerCase()
  if (['irish','irish citizen'].includes(nationality)) return false
  return Boolean((passport && !['united kingdom','uk','gb','gbr'].includes(passport)) || (nationality && !['british','british citizen'].includes(nationality)))
}
export function applicableSections(profile, values) {
  const identity = birthCertificateRoute(values) ? 'Birth certificate' : 'Passport'
  return (profile?.sections || []).filter(s => (!['Work Details','VAT Details','DBS','National Insurance'].includes(s.title) || profile.submitted) && (s.title!=='DBS' || profile.dbs_required) && (s.title !== 'Birth Certificate' || identity === 'Birth certificate') && (!['Right to Work','Immigration'].includes(s.title) || requiresImmigration(values))).map(section => ({
    ...section, fields: section.fields.filter(field => {
      if(field.key==='utr_number' && !profile.submitted)return false
      if(section.title==='DBS Check'){
        if(profile.dbs_amazon_site)return ['mothers_first_name','mothers_maiden_name'].includes(field.key)
        if(['mothers_first_name','mothers_maiden_name'].includes(field.key))return false
        else if(field.key!=='portal_has_recent_dbs' && values.portal_has_recent_dbs!=='Yes')return false
        if(field.key==='portal_dbs_certificate_file' && (values.portal_has_dbs_share_code!=='No'||values.portal_has_dbs_certificate!=='Yes'))return false
        if(field.key==='portal_has_dbs_certificate' && values.portal_has_dbs_share_code!=='No')return false
        if(['portal_dbs_share_code','portal_dbs_reference'].includes(field.key) && values.portal_has_dbs_share_code!=='Yes')return false
      }
      if(field.key==='portal_dbs_share_code' && section.title!=='DBS Check')return false // Retained for the future native app, outside onboarding.
      if (['vat_registered','vat_number'].includes(field.key))return !!profile.submitted
      if (section.title === 'Driving Licence' && noDrivingLicence(values)) return field.key === 'portal_no_driving_licence'
      if (field.key.startsWith('passport_') || field.key === 'passp_file') return identity === 'Passport'
      if (field.key.startsWith('idc_')) return false
      return true
    }).map(field => section.title === 'Driving Licence' ? {...field, required:licenceRequired(values) && field.key!=='portal_no_driving_licence'} : field)
  }))
}
export const normaliseVat = value => String(value || '').replace(/\s+/g, '').toUpperCase()
export function formatVat(value) { const n = normaliseVat(value); return /^GB[0-9]{9}$/.test(n) ? `GB ${n.slice(2,5)} ${n.slice(5,9)} ${n.slice(9)}` : value }
export const normaliseUtr = value => String(value || '').replace(/\s+/g, '')
export function formatUtr(value) { const n = normaliseUtr(value); return /^[0-9]{10}$/.test(n) ? `${n.slice(0,5)} ${n.slice(5)}` : value }
export const normaliseNino = value => String(value || '').replace(/\s+/g, '').toUpperCase()
export function formatNino(value) {
 const n = normaliseNino(value)
 return /^[A-Z]{2}[0-9]{6}[A-Z]$/.test(n) ? `${n.slice(0,2)} ${n.slice(2,4)} ${n.slice(4,6)} ${n.slice(6,8)} ${n.slice(8)}` : value
}
export function profileProgress(values, sections, today = new Date().toLocaleDateString('en-CA')) {
  const fields = sections.flatMap(s => s.title === 'Driving Licence' ? s.fields.filter(f => !noDrivingLicence(values) || f.key === 'portal_no_driving_licence').map(f => ({...f,required:licenceRequired(values) && f.key!=='portal_no_driving_licence'})) : s.fields)
  const errors = {}
  if(values.portal_identity_type==='Travel Document'&&!travelDocumentAllowed(values))errors.portal_identity_type='Travel documents are available only to non-EU, non-UK nationalities. Choose a passport or correct your nationality.'
  if(fields.some(f=>f.key==='portal_has_recent_dbs') && values.portal_has_recent_dbs && !['Yes','No'].includes(values.portal_has_recent_dbs))errors.portal_has_recent_dbs='Choose Yes or No.'
  const email=String(values.email||'').trim()
  if(fields.some(f=>f.key==='email') && email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))errors.email='Enter a valid email address.'
  for (const key of nameFields) if (fields.some(f => f.key === key) && values[key] && !validName(normaliseName(values[key]))) errors[key] = 'Use letters and spaces only. Hyphens are replaced with spaces.'
  if (yes(values.portal_no_passport) && !birthCertificateRoute(values)) errors.portal_no_passport = 'The birth certificate route requires British nationality and United Kingdom as birth country. Check these details or contact your team.'
  const dbsCode = String(values.portal_dbs_share_code || '')
  if (fields.some(f => f.key === 'portal_dbs_share_code') && dbsCode && (dbsCode.length > 140 || /[\x00-\x1f]/.test(dbsCode))) errors.portal_dbs_share_code = 'Paste the share code only, without extra text or line breaks.'
  if (requiresImmigration(values)) for (const key of ['portal_rtw_share_code','portal_immigration_share_code']) {
    const code = String(values[key] || '').replace(/\s+/g,'').toUpperCase()
    if (code && !/^[A-Z0-9]{9}$/.test(code)) errors[key] = 'Enter nine letters and digits. Spaces are removed automatically.'
    else if (code && key === 'portal_rtw_share_code' && !code.startsWith('W')) errors[key] = 'Use a right-to-work code beginning with W.'
  }
  const vat = normaliseVat(values.vat_number)
  if (fields.some(f=>f.key==='vat_number') && vat && !/^GB[0-9]{9}$/.test(vat)) errors.vat_number = 'Start with GB followed by exactly nine digits, for example GB 123 4567 89. Do not include punctuation.'
  const utr = normaliseUtr(values.utr_number)
  if (fields.some(f=>f.key==='utr_number') && utr && !/^[0-9]{10}$/.test(utr)) errors.utr_number = 'Enter exactly 10 digits, for example 12345 67890. Do not include letters or punctuation.'
  const nino = normaliseNino(values.nino_number)
  if (nino && !/^[A-Z]{2}[0-9]{6}[A-Z]$/.test(nino)) errors.nino_number = 'Use two letters, six digits and one final letter, for example QQ 12 34 56 A'
  for (const field of fields) {
    const value = values[field.key]
    if (field.required && !present(value)) errors[field.key] = 'Required'
    else if (present(value) && dates.has(field.key)) {
      const text = String(value).slice(0,10)
      const parsed = new Date(text + 'T00:00:00Z')
      if (!/^\d{4}-\d{2}-\d{2}$/.test(text) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0,10) !== text) errors[field.key] = 'Enter a valid date'
      else if (['dl_expiry_date','dl_photocard_expiry'].includes(field.key) && text < today) errors[field.key] = 'Your licence has expired. Are you sure this date is correct?'
      else if (field.key === 'passport_expiry_date' && text < today && (values.portal_identity_type==='Travel Document' || !['united kingdom','uk','gb','gbr'].includes(String(values.passport_issuing_country || '').trim().toLowerCase()))) errors[field.key] = 'Your passport has expired. Use a current passport.'
      else if (['dl_issue_date','passport_issue_date'].includes(field.key) && text >= today) errors[field.key] = 'Issue date must be before today'
      else if (field.key === 'address_since' && text >= today) errors[field.key] = 'Enter the date you moved in—it must be before today'
      else if (pastDates.has(field.key) && text > today) errors[field.key] = 'Cannot be in the future'
    }
  }
  for (const [start,end] of [['dl_issue_date','dl_expiry_date'],['passport_issue_date','passport_expiry_date'],['idc_issuedate','idc_expriydate']]) {
    if (fields.some(f => f.key === end) && present(values[start]) && present(values[end]) && !errors[start] && !errors[end] && String(values[end]).slice(0,10) < String(values[start]).slice(0,10)) errors[end] = 'Must be on or after the issue date'
  }
  if(fields.some(f=>f.key==='birth_city') && present(values.birth_city) && (!['Matched','Review'].includes(values.portal_birthplace_status) || values.portal_birthplace_country!==values.birth_country))errors.birth_city='Choose a birthplace from the list, or enter it manually for review.'
  const required = fields.filter(f => f.required)
  const completed = required.filter(f => present(values[f.key]) && !errors[f.key]).length
  const total = required.length
  return { completed,total,percentage: total ? Math.floor(completed * 100 / total) : fields.length ? 100 : 0,errors,complete: fields.length > 0 && completed === total && !Object.keys(errors).length }
}

export function licenceType(country) {
  const value=String(country || '').trim().toLowerCase()
  if(!value)return ''
  if(['united kingdom','northern ireland','uk','gb','gbr'].includes(value))return 'Full UK'
  return 'Austria|Belgium|Bulgaria|Croatia|Cyprus|Czechia|Czech Republic|Denmark|Estonia|Finland|France|Germany|Greece|Hungary|Ireland|Italy|Latvia|Lithuania|Luxembourg|Malta|Netherlands|Poland|Portugal|Romania|Slovakia|Slovenia|Spain|Sweden'.toLowerCase().split('|').includes(value)?'EU':'International'
}
