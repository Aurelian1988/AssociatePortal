"""Reject low-resolution, blurred or unreadable evidence before storing it."""
from PIL import Image, ImageFilter, ImageStat

QUALITY_MESSAGE = 'This document is not clear enough to read. Use good lighting, avoid glare, keep the whole document in frame and hold the camera steady, then try again.'


def check_sharpness(image):
    if min(image.size) < 480:
        raise ValueError('The captured document is too small to read. Move closer while keeping every edge visible.')
    gray=image.convert('L')
    # Ignore outer margins and intentionally blurred background around camera captures.
    w,h=gray.size
    gray=gray.crop((int(w*.15),int(h*.15),int(w*.85),int(h*.85)))
    gray.thumbnail((1200,1200))
    edges=gray.filter(ImageFilter.Kernel((3,3),[0,1,0,1,-4,1,0,1,0],scale=1,offset=128))
    edges=edges.crop((2,2,edges.width-2,edges.height-2))
    if ImageStat.Stat(edges).var[0] < 18:
        raise ValueError('The captured text appears out of focus. Check the latest capture in Preview; allow the camera to focus before trying again.')


class OCRConfidenceError(ValueError):
    pass

def readable_text(image,lang='eng'):
    import pytesseract
    check_sharpness(image)
    data=pytesseract.image_to_data(image,lang=lang,config='--psm 6',output_type=pytesseract.Output.DICT,timeout=20)
    words=[]; reliable=[]
    for word,confidence in zip(data['text'],data['conf']):
        word=word.strip()
        if not word or not any(c.isalnum() for c in word): continue
        words.append(word)
        if float(confidence)>=60: reliable.append(word)
    if len(reliable)<6 or sum(len(w) for w in reliable)<25 or len(reliable)/max(1,len(words))<.6:
        raise OCRConfidenceError('The photo passed the image check, but OCR could not confidently read enough text. Check the printed details and bottom lines are readable; language or layout can also affect recognition.')
    # Keep line breaks needed by labelled-field and address extraction.
    lines={}
    for i,word in enumerate(data['text']):
        if word.strip():
            key=tuple(data[k][i] for k in ('page_num','block_num','par_num','line_num'))
            lines.setdefault(key,[]).append(word.strip())
    return '\n'.join(' '.join(words) for words in lines.values())


def readable_text_for_review(image,lang='eng'):
    """A clear photo may proceed to manual entry; failed image checks never do."""
    check_sharpness(image)
    try:
        return readable_text(image,lang=lang)
    except (OCRConfidenceError,RuntimeError,ImportError):
        return ''
