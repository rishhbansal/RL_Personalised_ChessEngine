import axios from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:8001/api",
    headers: {
        "Content-Type": "application/json",
    },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const demoUser = localStorage.getItem("demo_user");
  if (demoUser) {
    try {
      const parsed = JSON.parse(demoUser);
      config.headers["X-Demo-User"] = parsed.id || parsed.email;
    } catch {
      // ignore malformed value
    }
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
    }
    return Promise.reject(error);
  }
);

export default api;