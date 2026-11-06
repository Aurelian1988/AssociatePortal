"""Authenticated profile editing and one-time submission for the associate portal."""
from functools import wraps
import frappe
from frappe.utils import now_datetime
from onemotion.api.profile_policy import SECTIONS, READ_ONLY, schema, completion, identity_type, normalise_nino, yes, licence_required, editable_field

from onemotion.api.profile_identifiers import identifier_errors, normalise_utr, normalise_vat, normalise_passport

from onemotion.api.profile_address import normalise_address

from onemotion.api.profile_share_codes import CODES, read_codes, stage_codes

SUBMITTED = 'portal_profile_submitted_on'
IDENTITY = 'portal_identity_type'


def install_fields():
    """Run once during deployment, not during a web request."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as create_fields
    def create_custom_fields(definitions, **kwargs):
        # Associate is already close to MariaDB's inline row limit. Keep new
        # string tracking values off-row; choices are validated by this API.
        for field in definitions.get('Associate', []):
            if field['fieldtype'] in {'Data','Select'}:
                field['fieldtype']='Small Text'
                field.pop('options',None)
        return create_fields(definitions, **kwargs)
    create_custom_fields({'Associate': [
        dict(fieldname='portal_document_audits',label='Document OCR approval audit',fieldtype='Long Text',read_only=1,hidden=1,no_copy=1),
        dict(fieldname='portal_onboarding_progress',label='Portal submitted sections',fieldtype='Long Text',read_only=1,no_copy=1,hidden=1),
        dict(fieldname='portal_adm_draft',label='Portal address capture row',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_bcm_draft',label='Portal birth certificate row',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_birthplace_status',label='Birthplace lookup status',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_birthplace_country',label='Birthplace lookup country',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_birthplace_reference',label='Birthplace location reference',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_birthplace_manual',label='Birthplace manually entered',fieldtype='Check',read_only=1,no_copy=1),
        dict(fieldname='portal_no_passport',label='I do not have a Passport',fieldtype='Check',no_copy=1),
        dict(fieldname='portal_no_driving_licence',label='I don’t have a driving licence',fieldtype='Check',no_copy=1),
        dict(fieldname='portal_dbs_certificate_file',label='DBS certificate upload',fieldtype='Attach',read_only=1,no_copy=1),
        dict(fieldname='portal_dbs_draft',label='Portal DBS draft row',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_has_dbs_certificate',label='Has DBS certificate',fieldtype='Select',options='\nYes\nNo',no_copy=1),
        dict(fieldname='portal_has_dbs_share_code',label='Has DBS share code',fieldtype='Select',options='\nYes\nNo',no_copy=1),
        dict(fieldname='portal_dbs_reference',label='DBS reference number',fieldtype='Data',no_copy=1),
        dict(fieldname='portal_has_recent_dbs',label='Recent DBS check available',fieldtype='Select',options='\nYes\nNo',no_copy=1),
        dict(fieldname='portal_dbs_share_code',label='DBS share code',fieldtype='Data',no_copy=1),
        dict(fieldname='portal_dlm_draft',label='Portal licence capture row',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_pdm_draft',label='Portal passport capture row',fieldtype='Data',read_only=1,no_copy=1),
        dict(fieldname='portal_passport_manual_review',label='Passport needs manual review',fieldtype='Check',read_only=1,no_copy=1),
        dict(fieldname='portal_passport_scanned',label='Portal passport read',fieldtype='Check',read_only=1,no_copy=1),
        dict(fieldname=SUBMITTED,label='Portal profile submitted on',fieldtype='Datetime',read_only=1,no_copy=1),
        dict(fieldname=IDENTITY,label='Portal identity document type',fieldtype='Select',options='\nPassport\nTravel Document',no_copy=1),
    ], 'ADM':[dict(fieldname='portal_matched_last_name',label='OCR matched last name',fieldtype='Data',read_only=1,no_copy=1)]}, update=True)
    create_custom_fields({name:[dict(fieldname='portal_auto_approval_audit',label='Automatic document approval audit',fieldtype='Long Text',read_only=1,no_copy=1)] for name in ('ADM','PDM','DLM')},update=True)
    create_custom_fields({'PDM':[dict(fieldname='portal_identity_document_type',label='Identity document type',fieldtype='Data',read_only=1,no_copy=1)]},update=True)
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    options=(frappe.get_meta('ADM').get_field('adm_status').options or '').splitlines()
    if 'Accepted' not in options: make_property_setter('ADM','adm_status','options','\n'.join(options+['Accepted']),'Text')


def _associate():
    from onemotion.api.profile_contact_start import invitation, linked_associate
    record = invitation()
    if record:
        doc = linked_associate(record)
        if doc is None:
            frappe.throw('Submit Contact Information first.', frappe.PermissionError)
        if record.get('profile_completed_at') and not doc.get(SUBMITTED):
            doc.set(SUBMITTED, record.profile_completed_at)
        return doc
    # Import lazily: associate_portal also uses our API guard.
    from onemotion.api.associate_portal import _get_associate_name
    name = _get_associate_name()
    if not name:
        frappe.throw('No Associate profile is linked to your account.', frappe.PermissionError)
    doc = frappe.get_doc('Associate',name)
    if not doc.meta.has_field(SUBMITTED) or not doc.meta.has_field('id_photo'):
        frappe.throw('Profile setup is not ready. Please contact support.')
    return doc


def _push_registered(endpoint=None):
    filters = {'user': frappe.session.user}
    if endpoint: filters['endpoint'] = endpoint
    return bool(frappe.db.exists('Web Push Subscription', filters))


def _state(doc):
    from onemotion.api.profile_documents import hydrate_capture_drafts
    hydrate_capture_drafts(doc)
    available = {f.fieldname for f in doc.meta.fields} | set(CODES)
    keys = {x[0] for _, fields in SECTIONS for x in fields} | READ_ONLY | {IDENTITY,'portal_no_passport','role','contact_name'}
    keys.update({'primary_rtw_share_code','primary_rtw_indefinite','primary_rtw_status','primary_rtw_sc_ed','primary_rtw_outcome__status','primary_rtw_outcome_expiry','primary_rtw_share_code_file','primary_rtw_dd_file'})
    keys.update({'primary_immigration_share_code','primary_imi_indefinite','primary_immigration_status','primary_imi_outcome_status','primary_immigration_sc_ed','primary_immigration_outcome_expiry','primary_immigration_share_code_doc','primary_immigration_dd_file'})
    keys.update({'audit_status','audit_date','last_audit_date'} | {'audit_status_'+suffix for suffix in ('dlm','pdm','imi','adm','rtw','nim','dbs','bcm','odm','dvla','dva','pob','agreements')})
    values = {k:doc.get(k) for k in keys if k in available}
    from onemotion.api.profile_birthplace_api import META
    values.update({k:doc.get(k) for k in META})
    values.update(read_codes(doc))
    from onemotion.api.profile_dbs import dbs_required,active_site,needs_share_guidance,is_amazon_site,active_contracts
    values['_portal_dbs_required'] = dbs_required(doc)
    values['_portal_dbs_amazon_site'] = is_amazon_site(active_site(doc),active_contracts(doc))
    if doc.get('awr_status') != 'Active' and not doc.get('portal_passport_scanned') and not doc.get('portal_passport_manual_review'): values['passp_file'] = ''
    groups = schema(values,available)
    all_groups = schema(values,available,catalog=True)
    for group in all_groups:
        for field in group['fields']:
            meta = doc.meta.get_field(field['key'])
            if not meta: continue
            if meta.fieldtype == 'Select':
                field['type'] = 'select'
                field['options'] = [o.strip() for o in (meta.options or '').splitlines() if o.strip()]
            elif meta.fieldtype == 'Check': field['type'] = 'checkbox'
            # Mirrored ERP fields are edited through this explicit allowlist and child records.
            field['editable'] = editable_field(field['key'],values)
    result = completion(values,groups)
    from onemotion.api.profile_documents import document_state
    from onemotion.api.profile_address_evidence import evidence_status
    address_row=next((r for r in (doc.get('adm') or []) if str(r.name)==str(doc.get('portal_adm_draft'))),None)
    address_evidence=dict(status=evidence_status(address_row.get('portal_matched_last_name'),doc.get('last_name'),address_row.get('poa_date')),document_date=address_row.get('poa_date')) if address_row else None
    from onemotion.api.profile_stages import stage_state
    progress=stage_state(doc,values,groups)
    from onemotion.api.profile_approval_api import status as approval_status,scan_values,unsaved_draft
    return dict(dbs_amazon_site=is_amazon_site(active_site(doc),active_contracts(doc)),dbs_share_guidance_required=needs_share_guidance(active_site(doc)),**progress,document_draft_values=unsaved_draft(doc,progress['current_stage']),document_scan_values=scan_values(doc,progress['current_stage']),document_approvals=approval_status(doc),address_evidence=address_evidence,dbs_required=values['_portal_dbs_required'],documents=document_state(doc),values=values,sections=all_groups,completion=result,submitted=bool(doc.get(SUBMITTED)),
                submitted_on=doc.get(SUBMITTED),identity_type=identity_type(values,available),
                supports_identity_card=False)


@frappe.whitelist()
def get_profile_state():
    from onemotion.api.profile_contact_start import invitation, draft_associate
    record = invitation()
    if record and not record.associate:
        state = _state(draft_associate(record))
        state['contact_first_pending'] = True
        return state
    return _state(_associate())


@frappe.whitelist(methods=['POST'])
def save_profile(values, submit=False, push_endpoint=None, document_edits=None):
    doc = _associate()
    frappe.db.sql('SELECT name FROM `tabAssociate` WHERE name=%s FOR UPDATE',(doc.name,))
    doc.reload()
    from onemotion.api.profile_documents import hydrate_capture_drafts
    hydrate_capture_drafts(doc)
    incoming = frappe.parse_json(values) if isinstance(values,str) else values
    if not isinstance(incoming,dict): frappe.throw('Invalid profile details.')
    if incoming.get(IDENTITY) not in (None,'','Passport','Travel Document'): frappe.throw('Choose Passport or Travel Document, or the eligible birth certificate route.')
    submit = str(submit).lower() in {'true','1'}
    incoming = {k:v.strip() if isinstance(v,str) else v for k,v in incoming.items()}
    from onemotion.api.profile_names import NAME_FIELDS,normalise_name,unique_contact_name
    incoming = {k:normalise_name(v) if k in NAME_FIELDS else v for k,v in incoming.items()}
    incoming = normalise_address(incoming)
    from onemotion.api.profile_birthplace_api import apply_birthplace
    apply_birthplace(doc,incoming)
    from onemotion.api.profile_documents import enforce_document_locks
    enforce_document_locks(doc,incoming)
    if doc.get(SUBMITTED):
        locked_personal = {'first_name','middle_name','last_name','dob','birthpassport_gender','birth_country','birth_city','birth_nationality','preferred_language'}
        if any(key in locked_personal and str(value or '') != str(doc.get(key) or '') for key,value in incoming.items()):
            frappe.throw('Personal details are locked after onboarding. Please contact the team.')
    allowed = {x[0] for _, fields in SECTIONS for x in fields} - READ_ONLY
    if editable_field('email',{'email':doc.get('email')}):allowed.add('email')
    allowed.update({IDENTITY,'portal_no_passport'})
    from onemotion.api.profile_child_records import prepare_profile_update
    prepare_profile_update(doc,incoming)
    stage_codes(doc, incoming)
    for key,value in incoming.items():
        if key in CODES: continue
        meta = doc.meta.get_field(key)
        if key not in allowed or not meta:
            frappe.throw('This profile field cannot be edited.',frappe.PermissionError)
        if isinstance(value,(list,dict)): frappe.throw('Invalid field value.')
        value = value.strip() if isinstance(value,str) else value
        if key == 'passport_number': value = normalise_passport(value) or None
        if key == 'nino_number': value = normalise_nino(value) or None
        if key == 'utr_number': value = normalise_utr(value) or None
        if key == 'vat_number': value = normalise_vat(value) or None
        if meta.fieldtype == 'Select' and value and value not in (meta.options or '').splitlines():
            frappe.throw('Choose a valid value for ' + meta.label)
        if meta.fieldtype == 'Check':
            if value not in (True,False,0,1,'0','1'): frappe.throw('Invalid yes/no value.')
            value = int(value)
        if meta.fieldtype == 'Link' and value and not frappe.db.exists(meta.options,value):
            frappe.throw('Choose a valid value for ' + meta.label)
        doc.set(key,value)
    from onemotion.api.profile_licence import licence_type
    if doc.get('dl_issuing_country') and not yes(doc.get('portal_no_driving_licence')):
        derived_type=licence_type(doc.get('dl_issuing_country'))
        if not frappe.db.exists('DL Type',derived_type): frappe.throw('Licence type setup is incomplete. Please contact your team.')
        doc.set('dl_type',derived_type)
    # This declaration can remove DA only. Reopening the form never grants a role.
    if yes(doc.get('portal_no_driving_licence')) and doc.get('role') == 'DA':
        doc.set('role',None)
    for key in NAME_FIELDS:
        if doc.meta.has_field(key): doc.set(key,normalise_name(doc.get(key)))
    duplicates = identifier_errors(doc,doc.name)
    if duplicates: frappe.throw('\n'.join(duplicates.values()),frappe.ValidationError)
    state = _state(doc)
    if submit:
        if not state['all_stages_submitted']:
            frappe.throw('Submit each profile section before submitting the full profile.')
        if (licence_required(state['values']) and not state['documents']['licence_ready']) or (state['identity_type'] in {'Passport','Travel Document'} and not state['documents']['passport_ready']):
            frappe.throw('Upload both licence photos and scan your passport before submitting.')
        if not state['completion']['complete']:
            frappe.throw('Complete the required profile details before submitting.')
        if not push_endpoint or not _push_registered(push_endpoint):
            frappe.throw('Enable push notifications on this device before submitting.',frappe.PermissionError)
        doc.set('contact_name',unique_contact_name(doc))
        if not doc.get(SUBMITTED): doc.set(SUBMITTED,now_datetime())
    else:
        invalid = {k:v for k,v in state['completion']['errors'].items() if v != 'Required' and (k in incoming or k == 'portal_no_passport')}
        invalid = {k:v for k,v in invalid.items() if not ((k in {'dl_expiry_date','dl_photocard_expiry'} and v == 'Your licence has expired. Are you sure this date is correct?') or (k == 'passport_expiry_date' and v == 'Your passport has expired. Use a current passport.'))}
        invalid = {k:v for k,v in invalid.items() if not (k == 'birth_city' and v == 'Choose a birthplace from the list, or enter it manually for review.')}
        if invalid: frappe.throw('\n'.join(invalid.values()))
    from onemotion.api.profile_approval_api import edits as audit_edits
    audit_edits(doc,incoming,frappe.parse_json(document_edits) if isinstance(document_edits,str) else (document_edits or []))
    # Only the current associate's allowlisted fields can reach this save.
    from onemotion.api.profile_documents import sync_document_details
    sync_document_details(doc)
    from onemotion.api.profile_child_records import sync_profile_children
    sync_profile_children(doc)
    try:
        from onemotion.api.portal_onboarding import own_write
        with own_write(): doc.save(ignore_permissions=True)
    except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
        frappe.throw('An identifier is already used by another ERP record. Check the passport, National Insurance, UTR and VAT numbers or contact your team.',frappe.ValidationError)
    state = _state(doc)
    if submit:
        from onemotion.api.profile_contact_start import sync_tracking
        sync_tracking(doc, state, completed=True)
    return state


def require_portal_access(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        doc = _associate()
        if not doc.get(SUBMITTED):
            frappe.throw('Submit My Profile before using the rest of the portal.',frappe.PermissionError)
        if not _push_registered():
            frappe.throw('Enable push notifications before using the portal.',frappe.PermissionError)
        return fn(*args,**kwargs)
    return wrapped


def require_onboarding_chat(fn):
    """Chat is the explicit exception to the onboarding/push gate."""
    @wraps(fn)
    def wrapped(*args,**kwargs):
        doc=_associate()
        from inspect import signature
        supplied=signature(fn).bind_partial(*args,**kwargs).arguments
        identifier=supplied.get('contact_identifier')
        if identifier:
            from onemotion.api.associate_portal import _get_onechat_session
            chat=_get_onechat_session(doc.name)
            if str(chat.get('onechat_source_id') or '') != str(identifier):
                frappe.throw('Please reconnect your own chat session.',frappe.PermissionError)
        return fn(*args,**kwargs)
    return wrapped
