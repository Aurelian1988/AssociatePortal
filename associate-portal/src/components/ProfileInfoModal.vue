<template>
	<div class="flex flex-col gap-3 p-4">
		<div
			v-for="item in data"
			:key="item.fieldname"
		class="flex flex-row justify-between py-2 border-b border-gray-200"
		>
			<span class="text-sm text-gray-500">{{ item.label }}</span>
			<span class="text-sm font-medium text-gray-900 text-right max-w-[60%] truncate">
				{{ formatValue(item.value, item.fieldtype) }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { inject } from "vue"

const dayjs = inject("$dayjs")

const props = defineProps({
	title: String,
	data: Array,
})

function formatValue(value, fieldtype) {
	if (!value) return "—"
	if (fieldtype === "Date") {
		return dayjs(value).format("DD MMM YYYY")
	}
	if (fieldtype === "Check") {
		return value ? "Yes" : "No"
	}
	return value
}
</script>
