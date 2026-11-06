// Conservative readiness heuristic: four visible edges, size, interior focus and even lighting.
// This is capture guidance, not document authenticity verification.
export function assessDocumentFrame(image, previous, aspect = 1.586) {
  const {width:w,height:h,data}=image
  const gray=new Float32Array(w*h)
  let mean=0, glare=0
  for(let i=0;i<gray.length;i++){ gray[i]=.299*data[i*4]+.587*data[i*4+1]+.114*data[i*4+2]; mean+=gray[i]; if(gray[i]>250)glare++ }
  mean/=gray.length
  if(mean<45) return {ready:false,message:'Add more light',gray}
  const vertical=x=>{let sum=0;for(let y=Math.floor(h*.25);y<h*.75;y++)sum+=Math.abs(gray[y*w+x+1]-gray[y*w+x-1]);return sum/(h*.5)}
  const horizontal=y=>{let sum=0;for(let x=Math.floor(w*.25);x<w*.75;x++)sum+=Math.abs(gray[(y+1)*w+x]-gray[(y-1)*w+x]);return sum/(w*.5)}
  function peak(fn,start,end){let pos=start,score=0;for(let p=start;p<end;p++){const n=fn(p);if(n>score){score=n;pos=p}}return {pos,score}}
  let l=peak(vertical,2,Math.floor(w*.38)),r=peak(vertical,Math.floor(w*.62),w-2)
  let t=peak(horizontal,2,Math.floor(h*.4)),b=peak(horizontal,Math.floor(h*.6),h-2)
  // A licence's printed table can be stronger than its outer boundary. Select
  // four edges together, rather than treating each strongest text line as an edge.
  function candidates(fn,start,end){
    const scores=[]
    for(let p=start;p<end;p++)scores.push({pos:p,score:fn(p)})
    const chosen=[]
    for(const item of scores.sort((a,b)=>b.score-a.score)){
      if(item.score<7)break
      if(chosen.every(other=>Math.abs(other.pos-item.pos)>4))chosen.push(item)
      if(chosen.length===10)break
    }
    return chosen
  }
  const initialValid=Math.min(l.score,r.score,t.score,b.score)>=18 &&
    r.pos-l.pos>=w*.62 && b.pos-t.pos>=h*.48 &&
    Math.abs((r.pos-l.pos)/(b.pos-t.pos)/aspect-1)<=.22
  if(!initialValid){
    let best=null
    const left=candidates(vertical,2,Math.floor(w*.3)),right=candidates(vertical,Math.floor(w*.7),w-2)
    const top=candidates(horizontal,2,Math.floor(h*.35)),bottom=candidates(horizontal,Math.floor(h*.65),h-2)
    for(const a of left)for(const c of right)for(const d of top)for(const e of bottom){
      const cw=c.pos-a.pos,ch=e.pos-d.pos,ratioError=Math.abs(cw/ch/aspect-1)
      if(cw<w*.62||ch<h*.48||cw>w*.94||ch>h*.94||ratioError>.13)continue
      if(Math.abs((a.pos+c.pos)/2-w/2)>w*.12||Math.abs((d.pos+e.pos)/2-h/2)>h*.12)continue
      const score=Math.min(a.score,c.score,d.score,e.score)+cw*ch/(w*h)*25-ratioError*30
      if(!best||score>best.score)best={l:a,r:c,t:d,b:e,score}
    }
    if(best)({l,r,t,b}=best)
  }
  const width=r.pos-l.pos,height=b.pos-t.pos, ratio=width/height
  if(Math.min(l.score,r.score,t.score,b.score)<7) return {ready:false,message:'Show all four edges against a contrasting background',gray}
  if(width>w*.94 || height>h*.94) return {ready:false,message:'Move further away',gray}
  if(width<w*.62 || height<h*.48) return {ready:false,message:'Move closer',gray}
  if(Math.abs(ratio/aspect-1)>.22 || Math.abs((l.pos+r.pos)/2-w/2)>w*.12 || Math.abs((t.pos+b.pos)/2-h/2)>h*.12) return {ready:false,message:'Align the document with the outline',gray}
  const bounds={left:l.pos/w,right:r.pos/w,top:t.pos/h,bottom:b.pos/h}
  // Measure the document interior: background texture and card edges must not
  // make an out-of-focus page look sharp. Bright tile percentiles ignore ink.
  const x0=Math.ceil(l.pos+width*.08),x1=Math.floor(r.pos-width*.08)
  const y0=Math.ceil(t.pos+height*.08),y1=Math.floor(b.pos-height*.08)
  let focusSum=0,focusCount=0
  const lighting=[]
  for(let row=0;row<4;row++)for(let col=0;col<4;col++){
    const pixels=[]
    const xa=Math.floor(x0+(x1-x0)*col/4),xb=Math.floor(x0+(x1-x0)*(col+1)/4)
    const ya=Math.floor(y0+(y1-y0)*row/4),yb=Math.floor(y0+(y1-y0)*(row+1)/4)
    for(let y=ya;y<yb;y++)for(let x=xa;x<xb;x++){
      const i=y*w+x;pixels.push(gray[i])
      const lap=4*gray[i]-gray[i-1]-gray[i+1]-gray[i-w]-gray[i+w]
      focusSum+=lap*lap;focusCount++
    }
    pixels.sort((a,b)=>a-b)
    lighting.push(pixels[Math.floor((pixels.length-1)*.9)]||0)
  }
  lighting.sort((a,b)=>a-b)
  if(lighting[8]<110) return {ready:false,message:'Add more light to the document',gray}
  // Several dark areas relative to the paper indicate a broad shadow; tolerate
  // an isolated dark portrait, security feature or block of printed text.
  if(lighting[3]<65 || lighting[3]<lighting[12]*.5) return {ready:false,message:'Move away from shadows; light the whole document evenly',gray}
  if(focusSum/Math.max(1,focusCount)<95 || glare/gray.length>.7) return {ready:false,message:'Wait for focus; tilt slightly to avoid glare',gray}
  return {ready:true,qualityReady:true,message:'Clear and in range—capturing now',gray,bounds,focusScore:focusSum/Math.max(1,focusCount)}

}
