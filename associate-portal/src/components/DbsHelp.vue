<template>
  <div class="dbs-help">
    <div class="help-heading"><h3>{{ hasRecent ? 'Get a share code for your DBS check' : 'How to get your DBS check' }}</h3><a class="guidance-button" :href="guidance.url" @click.prevent="openGuidance" target="_blank" rel="noopener noreferrer">{{ hasRecent ? 'Open the DBS website' : 'Apply for your check' }} ↗</a></div>
    <p v-if="browserError" role="alert" class="browser-error">{{ browserError }}</p>
    <ol class="simple-steps">
      <li><strong>Open the official website.</strong><br>Tap the button above to get started.</li>
      <li v-if="!hasRecent"><strong>Follow the steps to apply.</strong><br>Have your ID and your addresses from the last 5 years ready.</li>
      <li><strong>Share your result with your employer.</strong><br>When your result is ready, choose the option to share it with your employer. Enter <strong>dbs@onemotion.co.uk</strong> and get your share code.</li>
      <li><strong>Get your share code when your check is complete.</strong><br>Choose the option to get a share code, then send it to us with your reference number. We’ll handle the rest — no need to wait for your certificate to arrive in the post.</li>
    </ol>
    <p class="cost-note"><strong>We cover the full cost, paid on your first invoice.</strong></p>
    <p class="support-note">Can’t find your share code? Tap <strong>Chat</strong> at the top of the page and we’ll help.</p>
    <button type="button" class="info help-button" :aria-expanded="open" aria-controls="dbs-instructions" @click="open=!open">ⓘ More help</button>
    <div v-if="open" id="dbs-instructions" class="instructions">
      <p>{{ guidance.title }}</p><p>{{ guidance.summary }}</p><p>{{ guidance.share }}</p>
      <p>This link is based on your address. If your job is in a different UK nation, ask the team which service to use.</p>
    </div>
  </div>
</template>
<script setup>
import {computed,ref} from 'vue'
import {disclosureRegion,disclosureGuidance} from '@/utils/dbsGuidance'
const props=defineProps({address:{type:Object,required:true},expanded:{type:Boolean,default:false},hasRecent:{type:Boolean,default:false}})
const open=ref(false)
const browserError=ref('')
function openGuidance(){
 browserError.value=''
 // Open synchronously from the tap. Never navigate the form as a fallback.
 const tab=window.open('about:blank','_blank')
 if(!tab){browserError.value='Your browser blocked the new tab. Allow pop-ups for this page, then try again. Your form is still here.';return}
 try{tab.opener=null;tab.location.replace(guidance.value.url)}
 catch{tab.close();browserError.value='Could not open the website in a new tab. Your form is still here. Please try again.'}
}
const guidance=computed(()=>disclosureGuidance[disclosureRegion(props.address)])
</script>
<style scoped>
.dbs-help{margin:.7rem 0}.dbs-help h3{font-size:1rem;font-weight:650}.simple-steps{list-style:decimal;padding-left:1.3rem}.simple-steps li{margin:.9rem 0;font-size:.92rem;line-height:1.5}.support-note{font-size:.9rem}.info{position:relative}.info::before{display:none!important}.info{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;background:transparent;color:#b91c1c;font-weight:700;font-family:serif;font-style:italic;border:0;margin-right:.3rem}.info::before{content:'';position:absolute;width:22px;height:22px;border:1.5px solid #b91c1c;border-radius:50%;pointer-events:none}.info:focus-visible{outline:2px solid #b91c1c;border-radius:4px}.dbs-help p{margin:.6rem 0}.dbs-help a{color:#a61d1d;text-decoration:underline}.instructions{background:#f3f4f6;padding:1rem;border-radius:.5rem}
.dbs-help .guidance-button,.dbs-help .help-button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:.45rem .85rem;border-radius:.5rem;font-size:.85rem;font-family:inherit;font-style:normal;font-weight:600;text-decoration:none;line-height:1.3;margin-top:.45rem}.dbs-help .guidance-button{background:#a61d1d;border:1px solid #a61d1d;color:#fff}.dbs-help .help-button{background:#fff;border:1px solid #b7bec8;color:#374151}.dbs-help .guidance-button:focus-visible,.dbs-help .help-button:focus-visible{outline:2px solid #2563eb;outline-offset:3px}
.help-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:.75rem}.help-heading h3{flex:1;min-width:0;margin:0}.dbs-help .help-heading .guidance-button{flex-shrink:0;margin:0;max-width:48%;text-align:center}
.cost-note{padding:.75rem;border:1px solid #bbf7d0;border-radius:.5rem;background:#f0fdf4;color:#166534;font-size:.92rem}
.browser-error{color:#b91c1c;font-size:.9rem}
</style>
