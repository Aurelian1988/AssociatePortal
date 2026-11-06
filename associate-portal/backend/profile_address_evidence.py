"""Proof-of-address OCR extraction and the requested name/date acceptance rule."""
import calendar
import re
import unicodedata
from datetime import date
try:
    from onemotion.api.profile_document_ocr import date_value
except ModuleNotFoundError:
    from profile_document_ocr import date_value


def canonical_name(value):
    return ' '.join(re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',str(value or '')).casefold()))


def name_found(text, last_name):
    name=canonical_name(last_name)
    return bool(name and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',canonical_name(text)))


def six_months_before(today):
    month_index=today.year*12+today.month-1-6
    year,month=divmod(month_index,12);month+=1
    return date(year,month,min(today.day,calendar.monthrange(year,month)[1]))


def evidence_status(matched_name,last_name,document_date,today=None):
    today=today or date.today()
    if not canonical_name(last_name) or canonical_name(matched_name)!=canonical_name(last_name): return 'Review'
    try: issued=date.fromisoformat(str(document_date)[:10])
    except (ValueError,TypeError): return 'Review'
    return 'Accepted' if six_months_before(today)<=issued<=today else 'Review'


def address_candidates(text,last_name):
    lines=[line.strip().strip('|.,; ') for line in text.splitlines() if line.strip()]
    candidates=[]
    for i,line in enumerate(lines):
        match=re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b',line,re.I)
        if not match: continue
        name_index=next((j for j in range(max(0,i-7),i) if name_found(lines[j],last_name)),None)
        if name_index is None: continue
        block=lines[name_index+1:i]
        if not block: continue
        code=re.sub(r'\s+','',match.group(1)).upper()
        suggestion={'postal_code':code[:-3]+' '+code[-3:],'country':'United Kingdom'}
        if len(block)>=2 and not re.search(r'\d',block[-1]):
            city=block.pop()
            town_county=re.fullmatch(r"([A-Z][A-Z '-]+)\s+([A-Z][a-z].*)",city)
            if town_county:
                suggestion['city']=town_county.group(1).strip().title()
                suggestion['state_region']=town_county.group(2).strip()
            else: suggestion['city']=city.title() if city.isupper() else city
        street=', '.join(block)
        suggestion['street_address']=street.title() if street.isupper() else street
        if suggestion['street_address']: candidates.append(suggestion)
    return candidates


def extract_address_evidence(text,last_name,today=None,recipient_texts=None):
    dates=[]
    for match in re.finditer(r'(?im)^\s*(?:document\s*date|invoice\s*date|bill\s*date|statement\s*date|issue\s*date|date\s*of\s*issue|dated|date)\s*[:.\-]?\s*([^\n]+)',text):
        candidate=date_value(match.group(1))
        if candidate and candidate not in dates: dates.append(candidate)
    document_date=dates[0] if len(dates)==1 else None
    blocks=recipient_texts if recipient_texts is not None else [text]
    matched=last_name if name_found(text+'\n'+'\n'.join(blocks),last_name) else ''
    candidates=[]
    for block in blocks:
        for suggestion in address_candidates(block,last_name):
            if suggestion not in candidates: candidates.append(suggestion)
    suggestions=candidates[0] if len(candidates)==1 else {}
    status=evidence_status(matched,last_name,document_date,today)
    if len(candidates)>1: status='Review'
    return dict(suggestions=suggestions,document_date=document_date,matched_name=matched,status=status)
