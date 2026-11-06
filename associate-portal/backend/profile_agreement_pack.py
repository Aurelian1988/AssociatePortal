"""Test-app ACAP pack: seven acknowledgements, one atomic signature submission."""
import base64
import hashlib
import io
import json
import uuid
import frappe
from bs4 import BeautifulSoup
from PIL import Image
from frappe.utils import now_datetime, escape_html
from onemotion.api.portal_agreement_signing import actor, definition, signed, PACK
from onemotion.api.portal_agreement_renderer import render, build_pdf
from onemotion.api.profile_contact_start import require_test_access

FIELDS = tuple(PACK)
BACKGROUND = ('nca_agrement', 'apn_agrement')
VISIBLE = tuple(f for f in FIELDS if f not in BACKGROUND)
from onemotion.api.profile_agreement_layout import format_agreement, build_print_pdf

def clean_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    signature_pages = [p for p in soup.select('.agreement-page') if p.select_one('canvas')]
    for page in signature_pages:
        frame = page.find_parent(class_='desktop-frame')
        (frame or page).decompose()
    for el in soup.select('button, input[type=checkbox], canvas'):
        parent = el.find_parent('label')
        (parent or el).decompose()
    for page in soup.select('.agreement-page'):
        page['class'] = sorted(set(page.get('class', []) + ['active']))
    return format_agreement(str(soup))

def pages(doc):
    return [dict(field=f, label=definition(f)[1], html=clean_page(render(f, doc))) for f in FIELDS]

def digest(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()

@frappe.whitelist()
def read_pack():
    require_test_access()
    doc = actor()
    if signed(doc, 'acap_agreement'):
        frappe.throw('ACAP is already signed.')
    items = pages(doc)
    return dict(pages=[p for p in items if p["field"] in VISIBLE], background=[p for p in items if p["field"] in BACKGROUND], version=digest(items))

@frappe.whitelist(methods=['POST'])
def sign_pack(signature, version, acknowledgements, background_accepted=False):
    require_test_access()
    if isinstance(acknowledgements, str): acknowledgements = json.loads(acknowledgements)
    if acknowledgements != list(VISIBLE) or str(background_accepted).lower() not in ("true","1"):
        frappe.throw('Acknowledge each displayed agreement and confirm the additional documents before signing.')
    if not isinstance(signature, str) or not signature.startswith('data:image/png;base64,') or len(signature)>1000000:
        frappe.throw('A valid signature is required.')
    try:
        raw=base64.b64decode(signature.split(',',1)[1],validate=True)
        im=Image.open(io.BytesIO(raw));im.load()
        if im.format!='PNG' or im.width>2000 or im.height>1000 or len(set(im.convert('RGBA').getdata()))<2: raise ValueError()
    except Exception: frappe.throw('Please draw your signature.')
    doc=actor()
    with frappe.cache.lock('portal-agreement-sign:'+str(doc.name),timeout=300,blocking_timeout=0):
        doc.reload()
        if signed(doc,'acap_agreement'): frappe.throw('ACAP is already signed.')
        if digest(pages(doc)) != version: frappe.throw('An agreement has changed. Reopen ACAP and read the updated documents.')
        when=now_datetime();receipt=uuid.uuid4().hex
        htmls=[clean_page(render(f,doc,signature=signature,signed_at=when,receipt=receipt)) for f in FIELDS]
        # Keep one signed PDF per original field, and a complete ACAP pack PDF.
        combined=BeautifulSoup(htmls[0],'html.parser')
        for html in htmls[1:]:
            other=BeautifulSoup(html,'html.parser')
            for item in list(other.body.contents): combined.body.append(item)
        style=combined.new_tag('style');style.string='.agreement-page{display:block!important}.desktop-frame{page-break-after:always}'
        combined.head.append(style)
        payloads=[(f,build_print_pdf(html)) for f,html in zip(FIELDS,htmls)]
        from pypdf import PdfReader, PdfWriter
        writer=PdfWriter()
        for _,pdf in payloads:
            for page in PdfReader(io.BytesIO(pdf)).pages:writer.add_page(page)
        pack_output=io.BytesIO();writer.write(pack_output)
        payloads.append(('acap_agreement',pack_output.getvalue()))
        if any(not pdf or not pdf.startswith(b'%PDF') for _,pdf in payloads): frappe.throw('Document generation failed. Nothing has been signed.')
        changes={}
        for field,pdf in payloads:
            file=frappe.get_doc(dict(doctype='File',file_name='Portal_Pack_'+field+'_'+receipt+'.pdf',content=pdf,is_private=1,attached_to_doctype='Associate',attached_to_name=doc.name))
            file.save(ignore_permissions=True)
            changes[field]=frappe.db.get_value('File',file.name,'file_url') or file.file_url
            _,_,check,date=definition(field)
            if check:changes[check]=1
            if date:changes[date]=when.date()
        frappe.db.set_value('Associate',doc.name,changes)
        frappe.get_doc(dict(doctype='Comment',comment_type='Info',reference_doctype='Associate',reference_name=doc.name,content='ACAP pack signed once after five individual acknowledgements and explicit final consent covering NCA and APN. Receipt '+receipt+'; version '+escape_html(version)+'; user '+escape_html(frappe.session.user))).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_document_cache('Associate',doc.name)
        return dict(signed=True)


@frappe.whitelist()
def read_single(field):
    require_test_access()
    if field not in ('sba_agrement','dld_agrement'):frappe.throw('Unsupported agreement.')
    doc=actor()
    if field=='dld_agrement' and not dld_eligible(doc):frappe.throw('This declaration applies to EU licences only.')
    if signed(doc,field):frappe.throw('This agreement is already signed.')
    html=clean_page(render(field,doc))
    return dict(html=html,version=hashlib.sha256(html.encode()).hexdigest())

@frappe.whitelist(methods=['POST'])
def sign_single(field,signature,version,accepted=False):
    require_test_access()
    if field not in ('sba_agrement','dld_agrement') or str(accepted).lower() not in ('true','1'):frappe.throw('Read and accept the agreement first.')
    if not isinstance(signature,str) or not signature.startswith('data:image/png;base64,') or len(signature)>1000000:frappe.throw('A valid signature is required.')
    try:
        im=Image.open(io.BytesIO(base64.b64decode(signature.split(',',1)[1],validate=True)));im.load()
        if im.format!='PNG' or im.width>2000 or im.height>1000 or len(set(im.convert('RGBA').getdata()))<2:raise ValueError()
    except Exception:frappe.throw('Please draw your signature.')
    doc=actor()
    with frappe.cache.lock('portal-agreement-sign:'+str(doc.name),timeout=300,blocking_timeout=0):
        doc.reload()
        if field=='dld_agrement' and not dld_eligible(doc):frappe.throw('This declaration applies to EU licences only.')
        if signed(doc,field):frappe.throw('This agreement is already signed.')
        html=clean_page(render(field,doc))
        if hashlib.sha256(html.encode()).hexdigest()!=version:frappe.throw('The agreement changed. Reopen it before signing.')
        when=now_datetime();receipt=uuid.uuid4().hex
        pdf=build_print_pdf(clean_page(render(field,doc,signature=signature,signed_at=when,receipt=receipt)))
        if not pdf or not pdf.startswith(b'%PDF'):frappe.throw('Document generation failed.')
        file=frappe.get_doc(dict(doctype='File',file_name='Portal_'+field+'_'+receipt+'.pdf',content=pdf,is_private=1,attached_to_doctype='Associate',attached_to_name=doc.name));file.save(ignore_permissions=True)
        _,_,check,date=definition(field)
        frappe.db.set_value('Associate',doc.name,{field:frappe.db.get_value('File',file.name,'file_url') or file.file_url,check:1,date:when.date()})
        frappe.get_doc(dict(doctype='Comment',comment_type='Info',reference_doctype='Associate',reference_name=doc.name,content=definition(field)[1]+' signed; receipt '+receipt+'; version '+escape_html(version)+'; user '+escape_html(frappe.session.user))).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_document_cache('Associate',doc.name)
        return dict(signed=True)

def apn_visible(doc):
    from onemotion.api.profile_dbs import active_site,active_contracts,active_values
    return (any('amzl' in value.casefold() for value in active_values(active_site(doc),'site'))
            or any('amazon' in value.casefold() for value in active_values(active_contracts(doc),'contract_type'))
            or 'amzl' in str(doc.get('site') or '').casefold())

@frappe.whitelist()
def signed_documents(field=None):
    require_test_access()
    doc=actor()
    allowed=tuple(f for f in FIELDS if f!='nca_agrement' and (f!='apn_agrement' or apn_visible(doc)))+('sba_agrement',)+(('dld_agrement',) if dld_eligible(doc) else ())
    if field is None:
        return [dict(field=f,label=definition(f)[1]) for f in allowed if signed(doc,f) and doc.get(f)]
    if field not in allowed or not signed(doc,field) or not doc.get(field):
        frappe.throw('Signed document is not available.',frappe.PermissionError)
    # Resolve exclusively from the authenticated associate, never a caller's URL.
    name=frappe.db.get_value('File',dict(file_url=doc.get(field),attached_to_doctype='Associate',attached_to_name=doc.name),'name')
    if not name:frappe.throw('Signed document file is unavailable.')
    data=frappe.get_doc('File',name).get_content()
    if isinstance(data,str):data=data.encode()
    if not data.startswith(b'%PDF'):frappe.throw('Document preview is unavailable.')
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text_pages=[page.extract_text() or '' for page in pdf.pages]
    # Read-only rendition of the signing screen, using the saved signature image.
    from pypdf import PdfReader
    reading=BeautifulSoup(clean_page(render(field,doc)),'html.parser')
    for element in reading.select('.meta-clone,.sig-clone,.signature-section'):
        element.decompose()
    signature=None
    for page in PdfReader(io.BytesIO(data)).pages:
        for image in page.images:
            if image.image.size==(600,200):
                output=io.BytesIO();image.image.save(output,format='PNG')
                signature='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
                break
        if signature:break
    block=reading.new_tag('div',attrs={'class':'readonly-signature'})
    label=reading.new_tag('p')
    label.string=('Included in the pack and accepted at final signing.' if field in BACKGROUND else '✓ I have read, understood and agree to the terms of this agreement.')
    block.append(label)
    title=reading.new_tag('p');title.string='Signature';block.append(title)
    if signature:
        image=reading.new_tag('img',attrs={'src':signature,'alt':'Saved signature','style':'width:100%;max-width:300px;height:100px;object-fit:contain;border:1px solid #cbd5e1;border-radius:8px;background:white'})
        block.append(image)
    else:
        note=reading.new_tag('p');note.string='Signed — signature available in the original A4.';block.append(note)
    block['style']='padding:12px 8px;color:#075da8'
    reading.body.append(block)
    return dict(pdf=base64.b64encode(data).decode(),text_pages=text_pages,mobile_html=str(reading))


EU_COUNTRIES = {'Austria','Belgium','Bulgaria','Croatia','Cyprus','Czech Republic','Czechia','Denmark','Estonia','Finland','France','Germany','Greece','Hungary','Ireland','Italy','Latvia','Lithuania','Luxembourg','Malta','Netherlands','Poland','Portugal','Romania','Slovakia','Slovenia','Spain','Sweden'}
def dld_eligible(doc):
    return str(doc.get('dl_issuing_country') or '').strip().casefold() in {v.casefold() for v in EU_COUNTRIES} or str(doc.get('dl_type') or '').strip().casefold() in {'eu','european','full eu','full european'}

@frappe.whitelist()
def dld_status():
    require_test_access()
    doc=actor()
    is_signed=signed(doc,'dld_agrement')
    return dict(field='dld_agrement',label='EU Driving Licence Declaration',visible=dld_eligible(doc),signed=is_signed,can_sign=not is_signed,source='WebPage')
