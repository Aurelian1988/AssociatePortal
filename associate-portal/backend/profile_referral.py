"""Authenticated associate referrals for the isolated ERP test app."""
import re
import hashlib
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address,escape_html
from onemotion.api.profile_contact_start import require_test_access
from onemotion.api.portal_agreement_signing import actor

@frappe.whitelist(methods=['POST'])
@rate_limit(limit=5,seconds=3600,ip_based=True)
def send(first_name,last_name,email,phone):
    require_test_access()
    referrer=actor()
    first_name=str(first_name or '').strip();last_name=str(last_name or '').strip()
    email=str(email or '').strip().lower();phone=str(phone or '').strip()
    if not first_name or not last_name or max(len(first_name),len(last_name))>100:frappe.throw('Enter first and last names, up to 100 characters each.')
    validate_email_address(email,throw=True)
    if not re.fullmatch(r'\+?[0-9 ()-]{7,30}',phone) or not 7<=len(re.sub(r'\D','',phone))<=15:frappe.throw('Enter a valid phone number including its country code.')
    from onemotion.api.portal_onboarding import transaction_lock,_invite
    transaction_lock('portal-referral:'+hashlib.sha256(email.encode()).hexdigest())
    # Do not expose an existing applicant's identity or send unsolicited repeats.
    if frappe.db.exists('ATS Application',{'email':email}) or frappe.db.exists('User',email):
        return {'message':'Thank you. If these details are already registered, the team will handle the existing application.'}
    user=frappe.session.user
    try:
        # The authenticated associate may only create this fixed, validated referral.
        # Existing staff-only provisioning is not exposed to caller-supplied records.
        frappe.set_user('Administrator')
        application=frappe.get_doc({'doctype':'ATS Application','first_name':first_name,'last_name':last_name,'email':email,'mobile':phone,'application_status':'App Link Sent','onboarding_status':'ONBOARDING','advert_source':'Associate referral'})
        application.insert(ignore_permissions=True)
        application.add_comment('Info','Referred by Associate '+escape_html(str(referrer.name))+' via '+escape_html(user)+'. No referral payment has been approved.')
        _invite(application.name,queue_email=True)
    finally:frappe.set_user(user)
    return {'message':'Referral received. The onboarding invitation has been queued for email delivery.'}
