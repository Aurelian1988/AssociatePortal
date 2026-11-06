import re
from onemotion.api.profile_onboarding import require_portal_access, require_onboarding_chat

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, today, get_url


# ─── Helper ───────────────────────────────────────────────────────────────

def _get_associate_name():
	"""Get Associate record linked to the current user's email."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login to access the Associate Portal"), frappe.AuthenticationError)

	associate = frappe.db.get_value(
		"Associate",
		{"email": user},
		"name",
	)
	if not associate:
		# Also check by contact_name or other email fields
		associate = frappe.db.get_value(
			"Associate",
			{"flex_email": user},
			"name",
		)
	return associate


# ─── User Info ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_current_user_info() -> dict:
	"""Return basic info about the logged-in user."""
	current_user = frappe.session.user
	user = frappe.db.get_value(
		"User",
		current_user,
		["name", "first_name", "full_name", "user_image"],
		as_dict=True,
	)
	user["roles"] = frappe.get_roles(current_user)
	return user


# ─── Associate Info (basic) ──────────────────────────────────────────────

@frappe.whitelist()
def get_current_associate_info() -> dict:
	"""Return basic Associate info for the logged-in user."""
	associate_name = _get_associate_name()
	if not associate_name:
		return {}

	associate = frappe.db.get_value(
		"Associate",
		associate_name,
		[
			"name",
			"first_name",
			"last_name",
			"contact_name",
			"email",
			"mobile",
			"id_photo",
			"site",
			"contract_type",
			"awr_status",
			"owner_driver",
		],
		as_dict=True,
	)

	if associate and frappe.db.get_value('Associate',associate_name,'portal_profile_submitted_on'):
		fcm = _get_associate_fuel_card(associate_name)
		associate["fuel_card_number"] = fcm.get("fuel_card_number") or ""
		associate["fuel_card_pin"] = fcm.get("fuel_card_pin") or ""
		associate["fuel_card_date_sent"] = fcm.get("fuel_card_date_sent") or ""

	return associate or {}


def _get_associate_fuel_card(associate_name):
	"""Return the best matching FCM (fuel card) record for an Associate."""
	rows = frappe.get_all(
		"FCM",
		filters={"contact_name": associate_name},
		fields=["fcm_card_number", "fcm_card_pin_number", "date_sent", "status", "modified"],
		order_by="modified desc",
	)
	if not rows:
		return {}

	active = [r for r in rows if (r.get("status") or "") == "Active"]
	best = active[0] if active else rows[0]
	return {
		"fuel_card_number": best.get("fcm_card_number") or "",
		"fuel_card_pin": best.get("fcm_card_pin_number") or "",
		"fuel_card_date_sent": best.get("date_sent") or "",
	}


def _associate_has_active_fuel_card(associate_name):
	"""Return True if the Associate has an Active FCM (fuel card) record."""
	if not associate_name:
		return False
	return bool(
		frappe.db.exists("FCM", {"contact_name": associate_name, "status": "Active"})
	)


# ─── Full Profile ─────────────────────────────────────────────────────────

@frappe.whitelist()
@require_portal_access
def get_associate_profile() -> dict:
        """Return all Associate fields as a flat dict for the Profile view."""
        associate_name = _get_associate_name()
        if not associate_name:
                return {}

        doc = frappe.get_doc("Associate", associate_name)

        # All profile fields listed here for clarity
        DATE_FIELDS = [
                "dob", "address_since", "applied_date", "activated_in_flex",
                "dl_issue_date", "dl_expiry_date", "dl_photocard_expiry",
                "passport_issue_date", "passport_expiry_date",
                "idc_issuedate", "idc_expriydate", "start_date",
        ]

        TEXT_FIELDS = [
                "name", "first_name", "middle_name", "last_name",
                "contact_name", "title", "email", "mobile", "mobile2",
                "birthpassport_gender", "birth_country", "birth_nationality",
                "birth_city", "preferred_language", "id_photo",
                "street_address", "city", "state_region", "postal_code", "country",
                "site", "contract_type", "awr_status", "owner_driver",
                "fuel_card_number",
                "dl_type", "dl_number", "dl_issuing_country",
                "passport_number", "passport_issuing_country",
                "nino_number", "utr_number", "vat_registered", "vat_number",
                "idc_number", "idc_country",
                "hsid",
        ]

        INT_FIELDS = ["licence_approved"]

        profile = {}
        for f in TEXT_FIELDS:
                profile[f] = doc.get(f) or ""
        for f in DATE_FIELDS:
                val = doc.get(f)
                profile[f] = str(val) if val else ""
        for f in INT_FIELDS:
                profile[f] = doc.get(f) or 0

        return profile


# ─── Documents ────────────────────────────────────────────────────────────

# Maps Associate field → (child_dt, parentfield, child_file_field, status_field)
# Documents live in child tables (PDM/DLM/ADM); Associate field may mirror after approval.
DOC_CHILD_MAP = {
	"passp_file":               ("PDM", "pdm", "passp_file",         "pdm_status"),
	"tab_dl_photocard_front":   ("DLM", "dlm", "dl_photocard_front", "status"),
	"tab_dl_photocard_rear":    ("DLM", "dlm", "dl_photocard_rear",  "status"),
	"tab_dl_paper_counterpart": ("DLM", "dlm", "dl_couterpart",      "status"),
	"proof_of_address_doc":     ("ADM", "adm", "poa_file",           "adm_status"),
	"proof_of_bank":            ("POB", "pob", "pob_file",           "pob_status"),
	"rtw_share_code_file":         ("Right To Work Share Codes", "rtw_share_code_history",         "rtw_sc_file",   "rtw_status"),
	"immigration_share_code_doc":  ("Immigration Share Codes",   "immigration_share_code_history", "imi_sc_file",   "imi_status"),
}

# Extra fields shown in the upload modal and saved to the child row alongside the file
DOC_METADATA_FIELDS = {
	"passp_file": [
		{"name": "passp_number", "label": "Passport Number", "type": "text"},
		{"name": "passp_id",     "label": "Issue Date",      "type": "date"},
		{"name": "passp_ed",     "label": "Expiry Date",     "type": "date"},
		{"name": "passp_ic",     "label": "Issuing Country", "type": "text"},
	],
	"tab_dl_photocard_front": [
		{"name": "dl_number",                "label": "DL Number",       "type": "text"},
		{"name": "dl_issue_date",            "label": "Issue Date",      "type": "date"},
		{"name": "dl_expiry_date",           "label": "Expiry Date",     "type": "date"},
		{"name": "dl_photocard_expiry_date", "label": "Photocard Expiry","type": "date"},
	],
	"tab_dl_photocard_rear": [
		{"name": "dl_number",                "label": "DL Number",       "type": "text"},
		{"name": "dl_expiry_date",           "label": "Expiry Date",     "type": "date"},
		{"name": "dl_photocard_expiry_date", "label": "Photocard Expiry","type": "date"},
	],
	"tab_dl_paper_counterpart": [
		{"name": "dl_number", "label": "DL Number", "type": "text"},
	],
	"proof_of_address_doc": [
		{"name": "full_address", "label": "Full Address", "type": "textarea"},
		{"name": "post_code",    "label": "Post Code",    "type": "text"},
		{"name": "from_date",    "label": "Date From",    "type": "date"},
	],
	"proof_of_bank": [
		{"name": "pob_date", "label": "Proof of Bank Date", "type": "date"},
	],
	"rtw_share_code_file": [
		{"name": "rtw_sc",    "label": "Share Code",  "type": "text"},
		{"name": "rtw_sc_ed", "label": "Expiry Date", "type": "date"},
	],
	"immigration_share_code_doc": [
		{"name": "imi_sc", "label": "Share Code", "type": "text"},
	],
}

DOCUMENT_DEFINITIONS = [
	# (field_name, label, category, expiry_field)
	("passp_file", "Passport", "Identity", "passport_expiry_date"),
	("bc_file", "Birth Certificate", "Identity", None),

	("tab_dl_photocard_front", "Driving Licence (Front)", "Driving Licence", "dl_expiry_date"),
	("tab_dl_photocard_rear", "Driving Licence (Rear)", "Driving Licence", "dl_expiry_date"),
	("tab_dl_paper_counterpart", "DL Paper Counterpart (NI)", "Driving Licence", None),
	("eu_licence_declaration", "EU Licence Declaration", "Driving Licence", None),

	("nino_file", "National Insurance", "Tax & Finance", None),
	("utr_file", "UTR Document", "Tax & Finance", None),
	("vat_certificate", "VAT Certificate", "Tax & Finance", None),
	("proof_of_bank", "Proof of Bank", "Tax & Finance", None),

	("proof_of_address_doc", "Proof of Address", "Address", None),

	("immigration_share_code_doc", "Immigration Share Code", "Immigration", None),
	("rtw_share_code_file", "RTW Share Code", "Immigration", None),
	("visa_file", "VISA / Work Permit", "Immigration", None),

	("crb_report_document", "CRB Report", "Other", None),
	("stage3_compliance_docs", "Stage 3 Compliance", "Other", None),
]

# Simple Associate Attach fields that do not have a child table still need a
# review state after portal upload. Prefer child tables when present (e.g. POB).
SIMPLE_DOC_STATUS_MAP = {
}


def _associate_field_exists(fieldname):
	try:
		return frappe.get_meta("Associate").has_field(fieldname)
	except Exception:
		return False


def _associate_db_column_exists(fieldname):
	try:
		return bool(frappe.db.sql("""
			SELECT COLUMN_NAME
			  FROM INFORMATION_SCHEMA.COLUMNS
			 WHERE TABLE_SCHEMA = DATABASE()
			   AND TABLE_NAME = 'tabAssociate'
			   AND COLUMN_NAME = %s
			 LIMIT 1
		""", fieldname))
	except Exception:
		return False


def _get_doc_status(value, expiry_date_value, child_status=None):
	"""Return status: uploaded, missing, expired, expiring_soon, under_review, or rejected."""
	if child_status == "Review":
		return "under_review"
	if child_status in {"Approved", "Accepted"}:
		return "uploaded"
	if child_status == "Rejected":
		return "rejected"
	if not value:
		return "missing"
	if expiry_date_value:
		try:
			expiry = getdate(expiry_date_value)
			if expiry < getdate(today()):
				return "expired"
			days_left = date_diff(expiry, today())
			if days_left <= 30:
				return "expiring_soon"
		except Exception:
			pass
	return "uploaded"


@frappe.whitelist()
@require_portal_access
def get_associate_documents() -> dict:
	"""Return documents grouped by category with upload status."""
	associate_name = _get_associate_name()
	if not associate_name:
		return {"groups": [], "summary": {}}

	# Fetch Associate fields (expiry dates + non-mapped file fields)
	status_fields = [
		status_field
		for status_field in SIMPLE_DOC_STATUS_MAP.values()
		if _associate_field_exists(status_field)
	]
	all_fields = list(set(
		["name"] +
		[d[0] for d in DOCUMENT_DEFINITIONS] +
		[d[3] for d in DOCUMENT_DEFINITIONS if d[3]] +
		status_fields
	))
	associate = frappe.db.get_value("Associate", associate_name, all_fields, as_dict=True)
	if not associate:
		return {"groups": [], "summary": {}}

	# Build the set of fields to fetch per child_dt (file field + status + metadata fields)
	_child_fetch = {}  # child_dt -> set of fieldnames
	for assoc_field, (child_dt, _pf, child_file, status_field) in DOC_CHILD_MAP.items():
		if child_dt not in _child_fetch:
			_child_fetch[child_dt] = {"name", status_field}
		_child_fetch[child_dt].add(child_file)
		for mf in DOC_METADATA_FIELDS.get(assoc_field, []):
			_child_fetch[child_dt].add(mf["name"])

	# Fetch one (latest modified) row per child_dt
	child_rows = {}
	for child_dt, fields in _child_fetch.items():
		row = frappe.db.get_value(
			child_dt,
			{"parent": associate_name, "parenttype": "Associate"},
			list(fields),
			as_dict=True,
			order_by="modified desc",
		)
		child_rows[child_dt] = row or {}

	groups = {}
	total = 0
	uploaded = 0
	missing = 0
	expired = 0
	expiring_soon = 0
	under_review = 0
	rejected = 0

	for field_name, label, category, expiry_field in DOCUMENT_DEFINITIONS:
		expiry_value = associate.get(expiry_field) if expiry_field else None

		child_info = DOC_CHILD_MAP.get(field_name)
		if child_info:
			child_dt, _pf, child_file_field, status_field = child_info
			child_row = child_rows.get(child_dt, {})
			# File lives in child table; fall back to Associate field if child row missing
			value = child_row.get(child_file_field) or associate.get(field_name) or ""
			child_status = child_row.get(status_field)
			# Build metadata current values (pre-fill the upload form)
			meta_defs = DOC_METADATA_FIELDS.get(field_name, [])
			meta_values = {mf["name"]: str(child_row.get(mf["name"]) or "") for mf in meta_defs}
		else:
			value = associate.get(field_name) or ""
			status_field = SIMPLE_DOC_STATUS_MAP.get(field_name)
			child_status = associate.get(status_field) if status_field else None
			meta_defs = []
			meta_values = {}

		status = _get_doc_status(value, expiry_value, child_status)

		doc_info = {
			"field": field_name,
			"label": label,
			"status": status,
			"file_url": value,
			"expiry_date": str(expiry_value or ""),
			"can_upload": status != "under_review",
			"metadata_fields": meta_defs,
			"metadata": meta_values,
		}

		if category not in groups:
			groups[category] = []
		groups[category].append(doc_info)

		total += 1
		if status == "uploaded":
			uploaded += 1
		elif status == "expiring_soon":
			expiring_soon += 1
			uploaded += 1  # expiring but still counts as uploaded
		elif status == "missing":
			missing += 1
		elif status == "expired":
			expired += 1
		elif status == "under_review":
			under_review += 1
		elif status == "rejected":
			rejected += 1

	# Convert to list of group dicts (preserve category order)
	group_list = []
	for category in ["Identity", "Driving Licence", "Tax & Finance", "Address", "Immigration", "Other"]:
		if category in groups:
			group_list.append({"category": category, "documents": groups[category]})

	return {
		"groups": group_list,
		"summary": {
			"total": total,
			"uploaded": uploaded,
			"missing": missing,
			"expired": expired,
			"expiring_soon": expiring_soon,
			"under_review": under_review,
			"rejected": rejected,
		},
	}


# ─── Upload Associate Document ──────────────────────────────────────────

_ALLOWED_UPLOAD_FIELDS = set(d[0] for d in DOCUMENT_DEFINITIONS)

# field_name -> expiry date field on the Associate (if any)
_DOC_EXPIRY_FIELD = {d[0]: d[3] for d in DOCUMENT_DEFINITIONS}

@frappe.whitelist()
@require_portal_access
def update_associate_document(field_name, file_url, metadata=None):
	"""Save uploaded document + metadata into child table row, set status to Review."""
	if field_name not in _ALLOWED_UPLOAD_FIELDS:
		frappe.throw(_("Invalid document field"), frappe.ValidationError)

	associate_name = _get_associate_name()
	if not associate_name:
		frappe.throw(_("Associate not found"), frappe.ValidationError)

	# Parse metadata (may arrive as JSON string or dict)
	if isinstance(metadata, str):
		import json as _json
		try:
			metadata = _json.loads(metadata) if metadata.strip() else {}
		except Exception:
			metadata = {}
	metadata = metadata or {}

	child_info = DOC_CHILD_MAP.get(field_name)
	if child_info:
		child_dt, parentfield, child_file_field, status_field = child_info

		# Determine the current effective status and only allow (re)upload when
		# the document has never been uploaded, was rejected, or is expiring/expired.
		latest_child = frappe.db.get_value(
			child_dt,
			{"parent": associate_name, "parenttype": "Associate"},
			[status_field, child_file_field],
			as_dict=True,
			order_by="modified desc",
		) or {}
		latest_status = latest_child.get(status_field)
		current_value = latest_child.get(child_file_field)
		expiry_field = _DOC_EXPIRY_FIELD.get(field_name)
		expiry_value = (
			frappe.db.get_value("Associate", associate_name, expiry_field)
			if expiry_field else None
		)
		effective_status = _get_doc_status(current_value, expiry_value, latest_status)

		if effective_status == "under_review":
			frappe.throw(
				_("Document is currently under review and cannot be replaced"),
				frappe.ValidationError,
			)
		if effective_status == "uploaded":
			frappe.throw(
				_("Document is valid and approved. It can only be updated if it is rejected or close to expiry."),
				frappe.ValidationError,
			)

		# Build the new row: file + status Review + validated metadata
		row_dict = {child_file_field: file_url, status_field: "Review"}
		if child_dt == "POB":
			row_dict["pob_sd"] = frappe.utils.now_datetime()
		allowed_meta = {mf["name"] for mf in DOC_METADATA_FIELDS.get(field_name, [])}
		for k, v in metadata.items():
			if k in allowed_meta:
				row_dict[k] = v or None

		# Always create a NEW child row so the team has a review/approve queue.
		# Insert the child row directly instead of saving the whole Associate:
		# legacy Associate records may contain old child rows with invalid select
		# values, and saving the parent would validate those unrelated rows.
		new_row = frappe.get_doc({
			"doctype": child_dt,
			"parent": associate_name,
			"parenttype": "Associate",
			"parentfield": parentfield,
			"idx": (frappe.db.count(child_dt, {"parent": associate_name, "parenttype": "Associate", "parentfield": parentfield}) or 0) + 1,
		})
		for k, v in row_dict.items():
			new_row.set(k, v)

		# Populate any Link-to-Associate field on the child row (e.g. "associate"
		# or "contact_name") so review queues show the associate's name.
		for df in frappe.get_meta(child_dt).fields:
			if df.fieldtype == "Link" and df.options == "Associate":
				new_row.set(df.fieldname, associate_name)

		new_row.insert(ignore_permissions=True)
		_attach_uploaded_file_to_field(file_url, child_dt, new_row.name, child_file_field)

	# Mirror URL to Associate record
	update_values = {field_name: file_url}
	status_field = SIMPLE_DOC_STATUS_MAP.get(field_name)
	if status_field and _associate_field_exists(status_field):
		update_values[status_field] = "Review"
	frappe.db.set_value("Associate", associate_name, update_values)
	frappe.db.commit()
	return "ok"


def _attach_uploaded_file_to_field(file_url, doctype, docname, fieldname):
	"""Attach an uploaded File record to the real document/field that owns it."""
	if not file_url:
		return

	file_name = frappe.db.get_value(
		"File",
		{"file_url": file_url},
		"name",
		order_by="creation desc",
	)
	if not file_name:
		return

	frappe.db.set_value(
		"File",
		file_name,
		{
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"attached_to_field": fieldname,
		},
		update_modified=False,
	)


@frappe.whitelist()
def ensure_associate_portal_custom_fields():
	"""Create Custom Fields needed by the Associate Portal simple-document flow."""
	# Kept for backwards compatibility with older deploy commands.
	# Proof of Bank is now handled exclusively via child table POB.
	return "ok"


def migrate_proof_of_bank_to_pob():
	"""Move legacy Associate.proof_of_bank uploads into the POB child table."""
	frappe.db.sql("""
		INSERT INTO `tabPOB`
			(name, creation, modified, modified_by, owner, docstatus, idx,
			 parent, parentfield, parenttype, pob_file, pob_status, pob_sd, contact_name)
		SELECT
			CONCAT('POB-MIG-', REPLACE(UUID(), '-', '')),
			NOW(6), NOW(6), %s, %s, 0,
			COALESCE((
				SELECT MAX(p2.idx)
				  FROM `tabPOB` p2
				 WHERE p2.parent = a.name
				   AND p2.parenttype = 'Associate'
				   AND p2.parentfield = 'pob'
			), 0) + 1,
		 a.name, 'pob', 'Associate', a.proof_of_bank, 'Review', NOW(6), a.name
		  FROM `tabAssociate` a
		 WHERE IFNULL(a.proof_of_bank, '') != ''
		   AND (
				a.proof_of_bank LIKE 'http%%'
				OR a.proof_of_bank LIKE '/files/%%'
				OR a.proof_of_bank LIKE '/private/files/%%'
		   )
		   AND NOT EXISTS (
				SELECT 1
				  FROM `tabPOB` p
				 WHERE p.parent = a.name
				   AND p.parenttype = 'Associate'
				   AND p.pob_file = a.proof_of_bank
		   )
	""", (frappe.session.user, frappe.session.user))
	created = frappe.db.sql("SELECT ROW_COUNT() AS count", as_dict=True)[0].count
	frappe.db.commit()
	frappe.clear_cache(doctype="Associate")
	return {"created": created}


def relink_proof_of_bank_files_to_pob():
	"""Attach existing Proof of Bank File records to their matching POB rows."""
	frappe.db.sql("""
		UPDATE `tabFile` f
		JOIN `tabPOB` p ON p.pob_file = f.file_url
		   SET f.attached_to_doctype = 'POB',
		       f.attached_to_name = p.name,
		       f.attached_to_field = 'pob_file'
		 WHERE IFNULL(p.pob_file, '') != ''
	""")
	frappe.db.commit()
	return {"updated": frappe.db.sql("SELECT ROW_COUNT() AS count", as_dict=True)[0].count}


@frappe.whitelist()
@require_portal_access
def scan_document_fields(field_name, image_base64):
	"""Extract document metadata using local Tesseract OCR + regex parsing.
	No external AI service or API key required.
	"""
	if field_name not in DOC_CHILD_MAP:
		frappe.throw("Invalid document type")

	meta_fields = DOC_METADATA_FIELDS.get(field_name, [])
	if not meta_fields:
		return {}

	parser = _OCR_PARSERS.get(field_name)
	if not parser:
		return {}

	try:
		text = _ocr_extract_text(image_base64)
	except Exception as e:
		frappe.log_error(f"scan_document_fields OCR error: {e}")
		frappe.throw("Could not read the document. Please enter the details manually.")

	if not text or not text.strip():
		return {}

	try:
		extracted = parser(_ocr_normalize_text(text))
	except Exception as e:
		frappe.log_error(f"scan_document_fields parse error: {e}")
		return {}

	# Keep only known metadata keys with non-empty values
	allowed = {mf["name"] for mf in meta_fields}
	cleaned = {k: v for k, v in extracted.items() if k in allowed and v}

	# Diagnostic: if nothing was parsed, log the raw OCR text so regex can be tuned
	if not cleaned:
		frappe.log_error(
			f"OCR raw text ({field_name}):\n{text[:1800]}",
			"scan_document_fields no match",
		)
	return cleaned


def _ocr_extract_text(image_base64):
	"""Decode a base64 image or PDF and return extracted plain text via Tesseract."""
	import base64, subprocess, tempfile, os, shutil
	from PIL import Image
	import pytesseract

	if image_base64.startswith("data:"):
		header, payload = image_base64.split(",", 1)
		mime_type = header.split(":")[1].split(";")[0]
	else:
		payload = image_base64
		mime_type = "image/jpeg"

	raw = base64.b64decode(payload)
	is_pdf = mime_type.endswith("/pdf") or raw[:5] == b"%PDF-"

	tmpdir = tempfile.mkdtemp(prefix="ocr_")
	try:
		image_paths = []
		if is_pdf:
			pdf_path = os.path.join(tmpdir, "doc.pdf")
			with open(pdf_path, "wb") as fh:
				fh.write(raw)
			# Render up to first 3 pages at 300 DPI using poppler
			out_prefix = os.path.join(tmpdir, "page")
			subprocess.run(
				["pdftoppm", "-r", "300", "-l", "3", "-png", pdf_path, out_prefix],
				check=True, capture_output=True, timeout=90,
			)
			image_paths = sorted(
				os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
				if f.startswith("page") and f.endswith(".png")
			)
		else:
			img_path = os.path.join(tmpdir, "doc.img")
			with open(img_path, "wb") as fh:
				fh.write(raw)
			image_paths = [img_path]

		texts = []
		for p in image_paths:
			try:
				img = _ocr_preprocess(Image.open(p))
				# PSM 3 = full page auto; PSM 6 = uniform text block.
				# Phone scans vary a lot, so keeping both outputs gives the
				# parser better chances without using an external OCR service.
				for psm in (3, 6):
					texts.append(
						pytesseract.image_to_string(
							img,
							config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1",
						)
					)
			except Exception:
				continue
		return "\n".join(texts)
	finally:
		shutil.rmtree(tmpdir, ignore_errors=True)


def _ocr_preprocess(img):
	"""Improve OCR accuracy: upscale small images, grayscale, autocontrast, sharpen."""
	from PIL import Image, ImageOps, ImageFilter

	# Upscale if the image is small so text is at least ~2000px on the long edge
	long_edge = max(img.size)
	if long_edge < 2000:
		factor = 2000.0 / long_edge
		new_size = (int(img.size[0] * factor), int(img.size[1] * factor))
		img = img.resize(new_size, Image.LANCZOS)

	img = ImageOps.exif_transpose(img)
	img = ImageOps.grayscale(img)
	img = ImageOps.autocontrast(img)
	img = img.filter(ImageFilter.MedianFilter(size=3))
	img = img.filter(ImageFilter.SHARPEN)
	return img


def _ocr_normalize_text(text):
	"""Normalise OCR text while preserving useful line structure."""
	if not text:
		return ""
	replacements = {
		"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
		"\u2013": "-", "\u2014": "-", "\xa0": " ",
	}
	for src, target in replacements.items():
		text = text.replace(src, target)
	text = re.sub(r"[ \t]+", " ", text)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


def _ocr_fix_numeric_date_token(value):
	"""Fix common OCR confusions only inside date-looking tokens."""
	return (value or "").translate(str.maketrans({
		"O": "0", "o": "0", "Q": "0", "D": "0",
		"I": "1", "l": "1", "|": "1",
		"S": "5", "s": "5",
		"B": "8",
	}))


def _ocr_find_date_near(text, label_pattern, chars=90):
	"""Find first date after a label such as 4a/4b/expiry/valid until."""
	m = re.search(label_pattern, text, re.I)
	if not m:
		return None
	window = text[m.end():m.end() + chars]
	dates = _ocr_find_dates(window)
	return dates[0] if dates else None




def _ocr_norm_date(raw_date):
	"""Normalise a date string into YYYY-MM-DD, or return None."""
	from datetime import datetime

	if not raw_date:
		return None
	s = raw_date.strip()
	s = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", s, flags=re.I)
	s = re.sub(r"\s+", " ", s)
	if re.search(r"[/.\-]", s):
		parts = re.split(r"([/.\-])", s)
		s = "".join(_ocr_fix_numeric_date_token(p) if idx % 2 == 0 else p for idx, p in enumerate(parts))
	formats = [
		"%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %m %Y",
		"%Y-%m-%d", "%Y/%m/%d",
		"%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y",
		"%b %d %Y", "%B %d %Y",
		"%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
	]
	for fmt in formats:
		try:
			return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
		except ValueError:
			continue
	return None


def _ocr_find_dates(text):
	"""Return list of normalised YYYY-MM-DD dates found in text, in order."""
	patterns = [
		r"\b[0-9OoQDISBl|]{1,2}[/.\-][0-9OoQDISBl|]{1,2}[/.\-][0-9OoQDISBl|]{2,4}\b",
		r"\b\d{1,2}[\s\-][A-Za-z]{3,9}[\s\-]\d{2,4}\b",
		r"\b[A-Za-z]{3,9}\s+\d{1,2}\s+\d{4}\b",
		r"\b[0-9OoQDISBl|]{4}[/\-][0-9OoQDISBl|]{1,2}[/\-][0-9OoQDISBl|]{1,2}\b",
	]
	found = []
	for pat in patterns:
		for m in re.findall(pat, text):
			norm = _ocr_norm_date(m)
			if norm and norm not in found:
				found.append(norm)
	return found


# ─── Per-document OCR regex parsers ──────────────────────────────────────

def _parse_passport(text):
	result = {}
	upper = text.upper()

	# MRZ: two bottom lines containing < — most reliable source
	mrz_lines = [ln.strip().replace(" ", "") for ln in upper.splitlines()
	             if "<" in ln and len(ln.strip().replace(" ", "")) >= 28]
	mrz_line1 = next((l for l in mrz_lines if l.startswith("P<")), None)
	mrz_line2 = next((l for l in mrz_lines if l is not mrz_line1
	                  and re.match(r"^[A-Z0-9<]{20,}$", l)), None)

	if mrz_line1 and len(mrz_line1) >= 5:
		country = mrz_line1[2:5].replace("<", "")
		if country:
			result["passp_ic"] = country
	if mrz_line2 and len(mrz_line2) >= 28:
		num = mrz_line2[0:9].replace("<", "")
		if num:
			result["passp_number"] = num

		def _mrz_date(yymmdd, expiry=False):
			from datetime import datetime
			if len(yymmdd) != 6 or not yymmdd.isdigit():
				return None
			yy = int(yymmdd[0:2]); mm = yymmdd[2:4]; dd = yymmdd[4:6]
			century = 20 if expiry else (19 if yy > 30 else 20)
			try:
				return datetime.strptime(f"{century}{yy:02d}-{mm}-{dd}", "%Y-%m-%d").strftime("%Y-%m-%d")
			except ValueError:
				return None

		exp = _mrz_date(mrz_line2[21:27], expiry=True)
		if exp:
			result["passp_ed"] = exp

	if "passp_number" not in result:
		m = re.search(r"\b([0-9]{9})\b", text)
		if m:
			result["passp_number"] = m.group(1)

	dates = _ocr_find_dates(text)
	if "passp_ed" not in result and dates:
		result["passp_ed"] = max(dates)
	if "passp_id" not in result and len(dates) >= 2:
		result["passp_id"] = min(dates)

	return result


def _parse_dl_front(text):
	result = {}
	compact = text.upper().replace(" ", "").replace("-", "")
	m = re.search(r"\b([A-Z9]{5}\d{6}[A-Z0-9]{5})\b", compact)
	if m:
		result["dl_number"] = m.group(1)
	else:
		m2 = re.search(r"(?:5|DRIVER\s*NUMBER|LICENCE\s*NUMBER)\s*[:\.]?\s*([A-Z0-9\s\-]{14,24})", text.upper())
		if m2:
			candidate = re.sub(r"[^A-Z0-9]", "", m2.group(1))
			if 14 <= len(candidate) <= 18:
				result["dl_number"] = candidate

	issue = _ocr_find_date_near(text, r"\b4\s*a\b\s*[:.\-]?", 70)
	if issue:
		result["dl_issue_date"] = issue
	photocard_expiry = _ocr_find_date_near(text, r"\b4\s*b\b\s*[:.\-]?", 70)
	if photocard_expiry:
		# UK photocard field 4b is the photocard expiry date. Keep it separate
		# from entitlement / driving licence expiry where the table has both.
		result["dl_photocard_expiry_date"] = photocard_expiry

	dates = _ocr_find_dates(text)
	if "dl_issue_date" not in result and len(dates) >= 2:
		result["dl_issue_date"] = min(dates)
	if "dl_photocard_expiry_date" not in result and dates:
		result["dl_photocard_expiry_date"] = max(dates)
	return result


def _parse_dl_rear(text):
	result = {}
	m = re.search(r"\b([A-Z9]{5}\d{6}[A-Z0-9]{5})\b", text.upper().replace(" ", "").replace("-", ""))
	if m:
		result["dl_number"] = m.group(1)
	dates = _ocr_find_dates(text)
	if dates:
		result["dl_expiry_date"] = max(dates)
	return result


def _parse_dl_counterpart(text):
	result = {}
	m = re.search(r"\b([A-Z9]{5}\d{6}[A-Z0-9]{5})\b", text.upper().replace(" ", "").replace("-", ""))
	if m:
		result["dl_number"] = m.group(1)
	return result


def _parse_proof_of_address(text):
	result = {}
	pc = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", text.upper())
	if pc:
		result["post_code"] = re.sub(r"\s+", " ", pc.group(1).strip())
	dates = _ocr_find_dates(text)
	if dates:
		# For bills/bank statements, the visible proof date is usually the
		# newest date on the document, not the oldest transaction period date.
		result["from_date"] = max(dates)
	return result


def _parse_proof_of_bank(text):
	result = {}
	dates = _ocr_find_dates(text)
	if dates:
		result["pob_date"] = max(dates)
	return result


def _parse_share_code(text, code_key, date_key=None):
	result = {}
	up = text.upper()
	# UK share code: letter + 2 groups of 3, e.g. W12 34A B7C ; allow spaces
	m = re.search(r"\b([A-Z]\s*[A-Z0-9]{2}\s*[A-Z0-9]{3}\s*[A-Z0-9]{3})\b", up)
	near = re.search(r"(?:SHARE\s*)?CODE\s*[:\-]?\s*([A-Z]\s*[A-Z0-9]{2}\s*[A-Z0-9]{3}\s*[A-Z0-9]{3})", up)
	chosen = near or m
	if chosen:
		result[code_key] = re.sub(r"\s+", " ", chosen.group(1).strip())
	if date_key:
		expiry = _ocr_find_date_near(text, r"\b(?:VALID\s*UNTIL|EXPIRES?|EXPIRY|VALID\s*TO)\b\s*[:.\-]?", 140)
		if not expiry:
			dates = _ocr_find_dates(text)
			expiry = max(dates) if dates else None
		if expiry:
			result[date_key] = expiry
	return result


_OCR_PARSERS = {
	"passp_file": _parse_passport,
	"tab_dl_photocard_front": _parse_dl_front,
	"tab_dl_photocard_rear": _parse_dl_rear,
	"tab_dl_paper_counterpart": _parse_dl_counterpart,
	"proof_of_address_doc": _parse_proof_of_address,
	"proof_of_bank": _parse_proof_of_bank,
	"rtw_share_code_file": lambda t: _parse_share_code(t, "rtw_sc", "rtw_sc_ed"),
	"immigration_share_code_doc": lambda t: _parse_share_code(t, "imi_sc"),
}



# ─── Compliance Summary ──────────────────────────────────────────────────

@frappe.whitelist()
@require_portal_access
def get_compliance_summary() -> dict:
	"""Return compliance percentage and alerts using the same data as Documents and Agreements."""
	associate_name = _get_associate_name()
	if not associate_name:
		return {"percentage": 0, "alerts": []}

	# Reuse the same sources used by the portal pages so Home reflects reality.
	docs = get_associate_documents()
	doc_summary = docs.get("summary", {})
	agreements_data = get_associate_agreements()
	agreement_summary = agreements_data.get("summary", {})

	doc_total = doc_summary.get("total", 0)
	doc_uploaded = doc_summary.get("uploaded", 0)
	doc_missing = doc_summary.get("missing", 0)
	doc_under_review = doc_summary.get("under_review", 0)
	doc_rejected = doc_summary.get("rejected", 0)

	agreement_total = agreement_summary.get("total", 0)
	agreement_signed = agreement_summary.get("signed", 0)
	agreement_unsigned = agreement_summary.get("unsigned", 0)

	total = doc_total + agreement_total
	completed = doc_uploaded + agreement_signed
	missing = doc_missing + agreement_unsigned

	percentage = round((completed / total * 100) if total > 0 else 0)

	alerts = []
	for group in docs.get("groups", []):
		for doc in group.get("documents", []):
			if doc["status"] == "expired":
				alerts.append({
					"type": "expired",
					"icon": "alert-circle",
					"message": f"{doc['label']} has expired",
				})
			elif doc["status"] == "expiring_soon":
				alerts.append({
					"type": "warning",
					"icon": "clock",
					"message": f"{doc['label']} expires soon ({doc['expiry_date']})",
				})
			elif doc["status"] == "under_review":
				alerts.append({
					"type": "under_review",
					"icon": "clock",
					"message": f"{doc['label']} is under review",
				})
			elif doc["status"] == "rejected":
				alerts.append({
					"type": "rejected",
					"icon": "alert-circle",
					"message": f"{doc['label']} was rejected",
				})
			elif doc["status"] == "missing":
				alerts.append({
					"type": "missing",
					"icon": "upload",
					"message": f"{doc['label']} not uploaded",
				})

	for agreement in agreements_data.get("agreements", []):
		if not agreement.get("signed"):
			alerts.append({
				"type": "missing",
				"icon": "file-text",
				"message": f"{agreement['label']} not signed",
			})

	# Limit alerts to top 5
	alerts = alerts[:5]

	return {
		"percentage": percentage,
		"completed": completed,
		"total": total,
		"missing": missing,
		"under_review": doc_under_review,
		"rejected": doc_rejected,
		"documents": doc_summary,
		"agreements": agreement_summary,
		"alerts": alerts,
	}


# ─── Agreements ───────────────────────────────────────────────────────────

AGREEMENT_DEFINITIONS = [
	# (file_field, label, signed_field, signed_date_field)
	("sba_agrement", "Subcontractor Business Agreement (SBA)", "sba_signed", "sba_signed_date"),
	("acap_agreement", "ACAP Agreement", "acap_signed", "acap_signed_date"),
	("dld_agrement", "DLD Agreement", "dld_signed", "dld_signed_date"),
	("nda_agreement", "Non-Disclosure Agreement (NDA)", None, None),
	("pii_agreement", "PII Agreement", None, None),
	("spp_agrement", "SPP Agreement", None, None),
	("mfd_agrement", "MFD Agreement", None, None),
	("vpp_agrement", "VPP Agreement", None, None),
	("nca_agrement", "NCA Agreement", None, None),
	("apn_agrement", "APN Agreement", None, None),
	("eu_licence_declaration", "EU Licence Declaration", None, None),
	("payement_plan_agreement", "Payment Plan Agreement", None, None),
	("fuel_card_agreement", "Fuel Card Agreement", "fca_signed", "fca_signed_date"),
]


@frappe.whitelist()
@require_portal_access
def get_associate_agreements() -> dict:
	"""Return agreement status list with signed/unsigned info."""
	associate_name = _get_associate_name()
	if not associate_name:
		return {"agreements": [], "summary": {}}

	# Collect all fields needed
	fields_to_fetch = ["name"]
	for file_field, _, signed_field, date_field in AGREEMENT_DEFINITIONS:
		fields_to_fetch.append(file_field)
		if signed_field:
			fields_to_fetch.append(signed_field)
		if date_field:
			fields_to_fetch.append(date_field)

	associate = frappe.db.get_value(
		"Associate",
		associate_name,
		list(set(fields_to_fetch)),
		as_dict=True,
	)
	if not associate:
		return {"agreements": [], "summary": {}}

	agreements = []
	total = 0
	signed_count = 0

	# The Fuel Card Agreement counts as signed when the associate has an
	# active fuel card issued to them.
	has_active_fuel_card = _associate_has_active_fuel_card(associate_name)

	for file_field, label, signed_field, date_field in AGREEMENT_DEFINITIONS:
		file_url = associate.get(file_field) or ""

		# Determine signed status
		if signed_field:
			is_signed = bool(associate.get(signed_field))
		else:
			# If no signed checkbox, check if file is uploaded
			is_signed = bool(file_url)

		signed_date = ""
		if date_field:
			signed_date = str(associate.get(date_field) or "")

		if file_field == "fuel_card_agreement" and has_active_fuel_card:
			is_signed = True

		agreements.append({
			"field": file_field,
			"label": label,
			"signed": is_signed,
			"signed_date": signed_date,
			"file_url": file_url,
		})

		total += 1
		if is_signed:
			signed_count += 1

	return {
		"agreements": agreements,
		"summary": {
			"total": total,
			"signed": signed_count,
			"unsigned": total - signed_count,
			"percentage": round((signed_count / total * 100) if total > 0 else 0),
		},
	}


# ─── Leave / Notice management ───────────────────────────────────────────

@frappe.whitelist()
@require_portal_access
def get_leave_records():
	"""Return LHS leave/notice records for the current associate."""
	associate_name = _get_associate_name()
	if not associate_name:
		return []
	rows = frappe.get_all(
		"LHS",
		filters={"parent": associate_name, "parentfield": "leave_records"},
		fields=[
			"name",
			"lv_type",
			"lv_status",
			"leave_date_start",
			"leave_date_end",
			"leave_date_booked",
		],
		order_by="leave_date_start desc",
	)
	return rows


@frappe.whitelist()
@require_portal_access
def submit_leave_request(lv_type, leave_date_start, leave_date_end):
	"""Create a new Holiday or Notice request from the associate portal."""
	associate_name = _get_associate_name()
	if not associate_name:
		frappe.throw(_("Associate not found"), frappe.PermissionError)

	if lv_type == "Holiday":
		doc = frappe.get_doc({
			"doctype": "Holiday Submission",
			"associate_id": associate_name,
			"leave_date_start": leave_date_start,
			"leave_date_end": leave_date_end,
			"leave_date_booked": frappe.utils.today(),
			"leave_updated_by": frappe.session.user,
		})
		doc.insert(ignore_permissions=True)
	elif lv_type == "Notice":
		doc = frappe.get_doc({
			"doctype": "Notice Submission",
			"associate_id": associate_name,
			"notice_period_date": leave_date_start,
			"finish_date": leave_date_end,
		})
		doc.insert(ignore_permissions=True)
	else:
		frappe.throw(_("Invalid request type"))

	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
@require_portal_access
def update_leave_request(lhs_row_name, leave_date_start, leave_date_end):
	"""Update dates on a leave request that is still in Review status."""
	associate_name = _get_associate_name()
	if not associate_name:
		frappe.throw(_("Associate not found"), frappe.PermissionError)

	row = frappe.db.get_value(
		"LHS", lhs_row_name, ["parent", "lv_status"], as_dict=True
	)
	if not row or row.parent != associate_name:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if row.lv_status not in ("Review", "Active"):
		frappe.throw(_("Only requests in Review or Active status can be modified"))

	frappe.db.set_value("LHS", lhs_row_name, {
		"leave_date_start": leave_date_start,
		"leave_date_end": leave_date_end,
		"leave_updated_by": frappe.session.user,
	})
	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
@require_portal_access
def cancel_leave_request(lhs_row_name):
	"""Cancel a leave/notice request (only if status is Review or Active)."""
	associate_name = _get_associate_name()
	if not associate_name:
		frappe.throw(_("Associate not found"), frappe.PermissionError)

	row = frappe.db.get_value(
		"LHS", lhs_row_name, ["parent", "lv_status"], as_dict=True
	)
	if not row or row.parent != associate_name:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if row.lv_status not in ("Review", "Active"):
		frappe.throw(_("Cannot cancel a request with status: ") + row.lv_status)

	frappe.db.set_value("LHS", lhs_row_name, {
		"lv_status": "Cancel",
		"leave_updated_by": frappe.session.user,
	})
	frappe.db.commit()
	return {"status": "ok"}


# ─── Boot context for dev mode ───────────────────────────────────────────

@frappe.whitelist()
def get_context_for_dev():
	"""Return boot context — used by Vite dev mode."""
	if not frappe.has_permission("Associate", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	csrf_token = frappe.sessions.get_csrf_token()
	return {
		"csrf_token": csrf_token,
		"site_name": frappe.local.site,
	}


# ─── Notifications ───────────────────────────────────────────────────────

@frappe.whitelist()
@require_portal_access
def get_notifications(start=0, page_length=20):
    """Get PWA Notifications for the current user."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    notifications = frappe.get_all(
        "PWA Notification",
        filters={"to_user": user},
        fields=[
            "name", "from_user", "message", "read",
            "creation", "reference_document_type",
            "reference_document_name",
        ],
        order_by="creation desc",
        start=int(start),
        page_length=int(page_length),
    )

    # Enrich with sender info
    for n in notifications:
        n["from_user_name"] = frappe.db.get_value(
            "User", n["from_user"], "full_name"
        ) or n["from_user"]
        n["from_user_image"] = frappe.db.get_value(
            "User", n["from_user"], "user_image"
        )

    return notifications


@frappe.whitelist()
@require_portal_access
def get_unread_notifications_count():
    """Get count of unread notifications for the current user."""
    user = frappe.session.user
    if user == "Guest":
        return 0

    return frappe.db.count(
        "PWA Notification",
        {"to_user": user, "read": 0},
    )


def _get_unread_notifications_count_for_user(user):
    """Return unread notification count for a specific user."""
    if not user:
        return 0
    return frappe.db.count(
        "PWA Notification",
        {"to_user": user, "read": 0},
    )


@frappe.whitelist()
@require_portal_access
def mark_notification_as_read(notification_name):
    """Mark a single notification as read."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    # Verify ownership
    to_user = frappe.db.get_value("PWA Notification", notification_name, "to_user")
    if to_user != user:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    frappe.db.set_value("PWA Notification", notification_name, "read", 1, update_modified=False)
    frappe.db.commit()
    return "ok"


@frappe.whitelist()
@require_portal_access
def mark_all_notifications_as_read():
    """Mark all notifications as read for the current user."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    frappe.db.set_value(
        "PWA Notification",
        {"to_user": user, "read": 0},
        "read",
        1,
        update_modified=False,
    )
    frappe.db.commit()
    return "ok"


@frappe.whitelist()
def are_push_notifications_enabled():
    """Check if push notifications are enabled."""
    try:
        return frappe.db.get_single_value(
            "Push Notification Settings", "enable_push_notification_relay"
        )
    except frappe.DoesNotExistError:
        return False



# ─── Chatwoot Chat Proxy ─────────────────────────────────────────────────
_CW_BASE = "https://onechat.onemotion.live"
_CW_INBOX = "8kJPHwtbTFmb6eLvfXQBfQkF"
_CW_API = _CW_BASE + "/public/api/v1/inboxes/" + _CW_INBOX


def _cw_req(method, path, payload=None):
    import requests as req
    url = _CW_API + path
    try:
        r = req.request(method, url, json=payload,
                        headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except req.exceptions.Timeout:
        frappe.log_error("Chatwoot timeout: " + method + " " + path)
        return [] if method == "GET" else {}
    except req.exceptions.RequestException as e:
        frappe.log_error("Chatwoot error: " + str(e))
        return [] if method == "GET" else {}


def _ensure_onechat_session_columns():
    if not _associate_db_column_exists("onechat_source_id"):
        frappe.db.sql("ALTER TABLE `tabAssociate` ADD COLUMN IF NOT EXISTS `onechat_source_id` varchar(140)")
    if not _associate_db_column_exists("onechat_conversation_id"):
        frappe.db.sql("ALTER TABLE `tabAssociate` ADD COLUMN IF NOT EXISTS `onechat_conversation_id` varchar(140)")


def _get_onechat_session(associate_name):
    _ensure_onechat_session_columns()
    rows = frappe.db.sql(
        """
        SELECT onechat_source_id, onechat_conversation_id
          FROM `tabAssociate`
         WHERE name = %s
         LIMIT 1
        """,
        associate_name,
        as_dict=True,
    )
    return rows[0] if rows else frappe._dict()


def _set_onechat_session(associate_name, source_id=None, conversation_id=None):
    _ensure_onechat_session_columns()
    updates = []
    values = []
    if source_id is not None:
        updates.append("onechat_source_id = %s")
        values.append(source_id)
    if conversation_id is not None:
        updates.append("onechat_conversation_id = %s")
        values.append(str(conversation_id) if conversation_id else "")
    if not updates:
        return
    values.append(associate_name)
    frappe.db.sql(
        "UPDATE `tabAssociate` SET " + ", ".join(updates) + " WHERE name = %s",
        values,
    )
    frappe.db.commit()


@frappe.whitelist()
@require_onboarding_chat
def chat_create_contact():
    aname = _get_associate_name()
    session = _get_onechat_session(aname)
    if session.get("onechat_source_id"):
        return {
            "source_id": session.get("onechat_source_id"),
            "conversation_id": session.get("onechat_conversation_id") or "",
            "cached": True,
        }

    doc = frappe.get_doc("Associate", aname)
    first = doc.first_name or ""
    last = doc.last_name or ""
    full = (first + " " + last).strip() or frappe.session.user
    email = doc.email or frappe.session.user
    ident = doc.hsid or aname
    data = _cw_req("POST", "/contacts", {"name": full, "email": email, "identifier": ident})
    if isinstance(data, dict) and data.get("source_id"):
        _set_onechat_session(aname, source_id=data.get("source_id"))
    return data


@frappe.whitelist()
@require_onboarding_chat
def chat_create_conversation(contact_identifier):
    data = _cw_req("POST", "/contacts/" + contact_identifier + "/conversations")
    if isinstance(data, dict) and data.get("id"):
        aname = _get_associate_name()
        _set_onechat_session(aname, source_id=contact_identifier, conversation_id=data.get("id"))
    return data


@frappe.whitelist()
@require_onboarding_chat
def chat_get_conversations(contact_identifier):
    data = _cw_req("GET", "/contacts/" + contact_identifier + "/conversations")
    conversations = data.get("payload") if isinstance(data, dict) else data
    if isinstance(conversations, list) and conversations:
        latest = sorted(
            [c for c in conversations if c.get("id")],
            key=lambda c: c.get("last_activity_at") or c.get("updated_at") or c.get("created_at") or c.get("id") or 0,
            reverse=True,
        )[0]
        aname = _get_associate_name()
        _set_onechat_session(aname, source_id=contact_identifier, conversation_id=latest.get("id"))
    return data


@frappe.whitelist()
@require_onboarding_chat
def chat_remember_session(contact_identifier, conversation_id=None):
    """Persist an existing Chatwoot public contact from the device localStorage."""
    if not contact_identifier:
        frappe.throw(_("Missing contact identifier"), frappe.ValidationError)

    data = _cw_req("GET", "/contacts/" + contact_identifier + "/conversations")
    if isinstance(data, dict) and data.get("error"):
        frappe.throw(_("OneChat contact not found"), frappe.ValidationError)

    conversations = data.get("payload") if isinstance(data, dict) else data
    latest_id = conversation_id
    if isinstance(conversations, list) and conversations:
        latest = sorted(
            [c for c in conversations if c.get("id")],
            key=lambda c: c.get("last_activity_at") or c.get("updated_at") or c.get("created_at") or c.get("id") or 0,
            reverse=True,
        )[0]
        latest_id = latest.get("id") or latest_id

    aname = _get_associate_name()
    _set_onechat_session(aname, source_id=contact_identifier, conversation_id=latest_id)
    return {"source_id": contact_identifier, "conversation_id": latest_id or ""}


@frappe.whitelist()
@require_onboarding_chat
def chat_send_message(contact_identifier, conversation_id, content):
    path = "/contacts/" + contact_identifier + "/conversations/" + str(conversation_id) + "/messages"
    return _cw_req("POST", path, {"content": content})


@frappe.whitelist()
@require_onboarding_chat
def chat_get_messages(contact_identifier, conversation_id):
    path = "/contacts/" + contact_identifier + "/conversations/" + str(conversation_id) + "/messages"
    return _cw_req("GET", path)


def _nested_get(data, *paths):
    for path in paths:
        cur = data
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur.get(part)
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return None


def _find_associate_for_onechat_payload(payload):
    email = _nested_get(
        payload,
        "contact.email",
        "conversation.contact_inbox.contact.email",
        "conversation.meta.sender.email",
        "sender.email",
        "meta.sender.email",
    )
    identifier = _nested_get(
        payload,
        "contact.identifier",
        "conversation.contact_inbox.contact.identifier",
        "conversation.meta.sender.identifier",
        "sender.identifier",
        "meta.sender.identifier",
    )

    if email:
        associate = frappe.db.get_value("Associate", {"email": email}, "name")
        if not associate:
            associate = frappe.db.get_value("Associate", {"flex_email": email}, "name")
        if associate:
            return associate

    if identifier:
        associate = frappe.db.get_value("Associate", {"hsid": identifier}, "name")
        if not associate:
            associate = frappe.db.get_value("Associate", identifier, "name")
        if associate:
            return associate

    return None


def _onechat_source_id_from_payload(payload):
    return _nested_get(
        payload,
        "source_id",
        "contact.source_id",
        "contact_inbox.source_id",
        "conversation.contact_inbox.source_id",
        "conversation.meta.sender.source_id",
        "sender.source_id",
        "meta.sender.source_id",
    )


def _onechat_conversation_id_from_payload(payload):
    return _nested_get(
        payload,
        "conversation.id",
        "conversation_id",
        "id",
    )


def _onechat_message_text(payload):
    return (
        _nested_get(payload, "content", "message.content", "conversation.messages.0.content")
        or "New message from OneMotion Support"
    )


def _notify_associate_chat_message(associate_name, message):
    associate = frappe.db.get_value("Associate", associate_name, ["email", "contact_name"], as_dict=True)
    if not associate or not associate.get("email"):
        return

    user = associate.email if frappe.db.exists("User", associate.email) else frappe.db.get_value("User", {"email": associate.email}, "name")
    if not user:
        return

    preview = frappe.utils.strip_html(str(message or ""))[:180] or "New message from OneMotion Support"
    frappe.get_doc({
        "doctype": "PWA Notification",
        "to_user": user,
        "from_user": "Administrator",
        "subject": "New OneChat message",
        "message": preview,
        "reference_document_type": "Associate",
        "reference_document_name": associate_name,
    }).insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def chatwoot_webhook():
    """Receive webhook callbacks from Chatwoot for the API channel.
    Links agent-created/replied OneChat conversations back to Associate Chat."""
    payload = frappe.request.get_json(silent=True) or frappe.form_dict or {}
    try:
        associate_name = _find_associate_for_onechat_payload(payload)
        source_id = _onechat_source_id_from_payload(payload)
        conversation_id = _onechat_conversation_id_from_payload(payload)

        if associate_name and (source_id or conversation_id):
            _set_onechat_session(associate_name, source_id=source_id, conversation_id=conversation_id)

            event = cstr(payload.get("event") or payload.get("event_name") or payload.get("name"))
            message_type = cstr(payload.get("message_type") or _nested_get(payload, "message.message_type"))
            private = payload.get("private") or _nested_get(payload, "message.private")

            # Chatwoot outgoing = agent reply. Notify associate and make /chat
            # open the persisted conversation.
            if event in ("message_created", "message_updated", "") and message_type in ("outgoing", "1", "") and not private:
                _notify_associate_chat_message(associate_name, _onechat_message_text(payload))

        elif not associate_name:
            frappe.log_error(
                "Could not match OneChat webhook to Associate. Keys: " + ", ".join(sorted(payload.keys())[:30]),
                "OneChat Webhook Match",
            )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "OneChat Webhook Error")

    return "ok"


# ─── Web Push Notification APIs ──────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_vapid_public_key():
    """Return the VAPID public key for push notification subscription."""
    return frappe.conf.get("vapid_public_key", "")


@frappe.whitelist()
def save_push_subscription(endpoint, p256dh, auth, browser="", device=""):
    """Save or update a Web Push subscription for the current user."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    # Check if subscription with this endpoint already exists
    existing = frappe.db.get_value(
        "Web Push Subscription",
        {"endpoint": endpoint},
        "name",
    )

    if existing:
        # Update existing subscription
        frappe.db.set_value("Web Push Subscription", existing, {
            "user": user,
            "p256dh_key": p256dh,
            "auth_key": auth,
            "browser": browser,
            "device": device,
        })
    else:
        # Create new subscription
        doc = frappe.get_doc({
            "doctype": "Web Push Subscription",
            "user": user,
            "endpoint": endpoint,
            "p256dh_key": p256dh,
            "auth_key": auth,
            "browser": browser or "",
            "device": device or "",
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return "ok"


@frappe.whitelist()
def remove_push_subscription(endpoint):
    """Remove a Web Push subscription."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    subs = frappe.get_all(
        "Web Push Subscription",
        filters={"endpoint": endpoint, "user": user},
        pluck="name",
    )
    for name in subs:
        frappe.delete_doc("Web Push Subscription", name, ignore_permissions=True)

    frappe.db.commit()
    return "ok"


@frappe.whitelist()
def save_fcm_token(fcm_token):
    """Save or update an FCM (Firebase Cloud Messaging) token for the current user.
    Called from the Flutter WebView app to register for push notifications."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    if not fcm_token:
        frappe.throw(_("FCM token is required"))

    # Check if this token already exists
    existing = frappe.db.get_value(
        "Web Push Subscription",
        {"endpoint": f"fcm://{fcm_token}"},
        "name",
    )

    if existing:
        # Update existing — just refresh the user link
        frappe.db.set_value("Web Push Subscription", existing, {
            "user": user,
            "browser": "Flutter App",
            "device": "mobile",
        })
    else:
        # Remove any old FCM subscriptions for this user
        old_fcm = frappe.get_all(
            "Web Push Subscription",
            filters={"user": user, "browser": "Flutter App"},
            pluck="name",
        )
        for name in old_fcm:
            frappe.delete_doc("Web Push Subscription", name, ignore_permissions=True)

        # Create new subscription using FCM token
        doc = frappe.get_doc({
            "doctype": "Web Push Subscription",
            "user": user,
            "endpoint": f"fcm://{fcm_token}",
            "p256dh_key": "",
            "auth_key": "",
            "browser": "Flutter App",
            "device": "mobile",
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return "ok"


def send_web_push_to_user(user_email, title, body, url=None, icon=None):
    """Send push notification to all subscriptions of a user.
    Handles both Web Push (browser/PWA) and FCM (Flutter app) subscriptions."""
    import re as re_mod
    try:
        from pywebpush import webpush, WebPushException
        import json

        # Strip HTML tags from body for push display
        clean_body = re_mod.sub(r'<[^>]+>', '', body) if body else ""

        # pywebpush works best with the raw base64url private key
        vapid_private_key = frappe.conf.get("vapid_private_key_raw", "") or frappe.conf.get("vapid_private_key_pem", "")
        vapid_claims_email = frappe.conf.get("vapid_claim_email", "mailto:admin@onemotion.uk")

        subscriptions = frappe.get_all(
            "Web Push Subscription",
            filters={"user": user_email},
            fields=["endpoint", "p256dh_key", "auth_key", "name"],
        )

        if not subscriptions:
            return

        payload = json.dumps({
            "title": title or "🔔 Update",
            "body": clean_body,
            "url": url or "/associate",
            "icon": icon or "/files/app-icon-192.png",
        })

        for sub in subscriptions:
            endpoint = sub["endpoint"] or ""

            # ── FCM subscription (Flutter app) ──
            if endpoint.startswith("fcm://"):
                fcm_token = endpoint.replace("fcm://", "")
                _send_fcm_notification(fcm_token, title or "🔔 Update", clean_body, url, sub["name"])
                continue

            # ── Web Push subscription (browser/PWA) ──
            if not vapid_private_key:
                frappe.log_error("Web Push: No VAPID private key configured")
                continue

            subscription_info = {
                "endpoint": endpoint,
                "keys": {
                    "p256dh": sub["p256dh_key"],
                    "auth": sub["auth_key"],
                },
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims={"sub": vapid_claims_email},
                    ttl=86400,
                )
            except WebPushException as e:
                error_msg = str(e)
                if "410" in error_msg or "404" in error_msg:
                    frappe.delete_doc(
                        "Web Push Subscription", sub["name"],
                        ignore_permissions=True,
                    )
                else:
                    frappe.log_error(
                        f"Web Push failed for {user_email}: {error_msg}",
                        "Web Push Error",
                    )
            except Exception as e:
                frappe.log_error(
                    f"Web Push unexpected error for {user_email}: {str(e)}",
                    "Web Push Error",
                )

    except ImportError:
        frappe.log_error("pywebpush not installed", "Web Push Error")
    except Exception as e:
        frappe.log_error(f"Web Push general error: {str(e)}", "Web Push Error")


def _send_fcm_notification(fcm_token, title, body, url=None, sub_name=None):
    """Send a push notification via Firebase Cloud Messaging HTTP v1 API.
    Uses a service account JSON file for authentication (new method, legacy keys deprecated)."""
    import json
    import requests
    import time
    import os

    try:
        # ── Get service account credentials path from site config ──
        sa_path = frappe.conf.get("fcm_service_account", "")
        if not sa_path:
            # Try default location
            bench_path = frappe.utils.get_bench_path()
            default_path = os.path.join(bench_path, "fcm-service-account.json")
            if os.path.exists(default_path):
                sa_path = default_path
            else:
                frappe.log_error(
                    "FCM: No service account configured. "
                    "Set 'fcm_service_account' in site_config.json or place "
                    "fcm-service-account.json in the bench root.",
                    "FCM Error",
                )
                return

        # ── Load service account JSON ──
        with open(sa_path, "r") as f:
            sa_info = json.load(f)

        project_id = sa_info.get("project_id", "")
        if not project_id:
            frappe.log_error("FCM: project_id not found in service account JSON", "FCM Error")
            return

        # ── Get OAuth2 access token using JWT ──
        access_token = _get_fcm_access_token(sa_info)
        if not access_token:
            return

        # ── Send via FCM HTTP v1 API ──
        fcm_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        badge_count = 0
        if sub_name:
            sub_user = frappe.db.get_value("Web Push Subscription", sub_name, "user")
            badge_count = _get_unread_notifications_count_for_user(sub_user)

        message = {
            "message": {
                "token": fcm_token,
                "notification": {
                    "title": title or "🔔 Update",
                    "body": body or "",
                },
                "data": {
                    "url": url or "/associate",
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "badge": str(badge_count),
                },
                "android": {
                    "notification": {
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "icon": "ic_notification",
                        "color": "#a61d1d",
                    },
                },
                "apns": {
                    "payload": {
                        "aps": {
                            "alert": {
                                "title": title or "🔔 Update",
                                "body": body or "",
                            },
                            "sound": "default",
                            "badge": badge_count,
                        },
                    },
                },
            }
        }

        response = requests.post(
            fcm_url,
            headers=headers,
            data=json.dumps(message),
            timeout=10,
        )

        if response.status_code == 200:
            return  # Success

        # Handle errors
        error_data = response.json()
        error_status = error_data.get("error", {}).get("status", "")
        error_code = error_data.get("error", {}).get("code", 0)
        error_msg = error_data.get("error", {}).get("message", "")

        # Token no longer valid — remove subscription
        if error_status in ("NOT_FOUND", "UNREGISTERED") or error_code == 404:
            if sub_name:
                frappe.delete_doc(
                    "Web Push Subscription", sub_name,
                    ignore_permissions=True,
                )
        else:
            frappe.log_error(
                f"FCM v1 send failed ({error_status}): {error_msg}",
                "FCM Error",
            )

    except Exception as e:
        frappe.log_error(f"FCM error: {str(e)}", "FCM Error")


def _get_fcm_access_token(sa_info):
    """Get an OAuth2 access token from a Google service account for FCM.
    Uses JWT to request a short-lived access token."""
    import json
    import time
    import base64
    import hashlib
    import requests

    try:
        import jwt as pyjwt
    except ImportError:
        # Fallback: use manual JWT construction with cryptography
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            from cryptography.hazmat.backends import default_backend
            pyjwt = None
        except ImportError:
            frappe.log_error(
                "FCM: Neither PyJWT nor cryptography is installed. "
                "Run: pip install PyJWT cryptography",
                "FCM Error",
            )
            return None

    try:
        now = int(time.time())
        client_email = sa_info["client_email"]
        private_key = sa_info["private_key"]
        token_uri = sa_info.get("token_uri", "https://oauth2.googleapis.com/token")

        # JWT payload
        claims = {
            "iss": client_email,
            "sub": client_email,
            "aud": token_uri,
            "iat": now,
            "exp": now + 3600,
            "scope": "https://www.googleapis.com/auth/firebase.messaging",
        }

        if pyjwt:
            # Use PyJWT library
            signed_jwt = pyjwt.encode(claims, private_key, algorithm="RS256")
        else:
            # Manual JWT with cryptography
            header = base64.urlsafe_b64encode(
                json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
            ).rstrip(b"=")
            payload_b64 = base64.urlsafe_b64encode(
                json.dumps(claims).encode()
            ).rstrip(b"=")
            signing_input = header + b"." + payload_b64

            key = serialization.load_pem_private_key(
                private_key.encode(), password=None, backend=default_backend()
            )
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            signature = key.sign(
                signing_input,
                asym_padding.PKCS1v15(),
                hashes.SHA256(),
            )
            sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")
            signed_jwt = (signing_input + b"." + sig_b64).decode()

        # Exchange JWT for access token
        response = requests.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
            timeout=10,
        )

        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            frappe.log_error(
                f"FCM OAuth token error ({response.status_code}): {response.text}",
                "FCM Error",
            )
            return None

    except Exception as e:
        frappe.log_error(f"FCM token generation error: {str(e)}", "FCM Error")
        return None


@frappe.whitelist()
def send_test_push_notification():
    """Send a test push notification to the current user."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login"), frappe.AuthenticationError)

    send_web_push_to_user(
        user_email=user,
        title="",
        body="Push notifications are working! 🎉",
        url="/associate",
    )
    return "ok"


# ─── PWA Notification Hook ───────────────────────────────────────────────

def on_pwa_notification_insert(doc, method):
    """Hook called after a PWA Notification is created.
    Sends a web push notification to the target user."""
    try:
        to_user = doc.get("to_user")
        message = doc.get("message") or ""
        subject = doc.get("subject") or ""
        ref_type = doc.get("reference_document_type") or ""
        ref_name = doc.get("reference_document_name") or ""

        # Build URL based on reference
        url = "/associate"
        if (subject or "").lower().startswith("new onechat"):
            url = "/associate/chat"
        if ref_type and ref_name:
            url = url if url == "/associate/chat" else "/associate/notifications"

        frappe.enqueue(
            "onemotion.api.associate_portal.send_web_push_to_user",
            user_email=to_user,
            title=subject,
            body=message,
            url=url,
            queue="short",
            timeout=30,
        )
    except Exception as e:
        frappe.log_error(f"Push notification hook error: {str(e)}", "Web Push Hook Error")
