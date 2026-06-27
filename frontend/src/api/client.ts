import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const stored = localStorage.getItem("mailsense-auth");
  if (stored) {
    const { state } = JSON.parse(stored);
    if (state?.token) {
      config.headers.Authorization = `Token ${state.token}`;
    }
  }
  return config;
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("mailsense-auth");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default client;
