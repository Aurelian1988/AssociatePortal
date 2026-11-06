import { computed, reactive } from "vue"
import { createResource, call } from "frappe-ui"
import { userResource } from "./user"
import { associateResource } from "./associate"
import router from "@/router"

export function sessionUser() {
	let cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let _sessionUser = cookies.get("user_id")
	if (_sessionUser === "Guest") {
		_sessionUser = null
	}
	return _sessionUser
}

export const session = reactive({
	login: async (email, password) => {
		let response = await call("login", { usr: email, pwd: password })
		// frappe-ui call() may return "Logged In" or { message: "Logged In" }
		let loggedIn = false
		if (response === "Logged In") loggedIn = true
		if (response?.message === "Logged In") loggedIn = true
		// Also check if cookie was set after the call
		if (!loggedIn) {
			let user = sessionUser()
			if (user) loggedIn = true
		}
		if (loggedIn) {
			for(const key of Object.keys(localStorage)) if(key.startsWith('om_associate_cache')) localStorage.removeItem(key)
			// Full page reload to re-initialize everything with new session
			window.location.href = "/associate"
		}
		return response
	},
	logout: createResource({
		url: "logout",
		onSuccess() {
			for(const key of Object.keys(localStorage)) if(key.startsWith('om_associate_cache')) localStorage.removeItem(key)
			sessionStorage.removeItem('sdt-test-contact-name')
			userResource.reset()
			associateResource.reset()
			session.user = sessionUser()
			window.location.href = "/associate/login"
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
})
