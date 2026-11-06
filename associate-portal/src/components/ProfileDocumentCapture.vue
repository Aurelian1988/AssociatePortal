<template>
  <div class="document-capture">
    <div class="capture-heading"><span>{{ label }}</span><span v-if="lastCapture && !uploading" class="saved">Latest capture · not saved</span><span v-else-if="file" class="saved">Uploaded ✓</span></div>
    <div class="capture-actions">
      <button v-if="!['birth_certificate','proof_of_address','dbs_certificate'].includes(kind)" type="button" class="camera-action" :disabled="uploading" @click="start">{{ file ? 'Retake photo' : 'Open camera' }}</button>
      <button v-if="(file || lastCapture) && ['passport','licence_front','licence_back'].includes(kind)" ref="previewButton" type="button" class="camera-action" :disabled="uploading" @click="showPreview">Preview</button>
      <button v-if="['birth_certificate','proof_of_address','dbs_certificate'].includes(kind)" type="button" class="camera-action upload-choice" :disabled="uploading" @click="fileInput?.click()">{{ ['proof_of_address','dbs_certificate'].includes(kind) ? 'Upload document' : 'Upload photo' }}</button>
      <input v-if="['birth_certificate','proof_of_address','dbs_certificate'].includes(kind)" ref="fileInput" type="file" class="hidden-file" :accept="['proof_of_address','dbs_certificate'].includes(kind) ? 'image/jpeg,image/png,application/pdf' : 'image/jpeg,image/png'" :disabled="uploading" @change="choose" />
    </div>
    <div v-if="uploading" class="upload-progress" :aria-busy="true">
      <p role="status" class="processing-label">{{ uploadStage === 'reading' ? 'Processing your document…' : 'Uploading your document…' }}<strong v-if="uploadStage === 'uploading' && uploadPercent !== null"> {{ uploadPercent }}%</strong></p>
      <div v-if="uploadStage === 'uploading' && uploadPercent !== null" class="activity-track" role="progressbar" aria-label="Document upload" :aria-valuenow="uploadPercent" aria-valuemin="0" aria-valuemax="100"><span class="activity-fill" :style="{width: uploadPercent + '%'}" /></div>
      <div v-else class="activity-track processing" role="progressbar" aria-label="Processing document"><span class="activity-fill" /></div>
      <p class="processing-help">Please keep this page open while we read your document.</p>
    </div>
    <p v-if="message" role="status">{{ message }}</p>
    <button v-if="(file || lastCapture) && ['passport','licence_front','licence_back'].includes(kind)" type="button" class="read-again" :disabled="uploading" @click="readAgain">Read photo again</button>
    <Teleport to="body"><div v-if="opened" class="capture-modal" role="dialog" aria-modal="true" :aria-label="label" @keydown.esc="close">
      <h2>{{ label }}</h2>
      <div class="camera" :style="{aspectRatio:viewAspect,width:`min(95vw, calc((100dvh - 210px) * ${viewAspect}))`}"><video ref="video" autoplay playsinline muted/><div class="shade" :style="{'--frame-height': (84 * viewAspect / aspect) + '%'}"><div class="blur-outside top"/><div class="blur-outside bottom"/><div class="blur-outside left"/><div class="blur-outside right"/><div class="outline" :style="{aspectRatio:aspect}"><template v-if="kind === 'passport'"><div class="passport-fold"/><div class="passport-photo-guide"><span>Photo</span></div><span class="passport-top-label">Facing page</span></template></div></div></div>
      <p role="status">{{ guidance }}</p>
      <p>{{ kind === 'passport' ? 'Open your passport flat. Show both pages, with the photo page in the lower half and the photo inside its outline.' : 'Place the licence on a contrasting surface with every corner visible.' }} Capture starts after a brief pause when it is clear, evenly lit and in range.</p>
      <div class="camera-bottom-actions"><button class="cancel-photo" type="button" @click="close">Cancel</button>
      <button class="take-photo" type="button" :disabled="uploading" @click="captureNow">Take photo</button></div>
    </div></Teleport>
    <Teleport to="body"><div v-if="captureReview" class="capture-modal document-preview" role="dialog" aria-modal="true" :aria-label="label + ' review'" @keydown.esc="captureReview=''">
      <h2>Check your photo</h2>
      <img :src="captureReview" :alt="label + ' captured photo for review'" />
      <p>Check all edges and the bottom text are visible and sharp before reading the document.</p>
      <div class="review-actions"><button type="button" @click="confirmCapture">Use photo</button><button type="button" @click="retakeCapture">Retake</button><button type="button" @click="captureReview=''">Cancel</button></div>
    </div></Teleport>
    <Teleport to="body"><div v-if="previewOpen" class="capture-modal document-preview" role="dialog" aria-modal="true" :aria-label="label + ' preview'" @keydown.esc="closePreview">
      <h2>{{ label }} preview</h2>
      <p v-if="previewError" role="alert">The photo could not be loaded. Close this preview and try again.</p>
      <img v-else :src="lastCapture || file" :alt="label + ' captured photo'" @error="previewError=true" />
      <button ref="previewClose" type="button" @click="closePreview">Close preview</button>
    </div></Teleport>
  </div>
</template>
<script setup>
import {nextTick,onBeforeUnmount,ref} from 'vue'
import {uploadDocument} from '@/utils/documentUpload'
import {cropDocument} from '@/utils/documentBackground'
import {assessDocumentFrame} from '@/utils/documentCaptureQuality'
const props=defineProps({kind:String,label:String,file:String})
const emit=defineEmits(['saved','captured'])
const lastCapture=ref(''),captureReview=ref('')
function confirmCapture(){const data=captureReview.value;captureReview.value='';if(data)upload(data)}
function retakeCapture(){captureReview.value='';start()}
const previewOpen=ref(false),previewError=ref(false),previewButton=ref(null),previewClose=ref(null)
async function showPreview(){previewError.value=false;previewOpen.value=true;await nextTick();previewClose.value?.focus()}
async function closePreview(){previewOpen.value=false;await nextTick();previewButton.value?.focus()}
async function readAgain(){
 if(uploading.value)return
 try{
  let data=lastCapture.value||props.file
  if(!data.startsWith('data:image/')){
   const response=await fetch(data,{credentials:'same-origin'})
   if(!response.ok)throw new Error('Could not load the saved photo. Try again or retake it.')
   const blob=await response.blob()
   if(!blob.type.startsWith('image/')||blob.size>6_000_000)throw new Error('Use a camera photo under 6 MB.')
   data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob)})
  }
  await upload(data)
 }catch(error){message.value=error?.message||'Could not read this saved photo. Please try again.'}
}
const fileInput=ref(null)
const uploadStage=ref('uploading'),uploadPercent=ref(0),elapsed=ref(0)
let elapsedTimer
const qualityReady=ref(false)
const video=ref(null),opened=ref(false),uploading=ref(false),guidance=ref('Align the document with the outline'),message=ref('')
const aspect=props.kind==='passport'?.71:1.586
const viewAspect=props.kind==='passport'?.75:4/3
let stream,timer,previous,steady=0,lastReady=0,readyFrames=0,generation=0,cameraStartedAt=0,captureCandidate=null
function close(){generation++;clearTimeout(timer);stream?.getTracks().forEach(t=>t.stop());stream=null;opened.value=false;previous=null;steady=0;lastReady=0;readyFrames=0;captureCandidate=null;qualityReady.value=false}
async function start(){
 close();const run=++generation;opened.value=true;message.value='';await nextTick()
 try{
  const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:props.kind==='passport'?1440:1920},height:{ideal:props.kind==='passport'?1920:1440}},audio:false})
  if(run!==generation){acquired.getTracks().forEach(t=>t.stop());return}
  stream=acquired;
  const track=stream.getVideoTracks()[0],caps=track.getCapabilities?.()||{},settings={}
  if(caps.focusMode?.includes('continuous'))settings.focusMode='continuous'
  if(caps.exposureMode?.includes('continuous'))settings.exposureMode='continuous'
  if(Object.keys(settings).length)try{await track.applyConstraints({advanced:[settings]})}catch{}
  video.value.srcObject=stream;await video.value.play();cameraStartedAt=Date.now();tick()
 }catch{close();message.value='Camera access is required. Allow it in your browser settings, then try again.'}
}
function frame(width){
 const v=video.value,c=document.createElement('canvas')
 const w=Math.min(v.videoWidth,v.videoHeight*viewAspect),h=w/viewAspect
 c.width=Math.min(width,Math.floor(w));c.height=Math.round(c.width/viewAspect)
 c.getContext('2d').drawImage(v,(v.videoWidth-w)/2,(v.videoHeight-h)/2,w,h,0,0,c.width,c.height)
 return c
}
function tick(){
 if(!opened.value)return
 if(video.value?.videoWidth){
  const captured=frame(1920),c=document.createElement('canvas');c.width=320;c.height=Math.round(320/viewAspect);c.getContext('2d').drawImage(captured,0,0,c.width,c.height)
  const result=assessDocumentFrame(c.getContext('2d').getImageData(0,0,c.width,c.height),previous,aspect)
  previous=result.gray;guidance.value=result.message;qualityReady.value=!!result.qualityReady
  if(Date.now()-cameraStartedAt<1800){steady=0;guidance.value=props.kind==='passport'?'Position the passport inside the outline':'Position the licence inside the outline'}
  else if(result.ready){
    if(Date.now()-lastReady>500){steady=0;readyFrames=0;captureCandidate=null}
    if(!steady)steady=Date.now()
    lastReady=Date.now();readyFrames++
    if(!captureCandidate||result.focusScore>captureCandidate.score)captureCandidate={image:captured,bounds:result.bounds,score:result.focusScore}
    guidance.value='Clear and in range—hold position briefly'
    if(Date.now()-steady>=1200 && readyFrames>=5){const data=cropDocument(captureCandidate.image,captureCandidate.bounds).toDataURL('image/jpeg',.96);close();lastCapture.value=data;captureReview.value=data;emit('captured',props.kind);return}
  }else if(Date.now()-lastReady>500){steady=0;readyFrames=0;captureCandidate=null}
 }
 timer=setTimeout(tick,180)
}
function captureNow(){
 if(!opened.value || uploading.value || !video.value?.videoWidth)return
 // Recheck the current frame rather than accepting an earlier focus result.
 const captured=frame(1920),c=document.createElement('canvas');c.width=320;c.height=Math.round(320/viewAspect);c.getContext('2d').drawImage(captured,0,0,c.width,c.height)
  const result=assessDocumentFrame(c.getContext('2d').getImageData(0,0,c.width,c.height),previous,aspect)
 qualityReady.value=!!result.qualityReady;guidance.value=result.message
 const frameHeight=.84*viewAspect/aspect
 const bounds=result.bounds || {left:.08,right:.92,top:(1-frameHeight)/2,bottom:(1+frameHeight)/2}
 const data=cropDocument(captured,bounds).toDataURL('image/jpeg',.94)
 close();lastCapture.value=data;captureReview.value=data;emit('captured',props.kind)
}
async function choose(event){
 const file=event.target.files?.[0];event.target.value='';if(!file)return
 if(!(['proof_of_address','dbs_certificate'].includes(props.kind) ? ['image/jpeg','image/png','application/pdf'] : ['image/jpeg','image/png']).includes(file.type)||file.size>(file.type === 'application/pdf' ? 10_000_000 : 6_000_000)){message.value=['proof_of_address','dbs_certificate'].includes(props.kind) ? 'Choose a JPEG/PNG photo under 6 MB or a PDF under 10 MB.' : 'Choose a JPEG or PNG photo under 6 MB.';return}
 const reader=new FileReader();reader.onload=()=>upload(reader.result);reader.onerror=()=>{message.value='Could not read this photo.'};reader.readAsDataURL(file)
}
async function upload(data){
 if(uploading.value)return
 uploading.value=true;message.value='';uploadStage.value='uploading';uploadPercent.value=0;elapsed.value=0
 const started=Date.now();elapsedTimer=setInterval(()=>{elapsed.value=Math.floor((Date.now()-started)/1000)},1000)
 try{
  const response=await uploadDocument({kind:props.kind,image_base64:data},progress=>{uploadStage.value=progress.stage;uploadPercent.value=progress.percent})
  const result=response?.message??response;lastCapture.value='';message.value=result.warning||'Photo saved. Review the extracted details below.';emit('saved',{...result,kind:props.kind})
 }catch(error){message.value=error?.messages?.[0] || error?.message || 'The document could not be read. Retake a sharp photo in good lighting, with all text visible.'}
 finally{clearInterval(elapsedTimer);uploading.value=false}
}
onBeforeUnmount(()=>{close();clearInterval(elapsedTimer)})
</script>
<style scoped>
.review-actions{display:flex;gap:.6rem;flex-wrap:wrap;justify-content:center}
.document-capture .read-again{background:transparent;color:#a61d1d;font-size:.78rem;padding:.3rem 0;min-height:36px;text-decoration:underline;font-weight:500}
.upload-progress{margin-top:.8rem;padding:1rem;background:#fff7ed;border:1px solid #fb923c;border-radius:.65rem}.document-capture .processing-label{font-size:1rem;font-weight:650;color:#7c2d12;line-height:1.4;margin:0 0 .75rem}.document-capture .processing-help{font-size:.9rem;line-height:1.4;color:#7c2d12;margin:.7rem 0 0}.activity-track{height:18px;background:#ffedd5;border:1px solid #fdba74;border-radius:9px;overflow:hidden}.activity-fill{display:block;height:100%;background:#f97316;border-radius:8px;transition:width .2s ease}.processing .activity-fill{width:40%;animation:document-processing 1.3s ease-in-out infinite alternate}@keyframes document-processing{from{transform:translateX(-80%)}to{transform:translateX(230%)}}@media(prefers-reduced-motion:reduce){.processing .activity-fill{animation:none;width:100%;background:repeating-linear-gradient(135deg,#f97316 0 12px,#fdba74 12px 24px)}}.upload-progress progress{display:block;width:100%;height:.55rem;accent-color:#a61d1d}.upload-progress .progress-detail{font-size:.75rem;color:#6b7280}
.document-preview img{width:100%;max-width:55rem;max-height:calc(100dvh - 10rem);object-fit:contain;min-height:0;flex:1}.document-preview h2{font-size:1.1rem}.document-preview button{flex-shrink:0}
.document-capture{background:#fff;padding:.8rem;margin:.65rem 0;border:1px solid #e5e7eb;border-radius:.75rem}.capture-heading{display:flex;align-items:center;justify-content:space-between;gap:.5rem;font-size:.9rem;font-weight:500}.saved{font-size:.72rem;color:#166534}.capture-actions{display:flex;align-items:center;gap:.8rem;margin-top:.4rem;flex-wrap:wrap}.hidden-file{display:none}.document-capture .camera-action{min-width:8rem;background:#fff;color:#111827;border:1px solid #d1d5db;padding:.35rem .8rem;font-size:.82rem;font-weight:500;min-height:40px;border-radius:.5rem}.document-capture .upload-choice{min-width:10rem;border:1px solid #d1d5db;background:#fff;color:#111827;padding:.35rem .8rem;font-size:.82rem;font-weight:500;min-height:40px;border-radius:.5rem}.document-capture p{margin:.5rem 0;font-size:.8rem;color:#6b7280}.file-option{display:block;margin-top:.7rem}.file-option input{display:block;max-width:100%}button{padding:.7rem;background:#a61d1d;color:#fff;border-radius:.5rem;min-height:44px}button:disabled{opacity:.5}.capture-modal{position:fixed;inset:0;z-index:10000;background:#fff;padding:1rem;display:flex;align-items:center;flex-direction:column;gap:1rem;overflow:auto}.capture-modal p{max-width:35rem;text-align:center}.camera{width:min(95vw,640px);aspect-ratio:4/3;position:relative;overflow:hidden;flex-shrink:0}.camera video{width:100%;height:100%;object-fit:cover}.shade{position:absolute;inset:0;display:flex;justify-content:center;align-items:center}.blur-outside{position:absolute;backdrop-filter:blur(7px);background:#0002}.blur-outside.top,.blur-outside.bottom{left:0;right:0;height:calc((100% - var(--frame-height))/2)}.blur-outside.top{top:0}.blur-outside.bottom{bottom:0}.blur-outside.left,.blur-outside.right{top:calc((100% - var(--frame-height))/2);height:var(--frame-height);width:8%}.blur-outside.left{left:0}.blur-outside.right{right:0}.passport-fold{position:absolute;top:50%;left:0;right:0;border-top:1px dashed #ffffffb3}.passport-photo-guide{position:absolute;left:7%;top:58%;width:25%;height:31%;border:1.5px solid #ffffffb3;border-radius:3px;display:flex;align-items:center;justify-content:center}.passport-photo-guide span,.passport-top-label{font-size:.7rem;color:white;text-shadow:0 1px 3px #000}.passport-top-label{position:absolute;left:0;right:0;top:20%;text-align:center}.outline{position:relative;width:84%;border:2px dashed white;border-radius:12px}
</style>
<style scoped>
.camera-bottom-actions{margin-top:auto;width:100%;display:flex;flex-direction:column;align-items:center;gap:1rem;padding-bottom:env(safe-area-inset-bottom)}
.camera-bottom-actions button{width:100%;min-height:44px}
.camera-bottom-actions .cancel-photo{background:#f3f4f6;color:#374151}
</style>
