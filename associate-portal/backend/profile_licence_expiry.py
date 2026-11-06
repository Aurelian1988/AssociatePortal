"""Conservative UK rear-table expiry extraction from OCR word positions."""
import re
from datetime import date


def table_date(text, today=None):
    match=re.fullmatch(r'(\d{1,2})[./](\d{1,2})[./](\d{2}|\d{4})',text.strip())
    if not match:return None
    day,month,year=match.groups();today=today or date.today()
    years=[int(year)] if len(year)==4 else [1900+int(year),2000+int(year),2100+int(year)]
    possible=[]
    for y in years:
        try:value=date(y,int(month),int(day))
        except ValueError:continue
        # Out-of-window historical dates require manual review, not a guessed century.
        if today.year-20<=y<today.year+80:possible.append(value.isoformat())
    return possible[0] if len(possible)==1 else None


def rear_expiry(data,width,height,today=None):
    words=[dict(text=t.strip(),x=data['left'][i]+data['width'][i]/2,y=data['top'][i],h=data['height'][i],confidence=float(data['conf'][i])) for i,t in enumerate(data['text']) if t.strip()]
    headers={}
    for w in words:
        label=w['text'].strip('., ')
        if label in {'9','10','11','12'} and w['y']<height*.25:headers.setdefault(label,w)
    if not all(k in headers for k in ('10','12')):return None
    b,d=(headers[k] for k in ('10','12'))
    if abs(b['y']-d['y'])>height*.06:return None
    gap=(d['x']-b['x'])/2
    if not width*.04<gap<width*.25:return None
    if '9' in headers and not .5*gap<b['x']-headers['9']['x']<1.8*gap:return None
    # Header 11 is often read as two vertical rules. Locate its column between
    # verified headers 10 and 12; never mix in issue dates from column 10.
    center=headers.get('11',{}).get('x',b['x']+gap)
    if not b['x']<center<d['x']:return None
    lower=(b['x']+center)/2;upper=(center+d['x'])/2
    candidates=[]
    for w in words:
        if lower<w['x']<upper and w['y']>max(b['y']+b['h'],d['y']+d['h']):
            value=table_date(w['text'],today)
            if value:candidates.append((value,w['confidence']))
    distinct={value for value,_ in candidates}
    reliable=[value for value,confidence in candidates if confidence>=50]
    return reliable[0] if len(distinct)==1 and len(reliable)>=2 else None
