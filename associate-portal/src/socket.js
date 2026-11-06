import { io } from "socket.io-client"

export function initSocket() {
	try {
		const host = window.location.hostname
		const siteName = window.site_name || window.location.hostname
		const url = `https://${host}/${siteName}`
		const socket = io(url, {
			withCredentials: true,
			reconnectionAttempts: 3,
			reconnectionDelay: 5000,
			transports: ["websocket"],
			timeout: 5000,
		})

		socket.on("connect_error", () => {
			// Silently handle — portal works without realtime
			socket.disconnect()
		})

		return socket
	} catch (e) {
		// Return a no-op socket if connection fails
		return {
			on: () => {},
			emit: () => {},
			off: () => {},
			connected: false,
		}
	}
}
