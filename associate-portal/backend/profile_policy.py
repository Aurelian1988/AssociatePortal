"""Profile requirements shared by the API, progress display and submission validation."""
from datetime import date
import re

# Work assignments, approval statuses, login email, and optional secondary details
# are not user-completion requirements.
SECTIONS = [
    ('Profile Picture', [('id_photo','Profile picture')]),
    ('Personal Details', [('first_name','First name'),('middle_name','Middle name',False),('last_name','Last name'),('dob','Date of birth'),('birthpassport_gender','Birth Gender'),('birth_country','Birth country'),('birth_city','Town/City of Birth'),('birth_nationality','Nationality'),('preferred_language','Preferred language')]),
    ('Address', [('proof_of_address_doc','Proof of address'),('street_address','Street address'),('city','City'),('state_region','County / region',False),('postal_code','Postcode'),('country','Country'),('address_since','Living at this address since')]),
    ('Contact Information', [('email','Email'),('mobile','Mobile')]),
    ('Driving Licence', [('portal_no_driving_licence','I don’t have a driving licence',False),('tab_dl_photocard_front','Licence front photo'),('tab_dl_photocard_rear','Licence back photo'),('dl_type','Licence type'),('dl_number','Licence number'),('dl_issuing_country','Issuing country'),('dl_issue_date','Issue date'),('dl_expiry_date','Licence expiry date'),('dl_photocard_expiry','Photocard expiry')]),
    ('Identity', [('passp_file','Passport photo scan'),('passport_number','Passport number'),('passport_issuing_country','Passport issuing country'),('passport_issue_date','Passport issue date'),('passport_expiry_date','Passport expiry date')]),
    ('Birth Certificate', [('bc_file','Birth certificate photo')]),
    ('Right to Work', [('portal_rtw_share_code','Right to Work share code')]),
    ('Immigration', [('portal_immigration_share_code','Immigration share code')]),
    ('DBS', [('portal_dbs_share_code','DBS share code'),('mothers_first_name',"Mother’s first name"),('mothers_maiden_name',"Mother’s maiden name")]),
    ('National Insurance', [('nino_number','National Insurance number',False),('utr_number','UTR number',False)]),
    ('DBS Check', [('portal_has_recent_dbs','Do you have a DBS check from the last 6 months?'),('mothers_first_name','Mother’s first name'),('mothers_maiden_name','Mother’s maiden name'),('portal_has_dbs_share_code','Do you have a DBS share code?'),('portal_has_dbs_certificate','Do you have a DBS certificate that you can upload?'),('portal_dbs_certificate_file','DBS certificate'),('portal_dbs_share_code','DBS share code'),('portal_dbs_reference','DBS reference number')]),
    ('VAT Details', [('vat_registered','VAT registered',False),('vat_number','VAT number',False)]),
]
READ_ONLY = {'portal_dbs_certificate_file','proof_of_address_doc','bc_file','tab_dl_photocard_front','tab_dl_photocard_rear','passp_file','id_photo', 'email', 'site', 'contract_type', 'owner_driver', 'awr_status', 'applied_date', 'activated_in_flex'}
WORK_FIELDS = [('site','Base site'),('contract_type','Contract type'),('owner_driver','Owner driver'),('awr_status','Status'),('applied_date','Applied date'),('activated_in_flex','Activated in Flex')]
DATE_FIELDS = {'dob','address_since','dl_issue_date','dl_expiry_date','dl_photocard_expiry','passport_issue_date','passport_expiry_date','idc_issuedate','idc_expriydate'}

def present(value):
    return value is not None and str(value).strip() != ''

def yes(value):
    return str(value).strip().lower() in {'1','yes','true'}

def licence_required(values):
    return not yes(values.get('portal_no_driving_licence'))

def is_british(values):
    return str(values.get('birth_nationality') or '').strip().casefold() in {'british','british citizen'}

def birth_certificate_route(values):
    country = str(values.get('birth_country') or '').strip().casefold()
    return is_british(values) and country in {'united kingdom','uk','gb','gbr'} and yes(values.get('portal_no_passport'))

def identity_type(values, available):
    if birth_certificate_route(values): return 'Birth certificate'
    return 'Travel Document' if values.get('portal_identity_type')=='Travel Document' else 'Passport'

TRAVEL_EXCLUDED=set('british|british citizen|english|scottish|welsh|northern irish|united kingdom|uk|gb|gbr|austrian|belgian|bulgarian|croatian|cypriot|czech|danish|estonian|finnish|french|german|greek|hungarian|irish|italian|latvian|lithuanian|luxembourger|luxembourgish|luxembourgian|maltese|dutch|polish|portuguese|romanian|slovak|slovakian|slovenian|spanish|swedish|austria|belgium|bulgaria|croatia|cyprus|czechia|czech republic|denmark|estonia|finland|france|germany|greece|hungary|ireland|italy|latvia|lithuania|luxembourg|malta|netherlands|poland|portugal|romania|slovakia|slovenia|spain|sweden'.split('|'))
def travel_document_allowed(values):
    nationality=str(values.get('birth_nationality') or '').strip().casefold()
    return bool(nationality) and nationality not in TRAVEL_EXCLUDED

def requires_immigration(values):
    if birth_certificate_route(values): return False
    passport = str(values.get('passport_issuing_country') or '').strip().casefold()
    nationality = str(values.get('birth_nationality') or '').strip().casefold()
    if nationality in {'irish','irish citizen'}: return False
    return bool((passport and passport not in {'united kingdom','uk','gb','gbr'}) or
                (nationality and nationality not in {'british','british citizen'}))

def editable_field(key,values):
    return key not in READ_ONLY or (key=='email' and not str(values.get('email') or '').strip())

def schema(values, available, catalog=False):
    identity = identity_type(values, available)
    employed = str(values.get('contract_type') or '').strip().lower() in {'employee','employed','employment','paye'}
    groups = []
    for title, definitions in SECTIONS:
        if not catalog and title in {'VAT Details','DBS','National Insurance'}: continue
        if not catalog and title=='DBS' and not values.get('_portal_dbs_required'): continue
        if not catalog and title == 'Birth Certificate' and identity != 'Birth certificate': continue
        if not catalog and title in {'Right to Work','Immigration'} and not requires_immigration(values): continue
        fields = []
        for item in definitions:
            key, label = item[:2]
            if key=='portal_dbs_share_code' and title!='DBS Check':continue
            if not catalog and key=='utr_number':continue
            if not catalog and title=='DBS Check' and values.get('_portal_dbs_amazon_site'):
                if key not in {'mothers_first_name','mothers_maiden_name'}:continue
            elif not catalog and title=='DBS Check':
                if key in {'mothers_first_name','mothers_maiden_name'}:continue
                elif key!='portal_has_recent_dbs' and values.get('portal_has_recent_dbs')!='Yes':continue
                if key=='portal_dbs_certificate_file' and (values.get('portal_has_dbs_share_code')!='No' or values.get('portal_has_dbs_certificate')!='Yes'):continue
                if key=='portal_has_dbs_certificate' and values.get('portal_has_dbs_share_code')!='No':continue
                if key in {'portal_dbs_share_code','portal_dbs_reference'} and values.get('portal_has_dbs_share_code')!='Yes':continue # Native app step, not onboarding.
            if key not in available:
                continue
            if not catalog and (key.startswith('passport_') or key == 'passp_file') and identity not in {'Passport','Travel Document'}: continue
            if not catalog and key.startswith('idc_') and identity != 'Identity card': continue
            required = item[2] if len(item) > 2 else True
            if title == 'Driving Licence':
                if not catalog and yes(values.get('portal_no_driving_licence')) and key != 'portal_no_driving_licence': continue
                if not licence_required(values): required = False
            fields.append(dict(key=key, label=label, required=required, editable=editable_field(key,values),
                               type='date' if key in DATE_FIELDS else 'email' if key=='email' else 'text'))
        if title=='DBS Check':
            for field in fields:
                if field['key'] in {'portal_has_recent_dbs','portal_has_dbs_share_code','portal_has_dbs_certificate'}:field.update(type='select',options=['Yes','No'])
        if fields: groups.append(dict(title=title, fields=fields))
    work = [dict(key=k,label=l,required=False,editable=False,type='text') for k,l in WORK_FIELDS if k in available]
    if work: groups.append(dict(title='Work Details',fields=work))
    return groups

def normalise_nino(value):
    return re.sub(r'\s+', '', str(value or '')).upper()

def field_errors(values, groups):
    errors = {}
    if values.get('portal_identity_type')=='Travel Document' and not travel_document_allowed(values):errors['portal_identity_type']='Travel documents are available only to non-EU, non-UK nationalities. Choose a passport or correct your nationality.'
    try:
        from onemotion.api.profile_names import NAME_FIELDS,normalise_name,valid_name
    except ModuleNotFoundError:
        from profile_names import NAME_FIELDS,normalise_name,valid_name
    visible_names={f['key'] for group in groups for f in group['fields']}
    if 'portal_has_recent_dbs' in visible_names and values.get('portal_has_recent_dbs') not in (None,'','Yes','No'):errors['portal_has_recent_dbs']='Choose Yes or No.'
    if 'portal_has_dbs_share_code' in visible_names and values.get('portal_has_dbs_share_code') not in (None,'','Yes','No'):errors['portal_has_dbs_share_code']='Choose Yes or No.'
    if 'portal_has_dbs_certificate' in visible_names and values.get('portal_has_dbs_certificate') not in (None,'','Yes','No'):errors['portal_has_dbs_certificate']='Choose Yes or No.'
    email=str(values.get('email') or '').strip()
    if 'email' in visible_names and email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):errors['email']='Enter a valid email address.'
    for key in NAME_FIELDS:
        if key in visible_names and values.get(key) and not valid_name(normalise_name(values[key])): errors[key] = 'Use letters and spaces only. Hyphens are replaced with spaces.'
    if yes(values.get('portal_no_passport')) and not birth_certificate_route(values):
        errors['portal_no_passport'] = 'The birth certificate route requires British nationality and United Kingdom as birth country. Check these details or contact your team.'
    if requires_immigration(values):
        for key in ('portal_rtw_share_code','portal_immigration_share_code'):
            code = re.sub(r'\s+', '', str(values.get(key) or '')).upper()
            if code and not re.fullmatch(r'[A-Z0-9]{9}', code): errors[key] = 'Enter nine letters and digits. Spaces are removed automatically.'
            elif code and key == 'portal_rtw_share_code' and not code.startswith('W'): errors[key] = 'Use a right-to-work code beginning with W.'
    dbs_code = str(values.get('portal_dbs_share_code') or '')
    if 'portal_dbs_share_code' in visible_names and values.get('_portal_dbs_required') and dbs_code and (len(dbs_code) > 140 or any(ord(c) < 32 for c in dbs_code)): errors['portal_dbs_share_code'] = 'Paste the share code only, without extra text or line breaks.'
    nino = normalise_nino(values.get('nino_number'))
    if nino and not re.fullmatch(r'[A-Z]{2}[0-9]{6}[A-Z]', nino):
        errors['nino_number'] = 'Use two letters, six digits and one final letter, for example QQ 12 34 56 A'

    vat = re.sub(r'\s+', '', str(values.get('vat_number') or '')).upper()
    if 'vat_number' in visible_names and vat and not re.fullmatch(r'GB[0-9]{9}', vat): errors['vat_number'] = 'Start with GB followed by exactly nine digits, for example GB 123 4567 89. Do not include punctuation.'
    utr = re.sub(r'\s+', '', str(values.get('utr_number') or ''))
    if 'utr_number' in visible_names and utr and not re.fullmatch(r'[0-9]{10}', utr): errors['utr_number'] = 'Enter exactly 10 digits'
    for group in groups:
        for field in group['fields']:
            key = field['key']; value = values.get(key)
            if group['title'] == 'Driving Licence' and yes(values.get('portal_no_driving_licence')) and key != 'portal_no_driving_licence': continue
            if field['required'] and not present(value):
                errors[key] = 'Required'
            elif present(value) and key in DATE_FIELDS:
                try:
                    parsed = date.fromisoformat(str(value)[:10])
                    if key in {'dl_expiry_date','dl_photocard_expiry'} and parsed < date.today(): errors[key] = 'Your licence has expired. Are you sure this date is correct?'
                    elif key == 'passport_expiry_date' and parsed < date.today() and (values.get('portal_identity_type')=='Travel Document' or str(values.get('passport_issuing_country') or '').strip().casefold() not in {'united kingdom','uk','gb','gbr'}): errors[key] = 'Your passport has expired. Use a current passport.'
                    elif key in {'dl_issue_date','passport_issue_date'} and parsed >= date.today(): errors[key] = 'Issue date must be before today'
                    elif key == 'address_since' and parsed >= date.today(): errors[key] = 'Enter the date you moved in—it must be before today'
                    elif key in {'dob','address_since','dl_issue_date','passport_issue_date','idc_issuedate'} and parsed > date.today():
                        errors[key] = 'Cannot be in the future'
                except ValueError: errors[key] = 'Enter a valid date'
    if 'birth_city' in visible_names and present(values.get('birth_city')):
        status=values.get('portal_birthplace_status')
        if status not in {'Matched','Review'} or values.get('portal_birthplace_country') != values.get('birth_country'):
            errors['birth_city']='Choose a birthplace from the list, or enter it manually for review.'
    visible = {f['key'] for g in groups for f in g['fields']}
    for start,end in [('dl_issue_date','dl_expiry_date'),('passport_issue_date','passport_expiry_date'),('idc_issuedate','idc_expriydate')]:
        if end in visible and present(values.get(start)) and present(values.get(end)) and not errors.get(start) and not errors.get(end):
            if str(values[end])[:10] < str(values[start])[:10]: errors[end] = 'Must be on or after the issue date'
    return errors

def completion(values, groups):
    errors = field_errors(values, groups)
    required = [f for g in groups for f in g['fields'] if f['required']]
    done = sum(present(values.get(f['key'])) and f['key'] not in errors for f in required)
    total = len(required)
    return dict(completed=done,total=total,percentage=(done * 100 // total if total else (100 if any(g['fields'] for g in groups) else 0)),errors=errors,
                complete=any(g['fields'] for g in groups) and done == total and not errors)
