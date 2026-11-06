"""Server-owned OCR audit persistence and child-table status updates."""
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import frappe
from onemotion.api.profile_document_approval import record_capture,note_edits,invalidate_changed,decide,public_status,REQUIRED,combined,draft_values
FIELD='portal_document_audits'
ROWS={'passport':('pdm','portal_pdm_draft','pdm_status'),'driving_licence':('dlm','portal_dlm_draft','status'),'address':('adm','portal_adm_draft','adm_status')}

def records(doc):
    try:
        value=json.loads(doc.get(FIELD) or '{}')
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):return {}

def check_file_references(doc,data):
    fields={'passport':'passp_file','licence_front':'tab_dl_photocard_front','licence_back':'tab_dl_photocard_rear','proof_of_address':'proof_of_address_doc'}
    for entry in data.values():
        if any(source.get('file_reference')!=doc.get(fields[kind]) for kind,source in entry.get('sources',{}).items() if kind in fields):entry['source_changed']=True
    return data

def database_timestamp(value):
    """Convert audit ISO timestamps to site-local, timezone-free database values."""
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo(frappe.utils.get_system_timezone())).replace(tzinfo=None)
    return parsed

def persist(doc,data):
    if not doc.meta.has_field(FIELD):frappe.throw('Document approval setup is incomplete. Please contact your team.')
    doc.set(FIELD,json.dumps(data,default=str))
    for group,entry in data.items():
        if group not in ROWS:continue
        table,reference,status=ROWS[group]
        row=next((r for r in doc.get(table) or [] if str(r.name)==str(doc.get(reference))),None)
        if not row:continue
        row.set(status,entry.get('status','Review'))
        decision=entry.get('decision',{})
        for key,value in {'document_check_result':decision.get('result','Manual Review'),
                          'document_check_note':decision.get('note','Awaiting section submission and automatic data checks.'),
                          'document_check_completed_on':database_timestamp(decision.get('decided_at')),
                          'portal_auto_approval_audit':json.dumps(entry,default=str)}.items():
            if row.meta.has_field(key):row.set(key,value)

def capture(doc,kind,reading,before,file_reference,content):
    persist(doc,record_capture(records(doc),kind,reading,before,file_reference,hashlib.sha256(content).hexdigest()))

def edits(doc,incoming,reported=()):
    if not isinstance(reported,list) or len(reported)>100 or any(not isinstance(k,str) for k in reported):frappe.throw('Invalid document edit history.')
    data=note_edits(check_file_references(doc,records(doc)),incoming,reported)
    persist(doc,invalidate_changed(data,{k:doc.get(k) for keys in REQUIRED.values() for k in keys}|{k:doc.get(k) for k in ('middle_name','state_region')}))

def submit(doc,section):
    if section not in ROWS:return
    if section=='driving_licence' and str(doc.get('portal_no_driving_licence')).lower() in {'1','true'}:return
    if section=='passport' and doc.get('portal_no_passport'):return
    from onemotion.api.profile_identifiers import identifier_errors
    unique_ok=not identifier_errors(doc,doc.name).get('passport_number') if section=='passport' else None
    values={k:doc.get(k) for keys in REQUIRED.values() for k in keys}|{k:doc.get(k) for k in ('middle_name','state_region')}
    persist(doc,decide(check_file_references(doc,records(doc)),section,values,unique_ok=unique_ok))

def status(doc):return public_status(records(doc))


def validate_document_approvals(doc,method=None):
    """Invalidate automatic approvals after desk/integration profile edits too."""
    if not doc.meta.has_field(FIELD) or not records(doc):return
    values={k:doc.get(k) for keys in REQUIRED.values() for k in keys}|{k:doc.get(k) for k in ('middle_name','state_region')}
    persist(doc,invalidate_changed(check_file_references(doc,records(doc)),values))


def scan_values(doc,section):return combined(records(doc).get(section,{}))[0]


def unsaved_draft(doc,section):return draft_values(records(doc),section)
