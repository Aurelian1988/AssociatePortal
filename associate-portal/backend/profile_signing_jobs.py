"""Durable, owner-scoped background signing for the test app."""
import json,base64,io
import frappe
from PIL import Image
from frappe.utils import now_datetime,add_to_date
from onemotion.api.profile_contact_start import require_test_access
from onemotion.api.portal_agreement_signing import actor
SERVICE='Associate agreement signing'

@frappe.whitelist(methods=['POST'])
def submit(kind,payload):
    require_test_access();doc=actor()
    if kind not in ('pack','sba','peak','dld'):frappe.throw('Unsupported agreement.')
    if isinstance(payload,str):payload=json.loads(payload)
    signature=payload.get('signature','')
    try:
        if not signature.startswith('data:image/png;base64,') or len(signature)>1000000:raise ValueError()
        im=Image.open(io.BytesIO(base64.b64decode(signature.split(',',1)[1],validate=True)));im.load()
        if im.format!='PNG' or im.width>2000 or im.height>1000 or len(set(im.convert('RGBA').getdata()))<2:raise ValueError()
    except Exception:frappe.throw('Draw your signature before submitting.')
    if kind=='pack':
        from onemotion.api.profile_agreement_pack import VISIBLE
        if payload.get('acknowledgements')!=list(VISIBLE) or not payload.get('background_accepted'):frappe.throw('Accept the agreements first.')
        keys=('signature','version','acknowledgements','background_accepted')
    else:
        if not payload.get('accepted'):frappe.throw('Accept the agreement first.')
        keys=('signature','version','accepted')
    with frappe.cache.lock('signing-receipt:'+str(doc.name)+':'+kind,timeout=15,blocking_timeout=0):
        existing=frappe.db.get_value('Integration Request',{'integration_request_service':SERVICE,'reference_docname':doc.name,'request_description':kind,'status':['in',['Queued','Authorized']]},'name')
        if existing:return {'queued':True}
        data={'user':frappe.session.user,'payload':{k:payload.get(k) for k in keys},'kind':kind}
        record=frappe.get_doc(dict(doctype='Integration Request',integration_request_service=SERVICE,request_description=kind,status='Queued',reference_doctype='Associate',reference_docname=doc.name,data=json.dumps(data)))
        record.insert(ignore_permissions=True)
        frappe.enqueue('onemotion.api.profile_signing_jobs.process',queue='long',timeout=600,enqueue_after_commit=True,record_name=record.name)
    return {'queued':True}

def process(record_name):
    record=frappe.get_doc('Integration Request',record_name)
    if record.integration_request_service!=SERVICE or record.status!='Queued':return
    data=json.loads(record.data);user=frappe.session.user
    try:
        frappe.set_user(data['user']);require_test_access()
        if str(actor().name)!=str(record.reference_docname):raise ValueError('Profile changed')
        record.db_set('status','Authorized');frappe.db.commit()
        payload=data['payload']
        if data['kind']=='pack':
            from onemotion.api.profile_agreement_pack import sign_pack
            sign_pack(**payload)
        elif data['kind'] in ('sba','dld'):
            from onemotion.api.profile_agreement_pack import sign_single
            sign_single(field='dld_agrement' if data['kind']=='dld' else 'sba_agrement',**payload)
        else:
            from onemotion.api.profile_peak_agreement import sign
            sign(**payload)
        frappe.db.set_value('Integration Request',record.name,{'status':'Completed','data':json.dumps({'user':data['user'],'kind':data['kind']}),'output':'Signed documents saved.'})
        frappe.db.commit()
    except Exception:
        frappe.db.rollback();frappe.log_error(title='Background agreement signing failed')
        frappe.db.set_value('Integration Request',record.name,{'status':'Failed','error':'Signing could not finish. Please reopen the agreement and try again.','data':json.dumps({'user':data['user'],'kind':data['kind']})});frappe.db.commit()
    finally:frappe.set_user(user)

@frappe.whitelist()
def status():
    require_test_access();doc=actor()
    rows = frappe.get_all('Integration Request',filters={'integration_request_service':SERVICE,'reference_docname':doc.name,'creation':['>',add_to_date(now_datetime(),hours=-2)]},fields=['name','request_description','status'],order_by='creation desc',limit_page_length=10)

    # Report only the latest attempt per agreement, so old failures cannot contradict success.
    latest={}
    for row in rows:
        latest.setdefault(row.request_description,row)
    return list(latest.values())
