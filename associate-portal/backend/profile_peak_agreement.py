"""Separate Peak 2026 agreement for the isolated associate test app."""
import base64,hashlib,io,uuid
from pathlib import Path
import frappe
from bs4 import BeautifulSoup
from PIL import Image
from frappe.utils import getdate,now_datetime,escape_html
from onemotion.api.profile_contact_start import require_test_access
from onemotion.api.portal_agreement_signing import actor
from onemotion.api.profile_agreement_layout import format_agreement,build_print_pdf
FIELD='peak_joining_2026'
LABEL='2026 Peak Joining Incentive Agreement'

def saved(doc,suffix='pdf'):
    return frappe.db.get_value('File',{'attached_to_doctype':'Associate','attached_to_name':doc.name,'file_name':['like','Peak2026_%.'+suffix]},'name',order_by='creation desc')

def eligible(doc):
    start=doc.get('start_date')
    return bool(start and getdate('2026-11-05')<=getdate(start)<=getdate('2026-12-31') and getdate()<=getdate('2026-12-31'))

def html_for(doc,signature=None,when=None):
    soup=BeautifulSoup(Path(__file__).with_name('templates').joinpath('peak_joining_2026.html').read_text(),'html.parser')
    for el in soup.select('.draft,.signature'):el.decompose()
    page=soup.new_tag('div',attrs={'class':'agreement-page'})
    for el in list(soup.body.contents):page.append(el.extract())
    soup.body.append(page)
    if signature:
        sig=soup.new_tag('div',attrs={'class':'sig-clone'});img=soup.new_tag('img',src=signature,alt='Saved signature');sig.append(img);page.append(sig)
        meta=soup.new_tag('div',attrs={'class':'meta-clone'});meta.string='Signed by '+str(doc.contact_name or doc.name)+' · '+str(when);page.append(meta)
    return format_agreement(str(soup))

@frappe.whitelist()
def status():
    require_test_access();doc=actor();signed=bool(saved(doc))
    return dict(field=FIELD,label=LABEL,source='WebPage',signed=signed,can_sign=not signed and eligible(doc),visible=signed or eligible(doc))

@frappe.whitelist()
def read(field=None):
    require_test_access();doc=actor()
    if saved(doc) or not eligible(doc):frappe.throw('This agreement is not available for signing.')
    html=html_for(doc);return dict(html=html,version=hashlib.sha256(html.encode()).hexdigest())

@frappe.whitelist(methods=['POST'])
def sign(signature,version,accepted=False,field=None):
    require_test_access();doc=actor()
    if str(accepted).lower() not in ('true','1'):frappe.throw('Read and accept the agreement first.')
    if not isinstance(signature,str) or not signature.startswith('data:image/png;base64,') or len(signature)>1000000:frappe.throw('Draw your signature.')
    try:
        image=Image.open(io.BytesIO(base64.b64decode(signature.split(',',1)[1],validate=True)));image.load()
        if image.format!='PNG' or image.width>2000 or image.height>1000 or len(set(image.convert('RGBA').getdata()))<2:raise ValueError()
    except Exception:frappe.throw('Draw your signature.')
    with frappe.cache.lock('peak-2026-sign:'+str(doc.name),timeout=90,blocking_timeout=0):
        doc.reload()
        if saved(doc) or not eligible(doc):frappe.throw('This agreement is not available for signing.')
        if hashlib.sha256(html_for(doc).encode()).hexdigest()!=version:frappe.throw('The agreement changed. Reopen it before signing.')
        when=now_datetime();receipt=uuid.uuid4().hex;html=html_for(doc,signature,when);pdf=build_print_pdf(html)
        if not pdf.startswith(b'%PDF'):frappe.throw('Document generation failed.')
        for ext,data in [('pdf',pdf),('txt',html)]:
            frappe.get_doc(dict(doctype='File',file_name='Peak2026_'+receipt+'.'+ext,content=data,is_private=1,attached_to_doctype='Associate',attached_to_name=doc.name)).save(ignore_permissions=True)
        frappe.get_doc(dict(doctype='Comment',comment_type='Info',reference_doctype='Associate',reference_name=doc.name,content='2026 Peak Joining Incentive Agreement signed by '+escape_html(frappe.session.user)+'; receipt '+receipt+'. Eligibility: Start Date '+str(doc.start_date)+'.')).insert(ignore_permissions=True)
        frappe.db.commit()
    return dict(signed=True)

@frappe.whitelist()
def preview(field=None):
    require_test_access();doc=actor();pdf_name=saved(doc);html_name=saved(doc,'txt')
    if not pdf_name or not html_name:frappe.throw('Signed agreement is unavailable.',frappe.PermissionError)
    pdf=frappe.get_doc('File',pdf_name).get_content();html=frappe.get_doc('File',html_name).get_content()
    if isinstance(html,bytes):html=html.decode()
    return dict(pdf=base64.b64encode(pdf).decode(),mobile_html=html,text_pages=[])
