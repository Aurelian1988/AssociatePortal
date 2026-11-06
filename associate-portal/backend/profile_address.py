import re
import frappe

def proper_address(value):
    text = str(value or '').strip()
    return text.title() if text.isupper() else text

def normalise_address(values):
    result = dict(values)
    for key in ('street_address','city','state_region'):
        if key in result: result[key] = proper_address(result[key])
    if 'postal_code' in result:
        postcode = re.sub(r'\s+','',str(result['postal_code'] or '')).upper()
        result['postal_code'] = postcode[:-3] + ' ' + postcode[-3:] if re.fullmatch(r'[A-Z]{1,2}[0-9][A-Z0-9]?[0-9][A-Z]{2}',postcode) else str(result['postal_code'] or '').strip().upper()
    return result

@frappe.whitelist()
def lookup_address(postcode, page=0):
    from onemotion.api.profile_onboarding import _associate
    _associate()
    key = frappe.conf.get('associate_address_lookup_api_key')
    if not key: frappe.throw('Address lookup is not available yet. Please enter your address manually.')
    code = re.sub(r'\s+','',str(postcode or '')).upper()
    if not re.fullmatch(r'(?:GIR0AA|[A-Z]{1,2}[0-9][A-Z0-9]?[0-9][A-Z]{2})',code):
        frappe.throw('Enter a UK postcode, for example SW1A 2AA.')
    try: page = int(page)
    except (TypeError,ValueError): frappe.throw('Invalid address page.')
    if not 0 <= page <= 20: frappe.throw('Invalid address page.')
    # API key stays on the server. Only the postcode is sent to the provider.
    import requests
    try:
        response = requests.get('https://api.ideal-postcodes.co.uk/v1/postcodes/' + code,
            headers={'Authorization': 'api_key="' + key + '"'}, params={'context':'GBR','page':page},timeout=10)
        if response.status_code == 404: return dict(addresses=[],has_more=False)
        response.raise_for_status()
        rows = response.json().get('result',[])
        if not isinstance(rows,list): raise ValueError('invalid lookup response')
    except (requests.RequestException,ValueError):
        frappe.throw('Address lookup is unavailable. Try again or enter your address manually.')
    addresses=[]
    for row in rows:
        address = normalise_address(dict(street_address=', '.join(row.get(k,'') for k in ('line_1','line_2','line_3') if row.get(k)),city=row.get('post_town',''),state_region=row.get('county',''),postal_code=row.get('postcode',''),country='United Kingdom'))
        addresses.append(address)
    return dict(addresses=addresses,has_more=len(rows)==100)
