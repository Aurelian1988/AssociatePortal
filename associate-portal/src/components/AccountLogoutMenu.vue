<template><div class="account-menu" @keydown.esc="open=false"><button type="button" class="avatar" aria-label="Account menu" :aria-expanded="open" @click="open=!open"><img v-if="onboarding.profile?.values?.id_photo" :src="onboarding.profile.values.id_photo" alt="Your profile"><span v-else>{{ (onboarding.profile?.values?.first_name||'A').slice(0,1) }}</span></button><div v-if="open" class="menu"><button type="button" @click="logout">Log out</button></div></div></template>
<script setup>
import {ref} from 'vue'
import {session} from '@/data/session'
import {onboarding} from '@/data/onboarding'
const open=ref(false)
function logout(){sessionStorage.removeItem('sdt-test-contact-name');session.logout.submit()}
</script>
<style scoped>.account-menu{position:relative}.avatar{width:44px;height:44px;border-radius:50%;overflow:hidden;background:#edf1f5;color:#17202b;border:0}.avatar img{width:100%;height:100%;object-fit:cover}.menu{position:absolute;right:0;top:100%;min-width:140px;padding:8px;background:white;border:1px solid #dfe5ec;border-radius:12px;box-shadow:0 4px 12px #0002;z-index:100}.menu button{width:100%;padding:12px;border:0;background:white;color:#a61d1d;text-align:left}</style>
