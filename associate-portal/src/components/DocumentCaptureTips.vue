<template>
  <section class="capture-tips" aria-label="Passport photo tips" @mouseenter="hovered=true" @mouseleave="hovered=false" @focusin="hovered=true" @focusout="hovered=false">
    <img :src="slides[index].image" :alt="slides[index].text" />
    <div class="tip-controls">
      <button type="button" aria-label="Previous photo tip" @click="move(-1)">‹</button>
      <span>{{ index + 1 }} / {{ slides.length }}</span>
      <button type="button" :aria-label="paused ? 'Play photo tips' : 'Pause photo tips'" @click="paused=!paused">{{ paused ? 'Play' : 'Pause' }}</button>
      <button type="button" aria-label="Next photo tip" @click="move(1)">›</button>
    </div>
  </section>
</template>
<script setup>
import {ref,onMounted,onBeforeUnmount} from 'vue'
import fullDocument from '@/assets/capture-tips/full-document.png'
import straight from '@/assets/capture-tips/straight.jpg'
import glare from '@/assets/capture-tips/glare.jpg'
import fingers from '@/assets/capture-tips/fingers.jpg'
const props=defineProps({active:Boolean})
const slides=[{image:fullDocument,text:'Keep the full document in view, straight and with nothing covering it.'},{image:straight,text:'Keep your document straight so all details can be read.'},{image:glare,text:'Avoid glare and shadows on the document.'},{image:fingers,text:'Keep your fingers clear of the document details.'}]
const index=ref(0),paused=ref(false),hovered=ref(false)
const move=direction=>{index.value=(index.value+direction+slides.length)%slides.length}
let timer
onMounted(()=>{paused.value=window.matchMedia('(prefers-reduced-motion: reduce)').matches;timer=setInterval(()=>{if(props.active&&!paused.value&&!hovered.value&&!document.hidden)move(1)},750)})
onBeforeUnmount(()=>clearInterval(timer))
</script>
<style scoped>
.capture-tips{max-width:320px;margin:.75rem auto;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#fff}
.capture-tips img{display:block;width:100%;height:auto;aspect-ratio:1.09;object-fit:contain}
.tip-controls{display:flex;align-items:center;justify-content:center;gap:1rem;padding:.25rem;border-top:1px solid #eef0f3;font-size:.8rem;color:#4b5563}
.tip-controls button{min-width:44px;min-height:44px;border:0;border-radius:6px;background:white;color:#a61d1d;font:inherit;cursor:pointer}
.tip-controls button:focus-visible{outline:2px solid #a61d1d}
</style>
