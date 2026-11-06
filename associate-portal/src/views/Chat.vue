<template>
	<ion-page>
		<ion-header class="ion-no-border chat-ion-header">
            <nav class="onboarding-topbar" aria-label="Profile and support">
                <router-link to="/profile">My Profile</router-link>
                <span class="active-tab" aria-current="page">Chat</span>
                <AccountLogoutMenu/>
            </nav>
		</ion-header>

		<ion-content
			ref="contentRef"
			class="chat-ion-content"
			:scroll-y="false"
			:fullscreen="false"
		>
			<div ref="chatBodyRef" class="chat-body">
				<!-- MESSAGES -->
				<div class="chat-messages" ref="messagesRef">
					<div v-if="initializing" class="flex flex-col items-center justify-center h-full">
						<div class="w-8 h-8 border-2 border-gray-200 border-t-[#a61d1d] rounded-full animate-spin mb-3"></div>
						<p class="text-sm text-gray-400">Connecting to support...</p>
					</div>

					<div v-else-if="initError" class="flex flex-col items-center justify-center h-full">
						<div class="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center mb-3">
							<FeatherIcon name="alert-circle" class="h-7 w-7 text-red-400" />
						</div>
						<p class="text-sm text-gray-500 mb-4 text-center px-4">{{ initError }}</p>
						<button
							class="px-5 py-2 text-sm font-medium text-white bg-[#a61d1d] rounded-full active:scale-95 transition"
							@click="retryInit"
						>Try again</button>
					</div>

					<div v-else-if="!messages.length" class="flex flex-col items-center justify-center h-full px-8">
						<div class="w-14 h-14 bg-blue-50 rounded-full flex items-center justify-center mb-3">
							<FeatherIcon name="message-circle" class="h-7 w-7 text-[#a61d1d]" />
						</div>
						<h3 class="text-base font-semibold text-gray-700 mb-1">OneMotion Support</h3>
						<p class="text-xs text-gray-400 text-center">
							Send a message and our team will reply as soon as possible.
						</p>
					</div>

					<div v-else class="px-4 py-3 space-y-3">
						<div
							v-for="(msg, idx) in messages"
							:key="msg.id"
							class="flex items-end gap-2"
							:class="msg.message_type === 0 ? 'justify-end' : 'justify-start'"
						>
							<div
								v-if="msg.message_type !== 0 && showAvatar(idx)"
								class="w-7 h-7 rounded-full bg-[#a61d1d] flex items-center justify-center shrink-0"
							>
								<FeatherIcon name="headphones" class="h-3.5 w-3.5 text-white" />
							</div>
							<div v-else-if="msg.message_type !== 0" class="w-7 shrink-0"></div>

							<div
								class="max-w-[78%] px-3.5 py-2.5 text-[14px] leading-relaxed"
								:class="msg.message_type === 0
									? 'bg-[#a61d1d] text-white rounded-2xl rounded-br-md shadow-sm'
									: 'bg-white text-gray-800 rounded-2xl rounded-bl-md shadow-sm'"
							>
								<div v-html="msg.content"></div>
								<div
									class="flex items-center gap-1 mt-1"
									:class="msg.message_type === 0 ? 'justify-end' : 'justify-start'"
								>
									<span
										class="text-[10px]"
										:class="msg.message_type === 0 ? 'text-white/50' : 'text-gray-300'"
									>{{ formatTime(msg.created_at) }}</span>
									<FeatherIcon
										v-if="msg.message_type === 0 && !String(msg.id).startsWith('temp-')"
										name="check"
										class="h-3 w-3 text-white/50"
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- INPUT BAR -->
				<div class="chat-input-bar">
					<div class="flex items-center gap-2 px-4 py-2.5">
						<input
							ref="inputRef"
							v-model="newMessage"
							type="text"
							enterkeyhint="send"
							inputmode="text"
							class="flex-1 px-4 py-2.5 text-sm bg-gray-100 rounded-full border-0 outline-none focus:ring-2 focus:ring-[#a61d1d]/30 placeholder-gray-400"
							style="font-size: 12px;"
							placeholder="Type a message..."
							@keydown.enter.prevent="sendMessage"
							@focus="onInputFocus"
							@blur="onInputBlur"
						/>
						<button
							class="flex items-center justify-center w-10 h-10 rounded-full bg-[#a61d1d] text-white shrink-0 transition active:scale-90 disabled:opacity-40"
							:disabled="!newMessage.trim() || sending"
							@click="sendMessage"
						>
							<FeatherIcon name="send" class="h-4 w-4" />
						</button>
					</div>
					<!-- Safe area spacer for iPhone home indicator -->
					<div class="chat-safe-area"></div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import AccountLogoutMenu from '@/components/AccountLogoutMenu.vue'
import { ref, onMounted, onUnmounted, nextTick, inject } from "vue"
import { IonPage, IonHeader, IonContent } from "@ionic/vue"
import { FeatherIcon, call } from "frappe-ui"
import { unreadCount } from "@/data/notifications"

const session = inject("$session")
const __ = inject("$translate")
const dayjs = inject("$dayjs")

const logoUrl = "/files/onemotion-logo-dark.png"

const initializing = ref(true)
const initError = ref("")
const messages = ref([])
const newMessage = ref("")
const sending = ref(false)
const inputRef = ref(null)
const messagesRef = ref(null)
const contentRef = ref(null)
const chatBodyRef = ref(null)

let contactIdentifier = ""
let conversationId = null
let pollInterval = null
let loadErrorCount = 0

// Capture the initial full window height BEFORE any keyboard opens
// On iOS Safari, window.innerHeight at load = full viewport without keyboard
let initialHeight = 0

function onInputFocus() {
	// When keyboard opens on iOS, the visual viewport shrinks but layout viewport stays.
	// We need to scroll our messages container to bottom so user sees latest messages.
	// Use multiple delayed scrolls to catch the keyboard animation completing.
	setTimeout(() => scrollToBottom(), 100)
	setTimeout(() => scrollToBottom(), 300)
	setTimeout(() => scrollToBottom(), 500)
}

function onInputBlur() {
	// Nothing needed — Ionic handles the layout
}

function formatTime(ts) {
	if (!ts) return ""
	const d = typeof ts === "number" && ts > 1e12 ? new Date(ts) : typeof ts === "number" ? new Date(ts * 1000) : new Date(ts)
	return dayjs(d).format("HH:mm")
}

function showAvatar(idx) {
	if (idx === 0) return true
	const prev = messages.value[idx - 1]
	const curr = messages.value[idx]
	return prev.message_type !== curr.message_type
}

function scrollToBottom() {
	nextTick(() => {
		setTimeout(() => {
			if (messagesRef.value) {
				messagesRef.value.scrollTop = messagesRef.value.scrollHeight
			}
		}, 50)
	})
}

function clearSession() {
	localStorage.removeItem("cw_contact")
	localStorage.removeItem("cw_conversation")
	contactIdentifier = ""
	conversationId = null
}

function normalizeList(data) {
	if (Array.isArray(data)) return data
	if (Array.isArray(data?.payload)) return data.payload
	if (Array.isArray(data?.data)) return data.data
	return []
}

function conversationTime(conv) {
	const raw = conv?.last_activity_at || conv?.last_activity || conv?.updated_at || conv?.created_at || conv?.id || 0
	if (typeof raw === "number") return raw > 1e12 ? raw : raw * 1000
	const parsed = new Date(raw).getTime()
	return Number.isFinite(parsed) ? parsed : 0
}

function pickLatestConversation(conversations) {
	return normalizeList(conversations)
		.filter((conv) => conv?.id)
		.sort((a, b) => conversationTime(b) - conversationTime(a))[0] || null
}

async function createContact() {
	const data = await call("onemotion.api.associate_portal.chat_create_contact")
	if (!data || !data.source_id) throw new Error("No source_id")
	contactIdentifier = data.source_id
	localStorage.setItem("cw_contact", JSON.stringify({ source_id: data.source_id }))
	if (data.conversation_id) {
		conversationId = parseInt(data.conversation_id)
		localStorage.setItem("cw_conversation", String(data.conversation_id))
	}
}

async function createConversation() {
	if (!contactIdentifier) throw new Error("No contact identifier")
	const data = await call("onemotion.api.associate_portal.chat_create_conversation", { contact_identifier: contactIdentifier })
	if (!data || !data.id) throw new Error("No conversation id")
	conversationId = data.id
	localStorage.setItem("cw_conversation", String(data.id))
}

async function syncLatestConversation() {
	if (!contactIdentifier) return false
	const data = await call("onemotion.api.associate_portal.chat_get_conversations", {
		contact_identifier: contactIdentifier,
	})
	const latest = pickLatestConversation(data)
	if (!latest?.id) return false

	if (String(latest.id) !== String(conversationId || "")) {
		conversationId = latest.id
		localStorage.setItem("cw_conversation", String(latest.id))
	}
	return true
}

async function loadMessages() {
	if (!contactIdentifier || !conversationId) return
	try {
		const data = await call("onemotion.api.associate_portal.chat_get_messages", {
			contact_identifier: contactIdentifier,
			conversation_id: conversationId,
		})
		loadErrorCount = 0
		const newMsgs = Array.isArray(data) ? data : (data && data.payload) ? data.payload : []
		messages.value = newMsgs.sort((a, b) => {
			const ta = typeof a.created_at === "number" ? a.created_at : new Date(a.created_at).getTime()
			const tb = typeof b.created_at === "number" ? b.created_at : new Date(b.created_at).getTime()
			return ta - tb
		})
		scrollToBottom()
	} catch (e) {
		loadErrorCount++
		console.error("Load messages error:", e)
		try {
			if (contactIdentifier && await syncLatestConversation()) {
				loadErrorCount = 0
			}
		} catch (syncError) {
			console.warn("Chat conversation sync failed:", syncError)
		}
		// Only stop polling after many consecutive errors, never clear session
		// so user can still send messages even if polling temporarily fails
		if (loadErrorCount >= 10) {
			if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
			// Restart polling with a slower interval instead of killing session
			pollInterval = setInterval(loadMessages, 15000)
			loadErrorCount = 0
		}
	}
}

async function sendMessage() {
	const text = newMessage.value.trim()
	if (!text || sending.value) return
	if (!contactIdentifier || !conversationId) return

	sending.value = true
	newMessage.value = ""

	const optimisticMsg = { id: "temp-" + Date.now(), content: text, message_type: 0, created_at: new Date().toISOString() }
	messages.value = [...messages.value, optimisticMsg]
	scrollToBottom()

	try {
		await call("onemotion.api.associate_portal.chat_send_message", {
			contact_identifier: contactIdentifier,
			conversation_id: conversationId,
			content: text,
		})
		await loadMessages()
	} catch (e) {
		console.error("Send message error:", e)
		messages.value = messages.value.filter(m => m.id !== optimisticMsg.id)
		newMessage.value = text
	} finally {
		sending.value = false
		nextTick(() => {
			inputRef.value?.focus()
			scrollToBottom()
		})
	}
}

async function initChat() {
	const savedContact = localStorage.getItem("cw_contact")
	const savedConversation = localStorage.getItem("cw_conversation")

	// If this device already has a Chatwoot public source_id, validate it first
	// and persist it server-side. This prevents opening a brand-new empty chat
	// after we introduced server-side persistence.
	if (savedContact) {
		try {
			const contactData = JSON.parse(savedContact)
			const savedSourceId = contactData?.source_id
			if (savedSourceId) {
				const remembered = await call("onemotion.api.associate_portal.chat_remember_session", {
					contact_identifier: savedSourceId,
					conversation_id: savedConversation || null,
				})
				if (remembered?.source_id) {
					contactIdentifier = remembered.source_id
					if (remembered.conversation_id) {
						conversationId = parseInt(remembered.conversation_id)
						localStorage.setItem("cw_conversation", String(remembered.conversation_id))
					}
					if (!await syncLatestConversation()) {
						await createConversation()
					}
					await loadMessages()
					pollInterval = setInterval(loadMessages, 5000)
					return
				}
			}
		} catch (e) {
			console.warn("Saved chat session could not be reused:", e)
		}
	}

	// Ask the server for the canonical OneChat contact. localStorage can be stale
	// after reinstall/cache clear and would otherwise open an empty chat.
	await createContact()
	if (!await syncLatestConversation()) {
		await createConversation()
	}
	await loadMessages()
	pollInterval = setInterval(loadMessages, 5000)
}

async function retryInit() {
	initError.value = ""
	initializing.value = true
	clearSession()
	try {
		await createContact()
		await createConversation()
		await loadMessages()
		pollInterval = setInterval(loadMessages, 5000)
	}
	catch (e) { initError.value = "Could not connect to support chat. Please try again later." }
	finally { initializing.value = false }
}

async function startNewChat() {
	if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
	clearSession()
	messages.value = []
	initializing.value = true
	initError.value = ""
	try {
		await createContact()
		await createConversation()
		await loadMessages()
		pollInterval = setInterval(loadMessages, 5000)
	} catch (e) {
		initError.value = "Could not start a new chat. Please try again."
	} finally {
		initializing.value = false
	}
}

// VisualViewport handler: adjust chat-body height when keyboard opens/closes
function handleViewportResize() {
	const vv = window.visualViewport
	if (!vv) return
	const chatBody = chatBodyRef.value
	if (!chatBody) return

	// ion-content already sits below ion-header.
	// We need chat-body to fill exactly the visual viewport minus the header.
	// Get the header height from the ion-header element
	const ionHeader = document.querySelector('.chat-ion-header')
	const headerHeight = ionHeader ? ionHeader.offsetHeight : 56

	// Visual viewport height = visible screen minus keyboard
	// Subtract header height to get the space available for chat-body
	const availableHeight = vv.height - headerHeight
	chatBody.style.height = Math.max(availableHeight, 200) + 'px'

	// If iOS scrolled the page up, scroll it back
	if (vv.offsetTop > 0) {
		window.scrollTo(0, 0)
	}

	scrollToBottom()
}

onMounted(async () => {
	initialHeight = window.innerHeight

	// Set initial chat-body height (full height minus header)
	nextTick(() => {
		const ionHeader = document.querySelector('.chat-ion-header')
		const headerHeight = ionHeader ? ionHeader.offsetHeight : 56
		if (chatBodyRef.value) {
			chatBodyRef.value.style.height = (initialHeight - headerHeight) + 'px'
		}
	})

	// Listen to visualViewport resize for keyboard show/hide
	if (window.visualViewport) {
		window.visualViewport.addEventListener('resize', handleViewportResize)
		window.visualViewport.addEventListener('scroll', handleViewportResize)
	}

	try {
		await initChat()
	} catch (e) {
		console.error("Chat init error:", e)
		clearSession()
		try {
			await createContact()
			await createConversation()
			await loadMessages()
			pollInterval = setInterval(loadMessages, 5000)
		}
		catch (e2) { initError.value = "Could not connect to support chat. Please try again later." }
	} finally {
		initializing.value = false
	}
})

onUnmounted(() => {
	if (window.visualViewport) {
		window.visualViewport.removeEventListener('resize', handleViewportResize)
		window.visualViewport.removeEventListener('scroll', handleViewportResize)
	}
	if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
})
</script>

<style scoped>
.onboarding-topbar{display:grid;grid-template-columns:repeat(3,1fr);max-width:42rem;margin:auto;padding:0 1rem;background:white}.onboarding-topbar>*{min-height:44px;display:flex;align-items:center;justify-content:center;font-size:.95rem;font-weight:500;color:#111827;border:1px solid #e5e7eb;background:white}.onboarding-topbar .active-tab{border:1px solid #c63624;box-shadow:0 2px 7px #a61d1d24;position:relative;z-index:1}

/*
 * Chat layout strategy:
 * - Uses Ionic's ion-page > ion-header > ion-content (same as Documents/Agreements)
 * - ion-header is managed by Ionic — it NEVER moves on keyboard open
 * - Inside ion-content we have a .chat-body flex container
 * - .chat-body uses visualViewport height so it shrinks when keyboard opens
 * - .chat-messages is flex:1 with overflow scroll
 * - .chat-input-bar is flex-shrink:0, always at bottom of visible area
 * - font-size:12px on input prevents iOS from zooming
 */

.chat-ion-header {
	background: #fff;
}

.chat-ion-content {
	--background: #f9fafb;
}

.chat-body {
	display: flex;
	flex-direction: column;
	/* Height is set dynamically via JS using visualViewport */
	height: 100%;
	overflow: hidden;
	background: #f9fafb;
}

.chat-messages {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	overflow-x: hidden;
	-webkit-overflow-scrolling: touch;
	background: #f9fafb;
}

.chat-input-bar {
	flex-shrink: 0;
	background: #fff;
	border-top: 1px solid #e5e7eb; /* reverted to gray-200 */
}

.chat-safe-area {
	height: env(safe-area-inset-bottom, 0px);
	background: #fff;
}
</style>
