"""Files DBS share-code entry for applicable assignments."""
import frappe
from onemotion.api.profile_contact_start import require_test_access
from onemotion.api.profile_onboarding import _associate
from onemotion.api.profile_dbs import active_site,active_contracts,active_values

def eligible(doc):
    values=active_values(active_site(doc),'site')+active_values(active_contracts(doc),'contract_type')
    return any(company in value.casefold() for value in values for company in ('fedex','dpd','dhl'))

@frappe.whitelist()
def status():
    require_test_access();doc=_associate()
    return dict(visible=eligible(doc))

@frappe.whitelist(methods=['POST'])
def save(share_code):
    require_test_access();doc=_associate()
    if not eligible(doc):frappe.throw('DBS is not applicable to your current assignments.',frappe.PermissionError)
    value=str(share_code or '').strip()
    if not value or len(value)>140:frappe.throw('Enter your DBS share code.')
    frappe.db.sql('SELECT name FROM `tabAssociate` WHERE name=%s FOR UPDATE',doc.name);doc.reload()
    from onemotion.api.profile_child_records import append_if_changed
    append_if_changed(doc,'dbs',{'dbs_sharecode':value,'document_type':'DBS UK'},['dbs_sharecode','document_type'],'dbs_status','dbs_submission_date')
    from onemotion.api.portal_onboarding import own_write
    with own_write():doc.save(ignore_permissions=True)
    return dict(saved=True)
