<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="signin-page">
				<div class="flex flex-col mx-auto gap-4 items-center">
					<img :src="logoUrl" alt="OneMotion" class="h-10" />
					<div class="text-2xl font-semibold text-gray-900 text-center">
						{{ __("Associate Portal") }}
					</div>
					<p class="text-sm text-gray-500 text-center">
						{{ __("Sign in to access your profile") }}
					</p>
				</div>

				<div class="signin-form-wrap">
					<form class="signin-form" @submit.prevent="submit">
						<Input
							:label="__('Email')"
							:placeholder="__('Enter your email address')"
							v-model="email"
							type="email"
							autocomplete="username"
						/>
						<Input
							:label="__('Password')"
							type="password"
							placeholder="Enter your password"
							v-model="password"
							autocomplete="current-password"
						/>
						<ErrorMessage :message="errorMessage" />
						<Button
							:loading="isLoading"
							variant="solid"
							type="submit"
							class="disabled:bg-gray-700 disabled:text-white !mt-6"
							style="background-color: #a61d1d"
						>
							{{ __("Sign In") }}
						</Button>
					</form>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { inject, ref } from "vue"
import { Input, Button, ErrorMessage } from "frappe-ui"

const logoUrl = "/files/onemotion-logo-dark.png"
const email = ref(null)
const password = ref(null)
const errorMessage = ref("")
const isLoading = ref(false)

const session = inject("$session")
const __ = inject("$translate")

async function submit() {
	try {
		isLoading.value = true
		errorMessage.value = ""
		await session.login(email.value, password.value)
	} catch (error) {
		errorMessage.value = error.messages?.join("\n") || "Login failed"
	} finally {
		isLoading.value = false
	}
}
</script>

<style scoped>
.signin-page{max-width:480px;margin:0 auto;padding:clamp(36px,9vh,80px) 28px 48px;min-height:calc(100dvh - 32px);display:flex;flex-direction:column;justify-content:center;gap:48px;background:white}
.signin-form-wrap{width:100%}.signin-form{display:grid;gap:28px}
.signin-form :deep(input){min-height:48px;padding:12px;font-size:17px;border-radius:12px}
.signin-form :deep(label){font-size:16px;margin-bottom:12px}
.signin-form :deep(button[type=submit]){min-height:48px;font-size:18px;border-radius:12px;margin-top:12px!important}
@media(max-height:550px){.signin-page{padding-top:24px;gap:28px;justify-content:flex-start}.signin-form{gap:20px}}
</style>
