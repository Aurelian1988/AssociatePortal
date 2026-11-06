"""DBS applicability is determined from the trusted ERP Active Site field."""
import frappe


def needs_dbs(active_site):
    # An empty assignment does not contain the exemption marker.
    if isinstance(active_site,(list,tuple)):
        sites=[row.get('site') if hasattr(row,'get') else row for row in active_site]
        return not any('AMZL-' in str(site or '').upper() for site in sites)
    return 'AMZL-' not in str(active_site or '').upper()


def active_site(doc):
    configured = frappe.conf.get('associate_active_site_field')
    if configured:
        if not doc.meta.has_field(configured): frappe.throw('The ERP Active Site mapping needs to be configured by your team.')
        return doc.get(configured)
    matches = [f.fieldname for f in doc.meta.fields if str(f.label or '').strip().casefold() == 'active site']
    if len(matches) == 1: return doc.get(matches[0])
    if doc.meta.has_field('active_site'): return doc.get('active_site')
    # Do not substitute Base Site or let a client-provided value waive this requirement.
    frappe.throw('The ERP Active Site mapping needs to be configured by your team.')


def dbs_required(doc):return needs_dbs(active_site(doc))

def needs_share_guidance(site):
    if isinstance(site,(list,tuple)):
        return any(needs_share_guidance(row.get('site') if hasattr(row,'get') else row) for row in site)
    return any(company in str(site or '').casefold() for company in ('fedex','dpd','evri','ups','dhl'))


def active_values(value,key):
    if isinstance(value,(list,tuple)):
        return [str(row.get(key) or '') if hasattr(row,'get') else str(row or '') for row in value if not hasattr(row,'get') or str(row.get('audit_status') or '').casefold()!='old']
    return [str(value or '')]


def active_contracts(doc):
    configured=frappe.conf.get('associate_active_contract_field')
    if configured:
        if not doc.meta.has_field(configured):frappe.throw('The ERP Active Contract mapping needs to be configured by your team.')
        return doc.get(configured)
    matches=[f.fieldname for f in doc.meta.fields if str(f.label or '').strip().casefold() in {'contract active','active contract'}]
    if len(matches)==1:return doc.get(matches[0])
    # Verified ERP Contract table; historical rows marked Old are excluded below.
    return doc.get('contract_type') if doc.meta.has_field('contract_type') else None


def is_amazon_site(site,contracts=None):
    site_match=any(any(marker in value.casefold() for marker in ('amzl-','pf-','inpo-')) for value in active_values(site,'site'))
    contract_match=any(any(marker in ''.join(value.casefold().split()) for marker in ('amazon','parcelforce','inpost')) for value in active_values(contracts,'contract_type'))
    return site_match or contract_match
