"""Local address OCR: preserve page detail, then isolate the named recipient."""
import re
from PIL import ImageOps
try:
    from onemotion.api.profile_address_evidence import canonical_name, extract_address_evidence
    from onemotion.api.profile_document_quality import check_sharpness
    from onemotion.api.profile_ocr_evidence import confident_text,matching_fields,engine_version,CONFIDENCE_FLOOR
except ModuleNotFoundError:
    from profile_address_evidence import canonical_name, extract_address_evidence
    from profile_document_quality import check_sharpness
    from profile_ocr_evidence import confident_text,matching_fields,engine_version,CONFIDENCE_FLOOR


def recipient_regions(data, last_name, size):
    """Bounded crops anchored to exact surname tokens, not a sender's postcode."""
    target=canonical_name(last_name).split()
    if not target: return []
    words=[(i,canonical_name(word)) for i,word in enumerate(data['text']) if canonical_name(word)]
    regions=[];width,height=size
    for pos in range(len(words)-len(target)+1):
        run=words[pos:pos+len(target)]
        if [word for _,word in run]!=target: continue
        ids=[i for i,_ in run]
        if any(float(data['conf'][i])<45 for i in ids): continue
        if len({tuple(data[k][i] for k in ('page_num','block_num','par_num','line_num')) for i in ids})!=1: continue
        left=min(data['left'][i] for i in ids);top=min(data['top'][i] for i in ids)
        right=max(data['left'][i]+data['width'][i] for i in ids)
        h=max(data['height'][i] for i in ids)
        # Padding covers the title/initials at left and longer address lines below.
        regions.append((max(0,left-6*h),max(0,top-h),min(width,right+6*h),min(height,top+10*h)))
        if len(regions)>=3: break
    return regions


def text_from_data(data):
    lines={}
    for i,word in enumerate(data['text']):
        if not word.strip(): continue
        key=tuple(data[k][i] for k in ('page_num','block_num','par_num','line_num'))
        lines.setdefault(key,[]).append(word.strip())
    return '\n'.join(' '.join(words) for words in lines.values())


def read_address_page(image,last_name):
    import pytesseract
    image=ImageOps.exif_transpose(image).convert('RGB')
    check_sharpness(image)
    image.thumbnail((3200,3200))
    prepared=ImageOps.autocontrast(ImageOps.grayscale(image))
    try:
        data=pytesseract.image_to_data(prepared,lang='eng',config='--psm 6',output_type=pytesseract.Output.DICT,timeout=20)
    except RuntimeError:
        return '',[], '',[]
    text=text_from_data(data);recipients=[];confident_recipients=[]
    for region in recipient_regions(data,last_name,prepared.size):
        try:
            crop_data=pytesseract.image_to_data(prepared.crop(region),lang='eng',config='--psm 6',output_type=pytesseract.Output.DICT,timeout=10)
            recipients.append(text_from_data(crop_data));confident_recipients.append(confident_text(crop_data))
        except RuntimeError: continue
    return text,recipients,confident_text(data),confident_recipients


def read_address_pages(images,last_name,today=None):
    pages=[];recipients=[];confident_pages=[];confident_blocks=[]
    for image in images:
        text,blocks,high_text,high_blocks=read_address_page(image,last_name)
        pages.append(text);recipients.extend(blocks);confident_pages.append(high_text);confident_blocks.extend(high_blocks)
    # Never fall back to the mixed page layout when recipient crops exist.
    result=extract_address_evidence('\n'.join(pages),last_name,today,recipient_texts=recipients or None)
    high=extract_address_evidence('\n'.join(confident_pages),last_name,today,recipient_texts=confident_blocks or None)
    result['approval_evidence']=dict(image_readable=True,confidence_floor=CONFIDENCE_FLOOR,
        validated_fields=matching_fields(result['suggestions'],high['suggestions']),
        recipient_last_name=high['matched_name'],one_recipient_address=bool(result['suggestions']),
        document_date_confident=bool(result['document_date'] and result['document_date']==high['document_date']),ocr_version=engine_version())
    return result
