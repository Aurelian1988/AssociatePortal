<template>
	<ion-page>
		<ion-header>
			<ion-toolbar style="--background: #a61d1d; --color: white; --border-color: transparent;">
				<ion-buttons slot="start">
					<ion-button style="--color: white;" @click="goBack">
						<FeatherIcon name="chevron-left" class="w-5 h-5" />
						<span class="text-sm">Back</span>
					</ion-button>
				</ion-buttons>
				<ion-title style="color: white; font-size: 12px; font-weight: 700;">
					{{ docInfo.label || 'Upload Document' }}
				</ion-title>
			</ion-toolbar>
		</ion-header>

		<ion-content>
			<!-- Loading -->
			<div v-if="loading" class="flex items-center justify-center py-20">
				<div class="w-7 h-7 border-2 border-gray-300 border-t-[#a61d1d] rounded-full animate-spin" />
			</div>

			<DbsFilesForm v-else-if="fieldName==='crb_report_document'"/><div v-else class="flex flex-col gap-5 p-4 pb-12">

				<!-- Status badge -->
				<div v-if="docInfo.status" class="flex items-center gap-2">
					<span class="text-sm text-gray-500">Status:</span>
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" :class="statusBadgeClass(docInfo.status)">
						{{ statusLabel(docInfo.status) }}
					</span>
				</div>

				<!-- Locked notice (under review or already valid) -->
				<div v-if="!canUpload" class="flex items-start gap-3 bg-blue-50 rounded-xl p-4">
					<FeatherIcon :name="docInfo.status === 'under_review' ? 'clock' : 'lock'" class="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
					<div>
						<p class="text-sm font-medium text-blue-800">
							{{ docInfo.status === 'under_review' ? 'Document under review' : 'Document locked' }}
						</p>
						<p class="text-xs text-blue-600 mt-0.5">{{ lockedReason }}</p>
					</div>
				</div>

				<!-- View current file -->
				<a v-if="docInfo.file_url" :href="docInfo.file_url" target="_blank"
					class="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-700">
					<FeatherIcon name="eye" class="w-4 h-4 text-gray-500 shrink-0" />
					<span class="truncate flex-1">View current document</span>
					<FeatherIcon name="external-link" class="w-3.5 h-3.5 text-gray-400 shrink-0" />
				</a>

				<template v-if="canUpload">
					<!-- File picker / camera scanner -->
					<div class="flex flex-col gap-2">
						<p class="text-sm font-semibold text-gray-700">
							{{ docInfo.file_url ? 'Replace document' : 'Upload document' }}
						</p>
						<div class="grid grid-cols-2 gap-3">
							<button
								type="button"
								@click="openCameraScanner"
								class="flex flex-col items-center justify-center gap-2 py-6 rounded-xl border-2 border-dashed border-blue-500/40 bg-blue-50 active:scale-95 transition">
								<div class="w-11 h-11 rounded-full bg-blue-100 flex items-center justify-center">
									<FeatherIcon name="camera" class="w-5 h-5 text-blue-600" />
								</div>
								<span class="text-sm font-semibold text-gray-700">Scan with Camera</span>
								<span class="text-xs text-gray-400">Camera / photo → PDF + OCR</span>
							</button>
							<label
								class="relative flex flex-col items-center justify-center gap-2 py-6 rounded-xl border-2 border-dashed border-[#a61d1d]/40 bg-red-50/40 active:scale-95 transition cursor-pointer overflow-hidden">
								<div class="w-11 h-11 rounded-full bg-[#a61d1d]/10 flex items-center justify-center">
									<FeatherIcon name="file-text" class="w-5 h-5 text-[#a61d1d]" />
								</div>
								<span class="text-sm font-semibold text-gray-700">Choose File</span>
								<span class="text-xs text-gray-400">PDF or image</span>
								<input
									ref="galleryInput"
									type="file"
									accept="application/pdf,.pdf,image/*"
									class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
									@change="handleFile"
								/>
							</label>
						</div>
						<div class="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
							<FeatherIcon name="alert-triangle" class="w-4 h-4 shrink-0 mt-0.5" />
							<span>Use the camera to scan the document or choose an existing PDF/image. The document is scanned automatically to fill the details below.</span>
						</div>
					</div>

					<!-- In-app camera scanner (avoids iOS/PWA file-picker camera crashes) -->
					<div v-if="cameraOpen" class="fixed inset-0 z-50 bg-black flex flex-col">
						<div class="flex items-center justify-between px-4 py-3 text-white bg-black/80">
							<button type="button" class="flex items-center gap-1 text-sm" @click="closeCameraScanner">
								<FeatherIcon name="x" class="w-5 h-5" />
								Cancel
							</button>
							<span class="text-sm font-semibold">Scan Document</span>
							<span class="w-16"></span>
						</div>
						<div class="relative flex-1 flex items-center justify-center overflow-hidden">
							<video
								ref="cameraVideo"
								autoplay
								muted
								playsinline
								webkit-playsinline
								disablepictureinpicture
								controlslist="nodownload nofullscreen noremoteplayback"
								class="camera-preview w-full h-full object-contain bg-black transition-opacity duration-150"
								:class="cameraReady ? 'opacity-100' : 'opacity-0'"
							></video>
							<div class="absolute inset-6 border-2 border-white/70 rounded-xl pointer-events-none"></div>
							<div v-if="cameraStarting" class="absolute inset-0 flex items-center justify-center bg-black/40">
								<div class="flex flex-col items-center gap-3 text-white">
									<div class="w-8 h-8 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>
									<span class="text-sm">Starting camera...</span>
								</div>
							</div>
							<div v-if="cameraError" class="absolute left-4 right-4 bottom-16 rounded-xl bg-red-600/90 px-4 py-3 text-white text-sm">
								<p class="font-semibold">Camera could not start</p>
								<p class="text-white/90 mt-1">{{ cameraError }}</p>
								<button type="button" class="mt-3 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-red-700" @click="chooseFileInstead">
									Choose file instead
								</button>
							</div>
							<div class="absolute bottom-4 left-4 right-4 text-center text-xs text-white/80">
								Place the document inside the frame, then capture.
							</div>
						</div>
						<div class="px-4 py-5 bg-black/90 flex items-center justify-center gap-4">
							<button
								type="button"
								class="px-4 py-3 rounded-xl border border-white/30 text-white text-sm"
								@click="closeCameraScanner"
							>
								Cancel
							</button>
							<button
								type="button"
								class="w-20 h-20 rounded-full bg-white border-4 border-blue-500 flex items-center justify-center active:scale-95 disabled:opacity-50 disabled:active:scale-100"
								:disabled="cameraStarting || !cameraReady"
								@click="captureCameraPhoto"
							>
								<span class="w-14 h-14 rounded-full bg-white border border-gray-300"></span>
							</button>
							<button
								type="button"
								class="px-4 py-3 rounded-xl border border-white/30 text-white text-sm opacity-0 pointer-events-none"
							>
								Cancel
							</button>
						</div>
					</div>

					<!-- Staged file -->
					<div v-if="stagedFile" class="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-green-200 bg-green-50">
						<FeatherIcon name="file" class="w-4 h-4 text-green-600 shrink-0" />
						<span class="text-sm text-green-800 truncate flex-1">{{ stagedFile.name }}</span>
						<button @click="clearFile" class="text-green-500 hover:text-red-500 shrink-0">
							<FeatherIcon name="x" class="w-4 h-4" />
						</button>
					</div>

					<!-- Processing / compressing -->
					<div v-if="processing" class="flex items-center gap-3 bg-blue-50 rounded-xl px-4 py-3">
						<div class="w-5 h-5 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin shrink-0" />
						<div>
							<p class="text-sm font-medium text-blue-800">Preparing document...</p>
							<p class="text-xs text-blue-500">Optimising file size</p>
						</div>
					</div>

					<!-- OCR loading -->
					<div v-if="scanning" class="flex items-center gap-3 bg-blue-50 rounded-xl px-4 py-3">
						<div class="w-5 h-5 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin shrink-0" />
						<div>
							<p class="text-sm font-medium text-blue-800">Reading document...</p>
							<p class="text-xs text-blue-500">Extracting data automatically</p>
						</div>
					</div>

					<!-- OCR success -->
					<div v-if="ocrFilled.length" class="flex flex-col gap-1 text-xs text-green-700 bg-green-50 px-3 py-2.5 rounded-lg">
						<div class="flex items-center gap-2 font-medium">
							<FeatherIcon name="check-circle" class="w-4 h-4 shrink-0" />
							Scanned successfully. Extracted:
						</div>
						<ul class="list-disc list-inside ml-1">
							<li v-for="f in ocrFilled" :key="f.name">{{ f.label }}: <b>{{ f.value }}</b></li>
						</ul>
						<span class="text-green-600/80">Please verify the values before submitting.</span>
					</div>

					<!-- OCR warning -->
					<div v-if="ocrError" class="flex items-center gap-2 text-xs text-orange-700 bg-orange-50 px-3 py-2 rounded-lg">
						<FeatherIcon name="alert-triangle" class="w-4 h-4 shrink-0" />
						Could not read automatically. Fill fields manually.
					</div>
				</template>

				<!-- Metadata fields -->
				<div v-if="metaFields.length" class="flex flex-col gap-3 border rounded-xl p-4"
					:class="ocrFilled.length ? 'border-green-200 bg-green-50/40' : 'border-gray-100 bg-gray-50'">
					<div class="flex items-center gap-2">
						<FeatherIcon v-if="ocrFilled.length" name="search" class="w-4 h-4 text-green-600 shrink-0" />
						<p class="text-xs font-semibold uppercase tracking-wide" :class="ocrFilled.length ? 'text-green-700' : 'text-gray-500'">
							{{ ocrFilled.length ? 'Review scanned details' : 'Document Details' }}
						</p>
					</div>
					<p v-if="ocrFilled.length" class="text-xs text-green-700/80 -mt-1">
						Please check each value below and correct it if needed before submitting.
					</p>
					<div v-for="mf in metaFields" :key="mf.name" class="flex flex-col gap-1">
						<div class="flex items-center justify-between">
							<label :for="'f-' + mf.name" class="text-xs font-medium text-gray-600">{{ mf.label }}</label>
							<span v-if="scannedFieldNames.includes(mf.name)"
								class="inline-flex items-center gap-1 text-[10px] font-medium text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full">
								<FeatherIcon name="check" class="w-2.5 h-2.5" /> Scanned
							</span>
						</div>
						<textarea v-if="mf.type === 'textarea'" :id="'f-' + mf.name" v-model="formData[mf.name]" rows="2"
							:disabled="!canUpload"
							class="w-full px-3 py-2 text-sm border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#a61d1d]/30 resize-none disabled:opacity-60"
							:class="scannedFieldNames.includes(mf.name) ? 'border-green-300' : 'border-gray-200'" />
						<input v-else :id="'f-' + mf.name" :type="mf.type" v-model="formData[mf.name]"
							:disabled="!canUpload"
							class="w-full px-3 py-2 text-sm border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#a61d1d]/30 disabled:opacity-60"
							:class="scannedFieldNames.includes(mf.name) ? 'border-green-300' : 'border-gray-200'"
							:placeholder="mf.label" />
					</div>
				</div>

				<!-- Confirmation before submit -->
				<label v-if="stagedFile && metaFields.length && canUpload"
					class="flex items-start gap-3 px-3 py-3 rounded-xl border border-gray-200 bg-white cursor-pointer">
					<input type="checkbox" v-model="confirmed"
						class="mt-0.5 w-4 h-4 accent-[#a61d1d] shrink-0" />
					<span class="text-sm text-gray-700">I have reviewed the details above and confirm they are correct.</span>
				</label>

				<!-- Error -->
				<div v-if="errorMsg" class="flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
					<FeatherIcon name="alert-circle" class="w-4 h-4 shrink-0" />
					{{ errorMsg }}
				</div>

				<!-- Uploading -->
				<div v-if="uploading" class="flex flex-col items-center gap-2 py-4">
					<div class="w-7 h-7 border-2 border-gray-300 border-t-[#a61d1d] rounded-full animate-spin" />
					<span class="text-xs text-gray-500">Uploading...</span>
				</div>

				<!-- Submit -->
				<button v-else-if="stagedFile && canUpload" @click="submit"
					:disabled="metaFields.length && !confirmed"
					class="w-full py-3.5 rounded-xl text-white text-sm font-semibold transition"
					:class="(metaFields.length && !confirmed) ? 'bg-gray-300 cursor-not-allowed' : 'bg-[#a61d1d] active:scale-95'">
					Submit
				</button>

				<!-- Save Details -->
				<button v-else-if="!stagedFile && docInfo.file_url && metaFields.length && canUpload"
					@click="saveDetails"
					class="w-full py-3.5 rounded-xl bg-gray-800 text-white text-sm font-semibold active:scale-95 transition">
					Save Details
				</button>

			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import DbsFilesForm from '@/components/DbsFilesForm.vue'
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons, IonButton } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"
import { jsPDF } from "jspdf"
import * as pdfjsLib from "pdfjs-dist"
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url"

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const route = useRoute()
const router = useRouter()
const fieldName = route.params.field

const loading = ref(true)
const docInfo = ref({})
const metaFields = ref([])
const formData = ref({})
const stagedFile = ref(null)
const scanning = ref(false)
const ocrError = ref(null)
const ocrFilled = ref([])
const uploading = ref(false)
const errorMsg = ref(null)
const confirmed = ref(false)
const processing = ref(false)

const galleryInput = ref(null)
const cameraVideo = ref(null)
const cameraOpen = ref(false)
const cameraStream = ref(null)
const cameraStarting = ref(false)
const cameraReady = ref(false)
const cameraError = ref(null)

const scannedFieldNames = computed(() => ocrFilled.value.map((f) => f.name))

// A document can only be (re)uploaded when it has never been uploaded,
// was rejected, or is expiring soon / expired. Once it is uploaded and valid
// or currently under review, it is locked.
const canUpload = computed(() => {
	const s = docInfo.value.status
	return !s || ["missing", "rejected", "expired", "expiring_soon"].includes(s)
})

const lockedReason = computed(() => {
	const s = docInfo.value.status
	if (s === "under_review") return "This document is under review and cannot be changed until our team has reviewed it."
	if (s === "uploaded") return "This document is valid and approved. It can only be updated if it is rejected or close to expiry."
	return ""
})

function goBack() {
	window.location.assign("/associate/documents")
}

function triggerGallery() { galleryInput.value?.click() }

function chooseFileInstead() {
	closeCameraScanner()
	nextTick(() => triggerGallery())
}

function requestNativeCameraPermission() {
	if (!window.__OM_NATIVE_APP || !window.FlutterBridge?.postMessage) {
		return Promise.resolve(true)
	}

	return new Promise((resolve) => {
		const id = `camera-${Date.now()}-${Math.random().toString(36).slice(2)}`
		const timeout = setTimeout(() => {
			window.removeEventListener("OM_NATIVE_PERMISSION_RESULT", onResult)
			resolve(true)
		}, 12000)

		function onResult(event) {
			const detail = event.detail || {}
			if (detail.id !== id || detail.action !== "REQUEST_CAMERA_PERMISSION") return
			clearTimeout(timeout)
			window.removeEventListener("OM_NATIVE_PERMISSION_RESULT", onResult)
			resolve(Boolean(detail.granted))
		}

		window.addEventListener("OM_NATIVE_PERMISSION_RESULT", onResult)
		try {
			window.FlutterBridge.postMessage(JSON.stringify({
				action: "REQUEST_CAMERA_PERMISSION",
				id,
			}))
		} catch {
			clearTimeout(timeout)
			window.removeEventListener("OM_NATIVE_PERMISSION_RESULT", onResult)
			resolve(true)
		}
	})
}

onMounted(async () => {
	try {
		const csrfToken = window.csrf_token || window.frappe?.csrf_token || ""
		const resp = await fetch(
			"/api/method/onemotion.api.associate_portal.get_associate_documents",
			{ headers: { "X-Frappe-CSRF-Token": csrfToken } }
		)
		if (!resp.ok) throw new Error("HTTP " + resp.status)
		const data = await resp.json()
		const msg = data?.message
		const groups = Array.isArray(msg) ? msg : (msg?.groups || [])
		let found = null
		for (const g of groups) {
			for (const d of (g.documents || [])) {
				if (d.field === fieldName) { found = d; break }
			}
			if (found) break
		}
		if (found) {
			docInfo.value = found
			metaFields.value = found.metadata_fields || []
			formData.value = { ...(found.metadata || {}) }
		} else {
			errorMsg.value = "Document not found: " + fieldName
		}
	} catch (e) {
		errorMsg.value = "Failed to load: " + e.message
	} finally {
		loading.value = false
	}

})

onBeforeUnmount(() => {
	stopCameraStream()
})

function clearFile() {
	stagedFile.value = null
	ocrFilled.value = []
	ocrError.value = null
	confirmed.value = false
}

async function openCameraScanner() {
	errorMsg.value = null
	ocrError.value = null
	cameraError.value = null
	cameraReady.value = false

	if (!navigator.mediaDevices?.getUserMedia) {
		cameraOpen.value = true
		cameraError.value = "Camera access is not available in this browser. Please choose a file or photo from your device."
		return
	}

	try {
		cameraOpen.value = true
		cameraStarting.value = true
		await nextTick()
		const video = cameraVideo.value
		if (!video) throw new Error("Camera preview is not ready. Please try again.")

		const nativePermissionGranted = await requestNativeCameraPermission()
		if (!nativePermissionGranted) {
			throw new Error("Camera permission is not enabled for the One Motion app. Please enable it in device settings and try again.")
		}

		let stream
		try {
			stream = await navigator.mediaDevices.getUserMedia({
				video: {
					facingMode: { ideal: "environment" },
					width: { ideal: 1600 },
					height: { ideal: 2200 },
				},
				audio: false,
			})
		} catch {
			stream = await navigator.mediaDevices.getUserMedia({
				video: true,
				audio: false,
			})
		}
		cameraStream.value = stream
		video.srcObject = stream
		await new Promise((resolve) => {
			if (video.readyState >= 2 && video.videoWidth) {
				resolve()
				return
			}
			const done = () => resolve()
			video.onloadedmetadata = done
			video.oncanplay = done
			setTimeout(done, 1500)
		})
		try {
			await video.play()
		} catch (playError) {
			console.warn("Camera preview play warning", playError)
		}
		cameraReady.value = true
	} catch (e) {
		stopCameraStream()
		cameraError.value = friendlyCameraError(e)
	} finally {
		cameraStarting.value = false
	}
}

function stopCameraStream() {
	if (cameraStream.value) {
		for (const track of cameraStream.value.getTracks()) {
			track.stop()
		}
	}
	cameraStream.value = null
	cameraReady.value = false
	if (cameraVideo.value) {
		cameraVideo.value.onloadedmetadata = null
		cameraVideo.value.oncanplay = null
		cameraVideo.value.srcObject = null
	}
}

function closeCameraScanner() {
	cameraOpen.value = false
	cameraStarting.value = false
	cameraError.value = null
	stopCameraStream()
}

function friendlyCameraError(error) {
	const name = error?.name || ""
	const message = error?.message || ""
	if (name === "NotAllowedError" || name === "PermissionDeniedError") {
		return "Camera permission was denied. Please allow camera access in device settings and try again."
	}
	if (name === "NotFoundError" || name === "DevicesNotFoundError") {
		return "No camera was found on this device."
	}
	if (name === "NotReadableError" || name === "TrackStartError") {
		return "The camera is already in use by another app. Close other camera apps and try again."
	}
	if (name === "OverconstrainedError" || name === "ConstraintNotSatisfiedError") {
		return "The requested camera mode is not supported on this device."
	}
	return message || "Please try again or choose an existing file/photo."
}

async function captureCameraPhoto() {
	const video = cameraVideo.value
	if (!video || !video.videoWidth || !video.videoHeight) {
		errorMsg.value = "Camera is not ready yet. Please try again."
		return
	}

	const canvas = document.createElement("canvas")
	canvas.width = video.videoWidth
	canvas.height = video.videoHeight
	const ctx = canvas.getContext("2d")
	ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
	const dataUrl = canvas.toDataURL("image/jpeg", 0.86)
	closeCameraScanner()

	const file = dataUrlToFile(dataUrl, `${fieldName || "document"}-scan.jpg`)
	await prepareSelectedFile(file)
}

function dataUrlToFile(dataUrl, filename) {
	const [header, payload] = dataUrl.split(",")
	const mime = header.match(/data:(.*?);/)?.[1] || "image/jpeg"
	const binary = atob(payload)
	const bytes = new Uint8Array(binary.length)
	for (let i = 0; i < binary.length; i++) {
		bytes[i] = binary.charCodeAt(i)
	}
	return new File([bytes], filename, { type: mime })
}

async function handleFile(event) {
	const file = event.target.files?.[0]
	event.target.value = ""
	if (!file) return
	await prepareSelectedFile(file)
}

async function prepareSelectedFile(file) {
	const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
	const isImage = file.type?.startsWith("image/") || /\.(png|jpe?g|webp|heic|heif)$/i.test(file.name || "")
	if (!isPdf && !isImage) {
		stagedFile.value = null
		errorMsg.value = "Only PDF or image files are accepted. Please scan/take a photo or upload a PDF."
		return
	}

	errorMsg.value = null
	ocrError.value = null
	ocrFilled.value = []
	confirmed.value = false
	processing.value = true

	let finalFile = file
	try {
		if (isPdf) {
			const { pdfFile } = await compressPdf(file)
			finalFile = pdfFile
		} else {
			finalFile = await imageToPdf(file)
		}
	} catch (e) {
		if (isPdf) {
			// Could not render/compress — keep the original PDF
			finalFile = file
			if (file.size > 9 * 1024 * 1024) {
				errorMsg.value = "This PDF is large. Upload may be slow; a smaller file is recommended."
			}
		} else {
			stagedFile.value = null
			processing.value = false
			errorMsg.value = "Could not prepare the photo. Please try again or choose a PDF."
			return
		}
	}
	processing.value = false
	stagedFile.value = finalFile

	// Run OCR on the ORIGINAL (uncompressed) file for best quality.
	// The backend reads PDFs directly server-side.
	if (metaFields.value.length) {
		try {
			const pdfBase64 = await fileToBase64(file)
			runOCR(pdfBase64)
		} catch (e) {
		ocrError.value = "Could not read automatically. Fill fields manually."
	}
}
}

function loadImageFromFile(file) {
	return new Promise((resolve, reject) => {
		const url = URL.createObjectURL(file)
		const img = new Image()
		img.onload = () => {
			URL.revokeObjectURL(url)
			resolve(img)
		}
		img.onerror = () => {
			URL.revokeObjectURL(url)
			reject(new Error("Could not read image"))
		}
		img.src = url
	})
}

async function imageToPdf(file) {
	const img = await loadImageFromFile(file)
	const maxDim = 1800
	const scale = Math.min(1, maxDim / Math.max(img.naturalWidth, img.naturalHeight))
	const width = Math.max(1, Math.round(img.naturalWidth * scale))
	const height = Math.max(1, Math.round(img.naturalHeight * scale))
	const canvas = document.createElement("canvas")
	canvas.width = width
	canvas.height = height
	const ctx = canvas.getContext("2d")
	ctx.fillStyle = "#ffffff"
	ctx.fillRect(0, 0, width, height)
	ctx.drawImage(img, 0, 0, width, height)

	const jpeg = canvas.toDataURL("image/jpeg", 0.82)
	const orientation = width > height ? "landscape" : "portrait"
	const pdf = new jsPDF({ unit: "pt", format: [width, height], orientation, compress: true })
	pdf.addImage(jpeg, "JPEG", 0, 0, width, height)
	const blob = pdf.output("blob")
	const baseName = (file.name || docInfo.value.label || "scanned-document").replace(/\.[^.]+$/, "")
	return new File([blob], baseName + ".pdf", { type: "application/pdf" })
}

function fileToBase64(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onload = () => resolve(reader.result)
		reader.onerror = reject
		reader.readAsDataURL(file)
	})
}

async function compressPdf(file) {
	const buf = await file.arrayBuffer()
	const pdf = await pdfjsLib.getDocument({ data: buf }).promise
	const maxPages = Math.min(pdf.numPages, 15)
	let out = null
	let firstPageImage = null

	for (let i = 1; i <= maxPages; i++) {
		const page = await pdf.getPage(i)
		const base = page.getViewport({ scale: 1 })
		const maxDim = Math.max(base.width, base.height)
		const scale = Math.min(2, 1600 / maxDim)
		const viewport = page.getViewport({ scale })
		const canvas = document.createElement("canvas")
		canvas.width = Math.floor(viewport.width)
		canvas.height = Math.floor(viewport.height)
		const ctx = canvas.getContext("2d")
		await page.render({ canvasContext: ctx, viewport }).promise
		const jpeg = canvas.toDataURL("image/jpeg", 0.7)
		if (i === 1) firstPageImage = jpeg

		const w = canvas.width
		const h = canvas.height
		const orientation = w > h ? "landscape" : "portrait"
		if (!out) {
			out = new jsPDF({ unit: "pt", format: [w, h], orientation, compress: true })
		} else {
			out.addPage([w, h], orientation)
		}
		out.addImage(jpeg, "JPEG", 0, 0, w, h)
	}

	const blob = out.output("blob")
	const baseName = (file.name || "document").replace(/\.[^.]+$/, "")
	const pdfFile = new File([blob], baseName + ".pdf", { type: "application/pdf" })
	return { pdfFile, firstPageImage }
}

async function runOCR(fileBase64) {
	scanning.value = true
	ocrError.value = null
	ocrFilled.value = []
	try {
		const csrfToken = window.csrf_token || window.frappe?.csrf_token || ""
		const resp = await fetch(
			"/api/method/onemotion.api.associate_portal.scan_document_fields",
			{
				method: "POST",
				headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": csrfToken },
				body: JSON.stringify({ field_name: fieldName, image_base64: fileBase64 }),
			}
		)
		if (!resp.ok) { ocrError.value = "HTTP " + resp.status; return }
		const data = await resp.json()
		const extracted = data?.message || {}
		const filledList = []
		for (const [k, v] of Object.entries(extracted)) {
			if (v !== null && v !== undefined && v !== "") {
				formData.value[k] = v
				const mf = metaFields.value.find((m) => m.name === k)
				filledList.push({ name: k, label: mf ? mf.label : k, value: v })
			}
		}
		ocrFilled.value = filledList
		if (!filledList.length) ocrError.value = "No data extracted"
	} catch (e) {
		ocrError.value = e.message
	} finally {
		scanning.value = false
	}
}

async function submit() {
	if (!stagedFile.value) return
	if (stagedFile.value.size > 10 * 1024 * 1024) { errorMsg.value = "File too large (max 10MB)"; return }
	uploading.value = true
	errorMsg.value = null
	try {
		const csrfToken = window.csrf_token || window.frappe?.csrf_token || ""

		const fd = new FormData()
		fd.append("file", stagedFile.value)
		fd.append("is_private", "0")
		const uploadResp = await fetch("/api/method/upload_file", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": csrfToken },
			body: fd,
		})
		if (!uploadResp.ok) {
			let detail = "HTTP " + uploadResp.status
			try {
				const e = await uploadResp.json()
				const msgs = e?._server_messages
				if (msgs) { const i = JSON.parse(JSON.parse(msgs)[0]); detail = i?.message || i?.title || detail }
				else if (e?.exc_type) detail = e.exc_type
			} catch {}
			throw new Error("Upload failed: " + detail)
		}
		const fileUrl = (await uploadResp.json())?.message?.file_url
		if (!fileUrl) throw new Error("No file URL returned")

		const saveResp = await fetch(
			"/api/method/onemotion.api.associate_portal.update_associate_document",
			{
				method: "POST",
				headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": csrfToken },
				body: JSON.stringify({ field_name: fieldName, file_url: fileUrl, metadata: formData.value }),
			}
		)
		if (!saveResp.ok) {
			const e = await saveResp.json().catch(() => ({}))
			const msgs = e?._server_messages
			let errMsg = "Failed to save"
			if (msgs) { try { const i = JSON.parse(JSON.parse(msgs)[0]); errMsg = i?.message || i?.title || errMsg } catch {} }
			throw new Error(errMsg)
		}
		goBack()
	} catch (err) {
		errorMsg.value = err.message || "Upload failed"
	} finally {
		uploading.value = false
	}
}

async function saveDetails() {
	if (!docInfo.value.file_url) return
	uploading.value = true
	errorMsg.value = null
	try {
		const csrfToken = window.csrf_token || window.frappe?.csrf_token || ""
		const resp = await fetch(
			"/api/method/onemotion.api.associate_portal.update_associate_document",
			{
				method: "POST",
				headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": csrfToken },
				body: JSON.stringify({ field_name: fieldName, file_url: docInfo.value.file_url, metadata: formData.value }),
			}
		)
		if (!resp.ok) {
			const e = await resp.json().catch(() => ({}))
			const msgs = e?._server_messages
			let errMsg = "Failed to save"
			if (msgs) { try { const i = JSON.parse(JSON.parse(msgs)[0]); errMsg = i?.message || i?.title || errMsg } catch {} }
			throw new Error(errMsg)
		}
		goBack()
	} catch (err) {
		errorMsg.value = err.message || "Failed to save"
	} finally {
		uploading.value = false
	}
}

function statusLabel(s) {
	const m = { uploaded: "Uploaded", missing: "Missing", expired: "Expired", expiring_soon: "Expiring Soon", under_review: "Under Review", rejected: "Rejected", approved: "Approved" }
	return m[s] || s
}
function statusBadgeClass(s) {
	const m = { uploaded: "bg-green-100 text-green-800", approved: "bg-green-100 text-green-800", missing: "bg-red-100 text-red-800", rejected: "bg-red-100 text-red-800", expired: "bg-orange-100 text-orange-800", expiring_soon: "bg-orange-100 text-orange-800", under_review: "bg-blue-100 text-blue-800" }
	return m[s] || "bg-gray-100 text-gray-800"
}
</script>

<style scoped>
.camera-preview::-webkit-media-controls,
.camera-preview::-webkit-media-controls-panel,
.camera-preview::-webkit-media-controls-play-button,
.camera-preview::-webkit-media-controls-start-playback-button,
.camera-preview::-webkit-media-controls-overlay-play-button {
	display: none !important;
	-webkit-appearance: none;
	appearance: none;
	opacity: 0 !important;
	pointer-events: none !important;
}
</style>
