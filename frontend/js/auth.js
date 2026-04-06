const API_URL = (
    window.API_URL ||
    localStorage.getItem("API_URL") ||
    "https://rindhuja-intelligent-doc-api.hf.space"
).replace(/\/$/, "")

async function login() {

    const username = document.getElementById("username").value
    const password = document.getElementById("password").value

    document.getElementById("error").innerText = ""

    const res = await fetch(API_URL + "/login", {

        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            username: username,
            password: password
        })

    })

    const data = await res.json()

    if (res.ok && data.access_token) {

        localStorage.setItem("token", data.access_token)
        localStorage.setItem("role", data.role)
        localStorage.setItem("username", username)
        localStorage.setItem("loginTime", new Date().toISOString())

        window.location = "search.html"

    } else {

        document.getElementById("error").innerText = data.detail || "Login failed"

    }

}

document.getElementById("password")?.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        login()
    }
})