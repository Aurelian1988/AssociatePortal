"""Explicit mappings verified against ERP DocType metadata on 4 November 2026."""
import frappe
from frappe.utils import now_datetime
from onemotion.api.profile_policy import normalise_nino


def append_if_changed(doc,table,fields,compare,status=None,submitted=None):
    rows=doc.get(table) or []
    latest=rows[-1] if rows else None
    if latest and all(str(latest.get(k) or '').strip()==str(fields.get(k) or '').strip() for k in compare): return latest
    values=dict(fields,contact_name=doc.name)
    if status: values[status]='Review'
    if submitted: values[submitted]=now_datetime()
    return doc.append(table,values)


def sync_contacts(doc):
    email=str(doc.get('email') or '').strip()
    phone=str(doc.get('mobile') or '').strip()
    rows=[r for r in (doc.get('contact_details_archive') or []) if r.get('cda_type')=='Personal']
    latest=next((r for r in reversed(rows) if r.get('cda_email')),None)
    if (email or phone) and not (latest and latest.get('cda_email')==email and latest.get('cda_mobile')==phone):
        doc.append('contact_details_archive',dict(contact_name=doc.name,cda_email=email,cda_mobile=phone,cda_type='Personal',cda_datetime_submited=now_datetime()))
    secondary=str(doc.get('mobile2') or '').strip()
    if secondary and not any(r.get('cda_mobile')==secondary for r in rows):
        doc.append('contact_details_archive',dict(contact_name=doc.name,cda_mobile=secondary,cda_type='Personal',cda_datetime_submited=now_datetime()))


def sync_nino(doc):
    value=normalise_nino(doc.get('nino_number'))
    if value:
        append_if_changed(doc,'national_insurance_management',{'nim_nino_number':value},['nim_nino_number'],'nim_status','nim_submission_datetime')


def sync_dbs(doc):
    from onemotion.api.profile_dbs import active_site,active_contracts,is_amazon_site
    if is_amazon_site(active_site(doc),active_contracts(doc)):return
    if doc.get('portal_has_recent_dbs')!='Yes' or doc.get('portal_has_dbs_share_code')!='Yes':return
    value=str(doc.get('portal_dbs_share_code') or '').strip()
    if not value: return
    address=' '.join(str(doc.get(k) or '') for k in ('country','state_region')).casefold()
    kind='DBS NI' if 'northern ireland' in address else 'DBS L1' if 'scotland' in address else 'DBS UK'
    append_if_changed(doc,'dbs',{'dbs_sharecode':value,'document_type':kind},['dbs_sharecode','document_type'],'dbs_status','dbs_submission_date')


def sync_address(doc):
    from onemotion.api.profile_address_evidence import evidence_status
    row=next((r for r in (doc.get('adm') or []) if str(r.name)==str(doc.get('portal_adm_draft'))),None)
    if not row: return
    row.full_address=', '.join(str(doc.get(k) or '').strip() for k in ('street_address','city','state_region','country') if doc.get(k))
    row.post_code=str(doc.get('postal_code') or '').strip()
    row.from_date=doc.get('address_since')
    # Approval is decided separately on submission, never by surname/date alone.


def sync_profile_children(doc):
    sync_contacts(doc);sync_nino(doc);sync_dbs(doc);sync_address(doc)


def prepare_profile_update(doc, incoming):
    """Preserve history before applying a completed profile's replacement details."""
    if not doc.get('portal_profile_submitted_on'): return
    changed=lambda keys:any(k in incoming and str(incoming[k] or '')!=str(doc.get(k) or '') for k in keys)
    if changed(('email','mobile')):
        sync_contacts(doc)
    if changed(('street_address','city','state_region','country','postal_code','address_since')):
        # The old ADM and its evidence remain untouched. New address needs review.
        values={k:incoming.get(k,doc.get(k)) for k in ('street_address','city','state_region','country','postal_code','address_since')}
        row=doc.append('adm',dict(contact_name=doc.name,adm_status='Review',adm_type='ADM',
            full_address=', '.join(str(values[k] or '').strip() for k in ('street_address','city','state_region','country') if values[k]),
            post_code=values['postal_code'],from_date=values['address_since'],adm_date=now_datetime()))
        if not row.name: row.name=frappe.generate_hash(length=10)
        doc.set('portal_adm_draft',row.name)
