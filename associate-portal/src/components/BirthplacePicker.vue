<template>
  <div class="birthplace-picker">
    <input :id="id" type="hidden" :value="modelValue" @input="emit('update:modelValue',$event.target.value)" />
    <template v-if="!manual">
      <input :id="id+'-search'" v-model="query" type="search" role="combobox" aria-autocomplete="list" :aria-expanded="!!places.length" :aria-controls="id+'-results'" aria-label="Search town, city or village of birth" :aria-required="true" :class="{pending:!modelValue || !status}" :disabled="disabled || !country" placeholder="Search town, city or village…" autocomplete="off" @input="queueSearch" @keydown.escape="cancelSearch" />
      <p v-if="!country" class="hint">Choose your birth country first.</p>
      <p v-if="busy" class="hint" role="status">Searching places in {{ country }}…</p>
      <div v-if="places.length" :id="id+'-results'" class="results" role="listbox" aria-label="Birthplace suggestions">
        <button v-for="place in places" :key="place.reference" type="button" role="option" :aria-selected="false" @click="choose(place)"><strong>{{ place.name }}</strong><small>{{ [place.region,place.country].filter(Boolean).join(', ') }}</small></button>
      </div>
      <p v-if="searched && !busy && !places.length && !error && !status" class="hint" role="status">No matches found. Try another spelling or enter your birthplace manually.</p>
      <p v-if="error" class="hint" role="status">{{ error }}</p>
      <p v-if="status==='Matched'" class="hint">Location selected: {{ modelValue }}, {{ country }}</p>
      <button type="button" class="manual-link" :disabled="disabled || !country" @click="startManual">I can’t find my birthplace</button>
    </template>
    <template v-else>
      <input :id="id+'-search'" :value="modelValue" type="text" aria-label="Town, city or village of birth" aria-required="true" :class="{pending:!modelValue}" maxlength="140" :disabled="disabled || !country" @input="manualInput($event.target.value)" />
      <p class="hint">Enter the town, city or village shown on your document. This entry will be sent for review.</p>
      <button type="button" class="manual-link" :disabled="disabled" @click="useSearch">Search for a place instead</button>
    </template>
    <small class="attribution">Place data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a></small>
  </div>
</template>
<script setup>
import {ref,watch,onUnmounted} from 'vue'
import {frappeRequest} from 'frappe-ui'
const props=defineProps({id:{type:String,default:'birth_city'},modelValue:String,country:String,status:String,disabled:Boolean})
const emit=defineEmits(['update:modelValue','selected'])
const query=ref(props.modelValue||''),manual=ref(props.status==='Review'),places=ref([]),busy=ref(false),searched=ref(false),error=ref('')
let timer,requestId=0
watch(()=>props.modelValue,value=>{if(value && value!==query.value)query.value=value;if(!value && !busy.value && !manual.value && props.status)query.value=''})
watch(()=>props.status,value=>{if(value==='Review')manual.value=true})
watch(()=>props.country,()=>{clearTimeout(timer);requestId++;query.value='';places.value=[];busy.value=false;searched.value=false;error.value='';manual.value=false})
function clearSelection(){emit('selected',{name:'',status:'',country:props.country,token:'',reference:'',manual:0})}
function queueSearch(){
 clearTimeout(timer);requestId++;places.value=[];error.value='';busy.value=false;searched.value=false;clearSelection()
 if(query.value.trim().length<2 || !props.country)return
 timer=setTimeout(search,600)
}
async function search(){
 const id=++requestId;busy.value=true;searched.value=true
 try{
  const response=await frappeRequest({url:'/api/method/onemotion.api.profile_birthplace_api.lookup_birthplaces',params:{country:props.country,query:query.value.trim()}})
  if(id!==requestId)return
  places.value=(response?.message??response).places||[]
 }catch{if(id===requestId)error.value='Location search is unavailable. Try again or enter your birthplace manually for review.'}
 finally{if(id===requestId)busy.value=false}
}
function choose(place){clearTimeout(timer);requestId++;busy.value=false;query.value=place.name;places.value=[];error.value='';emit('selected',{...place,status:'Matched',manual:0})}
function cancelSearch(){clearTimeout(timer);requestId++;places.value=[];busy.value=false;query.value=props.modelValue||''}
function startManual(){cancelSearch();manual.value=true;manualInput(props.modelValue||'')}
function manualInput(name){emit('selected',{name,status:'Review',country:props.country,token:'',reference:'',manual:1})}
function useSearch(){manual.value=false;clearSelection();query.value='';searched.value=false;error.value=''}
onUnmounted(()=>{clearTimeout(timer);requestId++})
</script>
<style scoped>
.birthplace-picker input:not([type=hidden]){width:100%;min-height:44px;padding:.7rem;border:1px solid #9ca3af;border-radius:.5rem;background:white;color:#111827;font:16px/1.4 system-ui,sans-serif}.birthplace-picker input.pending{border-color:#b91c1c}.birthplace-picker input:disabled{background:#f3f4f6;color:#6b7280}.hint{font-size:13px;color:#4b5563;margin:6px 0}.results{border:1px solid #d1d5db;border-radius:8px;max-height:240px;overflow:auto}.results button{display:block;width:100%;min-height:48px;text-align:left;padding:9px 10px;background:white;color:#111827;border:0;border-bottom:1px solid #eee;font:14px/1.4 system-ui,sans-serif}.results strong{font-weight:500}.results small{display:block;color:#6b7280;font-size:12px}.results button:focus-visible{outline:2px solid #2563eb;outline-offset:-2px}.manual-link{padding:8px 0;min-height:44px;background:transparent;border:0;color:#a61d1d;text-decoration:underline;font:13px/1.4 system-ui,sans-serif;text-align:left}.manual-link:disabled{opacity:.5}.attribution{display:block;font-size:11px;color:#6b7280;margin-top:4px}.attribution a{text-decoration:underline}
</style>
