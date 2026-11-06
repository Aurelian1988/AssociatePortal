"""Canonical format and uniqueness checks for Associate tax identifiers."""
import re
import frappe
from onemotion.api.profile_policy import normalise_nino

def normalise_passport(value):
    return re.sub(r'\s+', '', str(value or '')).upper()

def normalise_utr(value):
    return re.sub(r'\s+', '', str(value or ''))

def normalise_vat(value):
    return re.sub(r'\s+', '', str(value or '')).upper()

def identifier_errors(values, name=None):
    errors = {}
    for field, label, normalise, pattern in [
        ('passport_number','Passport number',normalise_passport,None),
        ('nino_number','National Insurance number',normalise_nino,r'[A-Z]{2}[0-9]{6}[A-Z]'),
        ('utr_number','UTR',normalise_utr,r'[0-9]{10}'),
        ('vat_number','VAT number',normalise_vat,r'GB[0-9]{9}'),
    ]:
        value = normalise(values.get(field))
        if not value: continue
        if pattern and not re.fullmatch(pattern,value):
            errors[field] = ('Use two letters, six digits and one final letter.' if field == 'nino_number' else 'Enter exactly 10 digits, for example 12345 67890. Do not include letters or punctuation.' if field == 'utr_number' else 'Start with GB followed by exactly nine digits, for example GB 123 4567 89. Do not include punctuation.')
            continue
        # Match legacy formatted values too; never disclose another record's identity.
        matches = frappe.db.sql(
            f"SELECT name FROM `tabAssociate` WHERE UPPER(REGEXP_REPLACE(COALESCE(`{field}`, ''), '[[:space:]]+', '')) = %s AND name != %s LIMIT 1",
            (value.upper(),name or ''),
        )
        if field == 'passport_number' and not matches:
            matches = frappe.db.sql("SELECT name FROM `tabPDM` WHERE UPPER(REGEXP_REPLACE(COALESCE(passp_number, ''), '[[:space:]]+', '')) = %s AND parent != %s LIMIT 1", (value,name or ''))
        if field == 'nino_number' and not matches:
            matches = frappe.db.sql("SELECT name FROM `tabNIM` WHERE UPPER(REGEXP_REPLACE(COALESCE(nim_nino_number, ''), '[[:space:]]+', '')) = %s AND parent != %s LIMIT 1", (value,name or ''))
        if matches: errors[field] = f'This {label} is already used by another ERP record. Check the number or contact your team.'
    return errors

def validate_associate_identifiers(doc, method=None):
    """Add to Associate validate hooks so desk edits follow the same rules."""
    errors = identifier_errors(doc,doc.name)
    if errors: frappe.throw('\n'.join(errors.values()),frappe.ValidationError)
    doc.passport_number = normalise_passport(doc.get('passport_number')) or None
    doc.nino_number = normalise_nino(doc.get('nino_number')) or None
    doc.utr_number = normalise_utr(doc.get('utr_number')) or None
    doc.vat_number = normalise_vat(doc.get('vat_number')) or None
    from onemotion.api.profile_approval_api import validate_document_approvals
    validate_document_approvals(doc)

def prepare_identifier_uniqueness(dry_run=True):
    """Bench-only deployment step. Refuse conflicting/invalid legacy data before changes.

    Run dry-run first. This is deliberately not whitelisted for web requests.
    Apply in a maintenance window, with a database backup and approval.
    """
    rows = frappe.get_all('Associate',fields=['name','passport_number','nino_number','utr_number','vat_number'])
    seen = {}; problems = []
    for row in rows:
        for field, normalise, pattern in [('passport_number',normalise_passport,None),('nino_number',normalise_nino,r'[A-Z]{2}[0-9]{6}[A-Z]'),('utr_number',normalise_utr,r'[0-9]{10}'),('vat_number',normalise_vat,r'GB[0-9]{9}')]:
            value = normalise(row.get(field))
            if not value: continue
            if pattern and not re.fullmatch(pattern,value): problems.append(dict(record=row.name,field=field,reason='invalid format'))
            key=(field,value)
            if key in seen: problems.append(dict(record=row.name,field=field,reason='duplicate',other_record=seen[key]))
            seen[key]=row.name
    if problems: return dict(ready=False,problems=problems)
    if dry_run: return dict(ready=True,records=len(rows),applied=False)
    for row in rows:
        frappe.db.set_value('Associate',row.name,dict(passport_number=normalise_passport(row.get('passport_number')) or None,nino_number=normalise_nino(row.get('nino_number')) or None,utr_number=normalise_utr(row.get('utr_number')) or None,vat_number=normalise_vat(row.get('vat_number')) or None),update_modified=False)
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    for field in ('passport_number','nino_number','utr_number','vat_number'):
        make_property_setter('Associate',field,'unique',1,'Check')
    frappe.db.updatedb('Associate')
    return dict(ready=True,records=len(rows),applied=True)
