import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import {
	Button,
	Input,
	setConfig,
	frappeRequest,
	resourcesPlugin,
	FormControl,
} from "frappe-ui"
import { translationsPlugin } from "./plugins/translationsPlugin.js"

import { IonicVue } from "@ionic/vue"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { associateResource } from "@/data/associate"

import { isNetworkError } from "@/utils/networkStatus"
import dayjs from "@/utils/dayjs"
import getIonicConfig from "@/utils/ionicConfig"
import { refreshProfile, refreshPush, canUsePortal } from "@/data/onboarding"

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css"

/* Theme variables */
import "./theme/variables.css"

import "./main.css"

const app = createApp(App)
const socket = initSocket()

setConfig("resourceFetcher", frappeRequest)
app.use(resourcesPlugin)
app.use(translationsPlugin)

app.component("Button", Button)
app.component("Input", Input)
app.component("FormControl", FormControl)

router.beforeEach(async (to) => {
  if (!session.isLoggedIn) return to.name === 'Login' ? true : { name: 'Login' }
  try {
    await userResource.reload()
    if (!associateResource.data) await associateResource.reload()
  } catch (error) {
    if (error?.exc_type === 'AuthenticationError') return { name: 'Login' }
    return to.name === 'Profile' ? true : { name: 'Profile' }
  }
  if (associateResource.data?.onboarding_pending) return ['Profile','Chat'].includes(to.name) ? true : { name: 'Profile' }
  if (!associateResource.data?.name) return to.name === 'InvalidAssociate' ? true : { name: 'InvalidAssociate' }
  if (['Profile','Chat'].includes(to.name)) return true
  try {
    await refreshProfile()
    await refreshPush()
  } catch { return { name: 'Profile' } }
  if (!canUsePortal.value) return { name: 'Profile' }
  if (to.name === 'Login' || to.name === 'InvalidAssociate') return { name: 'Home' }
  return true
})

app.use(router)
app.use(IonicVue, getIonicConfig())

if (session?.isLoggedIn && !associateResource?.data) {
	associateResource.reload()
}

app.provide("$session", session)
app.provide("$user", userResource)
app.provide("$associate", associateResource)
app.provide("$socket", socket)
app.provide("$dayjs", dayjs)

router.isReady().then(async () => {
	if (import.meta.env.DEV) {
		await frappeRequest({
			url: "/api/method/onemotion.api.associate_portal.get_context_for_dev",
		}).then(async (values) => {
			if (!window.frappe) window.frappe = {}
			window.frappe.boot = values
		})
	}

	await translationsPlugin.isReady()
	app.mount("#app")

	// Initialize push notifications after app is mounted
	if (session?.isLoggedIn) {
		refreshPush()
	}

	// Auto-reload data when coming back online
	window.addEventListener("online", () => {
		if (session?.isLoggedIn) {
			userResource.reload()
			associateResource.reload()
		}
	})
})

