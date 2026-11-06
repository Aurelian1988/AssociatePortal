<template>
	<div
		class="flex flex-row items-center justify-between p-3 bg-white rounded-lg border"
		@click="$emit('click')"
	>
		<div class="flex flex-row items-center gap-3 flex-1 min-w-0">
			<div
				class="flex items-center justify-center w-10 h-10 rounded-lg"
				:class="statusBgClass"
			>
				<FeatherIcon :name="icon" class="w-5 h-5" :class="statusIconClass" />
			</div>
			<div class="flex flex-col min-w-0">
				<span class="text-sm font-medium text-gray-900 truncate">{{ title }}</span>
				<span v-if="subtitle" class="text-xs text-gray-500 truncate">{{ subtitle }}</span>
			</div>
		</div>
		<div class="flex items-center gap-2 ml-2">
			<span
				class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
				:class="badgeClass"
			>
				{{ statusLabel }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: String,
	subtitle: String,
	icon: { type: String, default: "file" },
	status: { type: String, default: "missing" }, // uploaded, missing, expired, signed, unsigned
})

defineEmits(["click"])

const statusLabel = computed(() => {
	const labels = {
		uploaded: "Uploaded",
		missing: "Missing",
		expired: "Expired",
		signed: "Signed",
		unsigned: "Not Signed",
		approved: "Approved",
		pending: "Pending",
		under_review: "Under Review",
		rejected: "Rejected",
		expiring_soon: "Expiring Soon",
	}
	return labels[props.status] || props.status
})

const badgeClass = computed(() => {
	const classes = {
		uploaded: "bg-green-100 text-green-800",
		signed: "bg-green-100 text-green-800",
		approved: "bg-green-100 text-green-800",
		missing: "bg-red-100 text-red-800",
		unsigned: "bg-red-100 text-red-800",
		expired: "bg-orange-100 text-orange-800",
		expiring_soon: "bg-orange-100 text-orange-800",
		pending: "bg-yellow-100 text-yellow-800",
		under_review: "bg-blue-100 text-blue-800",
		rejected: "bg-red-100 text-red-800",
	}
	return classes[props.status] || "bg-gray-100 text-gray-800"
})

const statusBgClass = computed(() => {
	const classes = {
		uploaded: "bg-green-50",
		signed: "bg-green-50",
		approved: "bg-green-50",
		missing: "bg-red-50",
		unsigned: "bg-red-50",
		expired: "bg-orange-50",
		expiring_soon: "bg-orange-50",
		pending: "bg-yellow-50",
		under_review: "bg-blue-50",
		rejected: "bg-red-50",
	}
	return classes[props.status] || "bg-gray-50"
})

const statusIconClass = computed(() => {
	const classes = {
		uploaded: "text-green-600",
		signed: "text-green-600",
		approved: "text-green-600",
		missing: "text-red-500",
		unsigned: "text-red-500",
		expired: "text-orange-500",
		expiring_soon: "text-orange-500",
		pending: "text-yellow-500",
		under_review: "text-blue-500",
		rejected: "text-red-500",
	}
	return classes[props.status] || "text-gray-500"
})

</script>
