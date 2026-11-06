"""Private document capture before profile submission, tied to the current associate."""
import base64
import uuid
from io import BytesIO
import frappe
from PIL import Image, ImageOps
from onemotion.api.profile_document_ocr import extract_fields
from onemotion.api.profile_document_reader import read_document
from onemotion.api.profile_document_quality import readable_text_for_review as readable_text, QUALITY_MESSAGE

FILES = {
    'licence_front': ('dlm','dl_photocard_front','tab_dl_photocard_front','status','portal_dlm_draft'),
    'licence_back': ('dlm','dl_photocard_rear','tab_dl_photocard_rear','status','portal_dlm_draft'),
    'passport': ('pdm','passp_file','passp_file','pdm_status','portal_pdm_draft'),
}
ADDRESS = {'street_address','city','state_region','postal_code','country','address_since'}
PERSONAL = {'first_name','middle_name','last_name','dob','birthpassport_gender','birth_city'}


def hydrate_capture_drafts(doc):
    """Read the current draft child row, not ERP's approved-document mirrors.

    ERP intentionally clears the main mirrors for unapproved documents. The
    app must still let the owner review and submit their captured draft.
    This only changes the request's document object; it does not approve rows.
    """
    mappings = [
        ('dlm','portal_dlm_draft',{'dl_photocard_front':'tab_dl_photocard_front','dl_photocard_rear':'tab_dl_photocard_rear','dl_number':'dl_number','driving_licence_type':'dl_type','driving_licence_issuing_country':'dl_issuing_country','dl_issue_date':'dl_issue_date','dl_expiry_date':'dl_expiry_date','dl_photocard_expiry_date':'dl_photocard_expiry'}),
        ('pdm','portal_pdm_draft',{'passp_file':'passp_file','passp_number':'passport_number','passp_ic':'passport_issuing_country','passp_id':'passport_issue_date','passp_ed':'passport_expiry_date'}),
        ('birth_certificate_management','portal_bcm_draft',{'bcm_file':'bc_file'}),
        ('dbs','portal_dbs_draft',{'dbs_file':'portal_dbs_certificate_file'}),
    ]
    for table, reference, fields in mappings:
        row=next((r for r in doc.get(table) or [] if str(r.name)==str(doc.get(reference))),None)
        if not row: continue
        for source,target in fields.items():
            if row.get(source) is not None: doc.set(target,row.get(source))
    return doc


def document_state(doc):
    return dict(birth_certificate_ready=bool(doc.get('bc_file')),licence_ready=bool(doc.get('tab_dl_photocard_front') and doc.get('tab_dl_photocard_rear')),
                passport_ready=bool(doc.get('passp_file') and (doc.get('portal_passport_scanned') or doc.get('portal_passport_manual_review') or doc.get('awr_status')=='Active')),
                files=dict({kind:doc.get(config[2]) for kind,config in FILES.items()},birth_certificate=doc.get('bc_file'),proof_of_address=doc.get('proof_of_address_doc'),dbs_certificate=doc.get('portal_dbs_certificate_file')))


def enforce_document_locks(doc, incoming):
    state = document_state(doc)
    from onemotion.api.profile_policy import birth_certificate_route
    merged = {k:doc.get(k) for k in ('birth_country','birth_nationality','portal_no_passport')}
    merged.update(incoming)
    birth_route = birth_certificate_route(merged)
    passport = True
    from onemotion.api.profile_names import NAME_FIELDS,normalise_name
    for key, value in incoming.items():
        if key in NAME_FIELDS and normalise_name(value)==normalise_name(doc.get(key)): continue
        if value == doc.get(key): continue
        if key in ADDRESS and not doc.get('proof_of_address_doc'):
            frappe.throw('Upload a readable proof of address before editing address details.')
        if key.startswith('dl_') and not state['licence_ready']:
            frappe.throw('Upload the front and back of your driving licence before editing its details.')
        if birth_route and key in PERSONAL and not state['birth_certificate_ready']:
            frappe.throw('Upload your birth certificate before editing personal details.')
        if not birth_route and passport and (key.startswith('passport_') or key in PERSONAL) and not state['passport_ready']:
            frappe.throw('Upload and scan your passport before editing passport and personal details.')


def clean_document(encoded):
    from onemotion.api.profile_photo import clean_photo
    # Same bounded decoder/metadata stripping; preserve more pixels for document text.
    clean_photo(encoded)
    raw = base64.b64decode(encoded.split(',',1)[1],validate=True)
    with Image.open(BytesIO(raw)) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((3200,3200))
        out = BytesIO(); image.save(out,'JPEG',quality=94)
        return out.getvalue()


@frappe.whitelist(methods=['POST'])
def upload_profile_document(kind, image_base64):
    from onemotion.api.profile_onboarding import _associate, _state
    from frappe.utils.file_manager import save_file
    if kind == 'dbs_certificate':return upload_dbs_certificate(image_base64)
    if kind == 'proof_of_address': return upload_address_evidence(image_base64)
    if kind == 'birth_certificate': return upload_birth_certificate(image_base64)
    if kind not in FILES: frappe.throw('Choose a supported profile document.')
    doc = _associate()
    profile_before={key:doc.get(key) for key in ('first_name','middle_name','last_name','dob')}
    try: content = clean_document(image_base64)
    except (ValueError, OSError): frappe.throw('Use a clear JPEG or PNG document photo, smaller than 6 MB.')
    try:
        with Image.open(BytesIO(content)) as image: reading = read_document(image,kind)
    except Exception:
        if kind not in ('licence_front','licence_back'):raise
        # Image decoding already succeeded. OCR failure must not discard the capture.
        reading={'suggestions':{},'warning':'Photo saved for manual review. Automatic reading was unsuccessful; check and complete the details below.','ocr_error':True}

    table, child_field, parent_field, status, draft_key = FILES[kind]
    if not doc.meta.has_field(table): frappe.throw('Document setup is not ready. Please contact support.')
    # Serialize front/back writes so neither upload drops the other side.
    frappe.db.sql('SELECT name FROM `tabAssociate` WHERE name=%s FOR UPDATE',(doc.name,))
    doc.reload()
    if kind == 'passport' and doc.get('portal_profile_submitted_on'):
        from datetime import date
        nationality = str(doc.get('birth_nationality') or '').strip().casefold()
        expiry = str(doc.get('passport_expiry_date') or '')
        if not nationality or nationality in {'british','british citizen'} or not expiry or expiry >= date.today().isoformat():
            frappe.throw('Passport replacement is available only for an expired passport held by a non-British associate.')
    suggestions = {}; warning = reading.get('warning','')
    try:
        suggestions = reading['suggestions']
        # ERP's birth_nationality field is labelled Nationality in its actual schema.
        nationality=suggestions.get('_passport_nationality')
        if nationality:
            candidate={'GBR':'British','BRITISH CITIZEN':'British','IRL':'Irish'}.get(str(nationality).upper(),nationality)
            options=(doc.meta.get_field('birth_nationality').options or '').splitlines()
            match=next((o for o in options if o.casefold()==str(candidate).casefold()),None)
            if match: suggestions['birth_nationality']=match
        country_code = suggestions.pop('_issuing_country_code',None)
        if country_code:
            country = {'GBR':'United Kingdom','IRL':'Ireland'}.get(country_code)
            if not country:
                try:
                    import pycountry
                    country = pycountry.countries.get(alpha_3=country_code).name
                except (ImportError, AttributeError): pass
            if country: suggestions.setdefault('passport_issuing_country',country)
        for key,value in list(suggestions.items()):
            meta = doc.meta.get_field(key)
            if not meta: continue
            if meta.fieldtype == 'Select':
                options = (meta.options or '').splitlines()
                matching = next((o for o in options if o.casefold() == str(value).casefold()),None)
                if matching: suggestions[key] = matching
                else: suggestions.pop(key)
            elif meta.fieldtype == 'Link':
                match = frappe.db.get_value(meta.options, {'name':value},'name')
                if match: suggestions[key]=match
                else: suggestions.pop(key)
        if kind == 'passport': doc.set('portal_passport_scanned',int(bool(suggestions)))
        if kind == 'passport': doc.set('portal_passport_manual_review',int(not bool(suggestions)))
    except Exception:
        suggestions={}
        if kind == 'passport':
            doc.set('portal_passport_scanned',0);doc.set('portal_passport_manual_review',1)
    if not suggestions: warning='Photo saved for review. Automatic reading was unsuccessful; enter the document details manually.'
    file = save_file(kind+'_'+uuid.uuid4().hex+'.jpg',content,'Associate',doc.name,is_private=1,df=parent_field)
    doc.set(parent_field,file.file_url)
    row = None if kind == 'passport' and doc.get('portal_profile_submitted_on') else next((r for r in (doc.get(table) or []) if str(r.name)==str(doc.get(draft_key)) and r.get(status) == 'Review'),None)
    if row is None:
        row = doc.append(table,{status:'Review'})
        for field in row.meta.fields:
            if field.fieldtype == 'Link' and field.options == 'Associate': row.set(field.fieldname,doc.name)
    row.set(child_field,file.file_url)
    # Do not overwrite the profile until the driver has reviewed the extracted suggestions.
    doc.save(ignore_permissions=True)
    frappe.db.set_value('Associate',doc.name,draft_key,row.name,update_modified=False)
    doc.reload()
    from onemotion.api.profile_approval_api import capture
    capture(doc,kind,{**reading,'suggestions':suggestions},profile_before,file.file_url,content)
    doc.save(ignore_permissions=True)
    return dict(profile=_state(doc),suggestions=suggestions,warning=warning)


def sync_document_details(doc):
    mappings = [
        ('pdm','portal_pdm_draft','pdm_status',{'passp_number':'passport_number','passp_ic':'passport_issuing_country','passp_id':'passport_issue_date','passp_ed':'passport_expiry_date','pdm_firstname':'first_name','pdm_lastname':'last_name','document_date_of_birth':'dob'}),
        ('birth_certificate_management','portal_bcm_draft','bcm_status',{'document_date_of_birth':'dob'}),
        ('dlm','portal_dlm_draft','status',{'dl_number':'dl_number','dl_issue_date':'dl_issue_date','dl_expiry_date':'dl_expiry_date','dl_photocard_expiry_date':'dl_photocard_expiry','driving_licence_type':'dl_type','driving_licence_issuing_country':'dl_issuing_country','document_first_name':'first_name','document_last_name':'last_name','document_date_of_birth':'dob'}),
    ]
    for table, reference, status, fields in mappings:
        if table == 'dlm' and str(doc.get('portal_no_driving_licence')).lower() in {'1','true'}: continue
        row = next((r for r in (doc.get(table) or []) if str(r.name)==str(doc.get(reference)) and r.get(status) == 'Review'),None)
        if row:
            if table=='pdm' and row.meta.has_field('portal_identity_document_type'):row.set('portal_identity_document_type',doc.get('portal_identity_type') or 'Passport')
            for target, source in fields.items():
                if row.meta.has_field(target): row.set(target,doc.get(source))


def upload_birth_certificate(image_base64):
    from onemotion.api.profile_onboarding import _associate, _state
    from frappe.utils.file_manager import save_file
    doc = _associate()
    # Eligibility declarations may still be unsaved in the form. The file itself
    # is private and attached only to this account; submission enforces eligibility.
    if not doc.meta.has_field('bc_file'): frappe.throw('Birth certificate setup is not ready. Please contact support.')
    try: content = clean_document(image_base64)
    except (ValueError,OSError): frappe.throw('Use a clear JPEG or PNG photo smaller than 6 MB.')
    try:
        with Image.open(BytesIO(content)) as image: readable_text(image)
    except ValueError as error: frappe.throw(str(error))
    except Exception: frappe.throw('Document reading is unavailable. Please try again; the document has not been accepted.')
    file = save_file('birth-certificate.jpg',content,'Associate',doc.name,is_private=1,df='bc_file')
    row=doc.append('birth_certificate_management',dict(bcm_file=file.file_url,bcm_status='Review',contact_name=doc.name,bcm_submission_date=frappe.utils.now_datetime(),document_date_of_birth=doc.get('dob')))
    doc.set('bc_file',file.file_url)
    doc.save(ignore_permissions=True)
    frappe.db.set_value('Associate',doc.name,'portal_bcm_draft',row.name,update_modified=False)
    doc.reload()
    return dict(profile=_state(doc),suggestions={},warning='Birth certificate saved. Review your personal details before submitting.')


def read_address_document(encoded,last_name):
    """Bounded JPEG/PNG/PDF decoding and local OCR; no external document service."""
    import subprocess
    import tempfile
    from pathlib import Path
    from onemotion.api.profile_address_reader import read_address_pages
    if isinstance(encoded,str) and encoded.startswith('data:application/pdf;base64,'):
        if len(encoded)>14_000_000: raise ValueError('PDF must be smaller than 10 MB.')
        content=base64.b64decode(encoded.split(',',1)[1],validate=True)
        if not content.startswith(b'%PDF-'): raise ValueError('Invalid PDF.')
        images=[]
        with tempfile.TemporaryDirectory(prefix='portal-address-') as temp:
            path=Path(temp);(path/'document.pdf').write_bytes(content)
            subprocess.run(['pdftoppm','-f','1','-l','2','-scale-to','2400','-png',str(path/'document.pdf'),str(path/'page')],check=True,capture_output=True,timeout=40)
            for page in sorted(path.glob('page-*.png')):
                with Image.open(page) as image: images.append(image.copy())
        if not images: raise ValueError(QUALITY_MESSAGE)
        return content,'pdf',read_address_pages(images,last_name)
    content=clean_document(encoded)
    with Image.open(BytesIO(content)) as image:
        evidence=read_address_pages([image],last_name)
    return content,'jpg',evidence


def upload_address_evidence(image_base64):
    from onemotion.api.profile_onboarding import _associate,_state
    from onemotion.api.profile_address import normalise_address
    from frappe.utils.file_manager import save_file
    doc=_associate()
    profile_before={key:doc.get(key) for key in ('first_name','middle_name','last_name','dob')}
    try: content,extension,extracted=read_address_document(image_base64,doc.get('last_name'))
    except ValueError as error: frappe.throw(str(error))
    except Exception: frappe.throw('This document could not be read. Try a clear JPEG/PNG photo or an unprotected PDF. Your document has not been accepted.')
    file=save_file('proof-of-address.'+extension,content,'Associate',doc.name,is_private=1,df='proof_of_address_doc')
    address=normalise_address(extracted['suggestions'])
    row=doc.append('adm',dict(contact_name=doc.name,poa_file=file.file_url,poa_date=extracted['document_date'],
        adm_status='Review',portal_matched_last_name=extracted['matched_name'],adm_type='ADM',
        full_address=', '.join(str(address.get(k) or '') for k in ('street_address','city') if address.get(k)),
        post_code=address.get('postal_code'),from_date=doc.get('address_since'),adm_date=frappe.utils.now_datetime(),
        document_check_completed_on=frappe.utils.now_datetime(),document_check_result='Matched' if extracted['status']=='Accepted' else 'Manual Review',
        document_check_note='Last name found and document date within six calendar months.' if extracted['status']=='Accepted' else 'Check last name, document date and legibility.'))
    doc.set('proof_of_address_doc',file.file_url)
    doc.save(ignore_permissions=True)
    frappe.db.set_value('Associate',doc.name,'portal_adm_draft',row.name,update_modified=False)
    doc.reload()
    from onemotion.api.profile_approval_api import capture
    capture(doc,'proof_of_address',dict(suggestions=address,approval_evidence=extracted['approval_evidence'],address_evidence={'document_date':extracted['document_date']}),profile_before,file.file_url,content)
    doc.save(ignore_permissions=True)
    return dict(profile=_state(doc),suggestions=address,warning='Proof of address '+extracted['status'].lower()+'. Review the extracted address details.')


def upload_dbs_certificate(image_base64):
    from onemotion.api.profile_onboarding import _associate,_state
    from onemotion.api.profile_dbs_certificate import read_certificate
    from frappe.utils.file_manager import save_file
    doc=_associate()
    try:content,extension=read_certificate(image_base64)
    except ValueError as error:frappe.throw(str(error))
    except Exception:frappe.throw('We could not read this certificate. Use a clear photo or an unprotected PDF.')
    frappe.db.sql('SELECT name FROM `tabAssociate` WHERE name=%s FOR UPDATE',(doc.name,));doc.reload()
    file=save_file('dbs-certificate.'+extension,content,'Associate',doc.name,is_private=1,df='portal_dbs_certificate_file')
    row=next((r for r in (doc.get('dbs') or []) if str(r.name)==str(doc.get('portal_dbs_draft')) and r.get('dbs_status')=='Review'),None)
    if row is None:row=doc.append('dbs',dict(contact_name=doc.name,dbs_status='Review',dbs_submission_date=frappe.utils.now_datetime()))
    row.set('dbs_file',file.file_url)
    row.set('dbs_reference',doc.get('portal_dbs_reference'))
    doc.set('portal_dbs_certificate_file',file.file_url);doc.save(ignore_permissions=True)
    frappe.db.set_value('Associate',doc.name,'portal_dbs_draft',row.name,update_modified=False);doc.reload()
    return dict(profile=_state(doc),suggestions={},warning='DBS certificate uploaded and saved for review.')
