<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full sm:w-96">
				<div class="flex flex-col bg-white shadow-sm">
					<div class="flex flex-row justify-between items-center px-4 py-3">
						<div class="flex flex-row items-center gap-2">
							<img
								:src="logoUrl"
								alt="OneMotion"
								class="h-7"
							/>
							<h2 v-if="props.pageTitle" class="text-lg font-bold text-gray-900 ml-2">
								{{ props.pageTitle }}
							</h2>
						</div>
						<div class="flex flex-row items-center gap-3 ml-auto">
							<router-link
								v-if="canUsePortal" :to="{ name: 'Notifications' }"
								class="relative flex items-center justify-center p-1"
							>
								<FeatherIcon name="bell" class="h-5 w-5 text-gray-600" />
								<span
									v-if="unreadCount.data"
									class="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border border-white"
								>
									{{ unreadCount.data > 9 ? '9+' : unreadCount.data }}
								</span>
							</router-link>
<div class="relative" @keydown.esc="accountOpen=false"><button type="button" aria-label="Account menu" :aria-expanded="accountOpen" @click="accountOpen=!accountOpen"><Avatar :image="onboarding.profile?.values?.id_photo || user.data?.user_image" :label="avatarLabel" size="xl" /></button><div v-if="accountOpen" class="absolute right-0 top-full bg-white border rounded-xl shadow-lg p-2 z-50 min-w-40"><router-link :to="{name:'Profile'}" class="block p-3" @click="accountOpen=false">My Profile</router-link><button type="button" class="block p-3 text-red-700 w-full text-left" @click="logoutAccount">Log out</button></div></div>
						</div>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding">
			<div class="portal-body flex flex-col min-h-screen w-screen sm:w-96 pb-16">
				<SigningStatus/><slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import SigningStatus from '@/components/SigningStatus.vue'
import { IonHeader, IonContent, IonPage } from "@ionic/vue"
import { Avatar, FeatherIcon } from "frappe-ui"
import { inject, computed, ref } from "vue"
import {canUsePortal,onboarding} from '@/data/onboarding'
import { unreadCount, startNotificationPolling } from "@/data/notifications"

if (canUsePortal.value) startNotificationPolling()

import {session} from '@/data/session'
const accountOpen=ref(false)
function logoutAccount(){sessionStorage.removeItem('sdt-test-contact-name');session.logout.submit()}
const logoUrl = "/files/onemotion-logo-dark.png"
const user = inject("$user")
const associate = inject("$associate")

const avatarLabel = computed(() => {
	const first = onboarding.profile?.values?.first_name || associate?.data?.first_name || user.data?.first_name || ""
	const last = onboarding.profile?.values?.last_name || associate?.data?.last_name || ""
	return [first, last].filter(Boolean).join(" ") || "U"
})

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>

<style>.portal-body:has(.signing-page){min-height:0;padding-bottom:0}.agreements:has(.signing-page){padding-bottom:0}</style>
