"""Contact-first entry for the new app; the legacy onboarding API is unchanged.

All writes use the authenticated invitation, run in one request transaction,
and take email/phone locks until commit. No record IDs are accepted from clients.
"""
import hashlib
import re
import frappe
from frappe.utils import now_datetime

DT = 'Portal Onboarding'
OPEN = {'Invited', 'Not Started', 'In Progress', 'Action Required', 'Changes Requested'}


def require_test_access():
    if frappe.session.user == 'Guest':
        frappe.throw('Please sign in.', frappe.AuthenticationError)
    allowed = frappe.conf.get('portal_contact_first_test_users') or []
    if frappe.session.user not in allowed:
        frappe.throw('This new-app test is not enabled for your account.', frappe.PermissionError)


@frappe.whitelist(allow_guest=True)
def bootstrap():
    return {'user':frappe.session.user, 'csrf_token':frappe.sessions.get_csrf_token()}


@frappe.whitelist()
def get_current_associate_info():
    require_test_access()
    record = invitation()
    if not record: frappe.throw('No invitation is linked to your account.', frappe.PermissionError)
    doc = linked_associate(record) if record.associate else draft_associate(record)
    return dict({key:doc.get(key) for key in ('name','first_name','middle_name','last_name','contact_name','id_photo','email','mobile','awr_status')}, onboarding_pending=not bool(record.associate))


def email_key(value):
    return str(value or '').strip().lower()


def normalise_phone(value):
    import phonenumbers
    try:
        number = phonenumbers.parse(str(value or '').strip(), 'GB')
        if not phonenumbers.is_valid_number(number): raise ValueError()
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    except (phonenumbers.NumberParseException, ValueError):
        frappe.throw('Enter a valid phone number. For a number outside the UK, include its country code.')


def decide_match(email_matches, phone_matches, linked=None):
    """Resolve only exact normalized contact matches; never merge people."""
    emails, phones = set(email_matches), set(phone_matches)
    if len(emails) > 1 or len(phones) > 1:
        raise ValueError('Contact details match more than one profile. Please contact the team.')
    if linked and ((emails and emails != {linked}) or (phones and phones != {linked})):
        raise ValueError('These contact details do not match your linked profile. Please contact the team.')
    if emails and phones and emails != phones:
        raise ValueError('We could not safely match these contact details. Please contact the team.')
    if phones and not emails and not linked:
        raise ValueError('This phone number needs an ownership check. Please contact the team before continuing.')
    return linked or next(iter(emails), None)


def invitation(lock=False):
    require_test_access()
    user = frappe.session.user
    if user == 'Guest': frappe.throw('Please sign in.', frappe.AuthenticationError)
    names = frappe.get_all(DT, filters={'user': user, 'status': ['!=', 'Cancelled']},
                           pluck='name', limit_page_length=3)
    if not names: return None
    if len(names) != 1:
        frappe.throw('More than one onboarding invitation is linked to your account. Please contact the team.')
    record = frappe.get_doc(DT, names[0], for_update=lock)
    if record.user != user: frappe.throw('This invitation does not belong to your account.', frappe.PermissionError)
    return record


def application(record):
    ats = frappe.get_doc('ATS Application', record.ats_application)
    email = email_key(ats.get('email'))
    frappe.utils.validate_email_address(email, throw=True)
    if email != email_key(record.user):
        frappe.throw('The invitation email no longer matches the application. Please contact the team.')
    return ats, email


def draft_associate(record):
    """Read-only draft: opening the app never creates an Associate."""
    from onemotion.api.portal_onboarding import ATS_MAP
    ats, email = application(record)
    doc = frappe.new_doc('Associate')
    for target, source in ATS_MAP.items():
        if ats.get(source) is not None: doc.set(target, ats.get(source))
    doc.email = email
    doc.flags.contact_first_draft = record.name
    return doc


def linked_associate(record):
    if not record.associate: return None
    ats, _ = application(record)
    if ats.get('cms_associate') and ats.cms_associate != record.associate:
        frappe.throw('The application and onboarding profile links conflict. Please contact the team.')
    return frappe.get_doc('Associate', record.associate)


def contact_matches(email, phone):
    # Include historical entries in collision checks, but only Personal/Work
    # addresses may establish email ownership. Other matches require review.
    email_rows = frappe.db.sql('''SELECT name AS owner FROM `tabAssociate`
        WHERE LOWER(TRIM(COALESCE(email,'')))=%s OR LOWER(TRIM(COALESCE(flex_email,'')))=%s
        UNION SELECT parent AS owner FROM `tabCDA` WHERE parenttype='Associate'
        AND LOWER(TRIM(COALESCE(cda_email,'')))=%s''', (email, email, email), as_dict=True)
    digits = phone.lstrip('+')
    aliases = {digits, '00' + digits}
    if digits.startswith('44'): aliases.add('0' + digits[2:])
    placeholders = ','.join(['%s'] * len(aliases))
    sql = '''SELECT name AS owner FROM `tabAssociate` WHERE
      REGEXP_REPLACE(COALESCE(mobile,''),'[^0-9]','') IN ({p}) OR
      REGEXP_REPLACE(COALESCE(mobile2,''),'[^0-9]','') IN ({p})
      UNION SELECT parent AS owner FROM `tabCDA` WHERE parenttype='Associate'
      AND REGEXP_REPLACE(COALESCE(cda_mobile,''),'[^0-9]','') IN ({p})'''.format(p=placeholders)
    phone_rows = frappe.db.sql(sql, tuple(aliases) * 3, as_dict=True)
    return {row.owner for row in email_rows}, {row.owner for row in phone_rows}


def trusted_email_owner(doc, email):
    if email in {email_key(doc.get('email')), email_key(doc.get('flex_email'))}: return True
    return any(email_key(row.get('cda_email')) == email and
               row.get('cda_type') in {'Personal', 'Work(OM)'} and
               row.get('audit_status') != 'Old' and row.get('cda_verified')
               for row in (doc.get('contact_details_archive') or []))


def start_contact(values):
    """Called only by first section submit; caller finishes/commits the stage."""
    from onemotion.api.portal_onboarding import transaction_lock, _provision
    if not isinstance(values, dict) or set(values) - {'email', 'mobile'}:
        frappe.throw('Only contact information can be saved here.', frappe.PermissionError)
    record = invitation()
    if not record: frappe.throw('No onboarding invitation is linked to this account.', frappe.PermissionError)
    ats, email = application(record)
    if 'email' in values and email_key(values['email']) != email:
        frappe.throw('Use the email address linked to your invitation.', frappe.PermissionError)
    phone = normalise_phone(values.get('mobile') or (linked_associate(record).get('mobile') if record.associate else ats.get('mobile')))
    # Stable ordering prevents deadlocks between concurrent first submissions.
    for key in sorted(['email:' + email, 'phone:' + phone]):
        transaction_lock('app-contact:' + hashlib.sha256(key.encode()).hexdigest())
    record = invitation(lock=True)
    if record.status not in OPEN:
        frappe.throw('This onboarding has already been submitted. Reopen your profile.')
    ats, email = application(record)
    frappe.db.sql('SELECT name FROM `tabATS Application` WHERE name=%s FOR UPDATE', (ats.name,))
    ats.reload()
    links = {str(v) for v in (record.associate, ats.get('cms_associate')) if v}
    if len(links) > 1: frappe.throw('The saved profile links conflict. Please contact the team.')
    linked = next(iter(links), None)
    emails, phones = contact_matches(email, phone)
    try: name = decide_match(emails, phones, linked)
    except ValueError as error: frappe.throw(str(error))
    if name:
        doc = frappe.get_doc('Associate', name, for_update=True)
        if not trusted_email_owner(doc, email):
            frappe.throw('The saved contact needs an ownership check. Please contact the team.')
    else:
        doc = _provision(ats, create=True)
    if not doc.meta.has_field('portal_onboarding_progress'):
        frappe.throw('The new app profile fields are not installed yet.')
    # Do not erase an existing primary address when a verified alternate matched.
    from onemotion.api.profile_child_records import sync_contacts
    sync_contacts(doc)
    if not doc.get('email'): doc.email = email
    doc.mobile = phone
    sync_contacts(doc)
    if email_key(doc.get('email')) != email:
        rows = doc.get('contact_details_archive') or []
        if not any(email_key(r.get('cda_email')) == email and r.get('cda_mobile') == phone for r in rows):
            doc.append('contact_details_archive', dict(cda_email=email, cda_mobile=phone,
                cda_type='Personal', contact_name=doc.name, cda_datetime_submited=now_datetime()))
    if doc.get('awr_status') != 'Active': doc.awr_status = 'On-Boarding'
    from onemotion.api.portal_onboarding import own_write
    with own_write(): doc.save(ignore_permissions=True)
    record.associate = doc.name
    record.status = 'In Progress'
    record.save(ignore_permissions=True)
    frappe.db.set_value('ATS Application', ats.name, 'cms_associate', doc.name)
    return doc


def sync_tracking(doc, state, completed=False):
    record = invitation(lock=True)
    if not record: return
    if record.associate != doc.name: frappe.throw('Onboarding profile link mismatch.', frappe.PermissionError)
    if record.status == 'Completed': return
    record.completion_percentage = state['completion']['percentage']
    if completed:
        record.profile_completed_at = record.profile_completed_at or now_datetime()
        record.submitted_at = record.submitted_at or now_datetime()
        record.status = 'Submitted'
    elif record.status in OPEN:
        record.status = 'In Progress'
    record.save(ignore_permissions=True)
