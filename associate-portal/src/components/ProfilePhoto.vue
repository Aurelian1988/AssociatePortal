<template>
  <section class="photo-section" aria-label="Required profile picture">
    <div class="avatar" :class="{'photo-needed':!photo}"><img v-if="photo" :src="photo" alt="Your profile picture" /><span v-else>{{ initials }}</span></div>
    <button class="add-photo" type="button" :disabled="saving" aria-label="Take or replace profile picture" @click="openCamera">+</button>
    <strong class="photo-label">Profile picture *</strong>
    <p v-if="photo" class="saved-photo">Photo saved ✓</p>
    <template v-else><span class="required-badge">Required to continue</span><p class="photo-prompt">Let’s put a face to your name.</p><p>Tap + to add a clear headshot.</p></template>
    <p v-if="error" role="alert">{{ error }}</p>
    <Teleport to="body"><div v-if="opened" class="capture-dialog" role="dialog" aria-modal="true" aria-label="Take profile picture" @keydown.esc="close">
      <h2>Take your headshot</h2>
      <p v-if="!preview" class="face-status" :class="{ ready }" role="status">{{ faceGuidance }}</p>
      <div v-show="!preview" class="camera">
        <video ref="video" autoplay muted playsinline />
        <svg viewBox="0 0 300 400" aria-hidden="true">
          <rect x="30" y="20" width="240" height="325" rx="12" fill="none" :stroke="ready ? '#34c96f' : '#91c8ff'" :opacity="ready ? 1 : .65" stroke-width="2"/>
        </svg>
      </div>
      <img v-if="preview" :src="preview" class="preview" alt="Review your headshot" />
      <p role="status">{{ busy ? 'Preparing your photo…' : preview ? 'Check your face is clear and fully visible.' : 'Keep your head inside the blue frame. Face the camera and hold steady. The frame turns green when ready.' }}</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <div class="buttons" :class="{ 'capture-actions': !preview }">
        <button v-if="!preview" class="shutter" type="button" :disabled="!ready || busy" @click="capture">Take photo</button>
        <button v-if="preview" type="button" :disabled="busy || saving" @click="openCamera">Retake</button>
        <button v-if="preview" type="button" :disabled="busy || saving || !prepared" @click="save">{{ saving ? 'Saving…' : 'Use photo' }}</button>
        <button class="cancel-camera" type="button" :disabled="saving || busy" @click="close">Cancel</button>
      </div>
    </div></Teleport>
  </section>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { createFaceDetector, assessSelfie } from '@/utils/selfieFaceDetection'
const props = defineProps({ photo: String, firstName: String, lastName: String })
const emit = defineEmits(['saved'])
const initials = computed(() => ((props.firstName || '').charAt(0) + (props.lastName || '').charAt(0)).toUpperCase() || '?')
const video = ref(null), opened = ref(false), ready = ref(false), busy = ref(false), saving = ref(false), preview = ref(''), error = ref(''), prepared = ref(false)
const faceBoxes=ref([]),faceGuidance=ref('Starting smart camera…')
let detector,faceTimer,inFlight,previousBox,steadySince=0
const outline = 'M150 45 C105 45 94 78 96 119 C98 158 112 183 130 194 L130 215 C118 232 65 230 40 270 L25 355 L275 355 L260 270 C235 230 182 232 170 215 L170 194 C188 183 202 158 204 119 C206 78 195 45 150 45 Z'
let stream, source, previousFocus, generation = 0
let screenLock,analysisFrame,captureFrame,readyFrame
async function keepScreenAwake(run=generation){
  if(!opened.value || document.visibilityState!=='visible' || !navigator.wakeLock || (screenLock&&!screenLock.released))return
  try{
    const lock=await navigator.wakeLock.request('screen')
    if(run!==generation || !opened.value){await lock.release();return}
    screenLock=lock
    lock.addEventListener('release',()=>{if(screenLock===lock)screenLock=null})
  }catch{/* Camera remains usable when the device declines a wake lock. */}
}
function releaseScreen(){const lock=screenLock;screenLock=null;if(lock&&!lock.released)lock.release().catch(()=>{})}
function visibilityChanged(){if(document.visibilityState==='visible'&&opened.value)keepScreenAwake()}

function stop() {
  readyFrame=null;analysisFrame=null;captureFrame=null
  clearTimeout(faceTimer);const old=detector;detector=null
  if(old)Promise.resolve(inFlight).catch(()=>{}).then(()=>old.close()).catch(()=>{})
  stream?.getTracks().forEach(track => track.stop());stream=null;ready.value=false;faceBoxes.value=[];previousBox=null;steadySince=0
}
function cameraFrame(width=320) {
  const v=video.value,c=document.createElement('canvas');c.width=width;c.height=Math.round(width*4/3)
  const w=Math.min(v.videoWidth,v.videoHeight*3/4),h=w*4/3
  c.getContext('2d').drawImage(v,(v.videoWidth-w)/2,(v.videoHeight-h)/2,w,h,0,0,c.width,c.height)
  return c
}
async function detectLoop(run) {
  if(run!==generation||!detector||!video.value?.videoWidth)return
  try {
    const v=video.value,width=Math.min(720,v.videoWidth,v.videoHeight*3/4)
    captureFrame=cameraFrame(Math.floor(width))
    analysisFrame=document.createElement('canvas');analysisFrame.width=320;analysisFrame.height=Math.round(320*4/3)
    analysisFrame.getContext('2d').drawImage(captureFrame,0,0,analysisFrame.width,analysisFrame.height)
    inFlight=detector.send({image:analysisFrame});await inFlight
  }
  catch { if(run===generation){ready.value=false;faceGuidance.value='Face detection is unavailable. Close the camera and try again.'} return }
  if(run===generation)faceTimer=setTimeout(()=>detectLoop(run),150)
}
function close() { generation++; releaseScreen(); stop(); opened.value = false; preview.value = ''; source = null; previousFocus?.focus() }
async function openCamera() {
  const run = ++generation
  releaseScreen()
  previousFocus = document.activeElement
  stop(); error.value = ''; preview.value = ''; prepared.value = false; opened.value = true
  keepScreenAwake(run)
  await nextTick()
  try {
    const acquired = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:960},height:{ideal:1280}},audio:false})
    if (run !== generation) { acquired.getTracks().forEach(t => t.stop()); return }
    stream = acquired; video.value.srcObject = stream; await video.value.play()
    faceGuidance.value='Keep your head inside the blue frame'
    const model=await createFaceDetector(({detections})=>{
      if(run!==generation||!opened.value||preview.value)return
      faceBoxes.value=detections.map(d=>d.boundingBox)
      const frame=analysisFrame
      if(!frame)return
      const result=assessSelfie(detections,frame.getContext('2d').getImageData(0,0,frame.width,frame.height),previousBox)
      previousBox=result.box
      if(result.ready){if(!steadySince)steadySince=Date.now()}else steadySince=0
      ready.value=result.ready&&Date.now()-steadySince>=350
      readyFrame=ready.value?captureFrame:null
      faceGuidance.value=result.ready&&!ready.value?'Hold steady':result.message
    })
    if(run!==generation){await model.close();return}
    detector=model;detectLoop(run)
  } catch { error.value = 'Camera unavailable. Allow camera access in your browser settings and try again.' }
}
async function capture() {
  const v = video.value
  if (!v?.videoWidth || !ready.value) return
  if(!readyFrame)return
  // Save the same frame that passed face and clarity checks, before tap motion.
  source=readyFrame
  stop(); preview.value = source.toDataURL('image/jpeg',.9)
  prepared.value = true
}
async function save() {
  if (!prepared.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const response = await frappeRequest({url:'/api/method/onemotion.api.profile_photo.save_profile_photo',method:'POST',params:{image_base64:preview.value}})
    emit('saved',response?.message ?? response); close()
  } catch { error.value = 'Could not save your photo. Please try again. Your profile remains incomplete until it is saved.' }
  finally { saving.value = false }
}
defineExpose({openCamera})
onMounted(()=>document.addEventListener('visibilitychange',visibilityChanged))
onBeforeUnmount(() => { generation++; releaseScreen();stop();document.removeEventListener('visibilitychange',visibilityChanged) })
</script>
<style scoped>
.required-badge{font-size:.7rem;font-weight:600;color:#a61d1d;background:#fff3f1;border-radius:20px;padding:3px 9px}.photo-section>.photo-prompt{font-size:.85rem;font-weight:500;color:#111827;margin-top:.3rem}.avatar.photo-needed{outline:1px dashed #2563eb;outline-offset:5px}.photo-section>.saved-photo{color:#166534}
.photo-section{display:flex;align-items:center;flex-direction:column;gap:.3rem;margin:.75rem 0 1rem;padding:0;background:transparent;border:0;box-shadow:none}.photo-label{font-size:.9rem;font-weight:500}.photo-section>p{font-size:.8rem;color:#6b7280;margin:0}.avatar{width:76px;height:76px;border-radius:50%;background:#2563eb;color:white;display:grid;place-items:center;overflow:hidden;font-size:1.8rem;font-weight:700}.avatar img{width:100%;height:100%;object-fit:cover}.add-photo{border-radius:50%;font-size:1.2rem;width:36px;height:36px;min-height:36px;padding:0;margin-top:-12px;z-index:1;border:3px solid white;box-shadow:0 1px 4px #0002}button{background:#a61d1d;color:white;padding:.6rem 1rem;border-radius:.5rem;min-height:44px}button:disabled{opacity:.5}.capture-dialog{position:fixed;inset:0;z-index:1000002;background:#fff;display:flex;align-items:center;flex-direction:column;gap:1rem;padding:1rem;overflow:auto}.face-status{padding:.5rem .8rem;border-radius:.5rem;background:#fff0eb;color:#8c301f;font-size:.85rem;min-height:2.5rem}.face-status.ready{background:#e9f9ed;color:#166534}.capture-dialog h2{font-size:1.2rem;font-weight:700}.camera,.preview{width:min(75vw,300px);aspect-ratio:3/4;position:relative;flex-shrink:0}.camera video{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}.camera svg{position:absolute;inset:0;width:100%;height:100%}.preview{object-fit:cover}.buttons{display:flex;gap:.5rem;flex-wrap:wrap;width:100%;max-width:32rem;margin-top:auto;position:sticky;bottom:0;background:#fff;padding:.65rem 0 max(.3rem,env(safe-area-inset-bottom))}.buttons.capture-actions{display:flex;flex-direction:column;gap:.2rem;max-width:none;flex-shrink:0}.buttons .shutter{width:100%;min-height:58px;border-radius:8px;font-size:1.05rem;font-weight:600}.buttons .cancel-camera{background:#fff;color:#374151;min-height:44px}.capture-dialog{gap:.6rem;padding:max(.75rem,env(safe-area-inset-top)) .75rem 0}.capture-dialog .face-status{font-size:1rem;font-weight:600;color:#111827;background:#f3f4f6;width:100%;text-align:center}.capture-dialog .face-status.ready{color:#14532d;background:#dcfce7}.capture-dialog>.camera,.capture-dialog>.preview{width:min(75vw,300px,calc((100dvh - 270px)*.75))}.capture-dialog>p{color:#111827;font-size:.9rem}.capture-dialog p{max-width:30rem;text-align:center}[role=alert]{color:#b91c1c}
</style>
<style scoped>
.buttons.capture-actions{gap:1rem}
.buttons.capture-actions .cancel-camera{order:-1;width:100%;background:#f3f4f6}
</style>
