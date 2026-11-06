import { createRouter, createWebHistory } from "@ionic/vue-router"

import TabbedView from "@/views/TabbedView.vue"

const routes = [
	{
		path: "/",
		redirect: "/home",
	},
	{
		path: "/",
		component: TabbedView,
		children: [
            {path:'/tools',name:'Tools',component:()=>import('@/views/Tools.vue')},
			{
				path: "",
				redirect: "/home",
			},
			{
				path: "/home",
				name: "Home",
				component: () => import("@/views/Home.vue"),
			},
			{
				path: "/documents",
				name: "Documents",
				component: () => import("@/views/Documents.vue"),
			},
			{
				path: "/agreements",
				name: "Agreements",
				component: () => import("@/views/Agreements.vue"),
			},
			{
				path: "/chat",
				name: "Chat",
				component: () => import("@/views/Chat.vue"),
			},
			{
				path: "/leave",
				name: "Leave",
				component: () => import("@/views/Leave.vue"),
			},
		],
	},
	{
		path: "/login",
		name: "Login",
		component: () => import("@/views/Login.vue"),
	},
	{
		path: "/profile",
		name: "Profile",
		component: () => import("@/views/Profile.vue"),
	},
	{
		path: "/notifications",
		name: "Notifications",
		component: () => import("@/views/Notifications.vue"),
	},
	{
		path: "/invalid-associate",
		name: "InvalidAssociate",
		component: () => import("@/views/InvalidAssociate.vue"),
	},
	{
		path: "/document-upload/:field",
		name: "DocumentUpload",
		component: () => import("@/views/DocumentUpload.vue"),
	},
]

const router = createRouter({
	history: createWebHistory("/associate"),
	routes,
})

export default router
