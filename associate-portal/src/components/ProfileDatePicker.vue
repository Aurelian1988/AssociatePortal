<template>
 <div class="date-picker">
  <input :id="id" type="hidden" :value="modelValue" @input="emit('update:modelValue',$event.target.value)" />
  <button ref="trigger" :id="id+'-button'" type="button" class="date-trigger" :class="{attention:pending||invalid||warning}" :disabled="disabled" :aria-label="label" aria-haspopup="dialog" :aria-expanded="open" :aria-describedby="errorId" @click="show"><span>{{ display || 'Choose date…' }}</span><span aria-hidden="true">▦</span></button>
  <Teleport to="body">
   <div v-if="open" class="date-backdrop" @click.self="close">
    <section ref="dialog" class="date-dialog" role="dialog" aria-modal="true" :aria-labelledby="id+'-date-title'" @keydown="onKeydown">
     <header><h2 :id="id+'-date-title'">{{ label }}</h2><button type="button" aria-label="Close date picker" @click="close">×</button></header>
     <div class="date-controls"><div><label :for="id+'-month'">Month</label><button :id="id+'-month'" type="button" :aria-expanded="choosingMonth" @click="choosingYear=false;choosingMonth=!choosingMonth">{{ months[month-1] }} ⌄</button></div><div><label :for="id+'-year'">Year</label><button :id="id+'-year'" type="button" :aria-expanded="choosingYear" :aria-controls="id+'-years'" @click="showYears">{{ year }} ⌄</button></div></div>
     <div v-if="choosingYear" :id="id+'-years'" ref="yearList" class="years" role="region" aria-label="Choose year"><button v-for="number in years" :key="number" type="button" :data-year="number" :aria-pressed="+year===number" @click="chooseYear(number)">{{ number }}</button></div>
     <div v-else-if="choosingMonth" class="months" aria-label="Choose month"><button v-for="(name,index) in months" :key="name" type="button" :aria-pressed="month===index+1" @click="month=index+1;day=null;choosingMonth=false">{{ name }}</button></div>
     <template v-else>
      <div class="month-navigation"><button type="button" aria-label="Previous month" :disabled="!validYear" @click="moveMonth(-1)">‹</button><span>{{ months[month-1] }} {{ year }}</span><button type="button" aria-label="Next month" :disabled="!validYear" @click="moveMonth(1)">›</button></div>
      <div class="calendar"><span v-for="name in ['Mo','Tu','We','Th','Fr','Sa','Su']" :key="name" class="weekday">{{ name }}</span><span v-for="blank in offset" :key="'blank'+blank"></span><button v-for="number in days" :key="number" type="button" :aria-label="number+' '+months[month-1]+' '+year" :aria-pressed="day===number" :disabled="!allowed(iso(number))" @click="day=number">{{ number }}</button></div>
      <p v-if="!validYear" class="date-hint" role="status">Enter a four-digit year.</p>
     </template>
     <footer><button type="button" class="clear-date" @click="emit('update:modelValue','');close()">Clear</button><button type="button" class="use-date" :disabled="!selected || !allowed(selected)" @click="emit('update:modelValue',selected);close()">Use date</button></footer>
    </section>
   </div>
  </Teleport>
 </div>
</template>
<script setup>
import {computed,nextTick,ref} from 'vue'
const props=defineProps({id:String,label:String,modelValue:String,min:String,max:String,disabled:Boolean,pending:Boolean,invalid:Boolean,warning:Boolean,errorId:String})
const emit=defineEmits(['update:modelValue'])
const months=['January','February','March','April','May','June','July','August','September','October','November','December']
const open=ref(false),year=ref(''),month=ref(1),day=ref(null),choosingMonth=ref(false),choosingYear=ref(false),trigger=ref(null),dialog=ref(null),yearList=ref(null)
const years=computed(()=>{
 const current=new Date().getFullYear()
 const first=props.min?+props.min.slice(0,4):Math.min(1900,+year.value||1900)
 const last=props.max?+props.max.slice(0,4):Math.max(current+100,+year.value||current)
 return Array.from({length:Math.max(0,last-first+1)},(_,index)=>first+index)
})
async function showYears(){
 choosingYear.value=!choosingYear.value;choosingMonth.value=false
 if(!choosingYear.value)return
 await nextTick()
 const selected=yearList.value.querySelector('[data-year="'+year.value+'"]')
 if(selected){yearList.value.scrollTop=selected.offsetTop-(yearList.value.clientHeight-selected.clientHeight)/2;selected.focus({preventScroll:true})}
}
async function chooseYear(number){
 year.value=String(number);choosingYear.value=false
 if(day.value>days.value)day.value=days.value
 await nextTick();dialog.value.querySelector('[id="'+props.id+'-year"]')?.focus()
}
const validYear=computed(()=>/^\d{4}$/.test(year.value)&&+year.value>=1000)
const days=computed(()=>validYear.value?new Date(Date.UTC(+year.value,month.value,0)).getUTCDate():0)
const offset=computed(()=>validYear.value?(new Date(Date.UTC(+year.value,month.value-1,1)).getUTCDay()+6)%7:0)
const iso=number=>year.value+'-'+String(month.value).padStart(2,'0')+'-'+String(number).padStart(2,'0')
const selected=computed(()=>validYear.value&&day.value&&day.value<=days.value?iso(day.value):'')
const display=computed(()=>{
 const match=/^(\d{4})-(\d{2})-(\d{2})$/.exec(props.modelValue||'')
 return match&&months[+match[2]-1]?`${+match[3]} ${months[+match[2]-1]} ${match[1]}`:props.modelValue
})
function allowed(value){return (!props.min||value>=props.min)&&(!props.max||value<=props.max)}
async function show(){
 if(props.disabled)return
 const match=/^(\d{4})-(\d{2})-(\d{2})$/.exec(props.modelValue||'');const now=new Date()
 year.value=match?match[1]:String(now.getFullYear());month.value=match?+match[2]:now.getMonth()+1;day.value=match?+match[3]:null
 choosingMonth.value=false;choosingYear.value=false;open.value=true;await nextTick();dialog.value.querySelector('button')?.focus()
}
async function close(){open.value=false;await nextTick();trigger.value?.focus()}
function moveMonth(amount){const date=new Date(Date.UTC(+year.value,month.value-1+amount,1));year.value=String(date.getUTCFullYear());month.value=date.getUTCMonth()+1;day.value=null}
function onKeydown(event){
 if(event.key==='Escape'){event.preventDefault();close();return}
 if(event.key!=='Tab')return
 const controls=[...dialog.value.querySelectorAll('button,input')].filter(e=>!e.disabled&&e.getClientRects().length)
 const first=controls[0],last=controls.at(-1)
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
 else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}
</script>
<style scoped>
.date-trigger{display:flex;justify-content:space-between;align-items:center;gap:.5rem;width:100%;min-height:44px;border:1px solid #9ca3af;border-radius:.5rem;padding:.7rem;background:white;color:#111827;text-align:left;font:14px/1.4 system-ui,sans-serif}.date-trigger.attention{border-color:#b91c1c}.date-trigger:disabled{background:#f3f4f6;color:#6b7280}.date-backdrop{position:fixed;inset:0;z-index:1000001;background:#0005;display:flex;align-items:flex-end;justify-content:center;padding:10px}.date-dialog{width:min(100%,400px);max-height:90vh;max-height:90dvh;overflow:auto;border-radius:14px;background:#fff;color:#111827;box-shadow:0 8px 30px #0003;padding:10px;font:14px/1.4 system-ui,sans-serif}.date-dialog header{display:flex;align-items:center;justify-content:space-between}.date-dialog h2{font-size:15px;font-weight:600;margin:0}.date-dialog button{min-height:44px;border:0;background:#fff;color:#111827;border-radius:6px;font:14px/1.4 system-ui,sans-serif}.date-dialog header button{width:44px;font-size:24px}.date-controls{display:grid;grid-template-columns:1fr 100px;gap:10px;margin:8px 0}.date-controls label{display:block;font-size:12px;color:#4b5563;margin-bottom:3px}.date-controls button,.date-controls input{width:100%;min-height:44px;border:1px solid #9ca3af;border-radius:7px;padding:8px;background:white;color:#111827}.date-controls input{font:16px/1.4 system-ui,sans-serif}.years{position:relative;display:flex;flex-direction:column;height:264px;overflow-y:auto;overscroll-behavior:contain;scroll-snap-type:y proximity;border:1px solid #e5e7eb;border-radius:8px}.years button{flex-shrink:0;min-height:48px;scroll-snap-align:center}.months{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}.month-navigation{display:flex;align-items:center;justify-content:space-between}.month-navigation button{width:44px;font-size:24px}.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}.weekday{text-align:center;padding:5px;color:#6b7280;font-size:12px}.date-dialog button[aria-pressed=true]{background:#a61d1d;color:white}.date-dialog button:disabled{opacity:.35}.date-dialog footer{display:flex;justify-content:space-between;gap:12px;margin-top:10px;padding-bottom:env(safe-area-inset-bottom)}.date-dialog footer button{padding:8px 16px}.date-dialog .use-date{background:#a61d1d;color:white}.date-hint{font-size:13px;color:#b91c1c}.date-dialog button:focus-visible,.date-trigger:focus-visible{outline:2px solid #2563eb;outline-offset:-2px}
</style>
