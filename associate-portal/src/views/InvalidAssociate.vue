<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex h-screen w-screen flex-col items-center justify-center bg-white px-8">
				<img :src="logoUrl" alt="OneMotion" class="h-10 mb-6" />
				<FeatherIcon name="alert-circle" class="h-16 w-16 text-orange-400 mb-4" />
				<h2 class="text-xl font-bold text-gray-900 text-center mb-2">
					{{ __("No Associate Profile Found") }}
				</h2>
				<p class="text-sm text-gray-500 text-center mb-8">
					{{ __("Your account is not linked to an Associate profile. Please contact your administrator.") }}
				</p>
				<AccountLogoutMenu/>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import AccountLogoutMenu from '@/components/AccountLogoutMenu.vue'
import { inject } from "vue"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"

const logoUrl = "/files/onemotion-logo-dark.png"
const session = inject("$session")
const __ = inject("$translate")

const logout = async () => {
	try {
		await session.logout.submit()
	} catch (e) {
		console.error("Logout error:", e)
	}
}
</script>
