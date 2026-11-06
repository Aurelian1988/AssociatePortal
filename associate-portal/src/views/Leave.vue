<template>
	<BaseLayout :pageTitle="isOffboarding ? 'Notice / Offboarding' : 'Leave & Holiday'">
		<template #body><router-link to="/tools" class="leave-back">‹ Back to Tools</router-link>
			<div class="flex flex-col p-4 gap-4">

				<p class="text-sm text-gray-600">{{ isOffboarding ? 'Let the team know that you plan to leave One Motion. Tell us when your notice starts and your proposed last working day.' : 'Planning some time away? Enter your first and last day of leave. Your upcoming holidays are listed below—tap the pencil to change the dates.' }}</p>
                <!-- ── New request card ───────────────────────────────────────── -->
				<div class="bg-white rounded-xl shadow-sm overflow-hidden">
					<button
						class="w-full flex items-center justify-between p-4 active:bg-gray-50 transition"
						@click="showForm = !showForm"
					>
						<span class="flex items-center gap-2 text-sm font-semibold text-gray-900">
							<FeatherIcon name="plus-circle" class="w-4 h-4 text-[#a61d1d]" />
							{{ __("New Request") }}
						</span>
						<FeatherIcon
							:name="showForm ? 'chevron-up' : 'chevron-down'"
							class="w-4 h-4 text-gray-400"
						/>
					</button>

					<transition
						enter-active-class="transition duration-150"
						enter-from-class="opacity-0 -translate-y-1"
						enter-to-class="opacity-100 translate-y-0"
						leave-active-class="transition duration-100"
						leave-from-class="opacity-100 translate-y-0"
						leave-to-class="opacity-0 -translate-y-1"
					>
						<div v-if="showForm" class="px-4 pb-5 flex flex-col gap-4 border-t border-gray-100">
							<!-- Date fields -->
							<div class="flex flex-col gap-3">
								<div>
									<label class="block text-xs font-medium text-gray-500 mb-1">
										{{ form.lv_type === 'Notice' ? __("Notice Period Start") : __("Start Date") }}
									</label>
									<input
										type="date"
										v-model="form.leave_date_start"
										class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#a61d1d]"
									/>
								</div>
								<div>
									<label class="block text-xs font-medium text-gray-500 mb-1">
										{{ form.lv_type === 'Notice' ? __("Last Working Day") : __("End Date") }}
									</label>
									<input
										type="date"
										v-model="form.leave_date_end"
										class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#a61d1d]"
									/>
								</div>
							</div>

							<div v-if="isOffboarding">
 <label for="notice-reason" class="block text-sm font-semibold mb-2">Why are you leaving One Motion?</label>
 <p class="text-sm text-gray-600 mb-2">Please tell us in your own words. This helps the team understand your decision and arrange your offboarding.</p>
 <textarea id="notice-reason" v-model="form.notice_reason" rows="5" minlength="100" required aria-describedby="reason-count" class="w-full rounded-lg border border-gray-300 p-3 text-base" placeholder="Tell us why you’ve decided to leave…"></textarea>
 <p id="reason-count" class="text-sm text-gray-600">{{ form.notice_reason.trim().length }} characters · Minimum 100</p>
 </div>
 <!-- Error -->
							<p v-if="submitError" class="text-xs text-red-500">{{ submitError }}</p>

							<button
								:disabled="submitting"
								class="w-full py-2.5 rounded-lg bg-[#a61d1d] text-white text-sm font-semibold transition active:scale-95 disabled:opacity-60"
								@click="submitRequest"
							>
								{{ submitting ? __("Submitting…") : __("Submit Request") }}
							</button>
						</div>
					</transition>
				</div>

				<p v-if="usingSamples" class="p-3 bg-yellow-100 text-sm rounded-lg">SAMPLE PREVIEW — fictional notices for testing. Changes stay on this device and are not sent to ERP.</p><h2 class="text-base font-semibold">{{ isOffboarding ? 'Notice requests' : 'Upcoming holidays' }}</h2>
                <p v-if="leaveRecords.error" role="alert" class="text-sm text-red-600">Could not load your requests. Please try again.</p>
                <!-- ── Loading ────────────────────────────────────────────────── -->
				<div v-if="leaveRecords.loading" class="text-center py-10 text-gray-400 text-sm">
					{{ __("Loading…") }}
				</div>

				<!-- ── Empty state ────────────────────────────────────────────── -->
				<div
					v-else-if="!leaveRecords.loading && !visibleRecords.length"
					class="text-center py-10 text-gray-400 text-sm"
				>
					{{ isOffboarding ? 'No notice requests.' : 'No upcoming holidays scheduled.' }}
				</div>

				<!-- Upcoming records from the associate's LHS child table. -->
                <div v-if="!leaveRecords.loading && visibleRecords.length" class="overflow-x-auto bg-white rounded-xl border border-gray-200">
                  <table class="w-full text-sm"><thead><tr class="text-left text-gray-500 border-b"><th class="p-3">{{ isOffboarding ? 'Notice starts' : 'From' }}</th><th class="p-3">{{ isOffboarding ? 'Last working day' : 'To' }}</th><th class="p-3">Status</th><th class="p-2"><span class="sr-only">Edit</span></th></tr></thead>
                  <tbody><template v-for="rec in visibleRecords" :key="rec.name">
                    <tr class="border-b"><td class="p-3">{{ formatDate(rec.leave_date_start) }}</td><td class="p-3">{{ formatDate(rec.leave_date_end) }}</td><td class="p-3"><span :class="statusClass(rec.lv_status)" class="rounded px-2 py-1 text-xs">{{ rec.lv_status }}</span></td><td class="p-2"><button v-if="['Review','Active'].includes(rec.lv_status)" type="button" :aria-label="isOffboarding ? 'Edit notice dates' : 'Edit holiday dates'" class="p-3 text-red-700" @click="startEdit(rec)"><FeatherIcon name="edit-2" class="w-4 h-4" /></button><button v-if="isOffboarding && ['Review','Active'].includes(rec.lv_status)" type="button" aria-label="Cancel notice" class="p-3 text-red-700" @click="promptCancel(rec.name)"><FeatherIcon name="x-circle" class="w-4 h-4" /></button></td></tr>
                    <tr v-if="editId===rec.name"><td colspan="4" class="p-3"><div class="flex flex-col gap-3"><label>Start date<input type="date" v-model="editForm.leave_date_start" class="block w-full border rounded-lg p-2" /></label><label>End date<input type="date" v-model="editForm.leave_date_end" class="block w-full border rounded-lg p-2" /></label><p v-if="editError" role="alert" class="text-red-600">{{ editError }}</p><div class="flex gap-3"><button type="button" :disabled="saving" class="p-3 bg-red-800 text-white rounded-lg" @click="saveEdit(rec.name)">{{ saving?'Saving…':'Save changes' }}</button><button type="button" :disabled="saving" class="p-3" @click="cancelEdit">Cancel</button></div></div></td></tr>
                  </template></tbody></table>
                </div>

			</div>

			<!-- ── Cancel confirmation dialog ─────────────────────────────────── -->
			<div
				v-if="confirmCancelId"
				class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-6"
				@click.self="confirmCancelId = null"
			>
				<div class="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl flex flex-col gap-4">
					<h3 class="text-base font-bold text-gray-900">{{ __("Cancel this request?") }}</h3>
					<p class="text-sm text-gray-500">{{ __("This action cannot be undone.") }}</p>
					<p v-if="cancelError" class="text-xs text-red-500">{{ cancelError }}</p>
					<div class="flex gap-3">
						<button
							class="flex-1 py-2.5 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium transition active:scale-95"
							@click="confirmCancelId = null"
						>
							{{ __("Keep it") }}
						</button>
						<button
							:disabled="cancelling"
							class="flex-1 py-2.5 rounded-lg bg-red-600 text-white text-sm font-semibold transition active:scale-95 disabled:opacity-60"
							@click="confirmCancel"
						>
							{{ cancelling ? __("Cancelling…") : __("Yes, cancel") }}
						</button>
					</div>
				</div>
			</div>

		</template>
	</BaseLayout>
</template>

<script setup>
import { ref, inject, watch, computed } from "vue"
import { onIonViewDidEnter } from "@ionic/vue"
import { createResource, FeatherIcon, call } from "frappe-ui"
import {useRoute} from 'vue-router'
import BaseLayout from "@/components/BaseLayout.vue"

const route=useRoute()
const isOffboarding=computed(()=>route.query.type==='Notice')
const sampleKey='preview-notice-examples'
const sampleNotices=ref([])
if(['127.0.0.1','localhost'].includes(location.hostname)){try{sampleNotices.value=JSON.parse(sessionStorage.getItem(sampleKey)||'[]')}catch{}}
const usingSamples=computed(()=>isOffboarding.value&&sampleNotices.value.length>0)
function persistSamples(){sessionStorage.setItem(sampleKey,JSON.stringify(sampleNotices.value))}
const visibleRecords=computed(()=>{
 const now=new Date();const today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-')
 return (usingSamples.value?sampleNotices.value:leaveRecords.data||[]).filter(r=>isOffboarding.value?r.lv_type==='Notice':r.lv_type==='Holiday'&&r.leave_date_start>=today&&!['Cancel','Cancelled','Rejected'].includes(r.lv_status)).sort((a,b)=>isOffboarding.value?(Number(['Review','Active'].includes(b.lv_status))-Number(['Review','Active'].includes(a.lv_status))||String(b.leave_date_start).localeCompare(String(a.leave_date_start))):String(a.leave_date_start).localeCompare(String(b.leave_date_start)))
})
const __ = inject("$translate")

// ── Leave records resource ───────────────────────────────────────────────
const leaveRecords = createResource({
	url: "onemotion.api.associate_portal.get_leave_records",
	cache: false,
	initialData: [],
	auto: true,
})

onIonViewDidEnter(() => {
	leaveRecords.reload()
})

// ── New request form ─────────────────────────────────────────────────────
const showForm = ref(false)
const submitting = ref(false)
const submitError = ref("")

const form = ref({
	lv_type: "Holiday",
 notice_reason: "",
	leave_date_start: "",
	leave_date_end: "",
})

watch(()=>route.query.type,type=>{if(['Holiday','Notice'].includes(type)){form.value.lv_type=type;showForm.value=true}},{immediate:true})

async function submitRequest() {
	submitError.value = ""
	if (!form.value.leave_date_start || !form.value.leave_date_end) {
		submitError.value = __("Please fill in both dates.")
		return
	}
	if (form.value.leave_date_end < form.value.leave_date_start) {
		submitError.value = __("End date must be after start date.")
		return
	}
	if(isOffboarding.value && form.value.notice_reason.trim().length<100){submitError.value='Please explain why you are leaving in at least 100 characters.';return}
 submitting.value = true
	try {
		await call("onemotion.api.associate_portal.submit_leave_request", {
			lv_type: isOffboarding.value?'Notice':'Holiday',
 ...(isOffboarding.value?{notice_reason:form.value.notice_reason.trim()}:{}),
			leave_date_start: form.value.leave_date_start,
			leave_date_end: form.value.leave_date_end,
		})
		form.value.notice_reason = ""
		form.value.leave_date_start = ""
		form.value.leave_date_end = ""
		showForm.value = false
		await leaveRecords.reload()
	} catch (e) {
		submitError.value = e?.message || __("An error occurred. Please try again.")
	} finally {
		submitting.value = false
	}
}

// ── Edit record ──────────────────────────────────────────────────────────
const editId = ref(null)
const editForm = ref({ leave_date_start: "", leave_date_end: "" })
const saving = ref(false)
const editError = ref("")

function startEdit(rec) {
	editId.value = rec.name
	editForm.value = {
		leave_date_start: rec.leave_date_start || "",
		leave_date_end: rec.leave_date_end || "",
	}
	editError.value = ""
}

function cancelEdit() {
	editId.value = null
	editError.value = ""
}

async function saveEdit(name) {
	editError.value = ""
	if (!editForm.value.leave_date_start || !editForm.value.leave_date_end) {
		editError.value = __("Please fill in both dates.")
		return
	}
	if (editForm.value.leave_date_end < editForm.value.leave_date_start) {
		editError.value = __("End date must be after start date.")
		return
	}
    if(usingSamples.value && sampleNotices.value.some(r=>r.name===name)){
      Object.assign(sampleNotices.value.find(r=>r.name===name),editForm.value);persistSamples();editId.value=null;return
    }
	saving.value = true
	try {
		await call("onemotion.api.associate_portal.update_leave_request", {
			lhs_row_name: name,
			leave_date_start: editForm.value.leave_date_start,
			leave_date_end: editForm.value.leave_date_end,
		})
		editId.value = null
		await leaveRecords.reload()
	} catch (e) {
		editError.value = e?.message || __("An error occurred. Please try again.")
	} finally {
		saving.value = false
	}
}

// ── Cancel record ────────────────────────────────────────────────────────
const confirmCancelId = ref(null)
const cancelling = ref(false)
const cancelError = ref("")

function promptCancel(name) {
	confirmCancelId.value = name
	cancelError.value = ""
}

async function confirmCancel() {
    if(usingSamples.value && sampleNotices.value.some(r=>r.name===confirmCancelId.value)){
      sampleNotices.value.find(r=>r.name===confirmCancelId.value).lv_status='Cancel';persistSamples();confirmCancelId.value=null;return
    }
	cancelError.value = ""
	cancelling.value = true
	try {
		await call("onemotion.api.associate_portal.cancel_leave_request", {
			lhs_row_name: confirmCancelId.value,
		})
		confirmCancelId.value = null
		await leaveRecords.reload()
	} catch (e) {
		cancelError.value = e?.message || __("An error occurred. Please try again.")
	} finally {
		cancelling.value = false
	}
}

// ── Helpers ──────────────────────────────────────────────────────────────
function formatDate(d) {
	if (!d) return "—"
	const [y, m, day] = d.split("-")
	return `${day}/${m}/${y}`
}

function statusClass(status) {
	switch (status) {
		case "Review":    return "bg-yellow-100 text-yellow-800"
		case "Active":    return "bg-green-100 text-green-800"
		case "Rejected":  return "bg-red-100 text-red-800"
		case "Cancel":    return "bg-gray-100 text-gray-500"
		default:          return "bg-gray-100 text-gray-600"
	}
}
</script>

<style scoped>.leave-back{display:block;color:#a61d1d;padding:1rem 1rem 0;font-size:.85rem;min-height:44px}</style>
