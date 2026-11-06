"""Authenticated birthplace selection and explicit manual-review fallback."""
import uuid,hashlib
import frappe
from onemotion.api.profile_birthplaces import search_places,country_code,valid_place_name
META={'portal_birthplace_status','portal_birthplace_country','portal_birthplace_reference','portal_birthplace_manual'}
CHOICE_ERROR='Choose a birthplace from the list, or enter it manually for review.'

@frappe.whitelist()
def lookup_birthplaces(country,query):
    from onemotion.api.profile_onboarding import _associate
    _associate()
    query=str(query or '').strip()
    if not 2<=len(query)<=100:return dict(places=[])
    cache=frappe.cache()
    key='portal-birthplaces:'+hashlib.sha256((str(country)+'|'+query.casefold()).encode()).hexdigest()
    data=cache.get_value(key)
    if data is None:
        try:data=search_places(country,query,frappe.conf.get('associate_birthplace_search_url') or 'https://photon.komoot.io/api/')
        except Exception:frappe.throw('Location search is unavailable. Try again or enter your birthplace manually for review.')
        cache.set_value(key,data,expires_in_sec=600)
    places=[]
    for place in data['places']:
        token=uuid.uuid4().hex
        cache.set_value('portal-birthplace:'+frappe.session.user+':'+token,place,expires_in_sec=3600)
        places.append({**place,'token':token})
    return dict(places=places)

def apply_birthplace(doc,incoming):
    token=incoming.pop('portal_birthplace_token',None)
    manual=incoming.pop('portal_birthplace_manual',None)
    country=incoming.get('birth_country',doc.get('birth_country'))
    city=incoming.get('birth_city',doc.get('birth_city'))
    changed=any(k in incoming and incoming[k]!=doc.get(k) for k in ('birth_country','birth_city'))
    if not changed and not token and manual is None:return
    if token:
        if not isinstance(token,str) or len(token)>100:frappe.throw('Select your birthplace again.')
        place=frappe.cache().get_value('portal-birthplace:'+frappe.session.user+':'+token)
        if not place or place['country']!=country or place['name']!=city:frappe.throw('Select your birthplace again for the chosen country.')
        status='Matched';reference=place['reference'];manual=0
    elif str(manual).lower() in {'1','true'}:
        if not country or not valid_place_name(city):frappe.throw('Enter a town, city or village name and select its country.')
        status='Review';reference='';manual=1
    else:
        status='';reference='';manual=0
        if country!=doc.get('birth_country') and 'birth_city' not in incoming:incoming['birth_city']=''
    doc.set('portal_birthplace_status',status)
    doc.set('portal_birthplace_country',country if status else '')
    doc.set('portal_birthplace_reference',reference)
    doc.set('portal_birthplace_manual',manual)
