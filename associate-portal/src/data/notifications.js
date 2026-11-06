import { createResource } from "frappe-ui"
import { ref, computed } from "vue"

export const unreadCount = createResource({
	url: "onemotion.api.associate_portal.get_unread_notifications_count",
	cache: "associate:unread_notifications_count",
	initialData: 0,
	auto: true,
	onSuccess(data) {
		syncNativeAppBadge(data)
	},
})

export const notifications = createResource({
	url: "onemotion.api.associate_portal.get_notifications",
	cache: "associate:notifications",
	initialData: [],
	auto: false,
	transform(data) {
		return Array.isArray(data) ? data : []
	},
})

export const markAllAsRead = createResource({
	url: "onemotion.api.associate_portal.mark_all_notifications_as_read",
	onSuccess() {
		notifications.reload()
		unreadCount.reload()
		syncNativeAppBadge(0)
	},
})

export const markOneAsRead = createResource({
	url: "onemotion.api.associate_portal.mark_notification_as_read",
	onSuccess() {
		unreadCount.reload()
	},
})

// Poll for new notifications every 30 seconds
let pollInterval = null

export function startNotificationPolling() {
	if (pollInterval) return
	unreadCount.reload()
	pollInterval = setInterval(() => {
		unreadCount.reload()
	}, 30000)
}

export function stopNotificationPolling() {
	if (pollInterval) {
		clearInterval(pollInterval)
		pollInterval = null
	}
}

export function syncNativeAppBadge(count) {
	const numericCount = Math.max(0, parseInt(count || 0, 10) || 0)
	if (!window.__OM_NATIVE_APP || !window.FlutterBridge?.postMessage) return
	try {
		window.FlutterBridge.postMessage(JSON.stringify({
			action: "SET_APP_BADGE",
			count: numericCount,
		}))
	} catch {}
}
