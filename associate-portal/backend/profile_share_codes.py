"""Onboarding share codes use the existing ERP history tables."""
import re
import frappe

CODES = {
    'portal_rtw_share_code': ('rtw_share_code_history', 'rtw_sc', 'rtw_status'),
    'portal_immigration_share_code': ('immigration_share_code_history', 'imi_sc', 'immigration_status'),
}

def normalise_code(value):
    return re.sub(r'\s+', '', str(value or '')).upper()

def read_codes(doc):
    result = {}
    for key, (table, field, _) in CODES.items():
        rows = doc.get(table) or []
        result[key] = rows[-1].get(field) if rows else ''
    return result

def stage_codes(doc, incoming):
    existing = read_codes(doc)
    for key, (table, field, status) in CODES.items():
        if key not in incoming: continue
        value = normalise_code(incoming[key])
        if value and not re.fullmatch(r'[A-Z0-9]{9}', value):
            frappe.throw('Enter the nine letters and digits shown in your share code. Spaces are removed automatically.')
        if value and key == 'portal_rtw_share_code' and not value.startswith('W'):
            frappe.throw('Use a right-to-work share code beginning with W. Generate a code for proving your right to work.')
        if value == normalise_code(existing[key]): continue
        if not doc.meta.has_field(table): frappe.throw('Share code setup is not ready. Please contact support.')
        # Append history; never alter the previous review or mark evidence approved.
        row=doc.append(table, {field:value, status:'Review'})
        for meta in row.meta.fields:
            if meta.fieldtype=='Link' and meta.options=='Associate': row.set(meta.fieldname,doc.name)
