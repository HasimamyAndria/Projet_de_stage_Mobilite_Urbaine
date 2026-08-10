import axios from "axios";

// VITE_API_URL au build (Docker) ; fallback dev local
const baseURL =
    import.meta.env.VITE_API_URL?.toString() || "http://127.0.0.1:8000";

console.log("[API] baseURL =", baseURL);

const api = axios.create({
    baseURL,
});

export default api;
