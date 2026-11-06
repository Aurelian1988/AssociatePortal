<template>
  <ion-page>
    <ion-header v-if="!onboarding.profile?.submitted || !onboarding.pushReady" class="ion-no-border">
      <header class="profile-header">
        <div v-if="!onboarding.profile?.submitted" class="title-row">
          <h1 class="active-tab" aria-current="page">My Profile</h1>
          <button type="button" class="text-button" @click="router.push('/chat')">Chat</button>
          <AccountLogoutMenu/>
        </div>
        <div v-if="onboarding.profile" class="push-inline">
          <span>{{ onboarding.pushReady ? 'Push notifications enabled ✓' : 'Push notifications required' }}</span>
          <button v-if="!onboarding.pushReady" type="button" :disabled="onboarding.pushBusy" @click="notificationAction">{{ onboarding.pushBusy ? 'Connecting…' : 'Enable' }}</button>
        </div>
        <div v-if="pushOpen" class="push-popover" role="status">
          <button type="button" class="text-button" aria-label="Close notification help" @click="pushOpen=false">×</button>
          <p v-if="!pushSupported">This browser does not support push notifications. Use Chrome on Android, or on iPhone add the portal to your Home Screen.</p>
          <p v-else-if="permission === 'denied'">Allow notifications in this site's browser permissions and your device settings, then check again.</p>
          <p v-else>{{ onboarding.pushError || 'Enable notifications on this device to submit your profile and use the app.' }}</p>
          <button v-if="pushSupported" type="button" :disabled="onboarding.pushBusy" @click="enablePush">Check again</button>
        </div>
        <template v-if="onboarding.profile">
          <div v-if="!onboarding.profile.submitted" class="progress-label"><strong>{{ progress.percentage }}% Complete</strong></div>
          <progress v-if="!onboarding.profile.submitted" :value="progress.percentage" max="100" aria-label="Profile completion" />
          <p v-if="!onboarding.profile.submitted">Complete your details and submit your profile to unlock the app.</p>
        </template>
      </header>
    </ion-header>
    <ion-content ref="profileContent">
      <main class="profile-body">
        <p v-if="loading" role="status">Loading your profile…</p>
        <div v-if="loadError" role="alert" class="notice error"><p>{{ loadError }}</p><button @click="load">Try again</button></div>
        <template v-if="onboarding.profile && !loading">

          <ProfilePhoto ref="profilePhotoControl" v-if="currentStage?.id === 'personal'" :photo="draft.id_photo" :first-name="draft.first_name" :last-name="draft.last_name" @saved="photoSaved" />

          <p v-if="!onboarding.profile.submitted" class="hint">Fields marked * are required. Submit each section to save it and continue. You can return later to finish.</p>

          <ProfileOverview v-if="onboarding.profile.submitted" :values="draft" :errors="onboarding.profile.completion?.errors || {}" @saved="applyState" @agreements="router.push('/agreements')" @home="router.replace('/home')" />
          <form v-else @submit.prevent="onboarding.profile.submitted ? saveDraft() : currentStage ? submitSection() : submitProfile()" novalidate>
            <h2 v-if="currentStage && !['background_screening','national_insurance','dbs'].includes(currentStage.id)">{{ currentStage.title }}</h2>
            <p v-if="currentStage?.id === 'contact'" class="hint">Start with your contact details. We’ll use your invitation email and phone number to find your existing profile or create one. Your previous details will be kept.</p>
            <section v-for="section in formSections" :key="section.title" class="profile-section">
              <div class="section-heading"><h2>{{ section.title === 'Identity' ? 'Identity document' : section.title === 'DBS' ? 'Background Screening' : section.title === 'DBS Check' ? 'Background Screening' : section.title }}</h2>
                <label v-if="section.title === 'Identity'" class="document-option"><input type="checkbox" role="switch" :checked="showAlternativeDocuments" :disabled="saving" @change="togglePassportOptions($event.target.checked)" /><span>I don’t have a passport</span></label>
                <label v-if="section.title === 'Driving Licence'" class="document-option"><input id="no-driving-licence" type="checkbox" role="switch" :checked="noDrivingLicence(draft)" :disabled="saving" @change="toggleLicence($event.target.checked)" /><span>I don’t have a driving licence</span></label>
              </div>
              <p v-if="section.title === 'Identity' && !onboarding.profile.documents?.passport_ready && !showAlternativeDocuments" class="hint">Capture your passport photo page first. We’ll read the details for you to check.</p>
              <template v-if="section.title === 'Birth Certificate'">
                <ProfileDocumentCapture kind="birth_certificate" label="Birth certificate" :file="onboarding.profile.documents?.files.birth_certificate" @saved="documentSaved" @captured="documentCaptured" />
                <p v-if="!onboarding.profile.documents?.birth_certificate_ready">Upload your birth certificate to unlock your personal details.</p>
              </template>
              <template v-if="section.title === 'Driving Licence' && !noDrivingLicence(draft)">
                <ProfileDocumentCapture kind="licence_front" label="Licence front" :file="onboarding.profile.documents?.files.licence_front" @saved="documentSaved" @captured="documentCaptured" />
                <ProfileDocumentCapture kind="licence_back" label="Licence back" :file="onboarding.profile.documents?.files.licence_back" @saved="documentSaved" @captured="documentCaptured" />
                <p v-if="!hasCapture('licence_front') || !hasCapture('licence_back')">Take both photos to review the licence details.</p><p v-else-if="!onboarding.profile.documents?.licence_ready">Review your details below. Both photos must finish saving before you submit.</p>
              </template>
              <template v-if="section.title === 'Identity' && !draft.portal_no_passport && (!showAlternativeDocuments || documentChoice==='Travel Document')">
                <ProfileDocumentCapture kind="passport" :label="documentChoice==='Travel Document' ? 'Travel document photo page' : 'Passport photo page'" :file="onboarding.profile.documents?.files.passport" @saved="documentSaved" @captured="documentCaptured" />

              </template>

              <div v-if="section.title === 'Identity' && showAlternativeDocuments" class="identity-fields">
                <div id="document-choice" class="document-choices" role="group" aria-label="Identity document type">
                  <button v-for="choice in ['Travel Document','Birth Certificate']" :key="choice" type="button" :aria-pressed="documentChoice===choice" :disabled="saving || (choice==='Birth Certificate' && !birthCertificateEligible) || (choice==='Travel Document' && !travelDocumentAllowed(draft))" @click="documentChoice=choice">{{ choice }}</button>
                </div>
                <p v-if="!travelDocumentAllowed(draft)" class="hint">Travel Document is available only to non-EU, non-UK nationalities. Confirm your nationality below.</p>
                <p v-if="progress.errors.portal_identity_type" class="error-text">{{ progress.errors.portal_identity_type }}</p>
                <p v-if="!birthCertificateEligible" class="hint">Birth Certificate is available only to British applicants whose birth country is United Kingdom. Otherwise, use a passport.</p>
                <p v-if="progress.errors.portal_no_passport" class="error-text">{{ progress.errors.portal_no_passport }}</p>
              </div>

              <div v-if="section.title === 'Right to Work'" class="notice">
                <p>Enter your own current Right to Work share code. Saving a code does not verify your right to work.</p>
                <a href="https://www.gov.uk/prove-right-to-work/get-a-share-code-online" target="_blank" rel="noopener noreferrer">Get a Right to Work share code on GOV.UK ↗</a>
                <details><summary>Where to find your share code</summary><p>Example only. Do not use the code or expiry date pictured.</p><img :src="helpBase + 'rtw-share-code-example.png'" alt="Example showing where a Right to Work share code appears" loading="lazy" /></details>
              </div>
              <div v-if="section.title === 'Immigration'" class="notice">
                <p>Enter your own current Immigration share code.</p>
                <a href="https://www.gov.uk/view-prove-immigration-status" target="_blank" rel="noopener noreferrer">View and prove your immigration status on GOV.UK ↗</a>
                <details><summary>How to find your Immigration share code</summary><p>Examples only. Open your immigration status, choose “Get a share code”, then enter your own code.</p><img :src="helpBase + 'immigration-status-example.png'" alt="Example of the Get a share code button on the immigration status page" loading="lazy" /><img :src="helpBase + 'immigration-share-code-example.png'" alt="Example of an immigration share code result" loading="lazy" /></details>
              </div>
              <template v-if="section.title === 'Address'">
                <ProfileDocumentCapture kind="proof_of_address" label="Proof of address" :file="onboarding.profile.documents?.files.proof_of_address" @saved="documentSaved" @captured="documentCaptured" />
                <p v-if="onboarding.profile.address_evidence" class="notice">Name and date check: <strong>{{ onboarding.profile.address_evidence.status }}</strong><br>Document date: {{ onboarding.profile.address_evidence.document_date || 'Not readable — review needed' }}</p>
                <p class="hint">Upload a document showing your last name and dated within the last six months. Otherwise it will be sent for review.</p>
              </template>
              <p v-if="section.title==='Background Screening' || section.title==='DBS' || (section.title==='DBS Check' && onboarding.profile.dbs_amazon_site)" class="hint">We ask for your mother’s first name and maiden name because they are needed for DBS background-check validations.</p>
              <div v-for="field in section.fields.filter(f => fieldVisible(section.title, f.key))" :key="field.key" class="field" :class="{'expired-photocard': expiredDocumentDate(field.key), 'pending-required': pendingRequired(field)}">
                <label :for="fieldInputId(field.key) + (field.key==='birth_city'?'-search':(searchableField(field)||field.type==='date')?'-button':'')">{{ field.label }}<span v-if="field.required"> *</span><span v-else-if="field.editable" class="optional"> (optional)</span></label>
                <p v-if="!field.editable" class="read-only">{{ draft[field.key] ?? '—' }}<small>Managed by your team</small></p>
                <div v-else-if="['portal_has_recent_dbs','portal_has_dbs_share_code','portal_has_dbs_certificate'].includes(field.key)" class="answer-buttons" role="group" :aria-label="field.label" :id="fieldInputId(field.key)" :aria-invalid="!!visibleErrors[field.key]">
                  <button v-for="answer in ['Yes','No']" :key="answer" type="button" :disabled="saving" :aria-pressed="draft[field.key]===answer" @click="draft[field.key]=answer">{{ answer }}</button>
                </div>
                <BirthplacePicker v-else-if="field.key === 'birth_city'" :id="fieldInputId(field.key)" v-model="draft.birth_city" :country="draft.birth_country" :status="draft.portal_birthplace_status" :disabled="fieldLocked(field.key)" @selected="birthplaceSelected" />
                <SearchableSelect v-else-if="searchableField(field)" :id="fieldInputId(field.key)" :model-value="draft[field.key]" @update:model-value="value=>selectField(field,value)" :label="field.label" :required="field.required" :options="field.options" :disabled="fieldLocked(field.key)" :pending="pendingRequired(field)" :invalid="!!visibleErrors[field.key]" :error-id="visibleErrors[field.key] ? field.key + '-error' : undefined" />
                <select :disabled="fieldLocked(field.key)" v-else-if="field.type === 'select'" :id="fieldInputId(field.key)" v-model="draft[field.key]" @change="markDocumentEdit(field.key)" :aria-required="field.required" :aria-invalid="!!visibleErrors[field.key]" :aria-describedby="visibleErrors[field.key] ? field.key + '-error' : undefined">
                  <option value="">Select…</option><option v-for="option in field.options" :key="option" :value="option">{{ option }}</option>
                </select>
                <select :disabled="fieldLocked(field.key)" v-else-if="field.type === 'checkbox'" :id="fieldInputId(field.key)" v-model="draft[field.key]" @change="markDocumentEdit(field.key)"><option :value="0">No</option><option :value="1">Yes</option></select>
                <ProfileDatePicker v-else-if="field.type==='date'" :id="fieldInputId(field.key)" v-model="draft[field.key]" @update:model-value="markDocumentEdit(field.key,$event)" :label="field.label" :max="dateMaximum(field.key)" :disabled="fieldLocked(field.key)" :pending="pendingRequired(field)" :invalid="!!visibleErrors[field.key]" :warning="expiredDocumentDate(field.key)" :error-id="expiredDocumentDate(field.key) ? field.key+'-expiry-warning' : visibleErrors[field.key] ? field.key+'-error' : undefined" />
                <input v-else :disabled="fieldLocked(field.key)" :id="fieldInputId(field.key)" v-model="draft[field.key]" :type="field.key === 'mobile' ? 'tel' : field.type" :inputmode="field.key === 'mobile' ? 'tel' : undefined" :autocomplete="field.key === 'mobile' ? 'tel' : undefined" @input="markDocumentEdit(field.key,$event.target.value)" @blur="formatIdentifier(field.key)" :aria-required="field.required" :aria-invalid="!!visibleErrors[field.key]" :aria-describedby="[visibleErrors[field.key] && !expiredDocumentDate(field.key) ? field.key + '-error' : '', expiredDocumentDate(field.key) ? field.key + '-expiry-warning' : ''].filter(Boolean).join(' ') || undefined" />
                <p v-if="field.key==='dl_expiry_date'" class="hint">This expiry date is located on the rear of your photocard.</p>
                <p v-if="field.key==='dl_photocard_expiry'" class="hint">This expiry date is located on the front of your photocard.</p>
                <p v-if="expiredDocumentDate(field.key)" :id="field.key + '-expiry-warning'" class="error-text" role="status">{{ expiryWarning(field.key) }}</p>
                <p v-if="visibleErrors[field.key] && !expiredDocumentDate(field.key)" :id="field.key + '-error'" class="error-text">{{ visibleErrors[field.key] }}</p>
              </div>
              <ProfileDocumentCapture v-if="section.title==='DBS Check' && !onboarding.profile.dbs_amazon_site && draft.portal_has_recent_dbs==='Yes' && draft.portal_has_dbs_share_code==='No' && draft.portal_has_dbs_certificate==='Yes'" kind="dbs_certificate" label="DBS certificate" :file="onboarding.profile.documents?.files.dbs_certificate" @saved="documentSaved" />
              <div v-if="section.title==='DBS Check' && !onboarding.profile.dbs_amazon_site && ((draft.portal_has_recent_dbs==='No' && !onboarding.profile.dbs_amazon_site) || (draft.portal_has_recent_dbs==='Yes' && draft.portal_has_dbs_share_code==='No' && draft.portal_has_dbs_certificate==='No' && onboarding.profile.dbs_share_guidance_required))" class="notice">
                <DbsHelp :address="draft" :has-recent="draft.portal_has_recent_dbs==='Yes'" />
              </div>
            </section>
            <template v-if="currentStage?.id==='personal'">
              <input v-for="key in ['portal_birthplace_token','portal_birthplace_manual','portal_birthplace_status','portal_birthplace_country','portal_birthplace_reference']" :key="key" :id="key" type="hidden" v-model="draft[key]" />
            </template>
            <div v-if="documentApproval" class="notice" role="status"><strong>Document approval: {{ documentApproval.status === 'Approved' ? 'Approved' : documentApproval.decided ? 'Review required' : 'Checked when you submit' }}</strong><p v-if="documentApproval.decided && documentApproval.status !== 'Approved'">Your document is saved. The team will review any missing, corrected or uncertain details.</p></div>
            <div v-if="message" role="status" class="notice">{{ message }}</div>
            <div v-if="saveError" role="alert" class="notice error">{{ saveError }}</div>
            <div v-if="needsProfilePhoto" class="photo-submit-help">
              <p>Add your profile photo to submit Personal Details.</p>
              <button type="button" :disabled="saving" @click="profilePhotoControl?.openCamera()">Take profile photo</button>
            </div>
            <div class="actions">
              <button v-if="previousStage" type="button" class="secondary" :disabled="saving" @click="goBack">Back</button>
              <button type="button" class="secondary" :disabled="saving" @click="saveDraft">{{ saving ? 'Saving…' : onboarding.profile.submitted ? 'Save changes' : 'Save progress' }}</button>
              <button v-if="currentStage" type="submit" :disabled="saving || needsProfilePhoto">{{ saving ? 'Saving…' : (currentStage.id === 'driving_licence' && noDrivingLicence(draft)) || (currentStage.id === 'national_insurance' && onboarding.profile.dbs_amazon_site) ? 'Continue' : currentStage.id === 'national_insurance' ? 'Submit and continue' : 'Submit ' + currentStage.title }}</button>
              <button v-else-if="!onboarding.profile.submitted" type="submit" :disabled="saving || !onboarding.pushReady" aria-describedby="profile-submit-help">Submit Profile</button>
              <button v-else type="button" :disabled="saving || !canUsePortal" @click="router.replace('/home')">Continue to app</button>
            </div>
            <div v-if="!currentStage && !onboarding.profile.submitted" id="profile-submit-help" class="hint" role="status" aria-live="polite">
              <p v-if="!onboarding.pushReady">Before you can submit, enable push notifications. Tap Enable at the top of this page, then Allow when your browser asks. <button type="button" class="text-button" :disabled="onboarding.pushBusy" @click="notificationAction">Enable notifications</button></p>
              <p v-if="!progress.complete">Some required details are missing or need correcting. Review the highlighted fields before submitting. <button v-if="previousStage" type="button" class="text-button" :disabled="saving" @click="goBack">Review details</button></p>
              <p v-if="saving">Your profile is being saved. Please wait.</p>
            </div>
          </form>
        </template>
      </main>
      <aside v-if="idleHelpEnabled && idleHelp && !canUsePortal" class="idle-help" aria-live="polite">
        <button type="button" class="help-link" @click="router.push('/chat')">Do you need help? Click here to chat with the team 🤔</button>
        <button type="button" aria-label="Dismiss help suggestion" @click="resetIdle">×</button>
      </aside>
    </ion-content>
  </ion-page>
</template>

<script setup>
import AccountLogoutMenu from '@/components/AccountLogoutMenu.vue'
import DbsHelp from '@/components/DbsHelp.vue'
import {normaliseDocumentValue} from '@/utils/profileDocumentEdits'
import {nameFields,normaliseName} from '@/utils/profileNames'
import ProfileDocumentCapture from '@/components/ProfileDocumentCapture.vue'
import ProfilePhoto from '@/components/ProfilePhoto.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import BirthplacePicker from '@/components/BirthplacePicker.vue'
import ProfileDatePicker from '@/components/ProfileDatePicker.vue'
import ProfileOverview from '@/components/ProfileOverview.vue'
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { frappeRequest } from 'frappe-ui'
import { IonPage, IonHeader, IonContent } from '@ionic/vue'
import { onboarding, canUsePortal, refreshProfile, refreshPush, saveProfile, submitProfileSection, reopenProfileSection, enableRequiredPush } from '@/data/onboarding'
import { isPushSupported, getPermissionStatus } from '@/utils/pushNotifications'
import { profileProgress, applicableSections, isBritish, travelDocumentAllowed, birthCertificateRoute, noDrivingLicence, licenceType, formatNino, normaliseNino, formatUtr, normaliseUtr, formatVat, normaliseVat } from '@/utils/profileProgress'
const helpBase = import.meta.env.BASE_URL + 'help/'
const session = inject('$session')
const router = useRouter()
const draft = ref({})
const manualDocumentEdits=ref(new Set()),documentBaseline=ref({})
const documentFieldKeys=new Set(['passport_number','passport_issuing_country','passport_issue_date','passport_expiry_date','first_name','middle_name','last_name','dob','birth_nationality','birth_country','birthpassport_gender','dl_number','dl_issuing_country','dl_issue_date','dl_photocard_expiry','dl_expiry_date','street_address','city','state_region','postal_code','country'])
function markDocumentEdit(key,value=draft.value[key]){if(documentFieldKeys.has(key)&&normaliseDocumentValue(key,value)!==normaliseDocumentValue(key,documentBaseline.value[key]))manualDocumentEdits.value.add(key)}
const documentApproval=computed(()=>onboarding.profile?.document_approvals?.[currentStage.value?.id])
const profilePhotoControl=ref(null)
const needsProfilePhoto=computed(()=>currentStage.value?.id==='personal' && !String(onboarding.profile?.values?.id_photo || '').trim())
function expiredDocumentDate(key) {
  if(!['dl_expiry_date','dl_photocard_expiry','passport_expiry_date'].includes(key))return false
  if(key!=='passport_expiry_date' && noDrivingLicence(draft.value))return false
  const value=String(draft.value[key] || '').slice(0,10)
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && value < new Date().toLocaleDateString('en-CA')
}
function dateMaximum(key){
  const now=new Date()
  if(['dl_issue_date','passport_issue_date','address_since'].includes(key))now.setDate(now.getDate()-1)
  else if(key!=='dob')return undefined
  return now.toLocaleDateString('en-CA')
}
function expiryWarning(key) {
  if(key!=='passport_expiry_date')return 'Your licence has expired. Are you sure this date is correct?'
  if(draft.value.portal_identity_type==='Travel Document')return 'Your travel document has expired. Use a current document.'
  const uk=['united kingdom','uk','gb','gbr'].includes(String(draft.value.passport_issuing_country || '').trim().toLowerCase())
  return uk ? 'Your passport has expired. UK passports can still be submitted. Please check the date is correct.' : 'Your passport has expired. Use a current passport.'
}
watch(() => draft.value.dl_issuing_country, country => {draft.value.dl_type=licenceType(country)})
const birthCertificateEligible=computed(()=>birthCertificateRoute({...draft.value,portal_no_passport:1}))
const documentChoice=computed({get:()=>draft.value.portal_no_passport?'Birth Certificate':draft.value.portal_identity_type==='Travel Document'?'Travel Document':'Passport',set:value=>{if(value==='Birth Certificate'&&!birthCertificateEligible.value)return;if(value==='Travel Document'&&!travelDocumentAllowed(draft.value))return;draft.value.portal_no_passport=value==='Birth Certificate'?1:0;draft.value.portal_identity_type=value==='Travel Document'?'Travel Document':'Passport'}})
const showAlternativeDocuments = ref(false)
watch(documentChoice, choice => { if (choice !== 'Passport') showAlternativeDocuments.value = true })
function togglePassportOptions(enabled) {
  showAlternativeDocuments.value = enabled
  if (!enabled) documentChoice.value = 'Passport'
}
const routeOptions = key => (onboarding.profile?.sections || []).flatMap(s => s.fields).find(f => f.key === key)?.options || []
const loading = ref(true), saving = ref(false), attempted = ref(false)
const loadError = ref(''), saveError = ref(''), message = ref(''), permission = ref(getPermissionStatus())
const pushSupported = isPushSupported()
const pushOpen = ref(false)
async function notificationAction() {
  if (!pushSupported || permission.value === 'denied') { pushOpen.value = true; return }
  await enablePush(); pushOpen.value = !onboarding.pushReady
}
const visibleSections = computed(() => applicableSections(onboarding.profile, draft.value))
const backDrafts=ref({})
const previousStage=computed(()=>{
 if(onboarding.profile?.submitted)return null
 const stages=onboarding.profile?.stages||[]
 const index=currentStage.value?stages.findIndex(s=>s.id===currentStage.value.id):stages.length
 return index>0?stages[index-1]:null
})
async function goBack(){
 if(saving.value||!previousStage.value)return
 const current=currentStage.value
 if(current){const keys=new Set(current.fields.map(f=>f.key));backDrafts.value[current.id]=Object.fromEntries(Object.entries(draft.value).filter(([key])=>keys.has(key)))}
 saving.value=true;saveError.value='';message.value=''
 try{applyState(await reopenProfileSection(previousStage.value.id));attempted.value=false}
 catch(error){saveError.value=error?.messages?.[0]||error.message||'Could not go back. Please try again.'}
 finally{saving.value=false}
}
const currentStage = computed(() => onboarding.profile?.submitted ? null : onboarding.profile?.stages?.find(s => s.id === onboarding.profile.current_stage))
const profileContent = ref(null)
watch(() => currentStage.value?.id, async (stage, previous) => {
  if (stage === previous) return
  await nextTick()
  const content = profileContent.value?.$el || profileContent.value
  await content?.scrollToTop(0)
}, { flush: 'post' })
const formSections = computed(() => {
  if(onboarding.profile?.submitted)return visibleSections.value.filter(s=>s.title==='VAT Details')
  const stage = currentStage.value
  if (!stage) return []
  const sections = stage.section_titles.flatMap(title => visibleSections.value.filter(s => s.title === title && s.title !== 'Profile Picture'))
  if(stage.id==='national_insurance' && sections.some(s=>s.title==='DBS')){
    return [{title:'Background Screening',fields:sections.flatMap(s=>s.fields)}]
  }
  if (stage.id === 'passport' && !sections.some(s => s.title === 'Identity')) sections.push({title:'Identity',fields:[]})
  return sections.map(s => {
    let fields=s.fields.filter(f => stage.id !== 'personal' || f.key !== 'birth_nationality')
    if(s.title==='Identity') {
      const catalogue=visibleSections.value.flatMap(group=>group.fields)
      const routeFields=['birth_nationality','birth_country'].map(key=>({
        ...(catalogue.find(f=>f.key===key) || {}),key,
        label:key==='birth_nationality'?'Nationality':'Birth country',
        editable:true,required:true,type:'select',options:routeOptions(key),
      }))
      const coreKeys=['passport_number','passport_issuing_country','passport_issue_date','passport_expiry_date']
      const core=coreKeys.map(key=>fields.find(f=>f.key===key)).filter(Boolean)
      const personal=draft.value.portal_no_passport?[]:catalogue.filter(f=>passportPersonal.has(f.key)&&f.key!=='birth_city')
      fields=[...core,...routeFields,...personal]
    }
    fields=fields.map(f=>f.key==='birth_city'?{...f,label:'Town/City of Birth'}:draft.value.portal_identity_type==='Travel Document' && f.key.startsWith('passport_') ? {...f,label:f.label.replace(/Passport/i,'Travel document')} : f)
    return {...s,fields}
  })
})
const passportPersonal = new Set(['first_name','middle_name','last_name','dob','birthpassport_gender','birth_city'])
const addressKeys = ['street_address','city','state_region','postal_code','country','address_since']
const capturedDocuments=ref({})
function hasCapture(kind){return !!(capturedDocuments.value[kind] || onboarding.profile?.documents?.files?.[kind])}
function selectField(field,value){
  if(draft.value[field.key]!==value)markDocumentEdit(field.key,value)
  if(field.key==='birth_country' && draft.value.birth_country!==value)birthplaceSelected({name:'',status:'',country:'',token:'',reference:'',manual:0})
  draft.value[field.key]=value
}
function birthplaceSelected(place){
  Object.assign(draft.value,{birth_city:place.name,portal_birthplace_status:place.status,portal_birthplace_country:place.country,portal_birthplace_reference:place.reference,portal_birthplace_manual:place.manual,portal_birthplace_token:place.token})
}
function searchableField(field){return field.type==='select' && (/(country|nationality|language)/.test(field.key) || (field.options || []).length>12)}
function fieldInputId(key){return key==='birth_nationality'?'route-nationality':key==='birth_country'?'route-country':key}
function pendingRequired(field){
  const value=draft.value[field.key]
  return field.required && field.editable && !fieldLocked(field.key) && (value==null || String(value).trim()==='')
}
function fieldVisible(section,key){
  if(key==='portal_dbs_certificate_file')return false
  if(section==='Personal Details' && key==='birth_country')return true
  if(section==='Identity' && ['birth_nationality','birth_country'].includes(key))return !!onboarding.profile?.documents?.passport_ready || showAlternativeDocuments.value
  if(key==='portal_no_driving_licence' || (section==='Driving Licence' && noDrivingLicence(draft.value)))return false
  if(key==='dl_type')return false
  if(['proof_of_address_doc','passp_file','bc_file','tab_dl_photocard_front','tab_dl_photocard_rear','birth_nationality','birth_country'].includes(key))return false
  if(section==='Address')return !!onboarding.profile?.documents?.files?.proof_of_address
  if(section==='Driving Licence')return hasCapture('licence_front') && hasCapture('licence_back')
  if(section==='Identity'&&(key.startsWith('passport_')||passportPersonal.has(key)))return hasCapture('passport')&&!draft.value.portal_no_passport
  return true
}
function documentCaptured(kind){
  capturedDocuments.value[kind]=true
}

async function toggleLicence(checked) {
  const previous=draft.value.portal_no_driving_licence || 0
  draft.value.portal_no_driving_licence=checked?1:0
  saving.value=true;saveError.value=''
  try {
    const state=await saveProfile({portal_no_driving_licence:checked?1:0},false)
    // Save only the declaration; keep every other unsaved entry and capture.
    draft.value.role=state.values.role
    attempted.value=false
  } catch(error) {
    draft.value.portal_no_driving_licence=previous
    saveError.value=error?.messages?.[0] || 'Could not save this choice. Please try again.'
  } finally {saving.value=false}
}

function fieldLocked(key) {
  if (addressKeys.includes(key)) return !onboarding.profile?.documents?.files.proof_of_address
  if (birthCertificateRoute(draft.value) && passportPersonal.has(key)) return !onboarding.profile?.documents?.birth_certificate_ready
  if (birthCertificateRoute(draft.value) && key.startsWith('passport_')) return true
  if (key.startsWith('dl_')) return !(hasCapture('licence_front') && hasCapture('licence_back'))
  if (!birthCertificateRoute(draft.value) && draft.value.portal_identity_type !== 'Identity card' && (key.startsWith('passport_') || passportPersonal.has(key))) return !onboarding.profile?.documents?.passport_ready
  return false
}
function documentSaved(result) {
  for(const [key,value] of Object.entries(result.suggestions||{})){manualDocumentEdits.value.delete(key);documentBaseline.value[key]=value}
  onboarding.profile = result.profile
  if (result.kind === 'passport') {
    birthplaceSelected({name:'',status:'',country:'',token:'',reference:'',manual:0})
    for (const key of ['passport_number','passport_issuing_country','passport_issue_date','passport_expiry_date','birth_nationality',...passportPersonal]) { draft.value[key]='' }
  }
  if (result.kind === 'licence_front') {
    for(const key of ['dl_number','dl_issuing_country','dl_issue_date','dl_photocard_expiry']) {draft.value[key]=''}
  }
  if (result.kind === 'licence_back') draft.value.dl_expiry_date=''
  if (result.kind === 'proof_of_address') {
    for (const key of addressKeys) { draft.value[key] = '' }
  }
  for (const key of ['portal_dbs_certificate_file','proof_of_address_doc','passp_file','bc_file','tab_dl_photocard_front','tab_dl_photocard_rear']) draft.value[key] = result.profile.values[key]
  for (const [key,value] of Object.entries(result.suggestions || {})) {
    if (!key.startsWith('_')) draft.value[key] = value
  }
  const nationality = result.suggestions?._passport_nationality
  const place = result.suggestions?._place_of_birth
  message.value = result.warning || 'Review the extracted details before saving.' + (nationality ? ` Passport nationality: ${nationality}. Check your nationality below.` : '') + (place ? ` Place of birth: ${place}. Confirm the country of birth.` : '')
}
function photoSaved(state) { onboarding.profile = state; draft.value.id_photo = state.values.id_photo }
const progress = computed(() => profileProgress(draft.value, visibleSections.value))
const visibleErrors = computed(() => attempted.value ? progress.value.errors : {})
function applyState(state) { manualDocumentEdits.value.clear();documentBaseline.value={...state.values,...state.document_scan_values};draft.value = { ...state.values, ...state.document_draft_values, preferred_language: String(state.values.preferred_language || '').trim() || 'English', nino_number: formatNino(state.values.nino_number), utr_number: formatUtr(state.values.utr_number), vat_number: formatVat(state.values.vat_number), portal_identity_type: state.values.portal_identity_type || 'Passport', ...(backDrafts.value[state.current_stage]||{}) } }
async function load() {
  loading.value = true; loadError.value = ''
  try { applyState(await refreshProfile()); await refreshPush() }
  catch { loadError.value = onboarding.error || 'Could not load your profile. Please try again.' }
  finally { loading.value = false; permission.value = getPermissionStatus() }
}
async function enablePush() { await enableRequiredPush(); permission.value = getPermissionStatus(); if (onboarding.pushReady) pushOpen.value = false }
function formatIdentifier(key) { if (typeof draft.value[key] === 'string') draft.value[key] = draft.value[key].trim(); if (nameFields.has(key)) draft.value[key] = normaliseName(draft.value[key]); if (key === 'nino_number') draft.value[key] = formatNino(draft.value[key]); if (key === 'utr_number') draft.value[key] = formatUtr(draft.value[key]); if (key === 'vat_number') draft.value[key] = formatVat(draft.value[key]) }
function changedFields() {
  const editable = new Set((onboarding.profile?.sections || []).flatMap(s => s.fields.filter(f => f.editable).map(f => f.key)))
  editable.add('portal_birthplace_token');editable.add('portal_birthplace_manual');editable.add('portal_identity_type'); editable.add('portal_no_passport')
  return Object.fromEntries(Object.entries(draft.value).filter(([key,value]) => editable.has(key) && value !== onboarding.profile.values[key]).map(([key,value]) => [key, nameFields.has(key) ? normaliseName(value) : key === 'nino_number' ? normaliseNino(value) : key === 'utr_number' ? normaliseUtr(value) : key === 'vat_number' ? normaliseVat(value) : typeof value === 'string' ? value.trim() : value]))
}
function sectionChanges() {
  const stage=currentStage.value
  if(onboarding.profile?.submitted)return Object.fromEntries(Object.entries(changedFields()).filter(([key])=>['vat_registered','vat_number'].includes(key)))
  if (!stage) return {}
  const allowed=new Set(stage.id==='national_insurance' ? ['mothers_first_name','mothers_maiden_name','portal_has_recent_dbs','portal_has_dbs_share_code','portal_has_dbs_certificate','portal_dbs_share_code','portal_dbs_reference'] : stage.fields.map(f=>f.key))
  if(stage.id==='personal'){allowed.add('portal_birthplace_token');allowed.add('portal_birthplace_manual')}
  if (stage.id==='passport') for (const key of [...passportPersonal,'birth_nationality','birth_country','portal_no_passport','portal_identity_type',...visibleSections.value.filter(s=>s.title==='Identity').flatMap(s=>s.fields.map(f=>f.key))]) allowed.add(key)
  return Object.fromEntries(Object.entries(changedFields()).filter(([key])=>allowed.has(key)))
}
async function submitSection() {
  if (saving.value || !currentStage.value) return
  attempted.value=true;saveError.value='';message.value=''
  if(needsProfilePhoto.value){saveError.value='Add your profile photo before submitting Personal Details.';return}
  const stage=currentStage.value
  if(stage.id==='passport' && showAlternativeDocuments.value && documentChoice.value==='Passport'){saveError.value='Choose Travel Document or Birth Certificate, or switch off I don’t have a passport.';return}
  const fields=stage.id==='national_insurance' ? formSections.value.flatMap(s=>s.fields) : stage.id==='passport' && birthCertificateRoute(draft.value) ? stage.fields.filter(f=>['birth_nationality','birth_country'].includes(f.key)) : stage.fields
  const keys=new Set(fields.map(f=>f.key))
  const validation=profileProgress(draft.value,[{title:stage.title,fields}])
  const missing=Object.entries(validation.errors).filter(([k])=>keys.has(k)||k==='portal_no_passport'||k==='portal_identity_type')
  if(missing.length){saveError.value=missing.map(([key,error])=>`${fields.find(f=>f.key===key)?.label||key}: ${error}`).join(' · ');return}
  saving.value=true
  try {
    delete backDrafts.value[stage.id]
    applyState(await submitProfileSection(stage.id,sectionChanges(),[...manualDocumentEdits.value]))
    attempted.value=false;message.value=stage.title+' saved. Continue with the next section.'
  } catch(error) {saveError.value=error?.messages?.[0] || error?.message || 'Could not save this section. Your progress has not advanced. Please try again.'}
  finally {saving.value=false}
}
async function save(submit) {
  if (saving.value) return
  attempted.value = true; message.value = ''; saveError.value = ''
  if (submit && !progress.value.complete) { saveError.value = 'Please complete the required fields and correct the highlighted fields, including your profile picture.'; return }
  saving.value = true
  try {
    if (submit && !await refreshPush()) { saveError.value = 'Enable notifications on this device before submitting.'; return }
    const state = await saveProfile(submit ? changedFields() : sectionChanges(), submit,[...manualDocumentEdits.value])
    applyState(state)
    message.value = submit ? 'Profile submitted. You can now use the app.' : 'Your progress has been saved.'
    attempted.value = false
  } catch (error) { saveError.value = error?.messages?.[0] || 'Could not save your profile. Check your details and connection, then try again.' }
  finally { saving.value = false }
}
const saveDraft = () => save(false)
const submitProfile = () => save(true)
const logout = () => session.logout.submit()
const idleHelpEnabled = false // Enable only when the user requests launch.
const idleHelp = ref(false)
let idleTimer
const activityEvents = ['pointerdown','keydown','input','scroll','touchstart']
function resetIdle() {
  clearTimeout(idleTimer); idleHelp.value = false
  if (!idleHelpEnabled) return
  idleTimer = setTimeout(() => { if (!canUsePortal.value && router.currentRoute.value.name === 'Profile' && document.visibilityState !== 'hidden') idleHelp.value = true },20000)
}
watch(() => router.currentRoute.value.name,resetIdle)
onMounted(() => { load(); resetIdle(); activityEvents.forEach(event => document.addEventListener(event,resetIdle,{passive:true,capture:true})) })
onUnmounted(() => { clearTimeout(idleTimer); activityEvents.forEach(event => document.removeEventListener(event,resetIdle,true)) })
</script>

<style scoped>
.answer-buttons{display:flex;gap:.6rem;max-width:22rem;margin-top:.5rem}.answer-buttons button{flex:1;min-height:44px;padding:.6rem 1rem;background:#fff;color:#374151;border:1px solid #d1d5db;border-radius:.6rem;font-size:.9rem;font-weight:500;box-shadow:0 1px 2px #00000008}.answer-buttons button[aria-pressed="true"]{border-color:#a61d1d;background:#fff5f5;color:#a61d1d;box-shadow:0 0 0 1px #a61d1d}.answer-buttons button:focus-visible{outline:2px solid #2563eb;outline-offset:3px}

.document-choices{display:flex;flex-wrap:wrap;gap:.5rem}.document-choices button{flex:1;min-width:6rem;min-height:44px;padding:.6rem;background:white;border:1px solid #d1d5db;color:#374151;font-size:.85rem;font-weight:500;box-shadow:0 1px 2px #00000008}.document-choices button[aria-pressed="true"]{border-color:#a61d1d;background:#fff5f5;color:#a61d1d;box-shadow:0 0 0 1px #a61d1d}.document-choices button:focus-visible{outline:2px solid #2563eb;outline-offset:3px}

.photo-submit-help{display:flex;align-items:center;justify-content:space-between;gap:.75rem;border-top:1px solid #eee;padding:.75rem 0;margin-top:.5rem}.photo-submit-help p{font-size:.8rem;color:#a61d1d;margin:0}.photo-submit-help button{font-size:.8rem;flex-shrink:0}
.field.pending-required input,.field.pending-required select{border-color:#b91c1c}
.expired-photocard input{border-color:#b91c1c!important;color:#b91c1c}.expired-photocard>label{color:#b91c1c}
.document-option{display:flex;align-items:center;gap:.5rem;max-width:13rem;font-size:.75rem;min-height:44px;cursor:pointer}.document-option input{appearance:none;width:32px;height:19px;flex-shrink:0;border-radius:12px;background:#cbd5e1;position:relative;transition:background .15s}.document-option input:before{content:'';position:absolute;width:15px;height:15px;border-radius:50%;background:white;left:2px;top:2px;box-shadow:0 1px 3px #0003;transition:transform .15s}.document-option input:checked{background:#a61d1d}.document-option input:checked:before{transform:translateX(13px)}.document-option input:disabled{opacity:.45;cursor:not-allowed}.document-option input:focus-visible{outline:2px solid #2563eb;outline-offset:3px}
.section-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}.section-heading h2{margin:0}
.active-tab{border:1px solid #c63624!important;box-shadow:0 2px 7px #a61d1d24;position:relative;z-index:1;background:white}.push-inline{display:flex;align-items:center;justify-content:flex-end;gap:.5rem;font-size:.78rem;white-space:nowrap;margin:.3rem 0}.push-inline button{padding:.2rem .5rem;background:transparent;color:#a61d1d;text-decoration:underline;min-height:32px;font-size:.78rem}.push-popover{position:absolute;right:1rem;top:5rem;max-width:min(90vw,22rem);z-index:1100;background:white;border:1px solid #ddd;padding:1rem;border-radius:.6rem;box-shadow:0 4px 18px #0002}.push-popover>.text-button{float:right}.idle-help{position:fixed;bottom:1rem;right:1rem;max-width:min(90vw,25rem);z-index:1000;display:flex;align-items:center;gap:.3rem;background:white;border:1px solid #d1d5db;border-radius:.75rem;box-shadow:0 4px 18px #0002;padding:.5rem}.idle-help button{background:white;color:#a61d1d}.idle-help .help-link{text-align:left;font-size:.85rem}.title-row{display:grid!important;grid-template-columns:repeat(3,1fr);gap:0!important;min-height:44px;border-bottom:1px solid #e5e7eb}.title-row>*{text-align:center;font-size:.95rem!important;font-weight:500!important;margin:0;white-space:nowrap}.title-row button{color:#111827!important;border-radius:0;border-left:1px solid #e5e7eb;min-height:44px}.profile-header{padding-top:0!important}.title-row h1{line-height:44px}.progress-label{font-size:.78rem!important;margin-top:.5rem!important}.chat-top{font-size:.8rem}.notice[aria-label="Identity document choice"] label{display:block;margin-top:.5rem}.notice[aria-label="Identity document choice"] select{width:100%;padding:.5rem;border:1px solid #9ca3af;border-radius:.4rem}.passport-alternative{font-size:.85rem;margin:.65rem 0 1rem;gap:.5rem}.passport-alternative input{accent-color:#a61d1d;width:18px;height:18px}.identity-fields{display:grid;grid-template-columns:1fr;gap:.4rem;margin:.7rem 0}.identity-fields label{font-size:.85rem}.identity-fields select{padding:.6rem;border:1px solid #9ca3af;border-radius:.5rem;width:100%;background:white}.identity-fields .no-passport{display:flex;gap:.5rem;align-items:center;margin:.5rem 0}.no-passport{display:flex;align-items:center;gap:.6rem;margin-top:.8rem}.no-passport input{width:22px;height:22px}.profile-header,.profile-body{max-width:42rem;margin:auto;padding:1rem;background:#fff}.profile-header{border-bottom:1px solid #e5e7eb}.title-row,.progress-label,.actions{display:flex;justify-content:space-between;align-items:center;gap:1rem}.title-row h1{font-size:1.3rem;font-weight:700}.progress-label{margin-top:1rem;font-size:.85rem;flex-wrap:wrap}.profile-header p,.hint{font-size:.9rem;color:#4b5563;margin-top:.6rem}progress{width:100%;height:.65rem;accent-color:#16a34a}.profile-body{padding-bottom:3rem}.notice{padding:1rem;border-radius:.8rem;background:#f3f4f6;margin-bottom:1rem}.notice p{margin:.5rem 0;font-size:.95rem}.notice h2,.profile-section h2{font-weight:700;font-size:1.1rem}.profile-section{margin:1.4rem 0;padding:1rem;border:1px solid #e5e7eb;border-radius:.8rem}.field{margin-top:1rem}.field label{display:block;font-weight:500;margin-bottom:.4rem}.field input:disabled,.field select:disabled{background:#f3f4f6;color:#6b7280;cursor:not-allowed}.field input,.field select{width:100%;padding:.7rem;border:1px solid #9ca3af;border-radius:.5rem;background:white;min-height:44px}.optional,.read-only small{color:#6b7280;font-weight:400;font-size:.8rem}.read-only small{display:block}.read-only{padding:.5rem 0}.error-text{color:#b91c1c;font-size:.9rem;margin-top:.3rem}.error{border:1px solid #b91c1c}.success{color:#166534}button{background:#a61d1d;color:white;border-radius:.5rem;padding:.7rem 1rem;min-height:44px;font-weight:600}button:disabled{opacity:.5;cursor:not-allowed}button.secondary{background:#f3f4f6;color:#111827}button.text-button{background:none;color:#a61d1d;padding:.3rem}.actions{flex-wrap:wrap}.actions button{flex:1}[aria-invalid="true"]{border-color:#b91c1c}
</style>
