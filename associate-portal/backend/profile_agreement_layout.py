"""Shared screen/print agreement formatting without changing contract wording."""
from bs4 import BeautifulSoup

CSS = '''
@page{size:A4;margin:9mm}
*{box-sizing:border-box}html,body{margin:0;padding:0;color:#202936;background:#fff;font-family:Arial,Helvetica,sans-serif;font-size:11.5px;line-height:1.3}
.container,.page_content,.webpage-content,.web-page-content,.desktop-frame{width:100%!important;max-width:none!important;min-width:0!important;margin:0!important;padding:0!important;border:0!important;box-shadow:none!important}
.agreement-page{display:block!important;padding:8px!important;font:inherit!important}
p,li,span,b,strong,label,a{font-size:inherit;font-weight:400;line-height:inherit}p{margin:0 0 5px}ul,ol{margin:4px 0 7px;padding-left:19px}li{margin:0 0 2px}li p{margin:0}
h1,h2,h3,h4,h5,h6{font-weight:700;line-height:1.2;margin:9px 0 5px;font-size:12px}.confidential-line{text-align:center;margin:3px 0 7px}.agreement-page>h4:first-of-type{text-align:center}h4:first-child{text-align:center;font-size:13px;margin:0 0 6px}h5{font-size:11px}h1 *,h2 *,h3 *,h4 *,h5 *,h6 *{font-weight:700}
hr{border:0;border-top:1px solid #b8c2cc;margin:8px 0 6px}.page-nav,.page-counter{display:none!important}
.meta-clone{display:block!important;border-top:1px solid #b8c2cc;margin-top:8px;padding-top:5px;font-size:9px;line-height:1.3}.meta-row{display:inline-block;margin:0 14px 3px 0}.sig-clone{display:block!important;margin:5px 0;font-size:9px;page-break-inside:avoid}.sig-clone img{display:block;width:150px;height:42px;object-fit:contain;object-position:left}.sig-clone-title{font-weight:700}
.print-ack{border:1px solid #1a5276;border-radius:5px;padding:6px;color:#1a5276;background:#f3f8fc;margin:8px 0 5px;font-size:9px;page-break-inside:avoid}.signature-section{page-break-inside:avoid}.review-banner{color:#8b1728;border:1px solid #8b1728;padding:5px;margin-bottom:7px;font-size:9px;font-weight:700;text-align:center}
.agreement-footer{border-top:1px solid #b8c2cc;margin-top:7px;padding-top:4px;font-size:8px;color:#536171;text-align:center}
@media print{html,body{font-size:8.8pt;line-height:1.12}.agreement-page{padding:0!important}p{margin-bottom:3px}ul,ol{margin:2px 0 4px}li ul,li ol{margin:2px 0}h4:first-child{font-size:12pt}h4,h5{font-size:9.5pt}li{margin-bottom:1px}.agreement-footer{font-size:7pt}.meta-clone{font-size:7pt}.sig-clone img{height:35px}h1,h2,h3,h4,h5,h6{page-break-after:avoid}.meta-clone,.sig-clone{page-break-inside:avoid}}
'''

def format_agreement(html, sample=False):
    soup=BeautifulSoup(html,'html.parser')
    for el in soup.select('style,link,script,button,canvas,label[for^="agree-"],.page-nav,.page-counter'):
        el.decompose()
    for checkbox in soup.select('input[type=checkbox]'):
        label=soup.find('label',attrs={'for':checkbox.get('id')})
        if label:label.decompose()
        checkbox.decompose()
    # Some source pages leave the legal heading open around the remaining body.
    for heading in soup.select('h1,h2,h3,h4,h5,h6'):
        children=list(heading.children)
        first_block=next((i for i,c in enumerate(children) if getattr(c,'name',None) in ('p','div','ul','ol','hr')),None)
        if first_block is not None:
            cursor=heading
            for child in children[first_block:]:
                cursor.insert_after(child.extract());cursor=child
    for el in soup.find_all(['div','p']):
        if '(Private & Confidential)' in el.get_text(' ',strip=True) and len(el.get_text(' ',strip=True)) < 150:
            el['class'] = list(el.get('class', [])) + ['confidential-line']
    for el in soup.find_all(True):
        el.attrs.pop('style',None)
    # Remove only runs of layout breaks; retain meaningful single line breaks.
    for br in list(soup.find_all('br')):
        previous=br.previous_sibling
        while previous is not None and isinstance(previous,str) and not previous.strip():previous=previous.previous_sibling
        if getattr(previous,'name',None)=='br':br.decompose()
    for page in soup.select('.agreement-page'):
        signature=page.select_one('.sig-clone')
        metadata=page.select_one('.meta-clone')
        if signature and signature.select_one('img[src]'):
            block=soup.new_tag('div',attrs={'class':'signature-section'})
            acknowledgement=soup.new_tag('div',attrs={'class':'print-ack'})
            acknowledgement.string=('Included in the ACAP pack and accepted at final signing.' if page.get('id') in ('page-6','page-7') else 'I have read, understood and agree to the terms of this agreement')
            signature.insert_before(block)
            block.append(acknowledgement)
            block.append(signature.extract())
            if metadata:block.append(metadata.extract())
        footer=soup.new_tag('div',attrs={'class':'agreement-footer'})
        footer.string='One Motion Logistics Ltd · Private & Confidential'
        page.append(footer)
        if sample:
            banner=soup.new_tag('div',attrs={'class':'review-banner'});banner.string='LAYOUT SAMPLE — NOT SIGNED — NO LEGAL EFFECT';page.insert(0,banner)
    style=soup.new_tag('style');style.string=CSS;soup.head.append(style)
    return str(soup)


def build_print_pdf(html):
    """Position the legal/signature block at the printable bottom, PDF only.

    Measure the real renderer output so longer signatures and different amounts
    of legal text reserve their own space. Never discard text or add a page just
    to introduce whitespace.
    """
    import io
    import pdfplumber
    from onemotion.api.portal_agreement_renderer import build_pdf
    baseline=build_pdf(html)
    soup=BeautifulSoup(html,'html.parser')
    heading=next((h for h in soup.select('h1,h2,h3,h4,h5,h6') if h.get_text(' ',strip=True).lower()=='this is a legal agreement'),None)
    anchor=heading or soup.select_one('.signature-section')
    if anchor is None:return baseline
    previous=anchor.find_previous_sibling()
    if previous and previous.name=='hr':anchor=previous
    spacer=soup.new_tag('div',attrs={'class':'pdf-bottom-spacing'})
    anchor.insert_before(spacer)
    def measure(data):
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            last=pdf.pages[-1];words=last.extract_words()
            bottom=max((w['bottom'] for w in words),default=last.height)
            return len(pdf.pages),last.height-12*72/25.4-3-bottom,bottom
    count,gap,bottom=measure(baseline)
    if gap<3:return baseline
    best=baseline;best_gap=gap
    low=0;high=gap*3+30
    for _ in range(9):
        spacing=(low+high)/2
        spacer['style']='height:%.3fpt;min-height:%.3fpt;font-size:0;line-height:0;'%(spacing,spacing)
        candidate=build_pdf(str(soup));new_count,new_gap,new_bottom=measure(candidate)
        if new_count!=count or new_gap < -1:
            high=spacing
            continue
        low=spacing
        if new_gap < best_gap:best=candidate;best_gap=new_gap
        if new_gap<=2:break
    return best
