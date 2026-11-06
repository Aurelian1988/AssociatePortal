"""Versioned, fail-closed document data approval. No OCR authenticity claims."""
import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
try:
    from .profile_address_evidence import canonical_name, six_months_before
except ImportError:
    from profile_address_evidence import canonical_name, six_months_before

RULE_VERSION='document-data-v1'
GROUP={'passport':'passport','licence_front':'driving_licence','licence_back':'driving_licence','proof_of_address':'address'}
REQUIRED={
 'passport':('passport_number','passport_issuing_country','passport_issue_date','passport_expiry_date','first_name','last_name','dob','birth_nationality','birth_country','birthpassport_gender'),
 'driving_licence':('dl_number','dl_issuing_country','dl_issue_date','dl_photocard_expiry','dl_expiry_date','first_name','last_name','dob'),
 'address':('street_address','city','postal_code','country'),
}
PARTS={'passport':('passport',),'driving_licence':('licence_front','licence_back'),'address':('proof_of_address',)}
IDENTITY=('first_name','middle_name','last_name','dob')

def stamp(): return datetime.now(timezone.utc).isoformat()
def normalise(key,value):
    text=str(value or '').strip()
    if key in {'passport_number','dl_number','postal_code'}:return re.sub(r'\s+','',text).upper()
    if key=='dob' or key.endswith('_date') or key in {'dl_photocard_expiry'}:return text[:10]
    return canonical_name(text.replace('-',' '))
def parsed(value):
    try:return date.fromisoformat(str(value)[:10])
    except (ValueError,TypeError):return None

def record_capture(records,kind,reading,profile,file_reference,content_hash):
    records=copy.deepcopy(records or {});group=GROUP.get(kind)
    if not group:return records
    previous=records.get(group,{})
    # Front and back share one pre-scan identity snapshot. A new front starts a new pair.
    same_pair=group=='driving_licence' and kind=='licence_back' and previous.get('sources',{}).get('licence_front')
    history=list(previous.get('history',[]))
    if previous.get('decision'):history.append(previous['decision'])
    if same_pair:
        entry=previous;entry['history']=history;entry.pop('decision',None)
    else:
        entry=dict(profile_before={k:profile.get(k) for k in IDENTITY},sources={},manual_fields=[],history=history)
    evidence=copy.deepcopy(reading.get('approval_evidence') or {})
    entry['sources'][kind]=dict(raw_values=copy.deepcopy(reading.get('suggestions') or {}),evidence=evidence,
        document_date=(reading.get('address_evidence') or {}).get('document_date'),file_reference=file_reference,
        content_hash=content_hash,captured_at=stamp())
    entry['status']='Review';records[group]=entry
    return records

def combined(entry):
    values={};conflicts=[]
    for source in entry.get('sources',{}).values():
        for key,value in source.get('raw_values',{}).items():
            if key.startswith('_') or value in (None,''):continue
            if key in values and normalise(key,values[key])!=normalise(key,value):conflicts.append(key)
            else:values[key]=value
    return values,conflicts

def note_edits(records,incoming,reported=()):
    records=copy.deepcopy(records or {})
    for group,entry in records.items():
        raw,_=combined(entry);tracked=set(REQUIRED[group])|set(raw)
        changed=set(entry.get('manual_fields',[]))|({k for k in reported if k in tracked})
        for key,value in incoming.items():
            if key in tracked and normalise(key,value)!=normalise(key,raw.get(key)):
                changed.add(key)
        entry['manual_fields']=sorted(changed)
        entry['saved_fields']=sorted(set(entry.get('saved_fields',[])) | (set(incoming)&tracked))
    return records

def evaluate(group,entry,values,today=None,unique_ok=None):
    today=today or date.today();entry=entry or {};sources=entry.get('sources',{});raw,conflicts=combined(entry)
    checks={};reasons=[]
    def check(key,ok,reason):
        checks[key]=bool(ok)
        if not ok:reasons.append(reason)
    check('required_images',all(sources.get(k,{}).get('content_hash') for k in PARTS[group]),'Required document images are missing.')
    check('image_reference_unchanged',not entry.get('source_changed'),'A document image was replaced after the scan.')
    check('readable_images',bool(sources) and all(s.get('evidence',{}).get('image_readable') is True for s in sources.values()),'Image readability evidence is missing.')
    check('complete_extraction',all(raw.get(k) not in (None,'') for k in REQUIRED[group]),'Required fields were not all extracted.')
    verified=set()
    for source in sources.values():
        evidence=source.get('evidence',{})
        if evidence.get('confidence_floor',0)>=90:verified.update(evidence.get('validated_fields',[]))
        if group=='passport' and evidence.get('mrz_valid') is True:verified.update(set(evidence.get('checksum_fields',[])) & {'passport_number','dob','passport_expiry_date'})
    check('confident_extraction',set(REQUIRED[group])<=verified,'Required field confidence has not been established.')
    check('consistent_readings',not conflicts and all(not s.get('evidence',{}).get('conflicts') for s in sources.values()),'Document readings conflict.')
    check('no_manual_correction',not entry.get('manual_fields'),'Document details were manually entered or corrected.')
    compared=set(REQUIRED[group])|{k for k in raw if not k.startswith('_') and k in values}
    check('submitted_values_match_scan',all(normalise(k,values.get(k))==normalise(k,raw.get(k)) for k in compared),'Submitted details differ from the scan.')
    before=entry.get('profile_before',{})
    if group=='address':
        evidence=sources.get('proof_of_address',{}).get('evidence',{})
        recipient=evidence.get('recipient_last_name')
        check('recipient_surname',bool(before.get('last_name')) and normalise('last_name',recipient)==normalise('last_name',before.get('last_name')),'Recipient surname does not match the pre-scan profile.')
        check('profile_identity_unchanged',bool(before.get('last_name')) and normalise('last_name',values.get('last_name'))==normalise('last_name',before.get('last_name')),'Profile surname changed after the scan.')
        issued=parsed(sources.get('proof_of_address',{}).get('document_date'))
        check('document_date',issued is not None and six_months_before(today)<=issued<=today,'Document date must be within the last six months and not in the future.')
        check('document_date_confident',evidence.get('document_date_confident') is True,'Document date confidence is not established.')
        check('one_recipient_address',evidence.get('one_recipient_address') is True,'Recipient address is ambiguous or unconfirmed.')
    else:
        for key in ('last_name','dob'):
            check('profile_'+key,bool(before.get(key)) and normalise(key,raw.get(key))==normalise(key,before.get(key)),'Document '+key.replace('_',' ')+' does not match the pre-scan profile.')
        if before.get('first_name'):
            check('profile_first_name',normalise('first_name',raw.get('first_name'))==normalise('first_name',before['first_name']),'First name differs from the pre-scan profile.')
        issue=parsed(raw.get('passport_issue_date' if group=='passport' else 'dl_issue_date'))
        check('issue_date',issue is not None and issue<today,'Issue date must be before today.')
        if group=='passport':
            evidence=sources.get('passport',{}).get('evidence',{})
            check('mrz_checks',evidence.get('mrz_valid') is True,'Machine-readable passport checks did not pass.')
            check('printed_consistency',evidence.get('printed_consistent') is True,'Printed passport details were not independently matched.')
            check('unique_passport',unique_ok is True,'Passport uniqueness has not been confirmed.')
            expiry=parsed(raw.get('passport_expiry_date'));uk=normalise('country',raw.get('passport_issuing_country')) in {'united kingdom','uk','gb','gbr'}
            check('passport_expiry',expiry is not None and (expiry>=today or uk),'Non-UK passport is expired or expiry is missing.')
            checks['expired_uk_exception']=bool(uk and expiry and expiry<today)
        else:
            front=sources.get('licence_front',{}).get('raw_values',{}).get('dl_number')
            back=sources.get('licence_back',{}).get('raw_values',{}).get('dl_number')
            check('front_back_identity',bool(front and back) and normalise('dl_number',front)==normalise('dl_number',back),'Front and back have not been confirmed as the same licence.')
            for key in ('dl_photocard_expiry','dl_expiry_date'):
                expiry=parsed(raw.get(key));check(key,expiry is not None and expiry>=today,key.replace('_',' ')+' is expired or missing.')
    approved=not reasons
    return dict(status='Approved' if approved else 'Review',result='Matched' if approved else 'Manual Review',
        reasons=reasons,checks=checks,rule_version=RULE_VERSION,decided_at=stamp(),
        note=('Automatically approved by document data checks; no manual corrections. OCR matching does not establish authenticity.'+(' Expired UK passport exception applied.' if checks.get('expired_uk_exception') else '')) if approved else 'Automatic approval withheld: '+' '.join(reasons),
        values_fingerprint=hashlib.sha256(json.dumps({k:normalise(k,values.get(k)) for k in sorted(compared|set(IDENTITY))},sort_keys=True).encode()).hexdigest())

def decide(records,group,values,today=None,unique_ok=None):
    records=copy.deepcopy(records or {});entry=records.setdefault(group,dict(sources={},manual_fields=[],profile_before={},history=[]))
    if entry.get('decision'):entry.setdefault('history',[]).append(entry['decision'])
    entry['decision']=evaluate(group,entry,values,today,unique_ok);entry['status']=entry['decision']['status']
    return records

def invalidate_changed(records,values):
    records=copy.deepcopy(records or {})
    for group,entry in records.items():
        if entry.get('status')!='Approved':continue
        current=evaluate(group,entry,values,unique_ok=True)
        if current['status']!='Approved' or current['values_fingerprint']!=entry.get('decision',{}).get('values_fingerprint'):
            entry.setdefault('history',[]).append(entry['decision'])
            current.update(status='Review',result='Manual Review',note='Previous automatic approval invalidated. Submit the document section for a fresh check.')
            entry['decision']=current;entry['status']='Review'
    return records

def public_status(records):
    return {key:dict(status=value.get('status','Review'),decided=bool(value.get('decision')),reasons=value.get('decision',{}).get('reasons',[])) for key,value in (records or {}).items()}


def draft_values(records,group):
    entry=(records or {}).get(group,{})
    raw,_=combined(entry)
    return {key:value for key,value in raw.items() if key not in entry.get('saved_fields',[]) and not key.startswith('_')}
