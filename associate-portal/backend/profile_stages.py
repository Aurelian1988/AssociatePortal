"""Sequential, server-enforced onboarding stages. Completion is separate from submission."""
import hashlib
import json
import frappe
from onemotion.api.profile_policy import schema, completion, birth_certificate_route, requires_immigration, READ_ONLY, licence_required, editable_field

PROGRESS='portal_onboarding_progress'
ORDER=[
    ('contact','Contact Information',['Contact Information']),
    ('driving_licence','Driving Licence',['Driving Licence']),
    ('passport','Passport',['Identity']),
    ('birth_certificate','Birth Certificate',['Birth Certificate']),
    ('personal','Personal Details',['Profile Picture','Personal Details']),
    ('address','Address Details',['Address']),
    ('rtw','Right To Work',['Right to Work']),
    ('immigration','Immigration',['Immigration']),
    ('national_insurance','Background Screening',['DBS Check']),
]
ROUTE_KEYS={'birth_nationality','birth_country','portal_no_passport','portal_identity_type'}
PERSONAL_KEYS={'first_name','middle_name','last_name','dob','birthpassport_gender','birth_city'}


def definitions(values,groups):
    result=[]
    for key,title,titles in ORDER:
        if key=='birth_certificate' and not birth_certificate_route(values): continue
        if key in {'rtw','immigration'} and not requires_immigration(values): continue
        fields=[dict(f) for section_title in titles for group in groups if group['title']==section_title for f in group['fields']]
        if key=='passport':
            # Choosing the eligible birth-certificate route is submitted first; its file is the next stage.
            if birth_certificate_route(values): fields=[]
            fields += [dict(key=k,label=label,required=True) for k,label in [('birth_nationality','Nationality'),('birth_country','Birth country')]]
        if key=='personal': fields=[f for f in fields if f['key'] not in (ROUTE_KEYS - {'birth_country'})]
        result.append(dict(id=key,title=title,section_titles=titles,fields=fields))
    return result


def signature(stage,values):
    keys={f['key'] for f in stage['fields']}
    if stage['id']=='passport':
        keys |= ROUTE_KEYS
        if not birth_certificate_route(values): keys.discard('birth_country')
    if stage['id']=='personal': keys |= {'portal_birthplace_status','portal_birthplace_country','portal_birthplace_reference'}
    raw=json.dumps({k:values.get(k) for k in sorted(keys)},sort_keys=True,default=str,ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def saved_stages(doc):
    try:
        data=json.loads(doc.get(PROGRESS) or '{}')
        return data if isinstance(data,dict) else {}
    except (ValueError,TypeError): return {}


def stage_state(doc,values,groups):
    saved=saved_stages(doc); stages=definitions(values,groups); current=None
    for stage in stages:
        keys={f['key'] for f in stage['fields']}
        validation=completion(values,[dict(title=stage['title'],fields=stage['fields'])])
        errors={k:v for k,v in validation['errors'].items() if k in keys or k in {'portal_no_passport','portal_identity_type'}}
        stage['complete']=bool(stage['fields']) and not errors
        stage['submitted']=stage['complete'] and saved.get(stage['id'])==signature(stage,values)
        if doc.get('awr_status')=='Active' and saved.get('contact') and stage['complete']:
            # Existing evidence is retained. Never infer completion from values
            # alone when a document is required by this section.
            evidence = (stage['id']!='passport' or bool(values.get('passp_file')) or birth_certificate_route(values))
            if stage['id']=='driving_licence' and licence_required(values):
                evidence = bool(values.get('tab_dl_photocard_front') and values.get('tab_dl_photocard_rear'))
            if evidence: stage['submitted']=True
        stage['errors']=errors
        if current is None and not stage['submitted']: current=stage['id']
    return dict(stages=stages,current_stage=current,all_stages_submitted=current is None)


@frappe.whitelist(methods=['POST'])
def submit_profile_section(section,values,document_edits=None):
    from onemotion.api.profile_onboarding import _associate,_state,save_profile,get_profile_state
    incoming=frappe.parse_json(values) if isinstance(values,str) else values
    if not isinstance(incoming,dict): frappe.throw('Invalid section details.')
    if section == 'contact':
        from onemotion.api.profile_contact_start import invitation,start_contact,normalise_phone
        if invitation():
            current = get_profile_state()
            if current['current_stage'] != 'contact':
                contact = next((s for s in current['stages'] if s['id']=='contact'),None)
                same = (not set(incoming)-{'email','mobile'} and
                        ('email' not in incoming or str(incoming['email']).strip().lower()==str(current['values'].get('email') or '').strip().lower()) and
                        ('mobile' not in incoming or normalise_phone(incoming['mobile'])==normalise_phone(current['values'].get('mobile'))))
                if contact and contact['submitted'] and same: return current
                frappe.throw('Use the current section or reopen Contact Information first.')
            doc = start_contact(incoming)
            incoming = {'mobile':doc.get('mobile')}
    doc=_associate();before=_state(doc)
    stage=next((s for s in before['stages'] if s['id']==section),None)
    # Passport route declarations can introduce/remove later conditional stages.
    if not stage or before['current_stage']!=section:
        frappe.throw('Submit the previous section first.',frappe.PermissionError)
    allowed={f['key'] for f in stage['fields'] if editable_field(f['key'],before['values'])}
    if section=='passport': allowed |= ROUTE_KEYS | PERSONAL_KEYS | {f['key'] for group in before['sections'] if group['title']=='Identity' for f in group['fields'] if f['editable']}
    if section=='national_insurance':allowed |= {'mothers_first_name','mothers_maiden_name','portal_has_recent_dbs','portal_has_dbs_share_code','portal_has_dbs_certificate','portal_dbs_share_code','portal_dbs_reference'}
    if section=='personal': allowed |= {'portal_birthplace_token','portal_birthplace_manual'}
    if any(k not in allowed for k in incoming): frappe.throw('Only fields in this section can be saved here.',frappe.PermissionError)
    save_profile(incoming,submit=False,document_edits=document_edits)
    doc=_associate();after=_state(doc)
    stage=next((s for s in after['stages'] if s['id']==section),None)
    if section=='personal' and not str(after['values'].get('id_photo') or '').strip():
        frappe.throw('Add your profile photo before submitting Personal Details.')
    if not stage or not stage['complete']:
        frappe.throw('Complete this section and correct the highlighted fields before submitting.')
    if section=='passport' and after['identity_type'] in {'Passport','Travel Document'} and not after['documents']['passport_ready']:
        frappe.throw('Capture and scan your passport first.')
    if section=='driving_licence' and licence_required(after['values']) and not after['documents']['licence_ready']:
        frappe.throw('Capture the front and back of your licence first.')
    from onemotion.api.profile_approval_api import submit as approve_document
    approve_document(doc,section)
    from onemotion.api.portal_onboarding import own_write
    with own_write(): doc.save(ignore_permissions=True)
    progress=saved_stages(doc);progress[section]=signature(stage,after['values'])
    frappe.db.set_value('Associate',doc.name,PROGRESS,json.dumps(progress),update_modified=False)
    doc.reload()
    state = _state(doc)
    from onemotion.api.profile_contact_start import sync_tracking
    sync_tracking(doc,state)
    return state


@frappe.whitelist(methods=['POST'])
def reopen_profile_section(section):
    from onemotion.api.profile_onboarding import _associate,_state
    doc=_associate()
    frappe.db.sql('SELECT name FROM `tabAssociate` WHERE name=%s FOR UPDATE',(doc.name,))
    doc.reload();state=_state(doc)
    if state['submitted']:frappe.throw('This profile has already been submitted.',frappe.PermissionError)
    ids=[stage['id'] for stage in state['stages']]
    current=ids.index(state['current_stage']) if state['current_stage'] in ids else len(ids)
    if section not in ids or ids.index(section)>=current:frappe.throw('Choose a previous section.',frappe.PermissionError)
    progress=saved_stages(doc)
    for key in ids[ids.index(section):]:progress.pop(key,None)
    frappe.db.set_value('Associate',doc.name,PROGRESS,json.dumps(progress),update_modified=False)
    doc.reload()
    return _state(doc)
