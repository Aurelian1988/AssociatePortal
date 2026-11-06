<template>
	<ion-app>
		<ion-router-outlet id="main-content" />
		<Toasts />
		<!-- Offline banner -->
		<transition name="slide-down">
			<div
				v-if="!online"
				class="fixed top-0 left-0 right-0 z-[10000] bg-gray-800 text-white px-4 py-2.5 flex items-center justify-center gap-2 shadow-lg safe-area-top"
			>
				<svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M8.464 15.536a5 5 0 010-7.072M15.536 8.464a5 5 0 010 7.072M12 12h.01" />
				</svg>
				<p class="text-sm font-medium">No internet connection</p>
			</div>
		</transition>

	</ion-app>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { IonApp, IonRouterOutlet } from '@ionic/vue'
import { Toasts } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { session } from '@/data/session'
import { refreshPush, canUsePortal } from '@/data/onboarding'
import { useNetworkStatus } from '@/utils/networkStatus'
const { isOnline: online } = useNetworkStatus()
const router = useRouter()
let timer
async function recheckAccess() {
  if (!session.isLoggedIn || document.visibilityState === 'hidden') return
  await refreshPush()
  if (!canUsePortal.value && !['Profile','Chat','InvalidAssociate','Login'].includes(router.currentRoute.value.name)) {
    await router.replace({ name: 'Profile' })
  }
}
onMounted(() => {
  window.addEventListener('focus', recheckAccess)
  document.addEventListener('visibilitychange', recheckAccess)
  timer = setInterval(recheckAccess, 30000)
})
onUnmounted(() => {
  window.removeEventListener('focus', recheckAccess)
  document.removeEventListener('visibilitychange', recheckAccess)
  clearInterval(timer)
})
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
	transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
	transform: translateY(-100%);
	opacity: 0;
}
</style>
