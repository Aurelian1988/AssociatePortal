<template>
  <section class="pack">
    <p v-if="loading">Loading ACAP agreements…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <template v-if="pages.length">
      <template v-if="step < pages.length">
        <iframe :key="step" :srcdoc="pages[step].html" sandbox="" :title="pages[step].label" />
        <label class="ack"><input type="checkbox" v-model="acknowledged[step]" />I have read, understood and agree to the terms of this agreement</label>
        <nav><button v-if="step" type="button" @click="step--">◀ Previous</button><button type="button" :disabled="!acknowledged[step]" @click="step++">Next ▶</button></nav>
      </template>
      <div v-else ref="signingPage" class="signing-page" :style="{minHeight: signingHeight + 'px'}">
        <div class="signing-copy"><h2>Sign your associate compliance agreement</h2>
        <p>Your signature will apply to all of the agreements signed forthwith.</p>
        <p class="included-note">This pack also includes the NCA agreement and AMZL privacy notice (APN). Your signature applies to these documents too.</p>
        <label class="ack"><input type="checkbox" v-model="backgroundAccepted" />I have read, understood and agree to the terms of this agreement.</label>
        </div><canvas ref="canvas" width="600" height="200" aria-label="Draw your signature" @pointerdown="start" @pointermove="draw" @pointerup="stop" @pointercancel="stop" />
        <div class="signing-actions"><nav><button :disabled="saving" @click="step--">◀ Previous</button><button :disabled="saving" @click="clear">Clear signature</button></nav>
        <button class="sign" :disabled="saving || !hasInk || !backgroundAccepted || !acknowledged.every(Boolean)" @click="sign">{{ saving ? 'Saving signed agreements…' : 'Sign associate compliance agreement' }}</button>
        </div>
      </div>
    </template>
  </section>
</template>
<script setup>
import {ref,onMounted,onBeforeUnmount,nextTick,watch} from 'vue'
import {frappeRequest} from 'frappe-ui'
const emit=defineEmits(['signed'])
const background=ref([]),backgroundAccepted=ref(false)
const pages=ref([]),version=ref(''),step=ref(0),acknowledged=ref([]),loading=ref(true),error=ref(''),saving=ref(false),canvas=ref(null),hasInk=ref(false)
const signingPage=ref(null),signingHeight=ref(0)
async function fitSigningPage(){
 await nextTick()
 const el=signingPage.value;if(!el)return
 const content=el.closest('ion-content');await content?.scrollToTop(0)
 const toolbar=document.querySelector('[data-bottom-navigation]')
 const bottom=Math.min(content?.getBoundingClientRect().bottom||window.innerHeight,toolbar?.getBoundingClientRect().top||window.innerHeight)
 signingHeight.value=Math.max(0,bottom-el.getBoundingClientRect().top-12)
}
onMounted(()=>window.addEventListener('resize',fitSigningPage))
onBeforeUnmount(()=>window.removeEventListener('resize',fitSigningPage))
let drawing=false
const call=async(method,params={})=>{const r=await frappeRequest({url:'/api/method/onemotion.api.profile_agreement_pack.'+method,params});return r?.message??r}
onMounted(async()=>{try{const r=await call('read_pack');pages.value=r.pages;background.value=r.background||[];version.value=r.version;acknowledged.value=r.pages.map(()=>false)}catch(e){error.value=e?.messages?.[0]||'Could not load ACAP.'}finally{loading.value=false}})
watch(step,()=>{hasInk.value=false;drawing=false;fitSigningPage()})
function point(e){const r=canvas.value.getBoundingClientRect();return [(e.clientX-r.left)*600/r.width,(e.clientY-r.top)*200/r.height]}
function start(e){if(saving.value)return;drawing=true;canvas.value.setPointerCapture(e.pointerId);const c=canvas.value.getContext('2d');c.beginPath();c.moveTo(...point(e))}
function draw(e){if(!drawing)return;const c=canvas.value.getContext('2d');c.lineWidth=3;c.lineCap='round';c.strokeStyle='#17202b';c.lineTo(...point(e));c.stroke();hasInk.value=true}
function stop(){drawing=false}
function clear(){canvas.value?.getContext('2d').clearRect(0,0,600,200);hasInk.value=false}
async function sign(){if(saving.value||!hasInk.value||!backgroundAccepted.value||!acknowledged.value.every(Boolean))return;saving.value=true;error.value='';try{await frappeRequest({url:'/api/method/onemotion.api.profile_signing_jobs.submit',params:{kind:'pack',payload:{signature:canvas.value.toDataURL('image/png'),version:version.value,acknowledgements:pages.value.map(p=>p.field),background_accepted:backgroundAccepted.value}}});emit('signed')}catch(e){error.value=e?.messages?.[0]||'Could not save the agreement pack. Please try again.'}finally{saving.value=false}}
</script>
<style scoped>
.pack{color:#17202b}details{margin:.7rem 0}summary{color:#075da8;cursor:pointer}h2{font-size:1.2rem;font-weight:650}iframe{display:block;width:100%;height:58dvh;border:1px solid #ddd;border-radius:8px;margin:1rem 0;background:white}.ack{display:flex;gap:.7rem;align-items:flex-start;color:#075da8;font-size:.95rem}.ack input{accent-color:#0866ba;min-width:20px;height:20px}nav button{width:112px;min-width:112px;height:44px;padding:0 .6rem}nav{display:flex;justify-content:space-between;gap:1rem;margin:1rem 0}button{background:#0866ba;color:white;border-radius:8px;padding:.75rem 1rem;min-height:44px}button:disabled{opacity:.4}canvas{width:100%;height:150px;border:1px solid #aaa;border-radius:8px;background:white;touch-action:none}.sign{width:100%}
.signing-page{display:flex;flex-direction:column;justify-content:space-between;gap:16px;box-sizing:border-box}.signing-copy{display:flex;flex-direction:column;gap:12px}.signing-copy h2,.signing-copy p{margin:0}.signing-copy p{font-size:.85rem;line-height:1.4}.signing-page canvas{flex-shrink:0;height:clamp(100px,19dvh,150px)}.signing-actions nav{margin:0 0 12px}.signing-actions{width:100%}
</style>
