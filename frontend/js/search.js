const API_URL = "https://ai-doc-assistant-api.onrender.com"

const token = localStorage.getItem("token")

const role = localStorage.getItem("role")

const username = localStorage.getItem("username") || "Workspace User"

const loginTime = localStorage.getItem("loginTime")

const HISTORY_KEY = "ids_search_history"

const DOC_COUNTER_KEY = "ids_document_counter"

const ADMIN_DOCS_KEY = "ids_admin_documents"

if(!token){
window.location = "index.html"
}

if(role === "admin"){
document.getElementById("adminBtn").style.display="block"
}

document.addEventListener("DOMContentLoaded", initializeSearchPage)

function goAdmin(){
window.location="admin.html"
}

function initializeSearchPage(){
bindShellEvents()
renderSessionHeader()
renderProfilePanel()
renderHistory()
restoreConversationFromHistory()
renderTopDocs()
renderSidebarDocuments(getStoredAdminDocuments())
updateOverviewStats()
hydrateWelcomeMessage()

if(role === "admin"){
loadAdminDocumentsForSidebar()
}
}

function bindShellEvents(){
document.getElementById("profileButton")?.addEventListener("click", openProfileDrawer)
document.getElementById("closeProfile")?.addEventListener("click", closeProfileDrawer)
document.getElementById("profileOverlay")?.addEventListener("click", closeProfileDrawer)
document.getElementById("logoutButton")?.addEventListener("click", logout)
}

function hydrateWelcomeMessage(){
const greeting = role === "admin" ? "Monitor search performance and test knowledge retrieval." : "Find answers across your team knowledge base."
document.getElementById("welcomeTitle").textContent = greeting
}

function renderSessionHeader(){
const initials = (username[0] || "U").toUpperCase()
document.getElementById("profileAvatar").textContent = initials
document.getElementById("profileName").textContent = username
document.getElementById("profileRole").textContent = role === "admin" ? "Administrator" : "Company User"
document.getElementById("pageTitle").textContent = role === "admin" ? "Knowledge workspace + admin access" : "Knowledge search assistant"
}

function openProfileDrawer(){
document.body.classList.add("drawer-open")
}

function closeProfileDrawer(){
document.body.classList.remove("drawer-open")
}

function logout(){
localStorage.removeItem("token")
localStorage.removeItem("role")
localStorage.removeItem("username")
localStorage.removeItem("loginTime")
window.location = "index.html"
}

function getSearchHistory(){
try{
return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []
}catch{
return []
}
}

function saveSearchHistory(history){
localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 12)))
}

function getDocCounters(){
try{
return JSON.parse(localStorage.getItem(DOC_COUNTER_KEY)) || {}
}catch{
return {}
}
}

function saveDocCounters(counters){
localStorage.setItem(DOC_COUNTER_KEY, JSON.stringify(counters))
}

function getStoredAdminDocuments(){
try{
return JSON.parse(localStorage.getItem(ADMIN_DOCS_KEY)) || []
}catch{
return []
}
}

function saveStoredAdminDocuments(documents){
localStorage.setItem(ADMIN_DOCS_KEY, JSON.stringify(documents))
}

function addToHistory(question, answer, sources){
const history = getSearchHistory()
history.unshift({
question,
answer,
sources,
timestamp:new Date().toISOString()
})
saveSearchHistory(history)
}

function normalizeSourceName(source){
if(!source) return null
if(typeof source === "string") return source.trim()
if(source.filename) return String(source.filename).trim()
if(source.source) return String(source.source).trim()
return String(source).trim()
}

function updateDocCounters(sources){
if(!Array.isArray(sources)) return

const counters = getDocCounters()

sources.forEach(source => {
const name = normalizeSourceName(source)
if(!name) return
if(!counters[name]) counters[name] = 0
counters[name] += 1
})

saveDocCounters(counters)
}

function renderHistory(){
const history = getSearchHistory()
const target = document.getElementById("historyList")
const count = document.getElementById("historyCount")

count.textContent = history.length

if(!history.length){
target.innerHTML = '<div class="empty-state">Search history will appear here.</div>'
return
}

target.innerHTML = history.map(item => `
<div class="sidebar-item">
	<strong>${escapeHtml(item.question)}</strong>
	<small>${formatDateTime(item.timestamp)}</small>
	<small>${(item.sources || []).length} source${(item.sources || []).length === 1 ? "" : "s"}</small>
</div>`).join("")
}

function renderTopDocs(){
const counters = getDocCounters()
const entries = Object.entries(counters).sort((a,b) => b[1] - a[1]).slice(0, 6)
const target = document.getElementById("topDocsList")
const trackedDocs = document.getElementById("trackedDocs")

trackedDocs.textContent = String(Object.keys(counters).length)

if(!entries.length){
target.innerHTML = '<div class="empty-state">Top document activity will update after searches.</div>'
return
}

target.innerHTML = entries.map(([name, count]) => `
<div class="sidebar-item">
	<strong>${escapeHtml(name)}</strong>
	<small>${count} match${count === 1 ? "" : "es"}</small>
</div>`).join("")
}

function renderSidebarDocuments(documents){
const target = document.getElementById("sidebarDocuments")
const count = document.getElementById("documentsCount")
const uniqueDocs = Array.isArray(documents) ? documents : []

count.textContent = uniqueDocs.length

if(!uniqueDocs.length){
target.innerHTML = '<div class="empty-state">Relevant document names will appear here as you search.</div>'
return
}

target.innerHTML = uniqueDocs.slice(0, 8).map(doc => {
const name = typeof doc === "string" ? doc : doc.filename
const meta = typeof doc === "string" ? "Referenced in search results" : `Uploaded by ${doc.uploaded_by || "admin"}`
return `
<div class="sidebar-item">
	<strong>${escapeHtml(name)}</strong>
	<small>${escapeHtml(meta)}</small>
</div>`
}).join("")
}

async function loadAdminDocumentsForSidebar(){
try{
const res = await fetch(API_URL + "/documents", {
headers:{ Authorization:"Bearer " + token }
})

if(!res.ok) return

const documents = await res.json()
saveStoredAdminDocuments(documents)
renderSidebarDocuments(documents)
}catch{
renderSidebarDocuments(getStoredAdminDocuments())
}
}

function updateOverviewStats(){
const history = getSearchHistory()
document.getElementById("totalSearches").textContent = String(history.length)
document.getElementById("lastActivity").textContent = history.length ? formatRelativeTime(history[0].timestamp) : "No searches yet"
}

function renderProfilePanel(){
const history = getSearchHistory()
const counters = getDocCounters()
const details = document.getElementById("profileDetails")
const sessionStarted = loginTime ? formatDateTime(loginTime) : "Active session"

const sharedCards = `
	<div class="profile-card">
		<div class="profile-summary">
			<div>
				<strong>${escapeHtml(username)}</strong>
				<div class="profile-meta">${role === "admin" ? "Administrator" : "Company User"}</div>
			</div>
			<span class="profile-avatar">${(username[0] || "U").toUpperCase()}</span>
		</div>
		<div class="profile-badges">
			<span class="profile-badge">Role: ${escapeHtml(role)}</span>
			<span class="profile-badge">Session started: ${escapeHtml(sessionStarted)}</span>
			<span class="profile-badge">Searches: ${history.length}</span>
		</div>
	</div>
	<div class="profile-card">
		<strong>Basic details</strong>
		<div class="profile-meta">Name: ${escapeHtml(username)}</div>
		<div class="profile-meta">Role in company: ${role === "admin" ? "Admin" : "User"}</div>
		<div class="profile-meta">Access level: ${role === "admin" ? "Full admin controls" : "AI search workspace"}</div>
		<div class="profile-meta">Tracked documents: ${Object.keys(counters).length}</div>
	</div>`

const adminExtras = role === "admin"
? `
	<div class="profile-card">
		<strong>Admin controls</strong>
		<div class="profile-meta">Document upload: enabled</div>
		<div class="profile-meta">Analytics access: enabled</div>
		<div class="profile-meta">User directory visibility: enabled</div>
		<div class="quick-actions">
			<button class="ghost-btn small" type="button" onclick="goAdmin()">Open Admin Dashboard</button>
		</div>
	</div>`
: `
	<div class="profile-card">
		<strong>User workspace</strong>
		<div class="profile-meta">Use the assistant to search indexed documents.</div>
		<div class="profile-meta">History and most searched docs update from your current activity.</div>
	</div>`

details.innerHTML = sharedCards + adminExtras
}

function escapeHtml(value){
return String(value ?? "")
.replaceAll("&", "&amp;")
.replaceAll("<", "&lt;")
.replaceAll(">", "&gt;")
.replaceAll('"', "&quot;")
.replaceAll("'", "&#39;")
}

function formatDateTime(value){
const date = new Date(value)
if(Number.isNaN(date.getTime())) return "Unknown"
return date.toLocaleString()
}

function formatRelativeTime(value){
const date = new Date(value)
if(Number.isNaN(date.getTime())) return "Recent"

const diffMinutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60000))
if(diffMinutes < 60) return `${diffMinutes} min ago`

const diffHours = Math.round(diffMinutes / 60)
if(diffHours < 24) return `${diffHours} hr ago`

const diffDays = Math.round(diffHours / 24)
return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`
}

async function askQuestion(event){

if(event){
event.preventDefault()
}

const input = document.getElementById("questionInput")
const question = input.value.trim()

if(!question) return

const chatBox = document.getElementById("chatBox")

const emptyState = chatBox.querySelector(".empty-chat-state")
if(emptyState){
emptyState.remove()
}

// USER MESSAGE
const userMsg = document.createElement("div")
userMsg.className = "message user-msg"
userMsg.innerHTML = `
<div class="message-header">
	<span>You</span>
	<span>${formatDateTime(new Date().toISOString())}</span>
</div>
<div>${escapeHtml(question)}</div>`
chatBox.appendChild(userMsg)

input.value=""

// loading indicator
document.getElementById("loading").style.display="block"

let answerText = ""
let sources = []

try{
const res = await fetch(API_URL + "/query",{
method:"POST",
headers:{
"Content-Type":"application/json",
Authorization:"Bearer " + token
},
body:JSON.stringify({question})
})

let data = {}

try{
data = await res.json()
}catch{
data = {}
}

if(!res.ok){
answerText = data.detail || data.error || "Request failed. Please try again."
}else if(Array.isArray(data.answer)){
answerText = data.answer.filter(Boolean).join(" ").trim()
}else if(typeof data.answer === "string"){
answerText = data.answer.trim()
}else if(data.error){
answerText = data.error
}

if(!answerText){
answerText = "No answer found."
}

sources = Array.isArray(data.sources) ? data.sources : []
}catch(error){
answerText = "Unable to fetch response from server."
sources = []
}

document.getElementById("loading").style.display="none"

addToHistory(question, answerText, sources)
updateDocCounters(sources)
renderHistory()
renderTopDocs()
renderSidebarDocuments(mergeSourcesIntoSidebar(sources))
updateOverviewStats()
renderProfilePanel()

// AI MESSAGE CONTAINER
const aiMsg = document.createElement("div")
aiMsg.className="message ai-msg"
aiMsg.innerHTML = `
<div class="message-header">
	<span>Assistant</span>
	<span>${role === "admin" ? "Admin view" : "User view"}</span>
</div>
<div class="message-body"></div>`
chatBox.appendChild(aiMsg)

const messageBody = aiMsg.querySelector(".message-body")

// smooth animation
if(window.anime){
anime({
targets: aiMsg,
opacity:[0,1],
translateY:[15,0],
duration:400,
easing:"easeOutQuad"
})
}

messageBody.textContent = String(answerText || "No answer found.")

if(sources.length){
appendMatchMetrics(aiMsg, sources)
appendSources(aiMsg, sources)
}

requestAnimationFrame(() => {
chatBox.scrollTop = chatBox.scrollHeight
})
}

function restoreConversationFromHistory(){
const chatBox = document.getElementById("chatBox")
const history = getSearchHistory()

if(!chatBox || !history.length){
return
}

chatBox.innerHTML = ""

const recent = [...history].reverse().slice(-8)

recent.forEach(item => {
const userMsg = document.createElement("div")
userMsg.className = "message user-msg"
userMsg.innerHTML = `
<div class="message-header">
	<span>You</span>
	<span>${formatDateTime(item.timestamp)}</span>
</div>
<div>${escapeHtml(item.question || "")}</div>`
chatBox.appendChild(userMsg)

const aiMsg = document.createElement("div")
aiMsg.className = "message ai-msg"
aiMsg.innerHTML = `
<div class="message-header">
	<span>Assistant</span>
	<span>${role === "admin" ? "Admin view" : "User view"}</span>
</div>
<div class="message-body">${escapeHtml(item.answer || "No answer found.")}</div>`
chatBox.appendChild(aiMsg)

if(Array.isArray(item.sources) && item.sources.length){
appendMatchMetrics(aiMsg, item.sources)
appendSources(aiMsg, item.sources)
}
})

chatBox.scrollTop = chatBox.scrollHeight
}

function mergeSourcesIntoSidebar(sources){
const adminDocs = getStoredAdminDocuments()
const localDocs = [...new Set(Object.keys(getDocCounters()))]

if(role === "admin" && adminDocs.length){
return adminDocs
}

return [...new Set([
...localDocs,
...sources.map(normalizeSourceName).filter(Boolean)
])]
}

function appendSources(container, sources){
const sourceRows = sources
.map(source => {
const name = normalizeSourceName(source)
if(!name) return null
const percent = parseScorePercent(source)
return { name, percent }
})
.filter(Boolean)

if(!sourceRows.length) return

const wrapper = document.createElement("div")
wrapper.className = "message-sources"
wrapper.innerHTML = `<div class="message-sources-label">Referenced sources</div>`

const chips = document.createElement("div")
chips.className = "source-chip-wrap"

sourceRows.forEach(item => {
const chip = document.createElement("span")
chip.className = "result-source-chip"
const similarity = toSimilarityScore(item.percent)
chip.textContent = item.percent > 0
? `${item.name} • ${item.percent.toFixed(1)}% • sim ${similarity}`
: item.name
chips.appendChild(chip)
})

wrapper.appendChild(chips)
container.appendChild(wrapper)
}

function appendMatchMetrics(container, sources){
const percents = sources
.map(parseScorePercent)
.filter(score => Number.isFinite(score) && score > 0)

if(!percents.length) return

const top = Math.max(...percents)
const avg = percents.reduce((sum, score) => sum + score, 0) / percents.length

const metrics = document.createElement("div")
metrics.className = "match-metrics"
metrics.innerHTML = `
<span class="metric-pill">Top Match: ${top.toFixed(1)}%</span>
<span class="metric-pill">Similarity Score: ${toSimilarityScore(avg)}</span>`

container.appendChild(metrics)
}

function parseScorePercent(source){
if(!source || source.score === undefined || source.score === null){
return 0
}

const raw = Number(source.score)
if(!Number.isFinite(raw)) return 0

if(raw <= 1){
return raw * 100
}

return raw
}

function toSimilarityScore(percent){
return (percent / 100).toFixed(3)
}

document.getElementById("questionInput")
.addEventListener("keydown",function(e){

if(e.key==="Enter"){
e.preventDefault()
askQuestion(e)
}

})