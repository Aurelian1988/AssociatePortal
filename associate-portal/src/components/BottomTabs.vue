<template>
	<div
		v-if="route.path !== '/chat'"
		data-bottom-navigation
		class="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg sm:w-96 sm:mx-auto"
	>
		<div class="flex items-center justify-around py-1 pb-4 px-1">
			<router-link
				v-for="item in tabItems"
				:key="item.title"
				:to="item.route"
				class="flex flex-col items-center gap-0.5 py-1 px-2 rounded-lg transition active:scale-95"
				:class="[
					(route.path === item.route || (item.route === '/documents' && route.path === '/agreements'))
						? 'text-[#a61d1d] font-semibold'
						: 'text-gray-500 font-normal',
				]"
			>
				<FeatherIcon :name="item.icon" class="h-5 w-5" />
				<span class="text-xs">{{ item.title }}</span>
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { useRoute } from "vue-router"
import { FeatherIcon } from "frappe-ui"
import { inject } from "vue"

const __ = inject("$translate")
const route = useRoute()

const tabItems = [
 {icon:'tool',title:__('Tools'),route:'/tools'},
 {icon:'folder',title:__('Files'),route:'/documents'},
 {icon:'home',title:__('Home'),route:'/home'},
 {icon:'user',title:__('My Profile'),route:'/profile'},
 {icon:'message-circle',title:__('Chat'),route:'/chat'},
]
</script>
