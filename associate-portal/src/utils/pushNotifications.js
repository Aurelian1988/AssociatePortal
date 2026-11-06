/**
 * Push Notifications Utility
 * Handles service worker registration, push subscription, and permission management.
 */
import { frappeRequest } from "frappe-ui"

let swRegistration = null
let pushSubscription = null

/**
 * Convert a URL-safe base64 string to a Uint8Array (for applicationServerKey)
 */
function urlBase64ToUint8Array(base64String) {
	const padding = "=".repeat((4 - (base64String.length % 4)) % 4)
	const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/")
	const rawData = atob(base64)
	const outputArray = new Uint8Array(rawData.length)
	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i)
	}
	return outputArray
}

/**
 * Detect browser name
 */
function getBrowserName() {
	const ua = navigator.userAgent
	if (ua.indexOf("Chrome") > -1 && ua.indexOf("Edg") === -1) return "Chrome"
	if (ua.indexOf("Safari") > -1 && ua.indexOf("Chrome") === -1) return "Safari"
	if (ua.indexOf("Firefox") > -1) return "Firefox"
	if (ua.indexOf("Edg") > -1) return "Edge"
	return "Unknown"
}

/**
 * Detect device type
 */
function getDeviceType() {
	const ua = navigator.userAgent
	if (/iPad|Tablet/i.test(ua)) return "Tablet"
	if (/iPhone|Android.*Mobile/i.test(ua)) return "Mobile"
	return "Desktop"
}

/**
 * Check if push notifications are supported
 */
export function isPushSupported() {
	return (
		"serviceWorker" in navigator &&
		"PushManager" in window &&
		"Notification" in window
	)
}

/**
 * Get current notification permission status
 */
export function getPermissionStatus() {
	if (!("Notification" in window)) return "unsupported"
	return Notification.permission // "granted", "denied", or "default"
}

/**
 * Register the service worker and initialize push
 */
export async function registerServiceWorker() {
	if (!("serviceWorker" in navigator)) {
		console.log("[Push] Service workers not supported")
		return null
	}

	try {
		swRegistration = await navigator.serviceWorker.register("/files/sw.js", {
			scope: "/associate",
		})
		console.log("[Push] Service worker registered:", swRegistration.scope)

		// Wait for the SW to be active
		if (swRegistration.installing) {
			await new Promise((resolve) => {
				swRegistration.installing.addEventListener("statechange", (e) => {
					if (e.target.state === "activated") resolve()
				})
			})
		}

		return swRegistration
	} catch (error) {
		console.error("[Push] Service worker registration failed:", error)
		return null
	}
}

/**
 * Request notification permission from the user
 */
export async function requestNotificationPermission() {
	if (!("Notification" in window)) {
		console.log("[Push] Notifications not supported")
		return "unsupported"
	}

	if (Notification.permission === "granted") {
		return "granted"
	}

	if (Notification.permission === "denied") {
		console.log("[Push] Notifications are denied by user")
		return "denied"
	}

	// Ask for permission
	const permission = await Notification.requestPermission()
	console.log("[Push] Permission result:", permission)
	return permission
}

/**
 * Subscribe to push notifications
 */
export async function subscribeToPush() {
	if (!isPushSupported()) {
		console.log("[Push] Push not supported")
		return null
	}

	// Ensure SW is registered
	if (!swRegistration) {
		swRegistration = await registerServiceWorker()
	}

	if (!swRegistration) {
		console.log("[Push] No service worker registration")
		return null
	}

	// Request permission
	const permission = await requestNotificationPermission()
	if (permission !== "granted") {
		console.log("[Push] Permission not granted:", permission)
		return null
	}

	try {
		// Get VAPID public key from server
		const response = await frappeRequest({
			url: "/api/method/onemotion.api.associate_portal.get_vapid_public_key",
		})

		const vapidPublicKey = response.message || response
		if (!vapidPublicKey) {
			console.error("[Push] No VAPID public key from server")
			return null
		}

		// Check existing subscription
		pushSubscription = await swRegistration.pushManager.getSubscription()

		if (pushSubscription) {
			console.log("[Push] Already subscribed, updating server...")
			await saveSubscriptionToServer(pushSubscription)
			return pushSubscription
		}

		// Subscribe to push
		const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey)
		pushSubscription = await swRegistration.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: applicationServerKey,
		})

		console.log("[Push] Subscription created:", pushSubscription.endpoint.substring(0, 50) + "...")

		// Send subscription to server
		await saveSubscriptionToServer(pushSubscription)

		return pushSubscription
	} catch (error) {
		console.error("[Push] Subscription failed:", error)
		return null
	}
}

/**
 * Save the push subscription to the server
 */
async function saveSubscriptionToServer(subscription) {
	const key = subscription.getKey("p256dh")
	const auth = subscription.getKey("auth")

	const p256dh = key ? btoa(String.fromCharCode.apply(null, new Uint8Array(key))) : ""
	const authKey = auth ? btoa(String.fromCharCode.apply(null, new Uint8Array(auth))) : ""

	try {
		await frappeRequest({
			url: "/api/method/onemotion.api.associate_portal.save_push_subscription",
			params: {
				endpoint: subscription.endpoint,
				p256dh: p256dh,
				auth: authKey,
				browser: getBrowserName(),
				device: getDeviceType(),
			},
		})
		console.log("[Push] Subscription saved to server")
	} catch (error) {
		console.error("[Push] Failed to save subscription:", error)
		throw error
	}
}

/**
 * Unsubscribe from push notifications
 */
export async function unsubscribeFromPush() {
	if (!swRegistration) {
		swRegistration = await navigator.serviceWorker.ready
	}

	try {
		const subscription = await swRegistration.pushManager.getSubscription()
		if (subscription) {
			// Remove from server
			try {
				await frappeRequest({
					url: "/api/method/onemotion.api.associate_portal.remove_push_subscription",
					params: { endpoint: subscription.endpoint },
				})
			} catch (e) {
				console.error("[Push] Failed to remove from server:", e)
			}

			// Unsubscribe locally
			await subscription.unsubscribe()
			pushSubscription = null
			console.log("[Push] Unsubscribed")
		}
	} catch (error) {
		console.error("[Push] Unsubscribe failed:", error)
	}
}

/**
 * Initialize push notifications — call this on app startup
 * Automatically subscribes if permission was already granted
 */
export async function initPushNotifications() {
	if (!isPushSupported()) {
		console.log("[Push] Push notifications not supported on this device/browser")
		return
	}

	// Register service worker
	await registerServiceWorker()

	// If permission was already granted, subscribe automatically
	if (Notification.permission === "granted") {
		await subscribeToPush()
	}

	// Listen for messages from the service worker (notification clicks)
	navigator.serviceWorker.addEventListener("message", (event) => {
		if (event.data && event.data.type === "NOTIFICATION_CLICK") {
			const url = event.data.url
			if (url && window.location.pathname !== url) {
				window.location.href = url
			}
		}
	})
}

/**
 * Send a test push notification
 */
export async function sendTestPush() {
	try {
		await frappeRequest({
			url: "/api/method/onemotion.api.associate_portal.send_test_push_notification",
		})
		console.log("[Push] Test notification sent")
		return true
	} catch (error) {
		console.error("[Push] Test notification failed:", error)
		return false
	}
}
