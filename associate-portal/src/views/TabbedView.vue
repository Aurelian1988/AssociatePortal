<template>
	<ion-page>
		<ion-router-outlet></ion-router-outlet>
		<BottomTabs v-if="canUsePortal" />
	</ion-page>
</template>

<script setup>
import { IonPage, IonRouterOutlet } from "@ionic/vue"
import {canUsePortal} from '@/data/onboarding'
import BottomTabs from "@/components/BottomTabs.vue"
</script>
