import { reactive, computed } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { isPushSupported, getPermissionStatus, subscribeToPush, requestNotificationPermission } from '@/utils/pushNotifications'

export const onboarding = reactive({ profile: null, error: '', loading: false, pushReady: false, pushEndpoint: '', pushBusy: false, pushError: '' })
export const canUsePortal = computed(() => !!onboarding.profile?.submitted && onboarding.pushReady)
const api = 'onemotion.api.profile_onboarding.'
const unwrap = value => value?.message ?? value
export async function refreshProfile() {
  onboarding.loading = true
  onboarding.error = ''
  try {
    onboarding.profile = unwrap(await frappeRequest({ url: '/api/method/' + api + 'get_profile_state' }))
    return onboarding.profile
  } catch (error) {
    onboarding.profile = null
    onboarding.error = 'We could not check your profile. Reconnect and try again.'
    throw error
  } finally { onboarding.loading = false }
}
export async function saveProfile(values, submit = false, documentEdits = []) {
  const result = unwrap(await frappeRequest({ url: '/api/method/' + api + 'save_profile', params: { values, submit, document_edits:documentEdits, push_endpoint: onboarding.pushEndpoint } }))
  onboarding.profile = result
  return result
}
let pushCheck
export function refreshPush() {
  if (pushCheck) return pushCheck
  onboarding.pushReady = false
  onboarding.pushEndpoint = ''
  if (!isPushSupported() || getPermissionStatus() !== 'granted') return Promise.resolve(false)
  pushCheck = (async () => {
    try {
      const subscription = await Promise.race([subscribeToPush(), new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 15000))])
      onboarding.pushReady = !!subscription && getPermissionStatus() === 'granted'
      onboarding.pushEndpoint = onboarding.pushReady ? subscription.endpoint : ''
      if (!onboarding.pushReady) onboarding.pushError = 'Notification setup failed. Please try again.'
      return onboarding.pushReady
    } catch {
      onboarding.pushError = 'Notification setup failed. Check your connection and try again.'
      return false
    } finally { pushCheck = null }
  })()
  return pushCheck
}
export async function enableRequiredPush() {
  if (onboarding.pushBusy) return
  onboarding.pushBusy = true
  onboarding.pushError = ''
  try {
    // Request immediately from the user's tap, before any network awaits.
    await requestNotificationPermission()
    await refreshPush()
  } catch { onboarding.pushError = 'Could not enable notifications. Please try again.' }
  finally { onboarding.pushBusy = false }
}

export async function submitProfileSection(section,values,documentEdits=[]) {
  const result=unwrap(await frappeRequest({url:'/api/method/onemotion.api.profile_stages.submit_profile_section',params:{section,values,document_edits:documentEdits}}))
  onboarding.profile=result
  return result
}

export async function reopenProfileSection(section){
 const response=await frappeRequest({url:"/api/method/onemotion.api.profile_stages.reopen_profile_section",params:{section}})
 onboarding.profile=unwrap(response)
 return onboarding.profile
}
