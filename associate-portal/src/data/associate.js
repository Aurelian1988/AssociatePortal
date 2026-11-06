import router from "@/router"
import { createResource } from "frappe-ui"
import { isNetworkError } from "@/utils/networkStatus"

const CACHE_KEY = "om_associate_cache:" + (new URLSearchParams(document.cookie.split('; ').join('&')).get('user_id') || 'Guest')

function loadCachedAssociate() {
	try {
		const cached = localStorage.getItem(CACHE_KEY)
		return cached ? JSON.parse(cached) : null
	} catch {
		return null
	}
}

export const associateResource = createResource({
	url: "onemotion.api.profile_contact_start.get_current_associate_info",
	cache: "associate-portal:associate",
	onSuccess(data) {
		if (data) {
			localStorage.setItem(CACHE_KEY, JSON.stringify(data))
		}
	},
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			router.push("/login")
			return
		}
		// On network error, load from cache instead of crashing
		if (isNetworkError(error)) {
			const cached = loadCachedAssociate()
			if (cached) {
				associateResource.data = cached
			}
		}
	},
})
