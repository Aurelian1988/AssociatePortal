import router from "@/router"
import { createResource } from "frappe-ui"
import { isNetworkError } from "@/utils/networkStatus"

const CACHE_KEY = "om_user_cache"

function loadCachedUser() {
	try {
		const cached = localStorage.getItem(CACHE_KEY)
		return cached ? JSON.parse(cached) : null
	} catch {
		return null
	}
}

export const userResource = createResource({
	url: "onemotion.api.associate_portal.get_current_user_info",
	cache: "associate-portal:user",
	onSuccess(data) {
		if (data) {
			localStorage.setItem(CACHE_KEY, JSON.stringify(data))
		}
	},
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			router.push({ name: "Login" })
			return
		}
		// On network error, load from cache instead of crashing
		if (isNetworkError(error)) {
			const cached = loadCachedUser()
			if (cached) {
				userResource.data = cached
			}
		}
	},
})
