"""Local, bounded document OCR. Saved photos are never sharpened or resized here."""
import os
import re
from PIL import Image, ImageOps, ImageFilter
import pytesseract
os.environ.setdefault('OMP_THREAD_LIMIT','1')

try:
    from .profile_document_ocr import extract_fields, mrz_passport
    from .profile_document_quality import check_sharpness
except ImportError:
    from profile_document_ocr import extract_fields, mrz_passport
    from profile_document_quality import check_sharpness


PASSPORT_LANGUAGES = {
    # German/Luxembourgish packs were tested on the local sample. They added
    # processing time without improving its small printed labels.
    'LUX': ('fra', 'eng'),
    'BGR': ('bul','eng'), 'RUS': ('rus','eng'), 'UKR': ('ukr','eng'),
    'SRB': ('srp','eng'), 'MKD': ('mkd','eng'),
    'GBR': ('eng',), 'IRL': ('eng',),
    'FRA': ('fra', 'eng'), 'DEU': ('deu', 'eng'), 'ROU': ('ron', 'eng'),
}


def languages_for(country_code, available):
    wanted=PASSPORT_LANGUAGES.get(country_code, ('eng','fra'))
    selected=[lang for lang in wanted if lang in available]
    return '+'.join(selected or ['eng'])


def ocr_text(image, language='eng', mode=6, whitelist=False):
    config='--psm '+str(mode)
    if whitelist:config+=' -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'
    try:
        return pytesseract.image_to_string(image,lang=language,config=config,timeout=12)
    except (RuntimeError, pytesseract.TesseractError):
        # Image quality and OCR service failures are separate. A clear image may
        # proceed to manual review, but never gets invented field values.
        return ''


def prepare(image):
    return ImageOps.autocontrast(image.convert('L'),cutoff=.5).filter(
        ImageFilter.UnsharpMask(radius=1,percent=100,threshold=3))


def _read_document(image,kind):
    image=ImageOps.exif_transpose(image).convert('RGB')
    # Downsampling the whole open passport to 1800px made the MRZ unreadable.
    # Preserve camera resolution up to a bounded 3200px; crop before OCR.
    image.thumbnail((3200,3200))
    reading=image.crop((0,int(image.height*.45),image.width,image.height)) if kind=='passport' else image
    check_sharpness(reading)
    suggestions={};checked={};printed={}
    try: available=set(pytesseract.get_languages(config=''))
    except (RuntimeError,pytesseract.TesseractError):available={'eng'}
    language='eng'
    if kind=='passport':
        checked={}
        # The generic English model confuses OCR-B chevrons and digits. Use the
        # dedicated font model when installed, preserving strict check digits.
        models=['ocrb_int','eng'] if 'ocrb_int' in available else ['eng']
        for model in models:
            for start,end in ((.73,1),(.81,.94)):
                if model=='ocrb_int':
                    strip=image.crop((int(image.width*.04),int(image.height*start),int(image.width*.96),int(image.height*end)))
                else:
                    strip=ImageOps.autocontrast(image.crop((0,int(image.height*start),image.width,int(image.height*end))).convert('L'))
                checked=mrz_passport(ocr_text(strip,model,whitelist=model=='eng'))
                if checked:break
            if checked:break
        country_code=checked.get('_issuing_country_code')
        if not country_code:
            # Printed country identification is independent of MRZ validity.
            heading=reading.crop((0,0,reading.width,int(reading.height*.35)))
            hint=ocr_text(heading,'+'.join(x for x in ('eng','bul') if x in available) or 'eng',11)
            if re.search(r'REPUBLIC\s+OF\s+BULGARIA|РЕПУБЛИКА\s+БЪЛГАРИЯ',hint,re.I):country_code='BGR'
        language=languages_for(country_code,available)
        text=ocr_text(prepare(reading),language)
        suggestions=extract_fields(text,kind,context=checked)
        # A focused second pass removes the portrait and opposite page from the
        # text layout. Dates still require readable labels; never guess order.
        if not suggestions.get('passport_issue_date'):
            body=image.crop((int(image.width*.25),int(image.height*.5),
                             int(image.width*.95),int(image.height*.85)))
            extra=extract_fields(ocr_text(prepare(body),language,11),kind,context=checked)
            for key,value in extra.items():suggestions.setdefault(key,value)
        if checked.get('_issuing_country_code')=='GBR' and not suggestions.get('passport_issue_date'):
            # UK bilingual date labels are much smaller than the value text.
            # Isolate that printed column and enlarge the OCR copy only.
            column=image.crop((int(image.width*.30),int(image.height*.55),int(image.width*.67),int(image.height*.80)))
            column=column.resize((column.width*3,column.height*3),Image.Resampling.LANCZOS)
            label_language='+'.join(lang for lang in ('eng','fra') if lang in available) or 'eng'
            extra=extract_fields(ocr_text(column,label_language,11),kind,context=checked)
            if extra.get('passport_issue_date'):suggestions['passport_issue_date']=extra['passport_issue_date']
        # Check-digit-validated MRZ fields take priority over printed OCR.
        printed=extract_fields('\n'.join(line for line in text.splitlines() if '<' not in line),'passport',context=checked)
        suggestions.update(checked)
        code=suggestions.pop('_issuing_country_code',None)
        if code:
            country={'GBR':'United Kingdom','IRL':'Ireland','LUX':'Luxembourg'}.get(code)
            if not country:
                try:
                    import pycountry
                    match=pycountry.countries.get(alpha_3=code)
                    if match:country=match.name
                except ImportError:pass
            if country:suggestions['passport_issuing_country']=country
        nationality=suggestions.get('_passport_nationality','').upper()
        value={'GBR':'British','BRITISH CITIZEN':'British','IRL':'Irish','LUX':'Luxembourger'}.get(nationality)
        if value:suggestions['birth_nationality']=value
    else:
        # Photocard security patterns can get stronger after contrast correction.
        # Try the original pixels first, then a prepared copy only if needed.
        language='+'.join(lang for lang in ('eng','bul','rus') if lang in available) or 'eng'
        suggestions=extract_fields(ocr_text(reading,language),kind)
        if kind=='licence_front' and not all(k in suggestions for k in ('dl_number','dl_issue_date','dl_photocard_expiry')):
            extra=extract_fields(ocr_text(prepare(reading),language,mode=11),kind)
            for key,value in extra.items():suggestions.setdefault(key,value)
    rear_confident=False
    if kind=='licence_back':
        try:
            try: from .profile_licence_expiry import rear_expiry
            except ImportError: from profile_licence_expiry import rear_expiry
            data=pytesseract.image_to_data(image,lang='eng',config='--psm 11',output_type=pytesseract.Output.DICT,timeout=12)
            expiry=rear_expiry(data,image.width,image.height)
            if expiry:
                suggestions['dl_expiry_date']=expiry
                high_data={key:list(value) for key,value in data.items()}
                high_data['text']=[word if float(data['conf'][i])>=90 else '' for i,word in enumerate(data['text'])]
                rear_confident=rear_expiry(high_data,image.width,image.height)==expiry
        except (RuntimeError,pytesseract.TesseractError):pass
    fields=[key for key in suggestions if not key.startswith('_')]
    if fields:
        warning=f'Read {len(fields)} fields. Check the filled details and enter any fields left blank before submitting.'
    elif kind=='licence_back':
        warning='Back photo saved for review. No labelled details were recognised on this side. Check the front-photo details and enter any missing information.'
    else:
        warning='Photo saved for review. No fields were recognised. Enter the document details manually or retake the photo.'
    try:
        from .profile_ocr_evidence import confident_text,matching_fields,engine_version,CONFIDENCE_FLOOR
        from .profile_document_approval import normalise
    except ImportError:
        from profile_ocr_evidence import confident_text,matching_fields,engine_version,CONFIDENCE_FLOOR
        from profile_document_approval import normalise
    evidence=dict(image_readable=True,confidence_floor=CONFIDENCE_FLOOR,validated_fields=[],ocr_version=engine_version())
    try:
        confidence_data=pytesseract.image_to_data(reading,lang=language,config='--psm 6',output_type=pytesseract.Output.DICT,timeout=12)
        high=extract_fields(confident_text(confidence_data),kind)
        evidence['validated_fields']=matching_fields(suggestions,high)
    except (RuntimeError,pytesseract.TesseractError):pass
    if rear_confident:evidence['validated_fields'].append('dl_expiry_date')
    if kind=='passport':
        evidence['mrz_valid']=bool(checked)
        overlap=[k for k in ('passport_number','first_name','last_name','dob','passport_expiry_date') if printed.get(k) and checked.get(k)]
        evidence['conflicts']=[k for k in overlap if normalise(k,printed[k])!=normalise(k,checked[k])]
        evidence['printed_consistent']=all(k in overlap for k in ('passport_number','dob','passport_expiry_date')) and not evidence['conflicts']
        if checked:
            evidence['checksum_fields']=['passport_number','dob','passport_expiry_date']
    return dict(suggestions=suggestions,manual_review=not bool(fields),warning=warning,approval_evidence=evidence)


def read_document(image, kind):
    try:
        from .profile_document_scan import scan_document
    except ImportError:
        from profile_document_scan import scan_document
    scanned = scan_document(image, kind)
    if scanned is None:
        return _read_document(image, kind)
    try:
        result = _read_document(scanned, kind)
    except Exception:
        return _read_document(image, kind)
    # Retain the existing reader whenever scanning provides weaker evidence.
    try:
        original = _read_document(image, kind)
    except Exception:
        return result
    def strength(reading):
        evidence = reading.get('approval_evidence', {})
        return (bool(evidence.get('mrz_valid')), len(evidence.get('validated_fields', [])),
                -len(evidence.get('conflicts', [])), len(reading.get('suggestions', {})))
    return result if strength(result) > strength(original) else original
