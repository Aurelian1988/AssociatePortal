import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"
import path from "path"
import fs from "fs"

export default defineConfig({
	base: "/assets/onemotion/associate_portal/",
	server: {
		port: 8081,
		proxy: getProxyOptions(),
		allowedHosts: true,
	},
	plugins: [vue(), frappeui()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "../onemotion/public/associate_portal",
		emptyOutDir: true,
		target: "es2015",
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		sourcemap: true,
		rollupOptions: {
			output: {
				manualChunks: {
					"frappe-ui": ["frappe-ui"],
				},
			},
		},
	},
	optimizeDeps: {
		include: [
			"frappe-ui > feather-icons",
			"showdown",
			"tailwind.config.js",
			"engine.io-client",
		],
	},
})

function getProxyOptions() {
	return {
		"^/(app|login|api|files|private)": {
			target: "https://erp.onemotion.uk",
			changeOrigin: true,
			ws: true,
		},
		"^/assets/(?!onemotion/associate_portal/)": {
			target: "https://erp.onemotion.uk",
			changeOrigin: true,
		},
	}
}
