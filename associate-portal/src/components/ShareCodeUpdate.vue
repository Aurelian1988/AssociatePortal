<template>
 <section class="share-update">
  <h2 tabindex="-1" ref="title">Update {{ isWork ? 'Right to Work' : 'Immigration' }}</h2>
  <p>Let’s get your new share code. You only need to enter the code here — we’ll review it and update the other details.</p>
  <div class="help">
   <h3>Find your code on GOV.UK</h3>
   <ol><li>Open GOV.UK using the button below and sign in.</li><li>Choose to get a share code {{ isWork ? 'to prove your right to work' : 'for something else, to prove your immigration status' }}.</li><li>Come back here and paste your code. It should start with <strong>{{ prefix }}</strong>.</li></ol>
   <a :href="url" target="_blank" rel="noopener noreferrer">Get my share code ↗</a><small>Opens in a separate tab. Your form stays here.</small>
   <details open><summary>See an example</summary><p>Example screenshots only — enter your own code, not the one pictured.</p><img v-if="!isWork" :src="helpBase+'immigration-status-example.png'" alt="Example of the Get a share code option" /><img :src="helpBase+(isWork?'rtw-share-code-example.png':'immigration-share-code-example.png')" alt="Example showing where to find your share code" /></details>
  </div>
  <form @submit.prevent="submit" novalidate>
   <label for="new-share-code">Your new {{ isWork ? 'Right to Work' : 'Immigration' }} share code</label>
   <input id="new-share-code" v-model="code" :disabled="saving" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-describedby="code-hint code-error" :aria-invalid="!!error" />
   <p id="code-hint">Nine letters and numbers, starting with {{ prefix }}. Spaces are removed automatically.</p>
   <p id="code-error" role="alert">{{ error || feedback }}</p>
   <div class="actions"><button type="submit" :disabled="saving">{{ saving?'Saving…':'Submit share code' }}</button><button type="button" :disabled="saving" @click="$emit('cancel')">Cancel</button></div>
  </form>
 </section>
</template>
<script setup>
import {computed,ref,onMounted} from 'vue'
const props=defineProps({kind:String,saving:Boolean,feedback:String})
const emit=defineEmits(['submit','cancel'])
const code=ref(''),error=ref(''),title=ref(null)
const isWork=computed(()=>props.kind==='portal_rtw_share_code')
const prefix=computed(()=>isWork.value?'W':'S')
const helpBase=import.meta.env.BASE_URL+'help/'
const url=computed(()=>isWork.value?'https://www.gov.uk/prove-right-to-work/get-a-share-code-online':'https://www.gov.uk/view-prove-immigration-status')
onMounted(()=>title.value?.focus())
function submit(){const value=code.value.replace(/\s+/g,'').toUpperCase();error.value=!/^[A-Z0-9]{9}$/.test(value)?'Enter a nine-character share code.':!value.startsWith(prefix.value)?`Use a code beginning with ${prefix.value}.`:'';if(!error.value)emit('submit',value)}
</script>
<style scoped>
.share-update{max-width:640px;margin:auto}.share-update h2{font-size:24px}.share-update p,.share-update li{font-size:16px;line-height:1.55}.help{padding:18px;background:#f4f6f9;border:1px solid #dde2e8;border-radius:16px;margin:20px 0}.help ol{padding-left:22px}.help li{margin:10px 0}.help a,.actions button{display:inline-block;padding:12px 18px;border-radius:10px;background:#aa2436;color:white;text-decoration:none;border:0;font-weight:600}.help small{display:block;margin:10px 0;color:#566070}.help img{display:block;width:100%;height:auto;border-radius:8px;margin:12px 0}.help summary{cursor:pointer;font-weight:600;margin-top:16px}label{display:block;font-weight:600;margin-bottom:8px}input{box-sizing:border-box;width:100%;padding:14px;border:1px solid #9ba5b2;border-radius:10px;font-size:20px;text-transform:uppercase}input[aria-invalid=true]{border-color:#b42335}#code-error{color:#b42335}.actions{display:flex;gap:12px}.actions button:last-child{background:#eef0f4;color:#283345}button:disabled{opacity:.55}
</style>
