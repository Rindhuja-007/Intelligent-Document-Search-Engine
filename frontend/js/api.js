const API_URL = (
	window.API_URL ||
	localStorage.getItem("API_URL") ||
	"https://rindhuja-intelligent-doc-api.hf.space"
).replace(/\/$/, "")

const token = localStorage.getItem("token")

const role = localStorage.getItem("role")

const username = localStorage.getItem("username") || "Admin"

const loginTime = localStorage.getItem("loginTime")

const HISTORY_KEY = "ids_search_history"

const DOC_COUNTER_KEY = "ids_document_counter"
let isUploading = false

if (!token) {
	window.location = "index.html"
}

if (role !== "admin") {
	window.location = "search.html"
}

document.addEventListener("DOMContentLoaded", initializeAdminDashboard)

function initializeAdminDashboard() {
	bindAdminEvents()
	renderAdminSession()
	renderAdminSidebarHistory()
	renderAdminTopDocs()
	loadDocuments()
	loadStats()
	loadAnalytics()
	loadUsers()
}

function bindAdminEvents() {
	document.getElementById("adminLogoutButton")?.addEventListener("click", logout)
	document.getElementById("adminProfileButton")?.addEventListener("click", openAdminProfile)
	document.getElementById("closeAdminProfile")?.addEventListener("click", closeAdminProfile)
	document.getElementById("adminProfileOverlay")?.addEventListener("click", closeAdminProfile)
}

function logout() {
	localStorage.removeItem("token")
	localStorage.removeItem("role")
	localStorage.removeItem("username")
	localStorage.removeItem("loginTime")
	window.location = "index.html"
}

function openAdminProfile() {
	document.body.classList.add("drawer-open")
}

function closeAdminProfile() {
	document.body.classList.remove("drawer-open")
}

function getSearchHistory() {
	try {
		return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []
	} catch {
		return []
	}
}

function getDocCounters() {
	try {
		return JSON.parse(localStorage.getItem(DOC_COUNTER_KEY)) || {}
	} catch {
		return {}
	}
}

function renderAdminSession() {
	document.getElementById("adminProfileAvatar").textContent = (username[0] || "A").toUpperCase()
	document.getElementById("adminProfileName").textContent = username
	document.getElementById("adminProfileRole").textContent = "Administrator"

	const history = getSearchHistory()
	const counters = getDocCounters()
	const details = document.getElementById("adminProfileDetails")

	details.innerHTML = `
	<div class="profile-card">
		<div class="profile-summary">
			<div>
				<strong>${escapeHtml(username)}</strong>
				<div class="profile-meta">Administrator</div>
			</div>
			<span class="profile-avatar">${(username[0] || "A").toUpperCase()}</span>
		</div>
		<div class="profile-badges">
			<span class="profile-badge">Role in company: Admin</span>
			<span class="profile-badge">Search records: ${history.length}</span>
			<span class="profile-badge">Tracked docs: ${Object.keys(counters).length}</span>
		</div>
	</div>
	<div class="profile-card">
		<strong>Admin details</strong>
		<div class="profile-meta">Name: ${escapeHtml(username)}</div>
		<div class="profile-meta">Session started: ${escapeHtml(formatDateTime(loginTime))}</div>
		<div class="profile-meta">Document uploading: enabled</div>
		<div class="profile-meta">Analytics access: enabled</div>
		<div class="profile-meta">Every user details: available in dashboard</div>
		<div class="profile-meta">Admin related controls: active</div>
	</div>`
}

function renderAdminSidebarHistory() {
	const history = getSearchHistory()
	const list = document.getElementById("adminHistoryList")
	document.getElementById("adminHistoryCount").textContent = history.length

	if (!history.length) {
		list.innerHTML = '<div class="empty-state">Search activity from the assistant view appears here.</div>'
		return
	}

	list.innerHTML = history.slice(0, 8).map(item => `
<div class="sidebar-item">
	<strong>${escapeHtml(item.question)}</strong>
	<small>${escapeHtml(formatDateTime(item.timestamp))}</small>
	<small>${(item.sources || []).length} sources</small>
</div>`).join("")
}

function renderAdminTopDocs() {
	const counters = Object.entries(getDocCounters()).sort((a, b) => b[1] - a[1]).slice(0, 8)
	const list = document.getElementById("adminTopDocsList")

	if (!counters.length) {
		list.innerHTML = '<div class="empty-state">Document popularity updates after search activity.</div>'
		return
	}

	list.innerHTML = counters.map(([name, count]) => `
<div class="sidebar-item">
	<strong>${escapeHtml(name)}</strong>
	<small>${count} references</small>
</div>`).join("")
}

async function uploadFile() {
	if (isUploading) return

	const fileInput = document.getElementById("fileInput")
	const uploadButton = document.querySelector(".upload-box .primary-btn")
	const selectedFile = fileInput.files[0]

	if (!selectedFile) {
		document.getElementById("uploadStatus").innerText = "Select a file before uploading."
		return
	}

	const maxUploadMb = 15
	if (selectedFile.size > maxUploadMb * 1024 * 1024) {
		document.getElementById("uploadStatus").innerText = `File too large. Please upload a file below ${maxUploadMb} MB.`
		return
	}

	isUploading = true
	if (uploadButton) {
		uploadButton.disabled = true
		uploadButton.innerText = "Uploading..."
	}

	const formData = new FormData()

	formData.append("file", selectedFile)

	document.getElementById("uploadStatus").innerText = "Uploading document..."

	try {
		const res = await fetch(API_URL + "/upload", {

			method: "POST",

			headers: {
				Authorization: "Bearer " + token
			},

			body: formData

		})

		const raw = await res.text()
		let data = {}
		try {
			data = raw ? JSON.parse(raw) : {}
		} catch {
			data = { detail: raw || "Upload failed" }
		}

		document.getElementById("uploadStatus").innerText = data.message || data.detail || "Upload finished"

		if (res.ok) {
			fileInput.value = ""
			loadDocuments()
			loadStats()
		} else if (!data.message && !data.detail) {
			document.getElementById("uploadStatus").innerText = `Upload failed (HTTP ${res.status}).`
		}
	} catch {
		document.getElementById("uploadStatus").innerText = "Upload failed. Please retry."
	} finally {
		isUploading = false
		if (uploadButton) {
			uploadButton.disabled = false
			uploadButton.innerText = "Upload Document"
		}
	}

}

async function loadDocuments() {

	const res = await fetch(API_URL + "/documents", {

		headers: {
			Authorization: "Bearer " + token
		}

	})

	const docs = await res.json()

	const container = document.getElementById("documents")

	document.getElementById("adminDocumentsCount").textContent = Array.isArray(docs) ? docs.length : 0

	if (!Array.isArray(docs) || !docs.length) {
		container.innerHTML = '<div class="empty-state">No uploaded documents found.</div>'
		document.getElementById("adminSidebarDocuments").innerHTML = '<div class="empty-state">No uploaded documents found.</div>'
		return
	}

	container.innerHTML = docs.map(doc => `
<div class="table-item">
	<div class="table-item-content">
		<strong>${escapeHtml(doc.filename)}</strong>
		<span class="table-meta">Uploaded by ${escapeHtml(doc.uploaded_by || "admin")}</span>
		<span class="table-meta">${escapeHtml(doc.uploaded_at || "Recently uploaded")}</span>
	</div>
	<button class="danger-btn" onclick="deleteDoc(${doc.id})">Delete</button>
</div>`).join("")

	document.getElementById("adminSidebarDocuments").innerHTML = docs.slice(0, 8).map(doc => `
<div class="sidebar-item">
	<strong>${escapeHtml(doc.filename)}</strong>
	<small>Uploaded by ${escapeHtml(doc.uploaded_by || "admin")}</small>
</div>`).join("")

}

async function deleteDoc(id) {

	await fetch(API_URL + "/documents/" + id, {

		method: "DELETE",

		headers: {
			Authorization: "Bearer " + token
		}

	})

	loadDocuments()
	loadStats()
}


async function loadStats() {

	const res = await fetch(API_URL + "/admin/stats", {

		headers: {
			Authorization: "Bearer " + token
		}

	})

	const data = await res.json()

	document.getElementById("statDocuments").textContent = data.documents ?? 0
	document.getElementById("statChunks").textContent = data.chunks ?? 0
	document.getElementById("statUsers").textContent = data.users ?? 0
	document.getElementById("statQueries").textContent = data.queries ?? 0
}

async function loadAnalytics() {

	const res = await fetch(API_URL + "/admin/analytics", {

		headers: {
			Authorization: "Bearer " + token
		}

	})

	const data = await res.json()

	document.getElementById("analytics").innerHTML = `
<div class="analytics-block">
	<p class="analytics-kicker">Total queries</p>
	<h4>${data.total_queries ?? 0}</h4>
</div>
<div class="analytics-block">
	<p class="analytics-kicker">Top questions</p>
	${(data.top_questions || []).length ? data.top_questions.map(item => `
		<div class="analytics-list-item">
			<span>${escapeHtml(item.question)}</span>
			<strong>${item.count}</strong>
		</div>`).join("") : '<div class="empty-state">No query analytics yet.</div>'}
</div>
<div class="analytics-block">
	<p class="analytics-kicker">Most active users</p>
	${(data.active_users || []).length ? data.active_users.map(item => `
		<div class="analytics-list-item">
			<span>${escapeHtml(item.username)}</span>
			<strong>${item.count}</strong>
		</div>`).join("") : '<div class="empty-state">No user activity yet.</div>'}
</div>`

	renderAdminSession()

}

async function loadUsers() {

	const res = await fetch(API_URL + "/admin/users", {

		headers: {
			Authorization: "Bearer " + token
		}

	})

	const data = await res.json()
	const users = Array.isArray(data.users) ? data.users : []

	document.getElementById("usersPanel").innerHTML = users.length ? users.map(user => `
<div class="table-item">
	<div class="table-item-content">
		<strong>${escapeHtml(user[1])}</strong>
		<span class="table-meta">User ID: ${escapeHtml(user[0])}</span>
		<span class="table-meta">Role: ${escapeHtml(user[2])}</span>
	</div>
	<span class="pill">${escapeHtml(user[2])}</span>
</div>`).join("") : '<div class="empty-state">No user records available.</div>'

	renderAdminSession()
}

function escapeHtml(value) {
	return String(value ?? "")
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;")
		.replaceAll('"', "&quot;")
		.replaceAll("'", "&#39;")
}

function formatDateTime(value) {
	if (!value) return "Active session"
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return String(value)
	return date.toLocaleString()
}