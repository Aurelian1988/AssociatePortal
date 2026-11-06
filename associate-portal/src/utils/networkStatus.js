import { ref, readonly } from "vue"

const isOnline = ref(navigator.onLine)
const wasOffline = ref(false)

// Track online/offline events
window.addEventListener("online", () => {
	isOnline.value = true
	// Keep wasOffline true briefly so components can auto-retry
	setTimeout(() => {
		wasOffline.value = false
	}, 3000)
})

window.addEventListener("offline", () => {
	isOnline.value = false
	wasOffline.value = true
})

/**
 * Check if a fetch error is a network error (not an auth/server error)
 */
export function isNetworkError(error) {
	if (!navigator.onLine) return true
	if (!error) return false
	const msg = (error.message || error.toString() || "").toLowerCase()
	return (
		msg.includes("failed to fetch") ||
		msg.includes("network") ||
		msg.includes("networkerror") ||
		msg.includes("load failed") ||
		msg.includes("the internet connection appears to be offline") ||
		msg.includes("abort") ||
		msg.includes("timeout") ||
		error.name === "TypeError"
	)
}

export function useNetworkStatus() {
	return {
		isOnline: readonly(isOnline),
		wasOffline: readonly(wasOffline),
	}
}
