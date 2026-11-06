"""Country-filtered populated-place search. No names or document images are sent."""
import json,re,unicodedata
from urllib.parse import urlencode
from urllib.request import Request,urlopen
try:from .profile_country_codes import COUNTRY_CODES
except ImportError:from profile_country_codes import COUNTRY_CODES

PLACE_TYPES={'city','town','village','hamlet'}
def country_code(country):
    return COUNTRY_CODES.get(str(country or '').strip().casefold())
def valid_place_name(value):
    value=str(value or '').strip()
    return 2<=len(value)<=140 and sum(c.isalpha() for c in value)>=2 and not any(unicodedata.category(c).startswith('C') for c in value) and all(c.isalnum() or c.isspace() or c in "-'’.,()/" or unicodedata.category(c).startswith('M') for c in value)
def search_places(country,query,endpoint='https://photon.komoot.io/api/'):
    code=country_code(country);query=str(query or '').strip()
    if not code:raise ValueError('Search is unavailable for this country. You can enter your birthplace manually for review.')
    if not 2<=len(query)<=100:return dict(places=[],country_code=code)
    params=[('q',query),('countrycode',code),('limit','12'),('lang','en')]+[('osm_tag','place:'+t) for t in sorted(PLACE_TYPES)]
    request=Request(endpoint.rstrip('/')+'/?'+urlencode(params),headers={'User-Agent':'OneMotion-Associate-Onboarding/1.0'})
    with urlopen(request,timeout=6) as response:
        raw=response.read(250001)
        if len(raw)>250000:raise ValueError('Location search is unavailable. Please try again or enter your birthplace manually.')
        data=json.loads(raw)
    result=[];seen=set()
    for feature in data.get('features',[]):
        p=feature.get('properties',{})
        if p.get('countrycode','').upper()!=code or p.get('osm_key')!='place' or p.get('osm_value') not in PLACE_TYPES:continue
        name=p.get('name','');region=p.get('state') or p.get('county') or ''
        # UK constituent countries share GB, so restrict those explicit choices too.
        if str(country).casefold() in {'england','scotland','wales','northern ireland'} and str(country).casefold() not in str(p).casefold():continue
        if not valid_place_name(name):continue
        key=(name.casefold(),region.casefold())
        if key in seen:continue
        seen.add(key)
        result.append(dict(name=name,region=region,country=country,country_code=code,label=', '.join(dict.fromkeys(x for x in (name,region,country) if x)),reference='osm:'+str(p.get('osm_type',''))+':'+str(p.get('osm_id',''))))
    return dict(places=result,country_code=code)

if __name__=='__main__':
    import sys
    try:
        params=json.load(sys.stdin);print(json.dumps(search_places(params.get('country'),params.get('query'))))
    except Exception:print(json.dumps({'error':'Location search is unavailable. Try again or enter your birthplace manually for review.'}))
