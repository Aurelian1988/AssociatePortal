/**
 * OneMotion Associate Portal — Service Worker
 * Caches the app shell for offline/PWA support + Web Push Notifications.
 */

const CACHE_NAME = "onemotion-associate-v17"

// App shell files to pre-cache (populated at build time via URL patterns)
const APP_SHELL = [
	"/associate",
	"/files/onemotion-logo-dark.png",
	"/files/app-icon-192.png",
	"/files/app-icon-512.png",
	"/files/apple-touch-icon.png",
	"/files/favicon-32x32.png",
]

// Install — pre-cache app shell
self.addEventListener("install", (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => {
			return cache.addAll(APP_SHELL)
		})
	)
	// Activate immediately
	self.skipWaiting()
})

// Activate — clean up old caches
self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches.keys().then((cacheNames) => {
			return Promise.all(
				cacheNames
					.filter((name) => name !== CACHE_NAME)
					.map((name) => caches.delete(name))
			)
		})
	)
	// Take control of all clients immediately
	self.clients.claim()
})

// ─── Push Notification ──────────────────────────────────────────────────

self.addEventListener("push", (event) => {
	if (!event.data) return

	let data = {}
	try {
		data = event.data.json()
	} catch (e) {
		data = {
			title: "OneMotion",
			body: event.data.text(),
			url: "/associate",
			icon: "/files/app-icon-192.png",
		}
	}

	const title = data.title || "OneMotion"
	const options = {
		body: data.body || "",
		icon: data.icon || "/files/app-icon-192.png",
		badge: "/files/app-icon-192.png",
		tag: data.tag || "onemotion-notification-" + Date.now(),
		renotify: true,
		requireInteraction: false,
		vibrate: [200, 100, 200],
		data: {
			url: data.url || "/associate",
		},
		actions: [
			{ action: "open", title: "Open" },
			{ action: "dismiss", title: "Dismiss" },
		],
	}

	event.waitUntil(self.registration.showNotification(title, options))
})

// Handle notification click
self.addEventListener("notificationclick", (event) => {
	event.notification.close()

	if (event.action === "dismiss") return

	const targetUrl = (event.notification.data && event.notification.data.url) || "/associate"

	event.waitUntil(
		self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
			// If a window is already open, focus it and navigate
			for (const client of clientList) {
				if ("focus" in client) {
					client.focus()
					client.postMessage({
						type: "NOTIFICATION_CLICK",
						url: targetUrl,
					})
					return
				}
			}
			// Otherwise open a new window
			if (self.clients.openWindow) {
				return self.clients.openWindow(targetUrl)
			}
		})
	)
})

// ─── Fetch — network-first for API, cache-first for assets ─────────────

self.addEventListener("fetch", (event) => {
	const url = new URL(event.request.url)

	// Skip non-GET requests
	if (event.request.method !== "GET") return

	// Skip Frappe API calls — always go to network
	if (url.pathname.startsWith("/api/")) return

	// For navigation requests (HTML pages), network-first
	if (event.request.mode === "navigate") {
		event.respondWith(
			fetch(event.request)
				.then((response) => {
					// Cache the latest version
					const clone = response.clone()
					caches.open(CACHE_NAME).then((cache) => {
						cache.put(event.request, clone)
					})
					return response
				})
				.catch(() => {
					// Offline fallback — serve cached version
					return caches.match(event.request).then((cached) => {
						return cached || caches.match("/associate")
					})
				})
		)
		return
	}

	// For assets (JS, CSS, images) — cache-first
	if (
		url.pathname.startsWith("/assets/") ||
		url.pathname.startsWith("/files/")
	) {
		event.respondWith(
			caches.match(event.request).then((cached) => {
				if (cached) return cached
				return fetch(event.request).then((response) => {
					const clone = response.clone()
					caches.open(CACHE_NAME).then((cache) => {
						cache.put(event.request, clone)
					})
					return response
				})
			})
		)
		return
	}
})
