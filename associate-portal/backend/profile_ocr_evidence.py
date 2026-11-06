"""Conservative field evidence from OCR words at or above a confidence floor."""
import pytesseract
try:
    from .profile_document_approval import normalise
except ImportError:
    from profile_document_approval import normalise

CONFIDENCE_FLOOR=90

def confident_text(data):
    lines={}
    for i,word in enumerate(data['text']):
        if not word.strip():continue
        key=tuple(data[k][i] for k in ('page_num','block_num','par_num','line_num'))
        # Retain placeholders so dropping an uncertain word cannot merge two values.
        lines.setdefault(key,[]).append(word.strip() if float(data['conf'][i])>=CONFIDENCE_FLOOR else ' [unread] ')
    return '\n'.join(' '.join(words) for words in lines.values())

def matching_fields(original,confident):
    return [k for k,v in original.items() if not k.startswith('_') and v not in (None,'') and '[unread]' not in str(confident.get(k,'')) and normalise(k,v)==normalise(k,confident.get(k))]

def engine_version():
    try:return str(pytesseract.get_tesseract_version()).splitlines()[0]
    except Exception:return 'Unavailable'
