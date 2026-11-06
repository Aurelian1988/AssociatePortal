"""Conservative labelled-field extraction; never guess dates from their ordering."""
import re
import unicodedata
from datetime import datetime, date


def labelled(text, labels):
    pattern = r'(?im)^\s*(?:' + labels + r')\s*[:.\-]?\s*([^\n]+)'
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


MONTHS = {
    'JAN':1,'JANV':1,'JANUARY':1,'JANVIER':1,
    'FEB':2,'FEV':2,'FEVR':2,'FEBRUARY':2,'FEVRIER':2,
    'MAR':3,'MARS':3,'MARCH':3,'APR':4,'AVR':4,'APRIL':4,'AVRIL':4,
    'MAY':5,'MAI':5,'JUN':6,'JUIN':6,'JUNE':6,
    'JUL':7,'JUIL':7,'JULY':7,'JUILLET':7,'AUG':8,'AOUT':8,'AUGUST':8,
    'SEP':9,'SEPT':9,'SEPTEMBER':9,'SEPTEMBRE':9,
    'OCT':10,'OCTOBER':10,'OCTOBRE':10,'NOV':11,'NOVEMBER':11,'NOVEMBRE':11,
    'DEC':12,'DECEMBER':12,'DECEMBRE':12,
}


def date_value(value, field=None, context=None):
    if not value: return None
    for fmt in ('%d %b %Y','%d %B %Y','%d/%m/%Y','%d.%m.%Y','%d %m %Y','%d-%m-%Y','%Y-%m-%d'):
        try: return datetime.strptime(value.strip(),fmt).date().isoformat()
        except ValueError: pass
    normalized=''.join(c for c in unicodedata.normalize('NFKD',value.upper()) if not unicodedata.combining(c))
    match=re.fullmatch(r'\s*(\d{1,2})\s+([A-Z]{3,10})\.?(?:\s*/\s*([A-Z]{3,10})\.?)?\s+(\d{2}|\d{4})\s*',normalized)
    if not match:return None
    day,month,translation,year=match.groups();month=MONTHS.get(month)
    if not month or (translation and MONTHS.get(translation)!=month):return None
    years=[int(year)] if len(year)==4 else [1900+int(year),2000+int(year),2100+int(year)]
    possible=[]
    for candidate_year in years:
        try:candidate=date(candidate_year,month,int(day))
        except ValueError:continue
        if len(year)==2:
            context=context or {}
            anchor=context.get('passport_expiry_date' if field=='passport_issue_date' else field)
            try:anchor=date.fromisoformat(anchor)
            except (ValueError,TypeError):continue
            if field=='passport_issue_date':
                if not (0<=(anchor-candidate).days<=365.25*20 and candidate<=date.today()):continue
            elif candidate!=anchor:continue
        possible.append(candidate.isoformat())
    if len(possible)==1:return possible[0]
    return None


DATE_TOKEN = r'(?:\d{4}-\d{2}-\d{2}|\d{1,2}[./ -]\d{1,2}[./ -]\d{4}|\d{1,2}\s+[A-Za-zÀ-ÿ]{3,10}\.?(?:\s*/\s*[A-Za-zÀ-ÿ]{3,10}\.?)?\s+(?:\d{4}|\d{2}))(?!\d)'


def labelled_date(text, labels, field=None, context=None):
    """Read only a date alongside a label, or directly underneath it."""
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    for i,line in enumerate(lines):
        match=re.search(r'(?i)(?<!\w)(?:'+labels+r')(?!\w)',line)
        if not match: continue
        following=lines[i+1] if i+1<len(lines) else ''
        if re.match(r'(?i)(?:4\s*[ab]\.?|date\s+of\s+|expiry\s+date)',following):following=''
        for candidate in [line[match.end():],following]:
            date_match=re.search(DATE_TOKEN,candidate)
            if date_match:
                value=date_value(date_match.group(),field,context)
                if value:return value
    return None


def extract_fields(text, kind, context=None):
    result = {}
    if kind == 'passport':
        result.update(mrz_passport(text))
        date_context={**(context or {}),**result}
        labels = {
            'passport_number':r'passport\s*(?:number|no\.?)',
            'passport_issuing_country':r'(?:issuing\s*country|country\s*of\s*issue)',
            'first_name':r'(?:given\s*names?|first\s*name)', 'last_name':r'(?:surname|last\s*name)',
            'birth_country':r'country\s*of\s*birth',
            'birth_nationality':r'(?:nationality\s*at\s*birth|birth\s*nationality)',
            'birthpassport_gender':r'(?:sex|gender)',
            'passport_issue_date':r'(?:date\s*of\s*issue|de\s*d[ée]livrance)(?:\s*/\s*date\s*of\s*issue)?', 'passport_expiry_date':r'(?:date\s*of\s*expiry|expiry\s*date|date\s*d[’\']expiration)(?:\s*/\s*date\s*of\s*expiry)?',
            'dob':r'date\s*of\s*birth',
        }
        for key, pattern in labels.items():
            value = labelled(text,pattern)
            if key in {'passport_issue_date','passport_expiry_date','dob'}: value = labelled_date(text,pattern,key,date_context)
            if value: result[key] = value
        # Current passport nationality is a suggestion to review, not proof of nationality at birth.
        nationality = labelled(text,r'nationality')
        if nationality: result['_passport_nationality'] = nationality
        birthplace = labelled(text,r'place\s*of\s*birth')
        if birthplace:
            result['_place_of_birth'] = birthplace
            result['birth_city'] = birthplace.title() if birthplace.isupper() else birthplace
    else:
        if kind=='licence_front':
            surname=labelled(text,r'(?:1\.|surname|last\s*name)')
            given=labelled(text,r'(?:2\.|given\s*names?|first\s*name)')
            if surname and re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",surname):result['last_name']=surname.title() if surname.isupper() else surname
            if given and re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",given):
                names=given.split();result['first_name']=names[0].title() if names[0].isupper() else names[0]
                if len(names)>1:result['middle_name']=' '.join(names[1:]).title() if given.isupper() else ' '.join(names[1:])
            birth=labelled_date(text,r'(?:^3\.|date\s*of\s*birth)')
            if birth:result['dob']=birth
        number = labelled(text,r'(?:5\.|licen[cs]e\s*(?:number|no\.?)|driver\s*number)')
        # UK field 5 has a separate two-digit card issue number beside it.
        # Keep that suffix out of the 16-character driver number.
        uk_number=re.search(r'(?<![A-Z0-9])[A-Z9]{5}\d{6}[A-Z9]{2}\d[A-Z]{2}(?![A-Z])',text.upper())
        if uk_number: result['dl_number']=uk_number.group()
        elif number: result['dl_number'] = re.sub(r'\s+','',number).upper()
        country = labelled(text,r'(?:issuing\s*country|country\s*of\s*issue)')
        if country: result['dl_issuing_country'] = country
        elif re.search(r'\b(?:DVLA|DVLNI)\b',text,re.I): result['dl_issuing_country'] = 'United Kingdom'
        date_labels=[('dl_expiry_date',r'(?:licen[cs]e\s*expiry|entitlement\s*expiry)')] if kind=='licence_back' else [('dl_issue_date',r'(?:4\s*a\.?|date\s*of\s*issue)'),('dl_photocard_expiry',r'(?:4\s*b\.?|photocard\s*expiry)')]
        for key, label in date_labels:
            value = labelled_date(text,label)
            if value: result[key]=value
    return result

# TD3 offsets/check digits: ICAO Doc 9303 Part 4 (passport MRZ).
def check_digit(value):
    weights=(7,3,1)
    def number(c): return 0 if c=='<' else int(c) if c.isdigit() else ord(c)-55
    return str(sum(number(c)*weights[i%3] for i,c in enumerate(value))%10)


def mrz_passport(text):
    from datetime import date
    lines=[re.sub(r'\s+','',line.upper()) for line in text.splitlines()]
    for i,first in enumerate(lines[:-1]):
        second=lines[i+1]
        if len(first)!=44 or len(second)!=44 or not first.startswith('P') or not re.fullmatch(r'[A-Z<]{44}',first) or not re.fullmatch(r'[A-Z0-9<]{44}',second): continue
        if any(check_digit(value)!=digit for value,digit in [(second[:9],second[9]),(second[13:19],second[19]),(second[21:27],second[27]),(second[:10]+second[13:20]+second[21:43],second[43])]): continue
        result={'passport_number':second[:9].replace('<',''),'_issuing_country_code':first[2:5],'_passport_nationality':second[10:13]}
        names=first[5:].split('<<',1)
        result['last_name']=names[0].replace('<',' ').strip().title()
        if len(names)>1:
            given=names[1].replace('<',' ').strip().split()
            if given: result['first_name']=given[0].title()
            if len(given)>1: result['middle_name']=' '.join(given[1:]).title()
        if second[20] in 'MF': result['birthpassport_gender']={'M':'Male','F':'Female'}[second[20]]
        for key,raw in [('dob',second[13:19]),('passport_expiry_date',second[21:27])]:
            if not raw.isdigit(): continue
            candidates=[]
            for century in (1900,2000,2100):
                try: candidates.append(date(century+int(raw[:2]),int(raw[2:4]),int(raw[4:6])))
                except ValueError: pass
            today=date.today()
            candidates=[d for d in candidates if (0<=(today-d).days<=365.25*100 if key=='dob' else abs((d-today).days)<365.25*30)]
            if len(candidates)==1: result[key]=candidates[0].isoformat()
        return result
    return {}
