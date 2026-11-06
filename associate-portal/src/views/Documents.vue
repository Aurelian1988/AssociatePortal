<template><BaseLayout><template #body><FilesNavigation/><main class="documents"><h1>Documents</h1><p v-if="documents.loading">Loading documents…</p><template v-else><section v-for="group in documentGroups" :key="group.category"><button class="folder" :aria-expanded="opened[group.category]!==false" @click="opened[group.category]=opened[group.category]===false">{{ opened[group.category]===false?'▸':'▾' }} {{ group.category }}</button><template v-if="opened[group.category]!==false"><article v-for="doc in group.documents" :key="doc.field"><div><span class="name">{{ doc.label }}</span><small :class="'status-'+doc.status">{{ doc.status_label || String(doc.status||'').replaceAll('_',' ') }}<template v-if="doc.expiry_date"> · Expires {{ doc.expiry_date }}</template></small></div><button v-if="doc.file_url" class="view" :class="documentButtonClass(doc)" @click="preview=doc">View</button><button v-else-if="doc.can_upload" class="view" :class="documentButtonClass(doc)" @click="openUploadPage(doc)">Upload</button></article></template></section><p v-if="!documentGroups.length">No documents found.</p></template><FilePreview v-if="preview" :doc="preview" @close="preview=null"/></main></template></BaseLayout></template>
<script setup>
import FilePreview from '@/components/FilePreview.vue'
import FilesNavigation from '@/components/FilesNavigation.vue'
import { inject, computed, ref } from "vue"
import { onIonViewDidEnter } from "@ionic/vue"
import { createResource, FeatherIcon } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"
import DocumentCard from "@/components/DocumentCard.vue"

const preview=ref(null),opened=ref({}),dbsVisible=ref(false)
fetch("/api/method/onemotion.api.profile_dbs_portal.status").then(r=>r.json()).then(r=>{dbsVisible.value=!!r.message?.visible}).catch(()=>{})
const __ = inject("$translate")

const documents = createResource({
	url: "onemotion.api.associate_portal.get_associate_documents",
	cache: "associate-portal:documents",
	auto: true,
})

onIonViewDidEnter(() => { documents.reload() })

const documentGroups = computed(() => {
	if (!documents.data) return []
	const groups=Array.isArray(documents.data)?documents.data:documents.data.groups||[]
 return groups.map(group=>({...group,category:group.category==='Tax & Finance'?'Finance':group.category,documents:(group.documents||[]).filter(doc=>(doc.field!=='crb_report_document'||dbsVisible.value) && !['eu_licence_declaration','dld_agrement','immigration_share_code_doc','rtw_share_code_file','nino_file','utr_file','vat_certificate'].includes(doc.field) && String(doc.status||'').toLowerCase().replace(/[_-]/g,' ').trim()!=='not required')})).filter(group=>group.documents.length)
})

function documentButtonClass(doc) {
 const status=String(doc.status||'').toLowerCase().replace(/[\s-]+/g,'_')
 if (status==='missing') return 'view-missing'
 if (['under_review','review','in_review'].includes(status)) return 'view-review'
 return ''
}

function getDocIcon(category) {
	const icons = {
		"Identity": "user",
		"Driving Licence": "credit-card",
		"Tax & Finance": "dollar-sign",
		"Address": "map-pin",
		"Immigration": "globe",
		"Other": "file",
	}
	return icons[category] || "file"
}

function openUploadPage(doc) {
	// Use a full-page navigation so the browser always loads the latest JS
	// (avoids stale-SW-cache issues where router.push silently fails)
	window.location.assign("/associate/document-upload/" + doc.field)
}

function openScanPage(doc) {
	window.location.assign("/associate/document-upload/" + doc.field)
}

function canScan(doc) {
	return ["missing", "rejected", "expired", "expiring_soon"].includes(doc.status)
}
</script>

<style scoped>.documents{padding:.5rem .35rem 6rem;color:#17202b}.documents h1{font-size:1.4rem;font-weight:650}.documents p{font-size:.85rem}.folder{width:100%;text-align:left;margin-top:.65rem;padding:.6rem .8rem;background:#edf1f5;color:#17202b;border:1px solid #dfe5ec;border-radius:8px;font-weight:600;min-height:52px}article{display:flex;align-items:center;justify-content:space-between;padding:.5rem .75rem;margin:.4rem 0;gap:.75rem;background:white;border:1px solid #e3e8ee;border-radius:12px}.name{font-size:.9rem;font-weight:400}small{display:block;font-size:.75rem;color:#687586;margin-top:.3rem}.view{flex-shrink:0;min-height:40px;padding:.4rem .8rem;background:#edf1f5;color:#a61d1d;border:1px solid #dfe5ec;border-radius:8px;font-size:.8rem}.view-missing{background:#b91c1c;color:#fff;border-color:#b91c1c}.view-review{background:#075da8;color:#fff;border-color:#075da8}.status-missing,.status-rejected,.status-unsigned{color:#b91c1c}.status-pending,.status-expired,.status-expiring_soon{color:#b45309}.status-under_review{color:#075da8}.status-approved,.status-uploaded,.status-signed,.status-completed{color:#166534}</style>
