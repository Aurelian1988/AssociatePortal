/**
 * Post-build script: copies the Vite-built index.html to www/associate.html
 * and replaces dev placeholders with Jinja template variables for Frappe.
 */
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const src = path.resolve(__dirname, "../../onemotion/public/associate_portal/index.html")
const dest = path.resolve(__dirname, "../../onemotion/www/associate.html")

let html = fs.readFileSync(src, "utf-8")

// Replace the dev-safe <script> block with Jinja-powered one
const devScript = /<!--\s*boot-script-start\s*-->[\s\S]*?<!--\s*boot-script-end\s*-->/
const jinjaScript = `<script>
			window.csrf_token = "{{ csrf_token }}"
			window.site_name = "{{ site_name }}"
			if (!window.frappe) window.frappe = {}
			frappe.boot = {{ boot }}
		</script>`

if (devScript.test(html)) {
	html = html.replace(devScript, jinjaScript)
} else {
	// Fallback: replace the placeholder values directly
	html = html.replace(
		/window\.csrf_token\s*=\s*window\.csrf_token\s*\|\|\s*"dev"/,
		'window.csrf_token = "{{ csrf_token }}"'
	)
	html = html.replace(
		/window\.site_name\s*=\s*window\.site_name\s*\|\|\s*"localhost"/,
		'window.site_name = "{{ site_name }}"'
	)
	html = html.replace(
		/if\s*\(!window\.frappe\)\s*window\.frappe\s*=\s*\{\}\s*\n\s*if\s*\(!frappe\.boot\)\s*frappe\.boot\s*=\s*\{\}/,
		'if (!window.frappe) window.frappe = {}\n\t\t\tfrappe.boot = {{ boot }}'
	)
}

fs.writeFileSync(dest, html, "utf-8")
console.log(`✅ Injected Jinja variables into ${dest}`)
