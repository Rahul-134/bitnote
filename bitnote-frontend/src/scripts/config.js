// Central place to configure the backend API origin.
// Defaults to the local dev backend; override for other environments by
// setting `window.API_BASE` in a <script> tag before this file loads, e.g.:
//   <script>window.API_BASE = "https://api.example.com";</script>
window.API_BASE = window.API_BASE || "http://localhost:8000";

// fetch() wrapper that attaches the logged-in user's session token
// (stored at sessionStorage "token") as an Authorization header.
// Safe to use before login too — it just won't add the header.
window.authFetch = function (url, options = {}) {
    const token = sessionStorage.getItem("token");
    const headers = new Headers(options.headers || {});
    if (token) {
        headers.set("Authorization", "Bearer " + token);
    }
    return fetch(url, { ...options, headers });
};
