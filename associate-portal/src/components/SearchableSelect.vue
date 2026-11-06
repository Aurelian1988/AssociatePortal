<template>
  <div class="search-select">
    <input :id="id" type="hidden" :value="modelValue" @input="emit('update:modelValue', $event.target.value)" />
    <button ref="trigger" :id="id + '-button'" type="button" class="select-trigger" :class="{'needs-value':pending || invalid}" :disabled="disabled" :aria-label="label" role="combobox" aria-haspopup="dialog" :aria-expanded="open" :aria-controls="open ? id + '-dialog' : undefined" :aria-required="required" :aria-invalid="invalid" :aria-describedby="errorId" @click="show" @keydown.down.prevent="show" @keydown.up.prevent="show">
      <span :class="{placeholder:!modelValue}">{{ modelValue || 'Select…' }}</span><span aria-hidden="true">⌄</span>
    </button>
    <Teleport to="body">
      <div v-if="open" class="picker-backdrop" @click.self="close">
        <section :id="id + '-dialog'" ref="dialog" class="picker-dialog" role="dialog" aria-modal="true" :aria-labelledby="id + '-title'" @keydown="onKeydown">
          <header><h2 :id="id + '-title'">{{ label }}</h2><button type="button" aria-label="Close selection" @click="close">×</button></header>
          <div class="picker-search"><input ref="search" v-model="query" type="search" placeholder="Search…" :aria-label="'Search ' + label.toLowerCase()" autocomplete="off" /></div>
          <div class="picker-options">
            <button v-for="option in filtered" :key="option" type="button" class="picker-option" :aria-pressed="option === modelValue" @click="choose(option)"><span>{{ option }}</span><span v-if="option === modelValue" aria-hidden="true">✓</span></button>
            <p v-if="!filtered.length" role="status">No matches. Try another spelling.</p>
            <button type="button" class="picker-option clear-option" @click="choose('')">Clear selection</button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>
<script setup>
import {computed,nextTick,ref} from 'vue'
const props=defineProps({id:String,label:String,modelValue:[String,Number],options:{type:Array,default:()=>[]},disabled:Boolean,required:Boolean,pending:Boolean,invalid:Boolean,errorId:String})
const emit=defineEmits(['update:modelValue'])
const open=ref(false),query=ref(''),trigger=ref(null),dialog=ref(null),search=ref(null)
const normalise=value=>String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim()
const priority=value=>{
  const name=normalise(value)
  if(['united kingdom','british','british citizen'].includes(name))return 0
  if(['romania','romanian'].includes(name))return 1
  if(['bulgaria','bulgarian'].includes(name))return 2
  return 3
}
const ordered=computed(()=>[...new Set(props.options.filter(Boolean).map(String))].sort((a,b)=>priority(a)-priority(b)||a.localeCompare(b,'en',{sensitivity:'base'})))
const filtered=computed(()=>{
 const term=normalise(query.value)
 return ordered.value.filter(value=>normalise(value).includes(term) || (['uk','gb','britain'].includes(term)&&['united kingdom','british','british citizen'].includes(normalise(value))))
})
async function show(){if(props.disabled)return;query.value='';open.value=true;await nextTick();search.value?.focus()}
async function close(){open.value=false;await nextTick();trigger.value?.focus()}
function choose(value){emit('update:modelValue',value);close()}
function onKeydown(event){
 if(event.key==='Escape'){event.preventDefault();close();return}
 if(event.key!=='Tab')return
 const controls=[...dialog.value.querySelectorAll('button,input')].filter(e=>!e.disabled)
 const first=controls[0],last=controls.at(-1),current=document.activeElement
 if(event.shiftKey&&current===first){event.preventDefault();last.focus()}
 else if(!event.shiftKey&&current===last){event.preventDefault();first.focus()}
}
</script>
<style scoped>
.select-trigger{display:flex;align-items:center;justify-content:space-between;gap:.5rem;width:100%;min-height:44px;padding:.7rem;border:1px solid #9ca3af;border-radius:.5rem;background:#fff;color:#111827;text-align:left;font-family:inherit;font-size:14px;font-weight:400;line-height:1.4}.select-trigger.needs-value{border-color:#b91c1c}.select-trigger:disabled{background:#f3f4f6;color:#6b7280}.placeholder{color:#6b7280}.picker-backdrop{position:fixed;inset:0;z-index:1000001;background:#0005;display:flex;align-items:flex-end;justify-content:center;padding:10px}.picker-dialog{display:flex;flex-direction:column;width:min(100%,420px);max-height:75vh;max-height:75dvh;background:#fff;color:#111827;border-radius:14px;box-shadow:0 8px 30px #0003;overflow:hidden;font:14px/1.4 system-ui,sans-serif}.picker-dialog header{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid #e5e7eb}.picker-dialog h2{font-size:15px;font-weight:600;margin:0}.picker-dialog header button{width:44px;height:44px;border:0;background:transparent;color:#374151;font-size:24px}.picker-search{padding:8px 12px}.picker-search input{width:100%;min-height:44px;padding:8px 10px;border:1px solid #9ca3af;border-radius:8px;background:white;color:#111827;font:16px/1.4 system-ui,sans-serif}.picker-options{overflow:auto;overscroll-behavior:contain;padding:0 8px max(8px,env(safe-area-inset-bottom));min-height:0}.picker-option{display:flex;align-items:center;justify-content:space-between;width:100%;min-height:44px;border:0;border-bottom:1px solid #f3f4f6;padding:9px 8px;background:#fff;color:#111827;text-align:left;font:14px/1.4 system-ui,sans-serif}.picker-option[aria-pressed=true]{background:#fef2f2;color:#a61d1d}.clear-option{color:#6b7280}.picker-options p{padding:12px;color:#6b7280}.select-trigger:focus-visible,.picker-option:focus-visible{outline:2px solid #2563eb;outline-offset:-2px}
</style>
