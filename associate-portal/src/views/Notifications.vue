<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full sm:w-96">
				<div class="flex flex-col bg-white shadow-sm">
					<div class="flex flex-row justify-between items-center px-4 py-3">
						<div class="flex flex-row items-center gap-2">
							<button
								class="p-1 -ml-1 rounded-lg hover:bg-gray-100"
								@click="router.back()"
							>
								<FeatherIcon name="chevron-left" class="h-5 w-5 text-gray-700" />
							</button>
							<h2 class="text-lg font-bold text-gray-900">Notifications</h2>
						</div>
						<button
							v-if="unreadCount.data"
							class="text-sm text-blue-600 font-medium px-2 py-1 rounded hover:bg-blue-50"
							@click="handleMarkAllRead"
						>
							Mark all read
						</button>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding">
			<div class="flex flex-col min-h-screen w-screen sm:w-96">
				<!-- Unread count badge -->
				<div
					v-if="unreadCount.data"
					class="px-4 pt-4 pb-2"
				>
					<span class="text-sm font-semibold text-gray-700">
						{{ unreadCount.data }} unread
					</span>
				</div>

				<!-- Notification list -->
				<div
					v-if="notificationList.length"
					class="flex flex-col"
				>
					<div
						v-for="item in notificationList"
						:key="item.name"
						class="flex flex-row items-start px-4 py-3 border-b border-gray-200 gap-3 cursor-pointer hover:bg-gray-50 transition"
						:class="item.read ? 'bg-white' : 'bg-blue-50/40'"
						@click="handleNotificationClick(item)"
					>
						<!-- Unread dot -->
						<div class="flex items-center pt-2">
							<span
								class="w-2 h-2 rounded-full shrink-0"
								:class="item.read ? 'bg-transparent' : 'bg-blue-500'"
							></span>
						</div>

						<!-- Avatar -->
						<Avatar
							:image="item.from_user_image"
							:label="item.from_user_name"
							size="lg"
						/>

						<!-- Content -->
						<div class="flex flex-col gap-0.5 flex-1 min-w-0">
							<div
								class="text-sm leading-5 text-gray-800"
								v-html="item.message"
							></div>
							<div class="text-xs text-gray-400">
								{{ timeAgo(item.creation) }}
							</div>
						</div>
					</div>
				</div>

				<!-- Load more -->
				<div
					v-if="notificationList.length && hasMore"
					class="flex justify-center py-4"
				>
					<button
						class="text-sm text-blue-600 font-medium px-4 py-2 rounded-lg border border-blue-200 hover:bg-blue-50"
						@click="loadMore"
					>
						Load more
					</button>
				</div>

				<!-- Empty state -->
				<div
					v-if="!notifications.loading && !notificationList.length"
					class="flex flex-col items-center justify-center py-20 px-6"
				>
					<div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
						<FeatherIcon name="bell-off" class="h-8 w-8 text-gray-400" />
					</div>
					<h3 class="text-lg font-semibold text-gray-700 mb-1">No notifications</h3>
					<p class="text-sm text-gray-400 text-center">
						You're all caught up! New notifications will appear here.
					</p>
				</div>

				<!-- Loading state -->
				<div
					v-if="notifications.loading && !notificationList.length"
					class="flex items-center justify-center py-20"
				>
					<div class="w-8 h-8 border-2 border-gray-200 border-t-[#a61d1d] rounded-full animate-spin"></div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonHeader, IonContent } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"
import { useRouter } from "vue-router"
import { ref, computed, onMounted, inject } from "vue"
import {
	notifications,
	unreadCount,
	markAllAsRead,
	markOneAsRead,
} from "@/data/notifications"

const router = useRouter()
const dayjs = inject("$dayjs")

const currentPage = ref(0)
const pageLength = 20
const hasMore = ref(false)

const notificationList = computed(() => {
	const data = notifications.data
	return Array.isArray(data) ? data : []
})

function timeAgo(date) {
	if (!date) return ""
	return dayjs(date).fromNow()
}

function handleNotificationClick(item) {
	if (!item.read) {
		markOneAsRead.submit({ notification_name: item.name })
		item.read = 1
	}
}

function handleMarkAllRead() {
	markAllAsRead.submit()
}

function loadMore() {
	currentPage.value += pageLength
	notifications.submit({
		start: currentPage.value,
		page_length: pageLength,
	})
}

onMounted(() => {
	currentPage.value = 0
	notifications.submit({
		start: 0,
		page_length: pageLength,
	})
})
</script>
